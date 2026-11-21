import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request

log = logging.getLogger("roadping.cameras")

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
             "https://overpass.private.coffee/api/interpreter"]
QUERY = ('[out:json][timeout:150];area["ISO3166-1"="NL"]["admin_level"="2"]->.nl;'
         'rel(area.nl)["enforcement"="average_speed"]->.t;('
         'node(area.nl)["highway"="speed_camera"];'
         'node(area.nl)["enforcement"~"maxspeed|average_speed|traffic_signals"];'
         'node(area.nl)["man_made"="surveillance"]["surveillance:type"~"ALPR|ANPR|speed_camera",i];'
         '.t;node(r.t););out body;')
REFRESH = 24 * 3600

_lock = threading.Lock()
_state = {"updated": 0, "items": [], "json": b'{"updated":0,"items":[]}'}
_extra = []

ES_RADARS = "https://nap.dgt.es/datex2/dgt/PredefinedLocationsPublication/radares/content.xml"

def _es_radars():
    import io
    import xml.etree.ElementTree as ET
    req = urllib.request.Request(ES_RADARS, headers={"User-Agent": "Pardal-server (open-source)"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read(30 * 1024 * 1024)
    out, kind = [], "F"
    loc = lambda t: t.rsplit("}", 1)[-1]
    for ev, el in ET.iterparse(io.BytesIO(data), events=("start", "end")):
        t = loc(el.tag)
        if ev == "start" and t == "predefinedLocationSet":
            kind = "A" if "media" in (el.get("id") or "").lower() else "F"
        if ev == "end" and t == "predefinedLocation" and el.get("id"):
            lat = None
            pts = []
            for x in el.iter():
                n = loc(x.tag)
                if n == "latitude" and x.text:
                    lat = float(x.text)
                elif n == "longitude" and x.text and lat is not None:
                    pts.append((lat, float(x.text))); lat = None
            for i, (a, b) in enumerate(pts[:2] if kind == "A" else pts[:1]):
                out.append(["es-%s-%d" % (el.get("id"), i), round(a, 6), round(b, 6), kind, 0])
            el.clear()
    return out

def classify(t):
    hw = t.get("highway", "")
    sub = (t.get("speed_camera", "") + " " + t.get("enforcement", "")).lower()
    st = t.get("surveillance:type", "").lower()
    if hw == "speed_camera" or "maxspeed" in sub or "average" in sub or "traffic_signals" in sub:
        if "average" in sub:
            return "A"
        if "traffic_signals" in sub:
            return "R"
        return "F"
    if "alpr" in st or "anpr" in st:
        return "N"
    if "speed_camera" in st:
        return "F"
    return None

def _fetch():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    last = None
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, body, {"User-Agent": "Pardal-server (open-source)"})
            with urllib.request.urlopen(req, timeout=150) as r:
                d = json.load(r)
            if "error" in d.get("remark", "").lower():
                raise IOError(d["remark"][:120])
            els = d.get("elements", [])
            if len(els) < 300:
                raise IOError("maar %d camera's" % len(els))
            return els
        except Exception as e:
            last = e
            log.warning("Overpass %s: %s", ep, e)
    raise last or IOError("geen Overpass bereikbaar")

def _build(els):
    out = []
    traject = {}
    for e in els:
        if e.get("type") == "relation":
            ms = e.get("tags", {}).get("maxspeed", "")
            for m in e.get("members", []):
                if m.get("type") == "node":
                    traject[m["ref"]] = ms
    for e in els:
        if e.get("type") != "node":
            continue
        if not (50.6 <= e.get("lat", 0) <= 53.8):
            continue
        t = e.get("tags", {})
        k = "A" if e["id"] in traject else classify(t)
        if k == "A" and not t.get("maxspeed") and traject.get(e["id"]):
            t = dict(t, maxspeed=traject[e["id"]])
        if not k:
            continue
        ms = t.get("maxspeed", "")
        try:
            ms = int(ms) if ms.isdigit() else 0
        except ValueError:
            ms = 0
        out.append([e["id"], round(e["lat"], 6), round(e["lon"], 6), k, ms])
    return out

def _set(items, updated):
    with _lock:
        _state["items"] = items
        _state["updated"] = updated
        allitems = items + _extra
        _state["json"] = json.dumps({"updated": updated, "items": allitems},
                                    separators=(",", ":")).encode()

def payload():
    with _lock:
        return _state["json"]

def start(data_dir):
    path = os.path.join(data_dir, "cameras.json")

    def worker():
        try:
            with open(path) as f:
                d = json.load(f)
            _set(d["items"], d["updated"])
        except Exception:
            pass
        while True:
            age = time.time() - _state["updated"] / 1000
            if age > REFRESH:
                try:
                    items = _build(_fetch())
                    now = int(time.time() * 1000)
                    _set(items, now)
                    tmp = path + ".tmp"
                    with open(tmp, "w") as f:
                        json.dump({"updated": now, "items": items}, f, separators=(",", ":"))
                    os.replace(tmp, path)
                    log.warning("camera's bijgewerkt: %d", len(items))
                except Exception as e:
                    log.warning("camera's ophalen mislukt: %s", e)
                    time.sleep(15 * 60)
                    continue
            time.sleep(3600)

    def extra_worker():
        while True:
            try:
                es = _es_radars()
                if len(es) > 50:
                    _extra[:] = es
                    with _lock:
                        items, upd = _state["items"], _state["updated"]
                    _set(items, upd)
                    log.warning("Spaanse flitsers: %d", len(es))
            except Exception as e:
                log.warning("Spaanse flitsers mislukt: %s", e)
                time.sleep(3600)
                continue
            time.sleep(REFRESH)

    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=extra_worker, daemon=True).start()
