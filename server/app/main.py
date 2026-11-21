import hashlib
import ipaddress
import logging
import math
import os
import re
import secrets
import sqlite3
import json
import queue
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

from . import cameras, config, europe, msi, ndw, sky, weather

DATA = os.environ.get("ROADPING_DATA", "/data")
DB_PATH = os.path.join(DATA, "roadping.db")
MIN_CONFIRM = int(os.environ.get("ROADPING_MIN_CONFIRM", "3"))
MIN_GONE = int(os.environ.get("ROADPING_MIN_GONE", "2"))
ONLINE_SECONDS = 180
TRUST_AGE = int(os.environ.get("ROADPING_TRUST_AGE", "900"))
NEAR_WINDOW = int(os.environ.get("ROADPING_NEAR_WINDOW", "900"))
NEAR_KM = 3.0
MOVING_KMH = 15
DRIVE_SYNCS = int(os.environ.get("ROADPING_DRIVE_SYNCS", "5"))
DRIVE_SPAN = int(os.environ.get("ROADPING_DRIVE_SPAN", "600"))
ONLINE_PER_IP = 25
NEARBY_KM = 15.0

POLICE, AMBULANCE, FILE, ACCIDENT, WORKS, OBSTACLE = 1, 2, 3, 4, 5, 6
BBOX = (50.6, 3.2, 53.7, 7.3)

os.makedirs(DATA, exist_ok=True)

def _salt():
    p = os.path.join(DATA, "salt")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(secrets.token_hex(32))
        os.chmod(p, 0o600)
    with open(p) as f:
        return f.read().strip()

SALT = _salt()
DEV_RE = re.compile(r"^[0-9a-f]{16,64}$")

def dev_hash(device: str) -> str:
    if not DEV_RE.match(device or ""):
        raise HTTPException(400, "ongeldig toestel-id")
    return hashlib.sha256((SALT + device).encode()).hexdigest()[:24]

_db_lock = threading.Lock()
_db = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
_db.execute("PRAGMA journal_mode=WAL")
_db.executescript(
    """
CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    bearing REAL NOT NULL,          -- -1 = onbekend
    created REAL NOT NULL,
    expires REAL NOT NULL,
    confirmed REAL,                 -- moment waarop MIN_CONFIRM bereikt werd
    removed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS clusters_live ON clusters(removed, expires);
CREATE TABLE IF NOT EXISTS events (
    cluster INTEGER NOT NULL,
    dev TEXT NOT NULL,
    kind TEXT NOT NULL,             -- report | yes | no
    t REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS events_cluster ON events(cluster);
CREATE TABLE IF NOT EXISTS devices (
    dev TEXT PRIMARY KEY,           -- gehasht toestel-ID
    first_seen REAL NOT NULL,
    moved INTEGER NOT NULL DEFAULT 0, -- ooit >= MOVING_KMH gereden
    last_seen REAL NOT NULL DEFAULT 0
);
"""
)
for _col in ("events ADD COLUMN valid INTEGER NOT NULL DEFAULT 1",
             "events ADD COLUMN iph TEXT",
             "devices ADD COLUMN drive_syncs INTEGER NOT NULL DEFAULT 0",
             "devices ADD COLUMN first_drive REAL",
             "clusters ADD COLUMN place TEXT"):
    try:
        _db.execute("ALTER TABLE " + _col)
    except sqlite3.OperationalError:
        pass
log = logging.getLogger("roadping")
_flow_lock = threading.Lock()

def q(sql, args=()):
    with _db_lock:
        return _db.execute(sql, args).fetchall()

def q1(sql, args=()):
    r = q(sql, args)
    return r[0] if r else None

def dist_m(a_lat, a_lon, b_lat, b_lon):
    r = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))

def angle_diff(a, b):
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d

def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]

_rate = defaultdict(deque)
_rate_lock = threading.Lock()
_rate_swept = [0.0]
RATE_MAX_WINDOW = 900

def limit(key: str, n: int, per_s: int):
    now = time.time()
    with _rate_lock:
        if now - _rate_swept[0] > 60:
            _rate_swept[0] = now
            for k in [k for k, v in _rate.items() if not v or v[-1] < now - RATE_MAX_WINDOW]:
                del _rate[k]
        d = _rate[key]
        while d and d[0] < now - per_s:
            d.popleft()
        if len(d) >= n:
            raise HTTPException(429, "te veel verzoeken, probeer het later")
        d.append(now)

def client_ip(req: Request):
    xff = req.headers.get("x-forwarded-for", "")
    ip = xff.split(",")[-1].strip() if xff else (req.client.host if req.client else "")
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if a.is_private or a.is_loopback or a.is_link_local or a.is_unspecified:
        return None
    return ip

def limit_ip(req: Request, kind: str, n: int, per_s: int):
    ip = client_ip(req)
    if ip is not None:
        limit(kind + "ip:" + ip, n, per_s)

_online = {}
_track = {}
_online_lock = threading.Lock()

def ip_hash(ip):
    return None if ip is None else hashlib.sha256((SALT + "ip:" + ip).encode()).hexdigest()[:16]

def seen_device(dev, now, moving=False):
    q("INSERT INTO devices(dev, first_seen, last_seen) VALUES(?, ?, ?) "
      "ON CONFLICT(dev) DO UPDATE SET last_seen=excluded.last_seen", (dev, now, now))
    if moving:
        q("UPDATE devices SET drive_syncs=drive_syncs+1, first_drive=COALESCE(first_drive, ?), "
          "moved=CASE WHEN drive_syncs+1>=? AND ?-COALESCE(first_drive, ?)>=? THEN 1 ELSE moved END "
          "WHERE dev=?", (now, DRIVE_SYNCS, now, now, DRIVE_SPAN, dev))

def heartbeat(dev, lat, lon, kmh, iph):
    now = time.time()
    rl, ro = round(lat, 2), round(lon, 2)
    with _online_lock:
        _online[dev] = (now, rl, ro, kmh, iph)
        tr = _track.get(dev)
        if tr is None:
            tr = _track[dev] = deque(maxlen=30)
        tr.append((now, rl, ro))
        if len(_online) > 1000 or len(_track) > 1000:
            for k in [k for k, v in _online.items() if v[0] < now - ONLINE_SECONDS]:
                del _online[k]
            for k in [k for k, v in _track.items() if not v or v[-1][0] < now - NEAR_WINDOW]:
                del _track[k]
    seen_device(dev, now, kmh >= MOVING_KMH)

def trusted(dev, lat, lon, now):
    row = q1("SELECT first_seen, moved FROM devices WHERE dev=?", (dev,))
    if row is None or now - row[0] < TRUST_AGE:
        return False, "new"
    if not row[1]:
        return False, "not_driven"
    with _online_lock:
        pts = list(_track.get(dev, ()))
    for t, plat, plon in pts:
        if now - t <= NEAR_WINDOW and dist_m(lat, lon, plat, plon) <= NEAR_KM * 1000 + 800:
            return True, "ok"
    return False, "not_near"

def online_counts(lat=None, lon=None):
    now = time.time()
    total = driving = nearby = 0
    per_ip = defaultdict(int)
    with _online_lock:
        for t, olat, olon, kmh, iph in _online.values():
            if t < now - ONLINE_SECONDS:
                continue
            if iph is not None:
                per_ip[iph] += 1
                if per_ip[iph] > ONLINE_PER_IP:
                    continue
            total += 1
            if kmh >= 15:
                driving += 1
            if lat is not None and dist_m(lat, lon, olat, olon) <= NEARBY_KM * 1000:
                nearby += 1
    return {"online": total, "driving": driving, "nearby": nearby}

def counts(cid):
    rows = q("SELECT dev, kind, t, valid, iph FROM events WHERE cluster=? ORDER BY t", (cid,))
    confirmers, gone = set(), set()
    ip_of = {}
    last_pos = 0.0

    def counts_for(dev, iph):
        if iph is None:
            return True
        devs = ip_of.setdefault(iph, set())
        if dev in devs:
            return True
        if len(devs) >= 2:
            return False
        devs.add(dev)
        return True

    for dev, kind, t, valid, iph in rows:
        if valid and kind in ("report", "yes") and counts_for(dev, iph):
            confirmers.add(dev)
            last_pos = max(last_pos, t)
    for dev, kind, t, valid, iph in rows:
        if valid and kind == "no" and t > last_pos and counts_for(dev, iph):
            gone.add(dev)
    return confirmers, gone, [(d, k, t, v) for d, k, t, v, _ in rows]

def cluster_json(row, dev=None):
    cid, typ, lat, lon, brg, created, expires, confirmed = row[:8]
    place = row[9] if len(row) > 9 else None
    confirmers, gone, rows = counts(cid)
    out = {
        "id": cid,
        "type": typ,
        "label": config.label(DATA, typ),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "bearing": brg,
        "count": len(confirmers),
        "gone": len(gone),
        "created": int(created * 1000),
        "expires": int(expires * 1000),
        "confirmed": confirmed is not None,
        "place": place or "",
    }
    if dev is not None:
        out["mine"] = any(d == dev and k == "report" for d, k, _, _ in rows)
        out["voted"] = any(d == dev and k in ("yes", "no") for d, k, _, _ in rows)
    return out

LIVE_SQL = "SELECT * FROM clusters WHERE removed=0 AND expires>? "

def find_cluster(typ, lat, lon, brg, now):
    rad = config.merge_m(DATA, typ)
    dlat = rad / 111000.0
    dlon = rad / (111000.0 * max(0.2, math.cos(math.radians(lat))))
    rows = q(LIVE_SQL + "AND type=? AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? "
             "AND EXISTS(SELECT 1 FROM events e WHERE e.cluster=clusters.id AND e.valid=1 "
             "AND e.kind='report')",
             (now, typ, lat - dlat, lat + dlat, lon - dlon, lon + dlon))
    best, best_d = None, 1e18
    for r in rows:
        if brg >= 0 and r[4] >= 0 and angle_diff(brg, r[4]) > 60:
            continue
        d = dist_m(lat, lon, r[2], r[3])
        if d <= rad and d < best_d:
            best, best_d = r, d
    return best

def refresh(cid, now):
    row = q1("SELECT * FROM clusters WHERE id=?", (cid,))
    confirmers, gone, _ = counts(cid)
    typ = row[1]
    if len(gone) >= MIN_GONE:
        q("UPDATE clusters SET removed=1 WHERE id=?", (cid,))
        return
    if row[7] is None and len(confirmers) >= MIN_CONFIRM:
        q("UPDATE clusters SET confirmed=? WHERE id=?", (now, cid))
        _geo_q.put(cid)

PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"
_geo_q = queue.Queue()

def _place_for(lat, lon):
    url = PDOK + "?" + urllib.parse.urlencode({
        "lat": "%.6f" % lat, "lon": "%.6f" % lon, "type": "weg", "rows": 1,
        "fl": "straatnaam,woonplaatsnaam,gemeentenaam,afstand"})
    req = urllib.request.Request(url, headers={"User-Agent": "Pardal-server"})
    with urllib.request.urlopen(req, timeout=6) as r:
        docs = json.load(r).get("response", {}).get("docs", [])
    if not docs:
        return ""
    d = docs[0]
    street = d.get("straatnaam") or ""
    town = d.get("woonplaatsnaam") or d.get("gemeentenaam") or ""
    try:
        far = float(d.get("afstand", 0)) > 40
    except (TypeError, ValueError):
        far = False
    if far or not street:
        return ("bij " + town)[:80] if town else ""
    return " · ".join(x for x in (street, town) if x)[:80]

def _geocoder():
    while True:
        cid = _geo_q.get()
        try:
            row = q1("SELECT lat, lon, place FROM clusters WHERE id=?", (cid,))
            if row and not row[2]:
                q("UPDATE clusters SET place=? WHERE id=?", (_place_for(row[0], row[1]), cid))
        except Exception:
            log.exception("plaatsnaam opzoeken mislukt")
        time.sleep(0.3)

app = FastAPI(title="Pardal", docs_url=None, redoc_url=None, openapi_url=None)

def _f(**kw):
    return Field(allow_inf_nan=False, **kw)

class ReportIn(BaseModel):
    device: str = Field(max_length=64)
    type: int = Field(ge=1, le=99)
    lat: float = _f()
    lon: float = _f()
    bearing: float = _f(default=-1)

class VoteIn(BaseModel):
    device: str = Field(max_length=64)
    id: int = Field(ge=1, le=2 ** 63 - 1)
    still: bool

class SyncIn(BaseModel):
    device: str = Field(max_length=64)
    lat: float = _f()
    lon: float = _f()
    kmh: float = _f(default=0)
    radius_km: float = _f(default=30)
    official: bool = False
    official_radius_km: float = _f(default=25)
    official_hash: str = Field(default="", max_length=32)
    official_lines: bool = True
    reports_hash: str = Field(default="", max_length=32)

@app.post("/v1/report")
def report(r: ReportIn, req: Request):
    dev = dev_hash(r.device)
    if not config.reportable(DATA, r.type):
        raise HTTPException(400, "onbekende soort")
    if not config.in_report_area(DATA, r.lat, r.lon):
        raise HTTPException(400, "buiten het gebied")
    limit_ip(req, "rep", 40, 900)
    limit("rep:" + dev, 8, 900)
    with _flow_lock:
        return _report(r, dev, ip_hash(client_ip(req)))

def _report(r: ReportIn, dev, iph):
    now = time.time()
    seen_device(dev, now)
    ok, why = trusted(dev, r.lat, r.lon, now)
    ttl = config.ttl_s(DATA, r.type)
    brg = r.bearing % 360 if r.bearing >= 0 else -1
    row = find_cluster(r.type, r.lat, r.lon, brg, now)
    if row is None:
        with _db_lock:
            cur = _db.execute(
                "INSERT INTO clusters(type,lat,lon,bearing,created,expires) VALUES(?,?,?,?,?,?)",
                (r.type, r.lat, r.lon, brg, now, now + ttl))
            cid = cur.lastrowid
    else:
        cid = row[0]
        confirmers, _, _ = counts(cid)
        if ok and dev not in confirmers:
            n = len(confirmers)
            nlat = (row[2] * n + r.lat) / (n + 1)
            nlon = (row[3] * n + r.lon) / (n + 1)
            nbrg = row[4] if row[4] >= 0 else brg
            q("UPDATE clusters SET lat=?, lon=?, bearing=? WHERE id=?", (nlat, nlon, nbrg, cid))
        if ok:
            q("UPDATE clusters SET expires=MAX(expires, ?) WHERE id=?", (now + ttl, cid))
    q("INSERT INTO events(cluster,dev,kind,t,valid,iph) VALUES(?,?,?,?,?,?)",
      (cid, dev, "report", now, 1 if ok else 0, iph))
    refresh(cid, now)
    out = cluster_json(q1("SELECT * FROM clusters WHERE id=?", (cid,)), dev)
    out["needed"] = MIN_CONFIRM
    out["counted"] = ok
    out["reason"] = why
    return out

@app.post("/v1/vote")
def vote(v: VoteIn, req: Request):
    dev = dev_hash(v.device)
    limit_ip(req, "vote", 200, 900)
    limit("vote:" + dev, 60, 900)
    with _flow_lock:
        return _vote(v, dev, ip_hash(client_ip(req)))

def _vote(v: VoteIn, dev, iph):
    now = time.time()
    row = q1(LIVE_SQL + "AND id=?", (now, v.id))
    if row is None:
        raise HTTPException(404, "melding bestaat niet meer")
    if row[7] is None:
        raise HTTPException(409, "melding is nog niet bevestigd")
    seen_device(dev, now)
    ok, why = trusted(dev, row[2], row[3], now)
    q("DELETE FROM events WHERE cluster=? AND dev=? AND kind IN ('yes','no')", (v.id, dev))
    q("INSERT INTO events(cluster,dev,kind,t,valid,iph) VALUES(?,?,?,?,?,?)",
      (v.id, dev, "yes" if v.still else "no", now, 1 if ok else 0, iph))
    if v.still and ok:
        ttl = config.ttl_s(DATA, row[1])
        q("UPDATE clusters SET expires=MAX(expires, ?) WHERE id=?", (now + ttl, v.id))
    refresh(v.id, now)
    row = q1("SELECT * FROM clusters WHERE id=?", (v.id,))
    out = cluster_json(row, dev)
    out["removed"] = bool(row[8])
    out["counted"] = ok
    out["reason"] = why
    return out

def live_rows(lat, lon, radius_km, now, cap_km=60.0, extra="", args=()):
    rad = min(max(radius_km, 1.0), cap_km) * 1000
    dlat = rad / 111000.0
    dlon = rad / (111000.0 * max(0.2, math.cos(math.radians(lat))))
    rows = q(LIVE_SQL + "AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? " + extra,
             (now, lat - dlat, lat + dlat, lon - dlon, lon + dlon) + tuple(args))
    return [r for r in rows if dist_m(lat, lon, r[2], r[3]) <= rad]

@app.post("/v1/sync")
def sync(s: SyncIn, req: Request):
    dev = dev_hash(s.device)
    limit_ip(req, "sync", 1500, 300)
    limit("sync:" + dev, 20, 300)
    if not (-90 <= s.lat <= 90 and -180 <= s.lon <= 180):
        raise HTTPException(400, "ongeldige positie")
    heartbeat(dev, s.lat, s.lon, max(0.0, min(s.kmh, 300.0)), ip_hash(client_ip(req)))
    now = time.time()
    reports = [cluster_json(r, dev) for r in
               live_rows(s.lat, s.lon, s.radius_km, now, extra="AND confirmed IS NOT NULL")]
    mine = [cluster_json(r, dev) for r in
            live_rows(s.lat, s.lon, s.radius_km, now,
                      extra="AND confirmed IS NULL AND EXISTS(SELECT 1 FROM events e "
                            "WHERE e.cluster=clusters.id AND e.dev=? AND e.kind='report')",
                      args=(dev,))]
    out = online_counts(s.lat, s.lon)
    rh = hashlib.sha1(json.dumps([reports, mine], sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    out.update({"reports_hash": rh, "pending_n": len(mine), "server_time": int(now * 1000)})
    out["config_hash"] = config.hash_(DATA)
    if rh != s.reports_hash:
        out.update({"reports": reports, "pending": mine, "needed": MIN_CONFIRM})
    wx = weather.at(s.lat, s.lon, now)
    if wx:
        out["weather"] = wx
    if s.official:
        r_m = min(max(s.official_radius_km, 1.0), 40.0) * 1000
        items, _ = ndw.near(s.lat, s.lon, r_m)
        items += europe.near(s.lat, s.lon, r_m)
        h = hashlib.sha1(("L" if s.official_lines else "-").encode() + "|".join(sorted(
            "%s:%s:%s:%s:%s:%s" % (o["id"], o["end"], o["label"], o.get("place"), o.get("limit"), o.get("detail"))
            for o in items)).encode()).hexdigest()[:16]
        out["official_hash"] = h
        out["official_updated"] = ndw.snapshot_updated()
        if h != s.official_hash:
            keys = ("id", "rt", "type", "akey", "lat", "lon", "line", "start", "end", "detail", "limit", "place")
            if not s.official_lines:
                keys = tuple(k for k in keys if k != "line")
            out["official"] = [{k: o[k] for k in keys} for o in items if not o["planned"] and o["akey"]]
    return out

@app.get("/v1/live")
def live(req: Request, lat: float = 52.2, lon: float = 5.3, radius_km: float = 60):
    limit_ip(req, "live", 120, 300)
    if not all(math.isfinite(x) for x in (lat, lon, radius_km)):
        raise HTTPException(400, "ongeldige positie")
    now = time.time()
    reports = [cluster_json(r) for r in
               live_rows(lat, lon, radius_km, now, 250.0, extra="AND confirmed IS NOT NULL")]
    out = online_counts()
    out.update({"reports": reports, "needed": MIN_CONFIRM})
    return out

TZ_NL = ZoneInfo("Europe/Amsterdam")

VALHALLA = os.environ.get("ROADPING_VALHALLA", "")
PDOK_FREE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
PDOK_SUGGEST = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/suggest"
_VLANG = {"nl": "nl-NL", "en": "en-US", "de": "de-DE", "es": "es-ES", "pt": "pt-PT", "fy": "nl-NL"}
_nav_hits = defaultdict(deque)

def _nav_limit(request, per_min=30, kind="geo"):
    ip = client_ip(request)
    if ip is None:
        return
    if len(_nav_hits) > 20000:
        _nav_hits.clear()
    q = _nav_hits[kind + ":" + ip]
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= per_min:
        raise HTTPException(429, "te veel verzoeken")
    q.append(now)

def _decode6(s):
    out, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = res = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                res |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            vals.append(~(res >> 1) if res & 1 else res >> 1)
        lat += vals[0]
        lon += vals[1]
        out.append([round(lat / 1e6, 6), round(lon / 1e6, 6)])
    return out

PHOTON = "https://photon.komoot.io/api/"
_POI_SKIP = {"highway", "place", "boundary", "landuse", "natural", "waterway"}

def _pdok(q, lat, lon):
    params = {"q": q, "rows": "8", "fl": "weergavenaam,centroide_ll,type",
              "fq": "type:(adres OR weg OR woonplaats OR postcode OR gemeente)"}
    if lat is not None and lon is not None:
        params["lat"], params["lon"] = "%.2f" % lat, "%.2f" % lon
    req = urllib.request.Request(PDOK_SUGGEST + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "Pardal-server"})
    with urllib.request.urlopen(req, timeout=8) as r:
        docs = json.load(r)["response"]["docs"]
    out = []
    for d in docs:
        m = re.match(r"POINT\(([-0-9.]+) ([-0-9.]+)\)", d.get("centroide_ll", ""))
        if m:
            out.append({"name": d["weergavenaam"], "type": d.get("type", ""),
                        "lat": float(m.group(2)), "lon": float(m.group(1))})
    return out

_photon_cache = {}

def _photon(q, lat, lon):
    key = (q.lower(), None if lat is None else round(lat, 1), None if lon is None else round(lon, 1))
    hit = _photon_cache.get(key)
    if hit and time.time() - hit[0] < 900:
        return hit[1]
    items = _photon_fetch(q, lat, lon)
    if len(_photon_cache) > 2000:
        _photon_cache.clear()
    _photon_cache[key] = (time.time(), items)
    return items

def _photon_fetch(q, lat, lon):
    params = {"q": q, "limit": "15"}
    if lat is not None and lon is not None:
        params["lat"], params["lon"] = "%.1f" % lat, "%.1f" % lon
    req = urllib.request.Request(PHOTON + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": "Pardal-server (open-source)"})
    with urllib.request.urlopen(req, timeout=8) as r:
        feats = json.load(r).get("features", [])
    out, seen = [], set()
    for f in feats:
        p = f.get("properties", {})
        name, cc, key = p.get("name"), p.get("countrycode"), p.get("osm_key")
        if not name:
            continue
        nl = cc == "NL"
        if nl and key in _POI_SKIP:
            continue
        if not nl and key in ("boundary", "landuse", "natural", "waterway"):
            continue
        lon_, lat_ = f["geometry"]["coordinates"][:2]
        k = (name.lower(), (p.get("city") or "").lower(), cc) if nl else \
            (name.lower(), cc, round(lat_ * 5), round(lon_ * 5))
        if k in seen:
            continue
        seen.add(k)
        if nl:
            sub = " ".join(x for x in [p.get("street"), p.get("housenumber")] if x)
            sub = ", ".join(x for x in [sub, p.get("city")] if x)
        else:
            sub = ", ".join(x for x in [p.get("city") if p.get("city") != name else None,
                                        p.get("state"), p.get("country")] if x)
        out.append({"name": name, "type": "poi" if nl or key != "place" else "plaats", "sub": sub,
                    "lat": lat_, "lon": lon_, "cc": cc or ""})
    return out[:10]

_geo_pool = None

@app.get("/v1/geocode")
def geocode(request: Request, q: str = "", lat: float = None, lon: float = None, src: str = "all"):
    global _geo_pool
    _nav_limit(request, 90, "geo")
    q = q.strip()[:120]
    if len(q) < 2:
        return {"items": []}
    if src in ("adr", "poi"):
        try:
            return {"items": (_pdok if src == "adr" else _photon)(q, lat, lon)}
        except Exception as e:
            log.warning("geocode %s: %s", src, e)
            raise HTTPException(502, "zoeken niet beschikbaar")
    if _geo_pool is None:
        from concurrent.futures import ThreadPoolExecutor
        _geo_pool = ThreadPoolExecutor(8)
    fa = _geo_pool.submit(_pdok, q, lat, lon)
    fp = _geo_pool.submit(_photon, q, lat, lon)
    adr, poi = [], []
    try:
        adr = fa.result(timeout=10)
    except Exception as e:
        log.warning("geocode pdok: %s", e)
    try:
        poi = fp.result(timeout=10)
    except Exception as e:
        log.warning("geocode photon: %s", e)
    if not adr and not poi:
        raise HTTPException(502, "zoeken niet beschikbaar")
    if re.search(r"\d", q):
        items = adr + poi
    else:
        items = []
        for i in range(max(len(adr), len(poi))):
            if i < len(poi):
                items.append(poi[i])
            if i < len(adr):
                items.append(adr[i])
    return {"items": items[:12]}

_TOLL_PLAZAS = [
    [[3.7525, 51.4398], [3.7590, 51.4398], [3.7590, 51.4432], [3.7525, 51.4432], [3.7525, 51.4398]],
]

@app.post("/v1/route")
async def route(request: Request):
    _nav_limit(request, 20, "route")
    if not VALHALLA:
        raise HTTPException(503, "routeplanner niet ingesteld")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "ongeldige invoer")
    if not isinstance(body, dict):
        raise HTTPException(400, "ongeldige invoer")
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(_route_sync, body)

_ROUTEKAART = ((50.70, 53.70, 3.25, 7.25), (49.45, 51.55, 2.50, 6.45), (41.30, 51.15, -5.20, 9.60),
               (35.90, 43.85, -9.40, 4.40), (36.90, 42.20, -9.60, -6.10))

def _in_routekaart(lat, lon):
    return any(a <= lat <= b and c <= lon <= d for a, b, c, d in _ROUTEKAART)

def _route_sync(body):
    try:
        fl, fo = float(body["from"][0]), float(body["from"][1])
        tl, to = float(body["to"][0]), float(body["to"][1])
    except Exception:
        raise HTTPException(400, "from/to ontbreken")
    if not all(_in_routekaart(a, b) for a, b in ((fl, fo), (tl, to))):
        raise HTTPException(422, "Navigeren kan nu in Nederland, België, Frankrijk, Spanje en Portugal")
    start = {"lat": fl, "lon": fo}
    hd = body.get("heading")
    if isinstance(hd, (int, float)) and 0 <= hd < 360:
        start.update(heading=int(hd), heading_tolerance=60)
    opt = body.get("opt")
    if not isinstance(opt, dict):
        opt = {}
    auto = {"use_tolls": 0.5, "use_highways": 1.0, "use_ferry": 0.5}
    excl = []
    if opt.get("tolls"):
        auto.update(use_tolls=0.0, exclude_tolls=True)
        excl += _TOLL_PLAZAS
    if opt.get("highways"):
        auto.update(use_highways=0.0, exclude_highways=True)
    if opt.get("ferries"):
        auto.update(use_ferry=0.0, exclude_ferries=True)
    if opt.get("shortest"):
        auto["shortest"] = True
    req = {"locations": [start, {"lat": tl, "lon": to}], "costing": "auto",
           "costing_options": {"auto": auto},
           **({"exclude_polygons": excl} if excl else {}),
           "directions_options": {"language": _VLANG.get(str(body.get("lang", "nl")), "nl-NL"),
                                  "units": "kilometers"}}
    try:
        r = urllib.request.Request(VALHALLA + "/route", json.dumps(req).encode(),
                                   {"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=60) as resp:
            trip = json.load(resp)["trip"]
    except urllib.error.HTTPError as e:
        raise HTTPException(404 if e.code == 400 else 502, "geen route gevonden")
    except Exception as e:
        log.warning("route: %s", e)
        raise HTTPException(502, "routeplanner niet bereikbaar")
    try:
        leg = trip["legs"][0]
        leg["maneuvers"], leg["shape"], trip["summary"]["length"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(502, "geen route gevonden")
    man = [{"t": m.get("type", 0), "i": m.get("instruction", ""),
            "s": (m.get("street_names") or m.get("begin_street_names") or [""])[0],
            "b": m.get("begin_shape_index", 0), "x": m.get("roundabout_exit_count", 0) or 0,
            "len": int(m.get("length", 0) * 1000)} for m in leg["maneuvers"]]
    return {"len": int(trip["summary"]["length"] * 1000), "time": int(trip["summary"]["time"]),
            "pts": _decode6(leg["shape"]), "man": man}

_map_meta = {"mtime": 0, "data": None}

def _map_info():
    p = os.path.join(DATA, "wkd.json")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None
    if _map_meta["mtime"] != mt:
        with open(p) as f:
            _map_meta["data"] = json.load(f)
        _map_meta["mtime"] = mt
    return _map_meta["data"]

@app.get("/v1/map")
def map_info():
    info = _map_info()
    if not info or not os.path.isfile(os.path.join(DATA, "wkd.bin.gz")):
        raise HTTPException(404, "geen kaart")
    return dict(info, url="/v1/map/wkd.bin.gz")

@app.get("/v1/map/wkd.bin.gz")
def map_file(req: Request):
    limit_ip(req, "mapdl", 6, 3600)
    p = os.path.join(DATA, "wkd.bin.gz")
    if not os.path.isfile(p):
        raise HTTPException(404, "geen kaart")
    return FileResponse(p, media_type="application/octet-stream",
                        headers={"Cache-Control": "public, max-age=3600"})

MAPS_DIR = os.path.join(DATA, "maps")
_maps_meta = {"mtime": 0, "data": None}

def _maps_info():
    p = os.path.join(MAPS_DIR, "maps.json")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None
    if _maps_meta["mtime"] != mt:
        with open(p) as f:
            _maps_meta["data"] = json.load(f)
        _maps_meta["mtime"] = mt
    return _maps_meta["data"]

@app.get("/v1/maps")
def maps_list():
    info = _maps_info()
    if not info:
        raise HTTPException(404, "geen kaarten")
    return {"maps": [dict(m, url="/v1/maps/%s.bin.gz" % m["id"]) for m in info.get("maps", [])]}

@app.get("/v1/maps/{name}")
def maps_file(name: str, req: Request):
    m = re.fullmatch(r"([a-z0-9-]{2,12})\.bin\.gz", name)
    info = _maps_info()
    if not m or not info or m.group(1) not in {x["id"] for x in info.get("maps", [])}:
        raise HTTPException(404, "onbekende kaart")
    limit_ip(req, "mapsdl", 20, 3600)
    p = os.path.join(MAPS_DIR, name)
    if not os.path.isfile(p):
        raise HTTPException(404, "onbekende kaart")
    return FileResponse(p, media_type="application/octet-stream",
                        headers={"Cache-Control": "public, max-age=3600"})

B3D_WFS = "https://data.3dbag.nl/api/BAG3D/wfs"
B3D_Z = 15
B3D_DIR = os.path.join(DATA, "buildings")
B3D_TTL = 60 * 86400
_b3d_locks = [threading.Lock() for _ in range(64)]
_b3d_sem = threading.BoundedSemaphore(2)
_b3d_fail = {}

def _tile_bounds(x, y, z=B3D_Z):
    n = 2 ** z
    lon0, lon1 = x / n * 360 - 180, (x + 1) / n * 360 - 180
    lat0 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return lat0, lon0, lat1, lon1

def _simplify(ring, kx, ky, tol=0.45):
    pts = [(p[0], p[1]) for p in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    out = []
    for p in pts:
        if out and math.hypot((p[0] - out[-1][0]) * kx, (p[1] - out[-1][1]) * ky) < tol:
            continue
        out.append(p)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            ax, ay = (b[0] - a[0]) * kx, (b[1] - a[1]) * ky
            cx, cy = (c[0] - a[0]) * kx, (c[1] - a[1]) * ky
            ln = math.hypot(cx, cy)
            if ln > 0 and abs(ax * cy - ay * cx) / ln < tol * 0.5:
                del out[i]
                changed = True
                break
    return out

def _b3d_build(x, y):
    import gzip, struct
    lat0, lon0, lat1, lon1 = _tile_bounds(x, y)
    bbox = "%.7f,%.7f,%.7f,%.7f,urn:ogc:def:crs:EPSG::4326" % (lat1, lon0, lat0, lon1)
    feats, start = [], 0
    while True:
        params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "BAG3D:lod12",
                  "outputFormat": "application/json", "count": "10000", "startIndex": str(start),
                  "srsName": "urn:ogc:def:crs:EPSG::4326", "propertyName": "geom,b3_h_70p,b3_h_maaiveld",
                  "bbox": bbox}
        req = urllib.request.Request(B3D_WFS + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": "Pardal-server"})
        with urllib.request.urlopen(req, timeout=40) as r:
            doc = json.load(r)
        if not isinstance(doc, dict) or "features" not in doc:
            raise ValueError("onverwacht antwoord van 3D BAG")
        page = doc["features"]
        feats += page
        if len(page) < 10000 or start >= 60000:
            break
        start += 10000
    kx = math.cos(math.radians((lat0 + lat1) / 2)) * 111320.0
    ky = 110540.0
    Q = 16384.0
    body = []
    for f in feats:
        g, pr = f.get("geometry") or {}, f.get("properties") or {}
        h, m = pr.get("b3_h_70p"), pr.get("b3_h_maaiveld") or 0.0
        if h is None:
            continue
        hm = max(2.5, min(250.0, h - m))
        polys = g.get("coordinates") or []
        if g.get("type") == "MultiPolygon":
            polys = [pp[0] for pp in polys]
        elif g.get("type") == "Polygon":
            polys = [polys[0]] if polys else []
        else:
            continue
        for ring in polys:
            pts = _simplify(ring, kx, ky)
            if len(pts) < 3:
                continue
            cx_ = sum(p[0] for p in pts) / len(pts)
            cy_ = sum(p[1] for p in pts) / len(pts)
            if not (lon0 <= cx_ < lon1 and lat1 < cy_ <= lat0):
                continue
            tol = 0.45
            while len(pts) > 254 and tol < 20:
                tol *= 2
                pts = _simplify(ring, kx, ky, tol)
            if len(pts) < 3 or len(pts) > 254:
                continue
            rec = struct.pack("<HB", int(hm * 10), len(pts))
            for lo, la in pts:
                qx = int(round((lo - lon0) / (lon1 - lon0) * Q))
                qy = int(round((lat0 - la) / (lat0 - lat1) * Q))
                rec += struct.pack("<hh", max(-32768, min(32767, qx)), max(-32768, min(32767, qy)))
            body.append(rec)
    raw = b"PB1\0" + struct.pack("<I", len(body)) + b"".join(body)
    return gzip.compress(raw, 6), len(body)

@app.get("/v1/buildings/{x}/{y}")
def buildings(x: int, y: int, req: Request):
    limit_ip(req, "b3d", 600, 300)
    n_ = 2 ** B3D_Z
    if not (0 <= x < n_ and 0 <= y < n_):
        raise HTTPException(404, "buiten Nederland")
    lat0, lon0, lat1, lon1 = _tile_bounds(x, y)
    if not (50.7 < lat1 and lat0 < 53.6 and 3.3 < lon0 and lon1 < 7.25):
        raise HTTPException(404, "buiten Nederland")
    path = os.path.join(B3D_DIR, "%d_%d.bin.gz" % (x, y))
    key = "%d_%d" % (x, y)
    with _b3d_locks[hash(key) % 64]:
        fresh = os.path.isfile(path) and time.time() - os.path.getmtime(path) < B3D_TTL
        recent_fail = time.time() - _b3d_fail.get(key, 0) < 300
        if not fresh and not (recent_fail and os.path.isfile(path)):
            if recent_fail:
                raise HTTPException(503, "gebouwen even niet beschikbaar")
            try:
                with _b3d_sem:
                    data, n = _b3d_build(x, y)
            except Exception as e:
                log.warning("3dbag %d/%d: %s", x, y, e)
                if len(_b3d_fail) > 5000:
                    _b3d_fail.clear()
                _b3d_fail[key] = time.time()
                if not os.path.isfile(path):
                    raise HTTPException(503, "gebouwen even niet beschikbaar")
            else:
                os.makedirs(B3D_DIR, exist_ok=True)
                tmp = path + ".tmp"
                with open(tmp, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, path)
                log.info("3dbag %d/%d: %d panden, %d bytes", x, y, n, len(data))
    return FileResponse(path, media_type="application/octet-stream",
                        headers={"Cache-Control": "public, max-age=604800"})

@app.get("/v1/stats")
def stats(req: Request):
    limit_ip(req, "stats", 120, 300)
    now = time.time()
    midnight = datetime.now(TZ_NL).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    per_type = {str(t): n for t, n in q(
        "SELECT type, COUNT(*) FROM clusters WHERE confirmed>=? GROUP BY type", (midnight,))}
    reports = q1("SELECT COUNT(*) FROM events WHERE kind='report' AND valid=1 AND t>=?", (midnight,))[0]
    votes = q1("SELECT COUNT(*) FROM events WHERE kind IN ('yes','no') AND valid=1 AND t>=?",
               (midnight,))[0]
    drivers = q1("SELECT COUNT(*) FROM devices WHERE last_seen>=?", (midnight,))[0]
    hour0 = (int(now) // 3600 - 23) * 3600
    hourly = [0] * 24
    for (t,) in q("SELECT t FROM events WHERE kind='report' AND valid=1 AND t>=?", (hour0,)):
        i = int((t - hour0) // 3600)
        if 0 <= i < 24:
            hourly[i] += 1
    return {"confirmed_today": sum(per_type.values()), "per_type": per_type,
            "reports_today": reports, "votes_today": votes, "drivers_today": drivers,
            "hourly": hourly, "hour0": int(hour0 * 1000)}

@app.get("/v1/sky")
def sky_now(req: Request):
    limit_ip(req, "sky", 120, 300)
    return sky.snapshot()

@app.get("/v1/msi")
def msi_near(req: Request, lat: float, lon: float, r: float = 3000):
    limit_ip(req, "msi", 120, 300)
    if not all(math.isfinite(x) for x in (lat, lon, r)):
        raise HTTPException(400, "ongeldige positie")
    items, upd = msi.near(lat, lon, min(max(r, 100.0), 8000.0))
    if items is None:
        raise HTTPException(503, "matrixborden nog niet beschikbaar")
    return {"updated": int(upd * 1000), "items": items}

@app.get("/v1/weather")
def weather_now(req: Request):
    limit_ip(req, "weather", 60, 300)
    items, upd = weather.snapshot()
    return {"items": items, "updated": upd}

@app.get("/v1/cameras")
def cameras_all(req: Request):
    limit_ip(req, "cams", 30, 300)
    return Response(cameras.payload(), media_type="application/json",
                    headers={"Cache-Control": "public, max-age=3600"})

@app.get("/v1/official")
def official(req: Request, bbox: str = "", z: float = 12):
    limit_ip(req, "official", 240, 300)
    nl = ndw.snapshot()
    if not bbox:
        return nl
    try:
        a, b, c, d = (float(x) for x in bbox.split(","))
        if not all(math.isfinite(x) for x in (a, b, c, d)):
            raise ValueError
    except ValueError:
        raise HTTPException(400, "ongeldige bbox")
    eu, upd = europe.snapshot()

    def inside(it):
        pts = it["line"] or [(it["lat"], it["lon"])]
        return any(a <= p[0] <= c and b <= p[1] <= d for p in (pts[0], pts[len(pts) // 2], pts[-1]))

    keep_line = z >= 8
    items = [dict(i, cc=i.get("cc", "NL"), line=i["line"] if keep_line else [],
                  detail=i["detail"] if keep_line else "")
             for i in nl["items"] + eu if inside(i)]
    items.sort(key=lambda i: {"urgent": 0, "works": 1}.get(i["cat"], 2))
    cap = 8000 if keep_line else 20000
    return {"updated": nl["updated"], "updated_eu": upd, "items": items[:cap],
            "truncated": len(items) > cap}

@app.get("/v1/config")
def app_config():
    cfg = config.load(DATA)
    return dict(cfg, hash=config.hash_(DATA))

@app.get("/v1/health")
def health():
    return {"ok": True}

def _cleanup():
    while True:
        time.sleep(3600)
        try:
            old = time.time() - 86400
            q("DELETE FROM events WHERE cluster IN (SELECT id FROM clusters WHERE expires<?)", (old,))
            q("DELETE FROM clusters WHERE expires<?", (old,))
            q("DELETE FROM devices WHERE last_seen<?", (time.time() - 90 * 86400,))
        except Exception:
            log.exception("opruimen mislukt")

threading.Thread(target=_cleanup, daemon=True).start()
threading.Thread(target=_geocoder, daemon=True).start()
if os.environ.get("ROADPING_NDW", "1") == "1":
    ndw.start(_place_for)
    cameras.start(DATA)
    europe.start()
    sky.start()
    weather.start()
    msi.start()
for (_cid,) in q("SELECT id FROM clusters WHERE confirmed IS NOT NULL AND removed=0 "
                 "AND (place IS NULL OR place='') AND expires>?", (time.time(),)):
    _geo_q.put(_cid)

STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

@app.get("/privacy")
def privacy_page():
    return FileResponse(os.path.join(STATIC, "privacy.html"), headers={"Cache-Control": "no-cache"})

@app.get("/support")
def support_page():
    return FileResponse(os.path.join(STATIC, "support.html"), headers={"Cache-Control": "no-cache"})

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"),
                        headers={"Cache-Control": "no-cache"})

@app.exception_handler(StarletteHTTPException)
def _err(req, exc):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
def _bad(req, exc):
    return JSONResponse({"error": "ongeldige invoer"}, status_code=422)
