import gzip
import hashlib
import io
import json
import logging
import math
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

log = logging.getLogger("roadping.europe")
UA = {"User-Agent": "Pardal-server (open-source)", "Accept-Encoding": "gzip",
      "Digitraffic-User": "Pardal/open-source"}

FILE, ACCIDENT, WORKS, OBSTACLE, CLOSURE, SPEED, WEATHER, WRONGWAY = 3, 4, 5, 6, 7, 8, 10, 12

_lock = threading.Lock()
_items = {"DE": [], "ES": [], "FI": [], "FR": [], "PT": [], "BE": []}
_updated = {"DE": 0, "ES": 0, "FI": 0, "FR": 0, "PT": 0, "BE": 0}

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(60 * 1024 * 1024)
        if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
    return data

def _iso(s):
    if not s:
        return None
    try:
        s = re.sub(r"(\.\d{6})\d+", r"\1", s.strip())
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def _simplify(pts, n=40):
    if len(pts) <= n:
        return [(round(a, 5), round(b, 5)) for a, b in pts]
    step = len(pts) / float(n)
    out = [pts[int(i * step)] for i in range(n)] + [pts[-1]]
    return [(round(a, 5), round(b, 5)) for a, b in out]

def _item(cc, rid, typ, label, cat, lat, lon, line=None, start=None, end=None, place="", detail="",
          akey="", limit=None):
    return {"id": "%s:%s" % (cc, rid), "rt": cc, "type": typ, "label": label, "cat": cat,
            "akey": akey, "limit": limit, "planned": False, "cc": cc,
            "lat": round(lat, 5), "lon": round(lon, 5), "line": line or [],
            "start": int(start * 1000) if start else None, "end": int(end * 1000) if end else None,
            "detail": detail, "place": place}

_DE_END = re.compile(r"Ende:\s*(\d\d)\.(\d\d)\.(\d\d)\s*um\s*(\d\d):(\d\d)")

def _de_end(desc):
    m = _DE_END.search(" ".join(desc or []))
    if not m:
        return None
    d, mo, y, h, mi = (int(x) for x in m.groups())
    try:
        return datetime(2000 + y, mo, d, h, mi).astimezone().timestamp()
    except ValueError:
        return None

def _de_classify(kind, text):
    t = text.lower()
    if kind == "closure":
        return CLOSURE, "Weg dicht", "urgent", "WEGAFSLUITING"
    if kind == "roadworks":
        return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
    if "falschfahrer" in t or "geisterfahrer" in t:
        return WRONGWAY, "Spookrijder", "urgent", "SPOOKRIJDER"
    if "unfall" in t:
        return ACCIDENT, "Ongeval", "urgent", "ONGEVAL"
    if "stau" in t or "stockender verkehr" in t:
        return FILE, "File", "urgent", "FILE"
    if "panne" in t or "liegengebliebenes" in t:
        return OBSTACLE, "Pechgeval", "urgent", "PECHGEVAL"
    if "gegenst" in t or "gefahr" in t or "tiere" in t:
        return OBSTACLE, "Obstakel", "urgent", "OBSTAKEL"
    if "sperrung" in t or "gesperrt" in t:
        return CLOSURE, "Weg dicht", "urgent", "WEGAFSLUITING"
    if "fahrbahnmanagement" in t or "baustelle" in t:
        return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
    return OBSTACLE, "Verkeerswaarschuwing", "urgent", "OBSTAKEL"

def refresh_de():
    now = time.time()
    roads = json.loads(_get("https://verkehr.autobahn.de/o/autobahn/"))["roads"]
    out = {}
    for road in roads:
        if not re.match(r"^A\d+$", road.strip()):
            continue
        for kind, key in (("warning", "warning"), ("roadworks", "roadworks"), ("closure", "closure")):
            try:
                d = json.loads(_get("https://verkehr.autobahn.de/o/autobahn/%s/services/%s" % (road.strip(), kind), 30))
            except Exception as e:
                log.warning("DE %s/%s: %s", road, kind, e)
                continue
            for it in d.get(key, []):
                try:
                    lat = float(it["coordinate"]["lat"]); lon = float(it["coordinate"]["long"])
                except (KeyError, TypeError, ValueError):
                    continue
                desc = it.get("description") or []
                typ, label, cat, akey = _de_classify(kind, " ".join([it.get("title", "")] + desc))
                start = _iso(it.get("startTimestamp"))
                end = _de_end(desc)
                if start and start > now + 15 * 60:
                    continue
                if end and end < now:
                    continue
                line = []
                g = it.get("geometry") or {}
                if g.get("type") == "LineString":
                    line = _simplify([(c[1], c[0]) for c in g.get("coordinates", [])])
                place = (it.get("title") or "").replace(" | ", " · ").strip()
                sub = (it.get("subtitle") or "").strip()
                rid = it.get("identifier") or "%s-%.5f-%.5f" % (kind, lat, lon)
                out[rid] = _item("DE", rid, typ, label, cat, lat, lon, line if len(line) > 1 else [],
                                 start, end, place + (" (%s)" % sub if sub else ""), "", akey)
            time.sleep(0.12)
    return list(out.values())

def _local(tag):
    return tag.rsplit("}", 1)[-1]

def _es_classify(rtype, f):
    cause = f.get("causeType", "")
    if rtype == "Accident" or cause == "accident":
        return ACCIDENT, "Ongeval", "urgent", "ONGEVAL"
    if rtype == "AbnormalTraffic" or cause == "abnormalTraffic":
        return FILE, "File", "urgent", "FILE"
    if rtype == "SpeedManagement":
        return SPEED, "Snelheid aangepast", "info", "SNELHEID"
    if rtype in ("PoorEnvironmentConditions", "WeatherRelatedRoadConditions"):
        return WEATHER, "Slecht weer", "info", "WEER"
    if rtype in ("NonWeatherRelatedRoadConditions", "VehicleObstruction", "GeneralObstruction",
                 "AnimalPresenceObstruction"):
        return OBSTACLE, "Obstakel", "urgent", "OBSTAKEL"
    if rtype in ("RoadOrCarriagewayOrLaneManagement", "MaintenanceWorks", "ConstructionWorks"):
        if cause == "roadMaintenance" or rtype != "RoadOrCarriagewayOrLaneManagement":
            return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
        m = f.get("roadOrCarriagewayOrLaneManagementType", "").lower()
        if "closed" in m or "closure" in m:
            return CLOSURE, "Weg dicht", "urgent", "WEGAFSLUITING"
        return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
    if cause in ("obstruction", "roadMaintenance"):
        return (OBSTACLE, "Obstakel", "urgent", "OBSTAKEL") if cause == "obstruction" else \
               (WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN")
    return None

def refresh_es():
    now = time.time()
    data = _get("https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml", 90)
    out = {}
    for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
        if _local(el.tag) != "situationRecord":
            continue
        rtype = (el.get("{http://www.w3.org/2001/XMLSchema-instance}type") or "").split(":")[-1]
        rid = el.get("id") or ""
        f, pts = {}, []
        lat = None
        for x in el.iter():
            t = _local(x.tag)
            txt = (x.text or "").strip()
            if t == "latitude" and txt:
                lat = float(txt)
            elif t == "longitude" and txt and lat is not None:
                pts.append((lat, float(txt))); lat = None
            elif txt and t not in f:
                f[t] = txt
        el.clear()
        c = _es_classify(rtype, f)
        if not c or not pts:
            continue
        if f.get("validityStatus") == "suspended":
            continue
        start, end = _iso(f.get("overallStartTime")), _iso(f.get("overallEndTime"))
        if start and start > now + 15 * 60:
            continue
        if end and end < now:
            continue
        place = " · ".join(x for x in (f.get("roadName", ""), f.get("municipality", "")) if x)
        limit = None
        label = c[1]
        if c[0] == SPEED:
            try:
                limit = int(float(f.get("temporarySpeedLimit")))
                label = "Max. %d km/u" % limit
            except (TypeError, ValueError):
                pass
        line = _simplify(pts) if len(pts) > 1 else []
        out[rid] = _item("ES", rid, c[0], label, c[2], pts[0][0], pts[0][1], line, start, end,
                         place, "", c[3], limit)
    return list(out.values())

def _first_point(geom):
    if not geom:
        return None, []
    t, co = geom.get("type"), geom.get("coordinates")
    if t == "Point":
        return (co[1], co[0]), []
    if t == "LineString":
        pts = [(c[1], c[0]) for c in co]
        return pts[0], pts
    if t == "MultiLineString" and co:
        pts = [(c[1], c[0]) for c in co[0]]
        return pts[0], pts
    if t == "MultiPoint" and co:
        return (co[0][1], co[0][0]), []
    return None, []

def refresh_fi():
    now = time.time()
    d = json.loads(_get("https://tie.digitraffic.fi/api/traffic-message/v1/messages?inactiveHours=0"
                        "&includeAreaGeometry=false&situationType=TRAFFIC_ANNOUNCEMENT"
                        "&situationType=ROAD_WORK"))
    out = []
    for ft in d.get("features", []):
        p = ft.get("properties", {})
        pt, line = _first_point(ft.get("geometry"))
        if not pt:
            continue
        ann = (p.get("announcements") or [{}])[0]
        title = (ann.get("title") or "").strip()
        tad = ann.get("timeAndDuration") or {}
        start, end = _iso(tad.get("startTime")), _iso(tad.get("endTime"))
        if start and start > now + 15 * 60:
            continue
        if end and end < now:
            continue
        if p.get("situationType") == "ROAD_WORK":
            typ, label, cat, akey = WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
        else:
            tl = title.lower()
            if "onnettomuus" in tl:
                typ, label, cat, akey = ACCIDENT, "Ongeval", "urgent", "ONGEVAL"
            elif "ruuhka" in tl or "jono" in tl:
                typ, label, cat, akey = FILE, "File", "urgent", "FILE"
            else:
                typ, label, cat, akey = OBSTACLE, "Verkeerswaarschuwing", "urgent", "OBSTAKEL"
        place = title.split(".")[0].replace("Tie ", "Weg ").replace(", eli ", " · ").strip()
        out.append(_item("FI", p.get("situationId", title), typ, label, cat, pt[0], pt[1],
                         _simplify(line) if len(line) > 1 else [], start, end, place, "", akey))
    return out

def _datex_classify(rtype, f):
    mgmt = f.get("roadOrCarriagewayOrLaneManagementType", "").lower()
    if rtype == "Accident":
        return ACCIDENT, "Ongeval", "urgent", "ONGEVAL"
    if rtype == "AbnormalTraffic":
        return FILE, "File", "urgent", "FILE"
    if rtype in ("VehicleObstruction", "GeneralObstruction", "AnimalPresenceObstruction",
                 "EnvironmentalObstruction", "InfrastructureDamageObstruction",
                 "NonWeatherRelatedRoadConditions"):
        return OBSTACLE, "Obstakel", "urgent", "OBSTAKEL"
    if rtype in ("PoorEnvironmentConditions", "WeatherRelatedRoadConditions"):
        return WEATHER, "Slecht weer", "info", "WEER"
    if rtype == "SpeedManagement":
        return SPEED, "Snelheid aangepast", "info", "SNELHEID"
    if rtype == "ReroutingManagement":
        return 9, "Omleiding", "info", "OMLEIDING"
    if rtype in ("MaintenanceWorks", "ConstructionWorks", "RoadworksManagement"):
        return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
    if rtype == "RoadOrCarriagewayOrLaneManagement":
        if "weight" in mgmt or "width" in mgmt or "height" in mgmt:
            return None
        if mgmt in ("roadclosed", "closedpermanentlyforthewinter", "carriagewayclosures") or "closed" in mgmt:
            return CLOSURE, "Weg dicht", "urgent", "WEGAFSLUITING"
        if "lane" in mgmt:
            return WORKS, "Rijstrook dicht", "works", "RIJSTROOK DICHT"
        return WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN"
    return None

def _datex_records(data):
    for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
        if _local(el.tag) != "situationRecord":
            continue
        rtype = (el.get("{http://www.w3.org/2001/XMLSchema-instance}type") or "").split(":")[-1]
        rid = el.get("id") or ""
        f, pts, comments = {}, [], []
        lat = None
        for x in el.iter():
            t = _local(x.tag)
            txt = (x.text or "").strip()
            if t == "latitude" and txt:
                lat = float(txt)
            elif t == "longitude" and txt and lat is not None:
                pts.append((lat, float(txt))); lat = None
            elif t == "posList" and txt and not pts:
                n = [float(v) for v in txt.split()]
                poly = list(zip(n[0::2], n[1::2]))
                if poly:
                    pts.append((sum(a for a, _ in poly) / len(poly), sum(b for _, b in poly) / len(poly)))
            elif t == "value" and txt:
                comments.append(txt)
            elif txt and t not in f:
                f[t] = txt
        el.clear()
        yield rid, rtype, f, pts, comments

_FR_TOWN = re.compile(r"situ[ée] [^,]*? (?:de la |de l'|du |des |de |d')([^,\n]+?)\s*(?:,|$)")

def refresh_fr():
    now = time.time()
    data = _get("http://tipi.bison-fute.gouv.fr/bison-fute-ouvert/publicationsDIR/Evenementiel-DIR/grt/RRN/content.xml", 90)
    out = {}
    for rid, rtype, f, pts, comments in _datex_records(data):
        c = _datex_classify(rtype, f)
        if not c or not pts:
            continue
        start, end = _iso(f.get("overallStartTime")), _iso(f.get("overallEndTime"))
        if start and start > now + 15 * 60:
            continue
        if end and end < now:
            continue
        road = re.sub(r"^([A-Z]+)0*(\d+)", r"\1\2", f.get("roadNumber", ""))
        town = ""
        for cm in comments:
            m = _FR_TOWN.search(cm.split("\n")[0])
            if m:
                town = m.group(1).strip(); break
        place = " · ".join(x for x in (road, town) if x)
        label = c[1]
        limit = None
        if c[0] == SPEED:
            try:
                limit = int(float(f.get("temporarySpeedLimit")))
                label = "Max. %d km/u" % limit
            except (TypeError, ValueError):
                pass
        out[rid] = _item("FR", rid, c[0], label, c[2], pts[0][0], pts[0][1],
                         _simplify(pts) if len(pts) > 1 else [], start, end, place, "", c[3], limit)
    return list(out.values())

PT_UNPLANNED = ("https://dadosabertos.cm-porto.pt/dataset/539db002-9e19-11f1-84ed-6abdb6d5cf34/resource/"
                "75a3447c-bf9d-4c02-b3b7-aaecf5f00d2c/download/condicionamentos_nao_programados.xml")
PT_PLANNED = ("https://dadosabertos.cm-porto.pt/dataset/538f30de-9e19-11f1-84ed-6abdb6d5cf34/resource/"
              "36f62a04-9168-4bc5-a499-a3101cd77168/download/condicionamentos_programados.xml")
_pt_planned = {"t": 0, "items": []}

def _porto(data, now, planned):
    out = {}
    for rid, rtype, f, pts, comments in _datex_records(data):
        c = _datex_classify(rtype, f) or ((WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN") if planned else None)
        if not c or not pts:
            continue
        start, end = _iso(f.get("overallStartTime")), _iso(f.get("overallEndTime"))
        if start and start > now + 15 * 60:
            continue
        if end and end < now:
            continue
        if planned and not end and start and start < now - 30 * 86400:
            continue
        rid = rid.rsplit(":", 1)[-1]
        place = " · ".join(x for x in (f.get("roadName", ""), "Porto") if x)
        out[rid] = _item("PT", rid, c[0], c[1], c[2], pts[0][0], pts[0][1], [], start, end, place, "", c[3])
    return list(out.values())

def refresh_pt():
    now = time.time()
    items = _porto(_get(PT_UNPLANNED, 60), now, False)
    if now - _pt_planned["t"] > 3600:
        _pt_planned["items"] = _porto(_get(PT_PLANNED, 120), now, True)
        _pt_planned["t"] = now
    else:
        _pt_planned["items"] = [i for i in _pt_planned["items"] if not i["end"] or i["end"] / 1000 >= now]
    return items + _pt_planned["items"]

BXL = "http://data-mobility.brussels/mobiris/events/?events=all"
GIPOD = "https://geo.api.vlaanderen.be/GIPOD/ogc/features/v1/collections/HINDERGEVOLG_PUNT/items"
_gipod = {"t": 0, "items": []}

def _bxl_time(s):
    if not s:
        return None
    try:
        from zoneinfo import ZoneInfo
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("Europe/Brussels")).timestamp()
    except Exception:
        return None

def _brussels(now):
    d = json.loads(_get(BXL, 60))
    out = []
    for ft in d.get("features", []):
        p = ft.get("properties", {})
        g = ft.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        start, end = _bxl_time(p.get("start_time")), _bxl_time(p.get("end_time"))
        if start and start > now + 15 * 60:
            continue
        if end and end < now:
            continue
        code = (p.get("datex_codes") or "").upper()
        cons = (p.get("consequences_nl") or "").lower()
        if any(w in cons for w in ("voetpad", "fietspad", "buiten rijweg", "trottoir")):
            continue
        if code == "ACI":
            c = (ACCIDENT, "Ongeval", "urgent", "ONGEVAL")
        elif code in ("RCA", "RCD", "CLS") or "gesloten" in (p.get("type_nl") or "").lower():
            c = (CLOSURE, "Weg dicht", "urgent", "WEGAFSLUITING")
        elif code in ("RWK", "RWM", "WOR"):
            c = (CLOSURE, "Weg dicht", "works", "WEGAFSLUITING") if "afgesloten" in cons else \
                (WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN")
        elif code in ("LS1", "LS2", "LS3", "JAM", "QUE"):
            c = (FILE, "File", "urgent", "FILE")
        else:
            c = (OBSTACLE, "Verkeerswaarschuwing", "urgent", "OBSTAKEL")
        place = " · ".join(x for x in (p.get("location_nl"), "Brussel") if x)
        out.append(_item("BE", ft.get("id", place), c[0], c[1], c[2], lat, lon, [], start, end,
                         place, p.get("consequences_nl") or "", c[3]))
    return out

def _gipod_owner(o):
    o = (o or "").split(" - ")[0].strip()
    for pre in ("Stad ", "Gemeente ", "Stadsbestuur ", "Gemeentebestuur "):
        if o.startswith(pre):
            return o[len(pre):]
    return "Wegen en Verkeer" if o.startswith("Agentschap Wegen") else o

def _flanders(now):
    stamp = datetime.utcfromtimestamp(now).strftime("%Y-%m-%dT%H:%M:%SZ")
    flt = ("SevereHindrance=true AND ConsequenceTreeLevel0='Gemotoriseerd verkeer' AND "
           "HindranceStart<=TIMESTAMP('%s') AND HindranceEnd>=TIMESTAMP('%s')" % (stamp, stamp))
    import urllib.parse
    url = GIPOD + "?" + urllib.parse.urlencode({"f": "json", "limit": 1000, "filter": flt,
                                                "filter-lang": "cql2-text"})
    out, pages = {}, 0
    while url and pages < 40:
        d = json.loads(_get(url, 120))
        pages += 1
        for ft in d.get("features", []):
            p = ft.get("properties", {})
            g = ft.get("geometry") or {}
            if g.get("type") != "Point":
                continue
            lon, lat = g["coordinates"][:2]
            lvl = p.get("ConsequenceTreeLevel1") or ""
            if lvl.startswith("Geen doorgang"):
                c = (CLOSURE, "Weg dicht", "works", "WEGAFSLUITING")
            elif lvl.startswith("Afgesloten in 1 rijrichting"):
                c = (CLOSURE, "Rijbaan dicht", "works", "AFSLUITING")
            elif lvl == "Snelheidsbeperking":
                c = (SPEED, "Snelheid aangepast", "info", "SNELHEID")
            elif lvl.startswith(("Beperkte doorgang", "Wisselend verkeer")):
                c = (WORKS, "Wegwerkzaamheden", "works", "WERKZAAMHEDEN")
            else:
                continue
            hid = (p.get("HindranceUri") or "").rsplit("/", 1)[-1] + "-" + (p.get("ZoneId") or "")[:8]
            out[hid] = _item("BE", hid, c[0], c[1], c[2], lat, lon, [],
                             _iso(p.get("HindranceStart")), _iso(p.get("HindranceEnd")),
                             _gipod_owner(p.get("HindranceOwner")), p.get("Consequence") or "", c[3])
        url = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
    return list(out.values())

def refresh_be():
    now = time.time()
    items = []
    try:
        items += _brussels(now)
    except Exception as e:
        log.warning("BE Brussel: %s", e)
    if now - _gipod["t"] > 1800:
        try:
            _gipod["items"] = _flanders(now)
            _gipod["t"] = now
        except Exception as e:
            log.warning("BE GIPOD: %s", e)
    else:
        _gipod["items"] = [i for i in _gipod["items"] if not i["end"] or i["end"] / 1000 >= now]
    return items + _gipod["items"]

SOURCES = {"DE": (refresh_de, 600), "ES": (refresh_es, 300), "FI": (refresh_fi, 300),
           "FR": (refresh_fr, 300), "PT": (refresh_pt, 300), "BE": (refresh_be, 300)}

def _worker(cc):
    fn, every = SOURCES[cc]
    while True:
        try:
            items = fn()
            with _lock:
                if items or not _items[cc]:
                    _items[cc] = items
                    _updated[cc] = int(time.time() * 1000)
            log.warning("%s: %d meldingen", cc, len(items))
        except Exception as e:
            log.warning("%s mislukt: %s", cc, e)
        time.sleep(every)

def start():
    for cc in SOURCES:
        threading.Thread(target=_worker, args=(cc,), daemon=True).start()

def snapshot():
    with _lock:
        return [dict(i) for cc in _items for i in _items[cc]], dict(_updated)

def near(lat, lon, radius_m):
    dlat = radius_m / 110540.0
    dlon = radius_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    out = []
    with _lock:
        for cc in _items:
            for it in _items[cc]:
                pts = it["line"] or [(it["lat"], it["lon"])]
                for a, b in pts:
                    if abs(a - lat) <= dlat and abs(b - lon) <= dlon:
                        out.append(dict(it))
                        break
    return out
