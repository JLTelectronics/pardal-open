import gzip
import json
import logging
import threading
import time
import urllib.request
from datetime import datetime

log = logging.getLogger("roadping.weather")
UA = {"User-Agent": "Pardal-server (open-source)", "Accept-Encoding": "gzip"}
FEEDS = {"NL": "netherlands", "LU": "luxembourg"}
URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-%s"
REFRESH = 300

_lock = threading.Lock()
_items = {}
_updated = 0

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(30 * 1024 * 1024)
        if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
    return json.loads(data)

def _ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def _ring(txt, maxn=160):
    pts = []
    for p in txt.split():
        try:
            a, b = p.split(",")
            pts.append((round(float(a), 4), round(float(b), 4)))
        except ValueError:
            pass
    if len(pts) > maxn:
        step = len(pts) / float(maxn)
        pts = [pts[int(i * step)] for i in range(maxn)]
    return pts

def _num(v):
    try:
        return int(str(v).split(";")[0])
    except ValueError:
        return 0

def parse(d, cc, now):
    out = {}
    for w in d.get("warnings", []):
        a = w.get("alert") or {}
        if a.get("msgType") == "Cancel" or not a.get("info"):
            continue
        infos = a["info"]
        by = {(i.get("language") or "")[:2]: i for i in infos}
        i = by.get("en") or infos[0]
        if "AllClear" in (i.get("responseType") or []):
            continue
        p = {x.get("valueName"): x.get("value") for x in i.get("parameter", [])}
        lvl, typ = _num(p.get("awareness_level")), _num(p.get("awareness_type"))
        onset, exp = _ts(i.get("onset") or ""), _ts(i.get("expires") or "")
        if lvl < 2 or not exp or exp < now:
            continue
        rings = [_ring(poly) for ar in i.get("area", []) for poly in (ar.get("polygon") or [])]
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            continue
        area = ", ".join(ar.get("areaDesc", "") for ar in i.get("area", []))
        local = next((v for k, v in by.items() if k and k != "en"), None)
        head = {"en": i.get("headline") or i.get("event") or ""}
        if local:
            head[(local.get("language") or "")[:2]] = local.get("headline") or local.get("event") or ""
            area = ", ".join(ar.get("areaDesc", "") for ar in local.get("area", [])) or area
        key = (typ, area, onset, exp)
        sent = _ts(a.get("sent") or "") or 0
        it = {"id": "%s-%s" % (cc, (w.get("uuid") or a.get("identifier", ""))[-12:]), "cc": cc,
              "level": lvl, "type": typ, "area": area, "head": head,
              "start": int((onset or now) * 1000), "end": int(exp * 1000), "rings": rings, "_sent": sent}
        if key not in out or out[key]["_sent"] < sent:
            out[key] = it
    res = sorted(out.values(), key=lambda x: (-x["level"], x["start"]))
    for r in res:
        r.pop("_sent", None)
    return res

def _worker():
    global _updated
    while True:
        now = time.time()
        for cc, name in FEEDS.items():
            try:
                items = parse(_get(URL % name), cc, now)
                with _lock:
                    _items[cc] = items
                    _updated = int(now * 1000)
                log.warning("weer %s: %d waarschuwingen", cc, len(items))
            except Exception as e:
                log.warning("weer %s mislukt: %s", cc, e)
        time.sleep(REFRESH)

def start():
    threading.Thread(target=_worker, daemon=True).start()

def snapshot(now=None):
    now = now or time.time()
    with _lock:
        return [dict(w) for cc in _items for w in _items[cc] if w["end"] / 1000 >= now], _updated

def _inside(lat, lon, ring):
    ins = False
    j = len(ring) - 1
    for k in range(len(ring)):
        yi, xi = ring[k]
        yj, xj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            ins = not ins
        j = k
    return ins

def at(lat, lon, now=None):
    now = now or time.time()
    best = None
    with _lock:
        for cc in _items:
            for w in _items[cc]:
                if w["start"] / 1000 > now or w["end"] / 1000 < now:
                    continue
                if any(_inside(lat, lon, r) for r in w["rings"]):
                    if not best or w["level"] > best["level"]:
                        best = w
    if not best:
        return None
    return {k: best[k] for k in ("id", "level", "type", "area", "head", "start", "end")}
