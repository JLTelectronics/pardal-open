import gzip
import hashlib
import io
import math
import logging
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

log = logging.getLogger("roadping.ndw")

BASE = "https://opendata.ndw.nu/"
FEEDS = ["actueel_beeld.xml.gz", "veiligheidsgerelateerde_informatie_srti.xml.gz",
         "planningsfeed_brugopeningen.xml.gz",
         "tijdelijke_verkeersmaatregelen_maximum_snelheden.xml.gz"]
REFRESH = 60
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"

FILE, ACCIDENT, WORKS, OBSTACLE, CLOSURE, SPEED, REROUTE, WEATHER, BRIDGE, WRONGWAY, SHOULDER = \
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

_lock = threading.Lock()
_state = {"updated": 0, "items": [], "error": ""}
_place = {}
_place_todo = []
_place_queued = set()

def _iso(s):
    if not s:
        return None
    try:
        s = s.strip()
        if "." in s:
            head, frac = s.split(".", 1)
            tz = ""
            for i, ch in enumerate(frac):
                if not ch.isdigit():
                    tz = frac[i:]
                    frac = frac[:i]
                    break
            s = head + "." + frac[:6] + tz
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def _classify(rtype, f):
    mgmt = (f.get("roadOrCarriagewayOrLaneManagementType") or "").lower()
    vo = (f.get("vehicleObstructionType") or "").lower()
    if "wrongcarriageway" in vo or "wrongway" in vo:
        return WRONGWAY, "Spookrijder", "urgent"
    if "Accident" in rtype:
        return ACCIDENT, "Ongeval", "urgent"
    if "AbnormalTraffic" in rtype or "queueLength" in f or "Queue" in rtype:
        return FILE, "File", "urgent"
    if "VehicleObstruction" in rtype:
        if "brokendown" in vo:
            return OBSTACLE, "Pechgeval", "urgent"
        if "maintenance" in (f.get("vehicleType") or "").lower():
            return WORKS, "Pijlwagen / werkvoertuig", "works"
        return OBSTACLE, "Stilstaand voertuig", "urgent"
    if "Obstruction" in rtype:
        return OBSTACLE, "Obstakel", "urgent"
    if "GeneralNetworkManagement" in rtype:
        return BRIDGE, "Brug open", "urgent"
    if "RoadOrCarriagewayOrLaneManagement" in rtype:
        if mgmt == "roadclosed":
            return CLOSURE, "Weg dicht", "urgent"
        if mgmt == "carriagewayclosures":
            return CLOSURE, "Rijbaan dicht", "works"
        if mgmt == "laneclosures":
            return WORKS, "Rijstrook dicht", "works"
        if mgmt == "narrowlanes":
            return WORKS, "Versmalde rijstroken", "works"
        if mgmt == "lanesdeviated":
            return WORKS, "Rijstroken verlegd", "works"
        if mgmt == "hardshoulderrunninginoperation":
            return SHOULDER, "Spitsstrook open", "info"
        if mgmt == "useofspecifiedlanesorcarriagewaysallowed":
            return WORKS, "Aangepaste rijstrookindeling", "works"
        return WORKS, "Wegwerkzaamheden", "works"
    if "MaintenanceWorks" in rtype or "ConstructionWorks" in rtype:
        return WORKS, "Wegwerkzaamheden", "works"
    if "SpeedManagement" in rtype:
        v = f.get("temporarySpeedLimit")
        try:
            return SPEED, "Max. %d km/u" % round(float(v)), "info"
        except (TypeError, ValueError):
            return SPEED, "Snelheid aangepast", "info"
    if "Rerouting" in rtype:
        return REROUTE, "Omleiding", "info"
    if "PoorEnvironment" in rtype or "Weather" in rtype:
        return WEATHER, "Slecht weer", "info"
    if "Activities" in rtype or "Public" in rtype:
        return WORKS, "Evenement / activiteit", "info"
    return None

def _parse(data, now, out):
    with gzip.GzipFile(fileobj=io.BytesIO(data)) if data[:2] == b"\x1f\x8b" else io.BytesIO(data) as fh:
        for _, el in ET.iterparse(fh, events=("end",)):
            if not el.tag.endswith("}situationRecord"):
                continue
            rtype = (el.get(XSI) or "").split(":")[-1]
            rid = el.get("id") or ""
            f = {}
            pos = []
            for x in el.iter():
                tag = x.tag.split("}")[-1]
                txt = (x.text or "").strip()
                if not txt:
                    continue
                if tag == "posList":
                    pos.append(txt)
                elif tag not in f:
                    f[tag] = txt
            el.clear()
            c = _classify(rtype, f)
            if c is None:
                continue
            start, end = _iso(f.get("overallStartTime")), _iso(f.get("overallEndTime"))
            planned = False
            if c[0] == BRIDGE and start and start > now + 60:
                if start > now + 60 * 60:
                    continue
                planned = True
            elif start and start > now + 15 * 60:
                continue
            if end and end < now - 5 * 60:
                continue
            line = []
            if pos:
                nums = " ".join(pos).split()
                try:
                    pts = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums) - 1, 2)]
                except ValueError:
                    pts = []
                step = max(1, len(pts) // 40)
                line = [(round(a, 5), round(b, 5)) for a, b in pts[::step]]
                if pts and line[-1] != (round(pts[-1][0], 5), round(pts[-1][1], 5)):
                    line.append((round(pts[-1][0], 5), round(pts[-1][1], 5)))
            try:
                lat, lon = (float(f["latitude"]), float(f["longitude"])) if "latitude" in f else line[0]
            except (KeyError, IndexError, ValueError):
                continue
            if not (50.6 <= lat <= 53.7 and 3.2 <= lon <= 7.3):
                continue
            key = rid or "%s:%.5f,%.5f" % (rtype, lat, lon)
            if key in out:
                continue
            label, cat = c[1], c[2]
            if planned:
                label, cat = "Brug open om " + datetime.fromtimestamp(start).astimezone().strftime("%H:%M"), "info"
            detail = ""
            limit = None
            if c[0] == SPEED:
                try:
                    limit = int(round(float(f.get("temporarySpeedLimit"))))
                except (TypeError, ValueError):
                    pass
            if c[0] == FILE and f.get("queueLength"):
                try:
                    detail = "%.1f km" % (float(f["queueLength"]) / 1000)
                except ValueError:
                    pass
            out[key] = {
                "id": key, "rt": rtype, "type": c[0], "label": label, "cat": cat,
                "akey": _app_label(c[0], c[1], f, planned), "limit": limit, "planned": planned,
                "lat": round(lat, 5), "lon": round(lon, 5),
                "line": line if c[0] in (FILE, CLOSURE, WORKS, SPEED, SHOULDER) and len(line) > 1 else [],
                "start": int(start * 1000) if start else None,
                "end": int(end * 1000) if end else None,
                "detail": detail,
            }

def _app_label(typ, label, f, planned):
    if planned:
        return ""
    vo = (f.get("vehicleObstructionType") or "").lower()
    return {
        WRONGWAY: "SPOOKRIJDER", ACCIDENT: "ONGEVAL", FILE: "FILE", BRIDGE: "BRUG OPEN",
        REROUTE: "OMLEIDING", WEATHER: "WEER", SHOULDER: "",
    }.get(typ) or {
        "Pechgeval": "PECHGEVAL", "Pijlwagen / werkvoertuig": "PIJLWAGEN",
        "Weg dicht": "WEGAFSLUITING", "Rijbaan dicht": "AFSLUITING", "Rijstrook dicht": "RIJSTROOK DICHT",
    }.get(label) or ("SNELHEID" if typ == SPEED else "OBSTAKEL" if typ == OBSTACLE else "WERKZAAMHEDEN")

def _dist(a_lat, a_lon, b_lat, b_lon):
    dx = (b_lon - a_lon) * 111320 * math.cos(math.radians((a_lat + b_lat) / 2))
    dy = (b_lat - a_lat) * 110540
    return math.hypot(dx, dy)

def near(lat, lon, radius_m):
    dlat = radius_m / 110540.0
    dlon = radius_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    out = []
    with _lock:
        for it in _state["items"]:
            pts = it["line"] or [(it["lat"], it["lon"])]
            ok = False
            for a, b in pts if len(pts) < 3 else [pts[0], pts[len(pts) // 2], pts[-1]] + pts:
                if abs(a - lat) <= dlat and abs(b - lon) <= dlon and _dist(lat, lon, a, b) <= radius_m:
                    ok = True
                    break
            if ok:
                d = dict(it)
                d["place"] = _place.get(it["id"], "")
                out.append(d)
    h = hashlib.sha1("|".join(sorted("%s:%s:%s" % (o["id"], o["end"], o["label"]) for o in out))
                     .encode()).hexdigest()[:16]
    return out, h

def refresh_once():
    now = time.time()
    items = {}
    errors = []
    for name in FEEDS:
        try:
            req = urllib.request.Request(BASE + name, headers={"User-Agent": "Pardal-server"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read(40 * 1024 * 1024)
            _parse(data, now, items)
        except Exception as e:
            errors.append("%s: %s" % (name, e))
            log.warning("NDW %s mislukt: %s", name, e)
    lst = list(items.values())
    with _lock:
        if lst or not _state["items"]:
            _state["items"] = lst
            _state["updated"] = int(now * 1000)
        _state["error"] = "; ".join(errors)
        lst.sort(key=lambda it: {"urgent": 0, "works": 1}.get(it["cat"], 2))
        live = {it["id"] for it in lst}
        _place_todo[:] = [i for i in _place_todo if i in live]
        _place_queued.intersection_update(live)
        for it in lst:
            if it["id"] not in _place and it["id"] not in _place_queued:
                _place_todo.append(it["id"])
                _place_queued.add(it["id"])
    return len(lst)

def snapshot():
    with _lock:
        out = []
        for it in _state["items"]:
            d = dict(it)
            d["place"] = _place.get(it["id"], "")
            out.append(d)
        return {"updated": _state["updated"], "items": out, "ok": not _state["error"] or bool(out)}

def _worker(place_for):
    while True:
        try:
            refresh_once()
        except Exception:
            log.exception("NDW verversen mislukt")
        deadline = time.time() + REFRESH
        while time.time() < deadline:
            with _lock:
                rid = _place_todo.pop(0) if _place_todo else None
                if rid is not None:
                    _place_queued.discard(rid)
                it = next((x for x in _state["items"] if x["id"] == rid), None) if rid else None
            if it is None:
                time.sleep(2)
                continue
            try:
                p = place_for(it["lat"], it["lon"])
            except Exception:
                p = ""
            with _lock:
                _place[rid] = p
                if len(_place) > 20000:
                    _place.clear()
            time.sleep(0.4)

def start(place_for):
    threading.Thread(target=_worker, args=(place_for,), daemon=True).start()

def snapshot_updated():
    with _lock:
        return _state["updated"]
