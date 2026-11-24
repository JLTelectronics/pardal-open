import copy
import hashlib
import json
import logging
import os
import threading

log = logging.getLogger("roadping.config")

DEFAULT = {
    "version": 1,
    "types": [
        {"id": 1, "name": "Politie", "key": "POLITIE", "color": "#4C8DFF", "icon": "police", "life_min": 45, "ttl_min": 45,
         "merge_m": 250, "report": 1, "alert": True, "quiet": False, "planned": False, "sound": "POLITIE"},
        {"id": 2, "name": "Hulpdienst", "key": "AMBULANCE", "color": "#FFC93C", "icon": "ambulance", "life_min": 20, "ttl_min": 20,
         "merge_m": 250, "report": 6, "alert": True, "quiet": False, "planned": False, "sound": "HULPDIENST",
         "report_key": "HULPDIENST"},
        {"id": 3, "name": "File", "key": "FILE", "color": "#FF7A00", "icon": "file", "life_min": 60, "ttl_min": 30,
         "merge_m": 700, "report": 2, "alert": True, "quiet": False, "planned": False, "sound": "FILE"},
        {"id": 4, "name": "Ongeval", "key": "ONGEVAL", "color": "#FF4A3D", "icon": "accident", "life_min": 90, "ttl_min": 60,
         "merge_m": 250, "report": 3, "alert": True, "quiet": False, "planned": False, "sound": "ONGEVAL"},
        {"id": 5, "name": "Werkzaamheden", "key": "WERKZAAMHEDEN", "color": "#FFB020", "icon": "works", "life_min": 480, "ttl_min": 240,
         "merge_m": 250, "report": 4, "alert": True, "quiet": True, "planned": True, "sound": "WERKZAAMHEDEN",
         "report_key": "WERK"},
        {"id": 6, "name": "Obstakel", "key": "OBSTAKEL", "color": "#22C7A9", "icon": "obstacle", "life_min": 120, "ttl_min": 45,
         "merge_m": 250, "report": 5, "alert": True, "quiet": False, "planned": False, "sound": "OBSTAKEL"},
        {"id": 7, "key": "WEGAFSLUITING", "color": "#FF4A3D", "icon": "closure", "life_min": 60,
         "report": 0, "alert": True, "quiet": False, "planned": True, "sound": "AFSLUITING"},
        {"id": 8, "key": "SNELHEID", "color": "#35C4F0", "icon": "speed", "life_min": 60,
         "report": 0, "alert": True, "quiet": False, "planned": True, "sound": "SNELHEID"},
        {"id": 9, "key": "OMLEIDING", "color": "#B388FF", "icon": "reroute", "life_min": 60,
         "report": 0, "alert": False, "quiet": True, "planned": True, "sound": "WERKZAAMHEDEN"},
        {"id": 10, "key": "WEER", "color": "#5AD1C8", "icon": "weather", "life_min": 60,
         "report": 0, "alert": True, "quiet": True, "planned": False, "sound": "WEER"},
        {"id": 11, "key": "BRUG", "color": "#C98CFF", "icon": "bridge", "life_min": 60,
         "report": 0, "alert": True, "quiet": False, "planned": False, "sound": "BRUG"},
        {"id": 12, "key": "MELDING", "color": "#FF6A00", "icon": "obstacle", "life_min": 60,
         "report": 0, "alert": False, "quiet": False, "planned": False, "sound": "OBSTAKEL"},
    ],
    "flags": {
        "community": True,
        "report": True,
        "ndw": True,
        "msi": True,
        "signs": True,
        "buildings": True,
        "nav": True,
    },
    "countries": {
        "NL": {},
        "BE": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "DE": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "LU": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "BR": {"flags": {"ndw": False, "msi": False, "signs": False, "buildings": False, "nav": False}},
        "PT": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "ES": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "FR": {"flags": {"msi": False, "signs": False, "buildings": False}},
        "AT": {"flags": {"ndw": False, "msi": False, "signs": False, "buildings": False, "nav": False}},
        "CH": {"flags": {"ndw": False, "msi": False, "signs": False, "buildings": False, "nav": False}},
        "IT": {"flags": {"ndw": False, "msi": False, "signs": False, "buildings": False, "nav": False}},
        "DK": {"flags": {"ndw": False, "msi": False, "signs": False, "buildings": False, "nav": False}},
    },
    "report_areas": [[50.6, 3.2, 53.7, 7.3],
                     [36.9, -9.6, 42.2, -6.1], [32.3, -17.4, 33.2, -16.2], [36.8, -31.4, 39.8, -24.9],
                     [35.9, -7.6, 42.4, 3.35], [42.4, -9.4, 43.8, -1.8], [42.2, -1.8, 42.8, 0.7],
                     [38.6, 1.1, 40.1, 4.4], [27.6, -18.2, 29.5, -13.3]],
    "update": {
        "ios": {"min_build": 0, "min_version": "", "store": "https://apps.apple.com/app/id6836411492"},
        "android": {"min_build": 0, "min_version": "",
                    "store": "https://play.google.com/store/apps/details?id=com.pardal.app"},
        "message": {},
    },
    "messages": [],
    "texts": {},
}

_lock = threading.Lock()
_state = {"mtime": None, "cfg": copy.deepcopy(DEFAULT), "hash": None}

def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k == "types" and isinstance(v, list):
            by = {t["id"]: t for t in out.get("types", [])}
            for t in v:
                if not isinstance(t, dict) or not isinstance(t.get("id"), int):
                    continue
                if t.get("remove"):
                    by.pop(t["id"], None)
                else:
                    by[t["id"]] = _merge(by.get(t["id"], {}), t)
            out["types"] = sorted(by.values(), key=lambda t: t["id"])
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out

def _check(cfg):
    for t in cfg["types"]:
        if not (1 <= t["id"] <= 99):
            raise ValueError("type-id buiten 1..99: %r" % t["id"])
        if not isinstance(t.get("key"), str) or not t["key"]:
            raise ValueError("type %d zonder key" % t["id"])
        c = t.get("color", "#FF6A00")
        if not (isinstance(c, str) and len(c) == 7 and c[0] == "#"):
            raise ValueError("type %d: kleur moet #RRGGBB zijn" % t["id"])
    for a in cfg.get("report_areas", []):
        if len(a) != 4:
            raise ValueError("report_areas: [min_lat, min_lon, max_lat, max_lon]")
    for k, u in (cfg.get("update") or {}).items():
        if k in ("ios", "android") and not isinstance(u.get("min_build", 0), int):
            raise ValueError("update.%s.min_build moet een geheel getal zijn" % k)
    for m in cfg.get("messages", []):
        if not m.get("id"):
            raise ValueError("bericht zonder id")

def load(data_dir):
    p = os.path.join(data_dir, "config.json")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        mt = None
    with _lock:
        if _state["hash"] is not None and mt == _state["mtime"]:
            return _state["cfg"]
        cfg = copy.deepcopy(DEFAULT)
        if mt is not None:
            try:
                with open(p, encoding="utf-8") as f:
                    cand = _merge(DEFAULT, json.load(f))
                _check(cand)
                cfg = cand
            except Exception as e:
                log.warning("config.json genegeerd: %s", e)
                if _state["hash"] is not None:
                    _state["mtime"] = mt
                    return _state["cfg"]
        _state["cfg"] = cfg
        _state["mtime"] = mt
        _state["hash"] = hashlib.sha1(json.dumps(cfg, sort_keys=True, separators=(",", ":"))
                                      .encode()).hexdigest()[:16]
        return cfg

def hash_(data_dir):
    load(data_dir)
    return _state["hash"]

def type_def(data_dir, typ):
    for t in load(data_dir)["types"]:
        if t["id"] == typ:
            return t
    return None

def reportable(data_dir, typ):
    t = type_def(data_dir, typ)
    return t is not None and t.get("report", 0) > 0

def ttl_s(data_dir, typ):
    t = type_def(data_dir, typ) or {}
    return int(t.get("ttl_min", t.get("life_min", 60))) * 60

def merge_m(data_dir, typ):
    t = type_def(data_dir, typ) or {}
    return int(t.get("merge_m", 250))

def label(data_dir, typ):
    t = type_def(data_dir, typ) or {}
    return t.get("name") or t.get("key", "MELDING").capitalize()

def in_report_area(data_dir, lat, lon):
    return any(a[0] <= lat <= a[2] and a[1] <= lon <= a[3] for a in load(data_dir).get("report_areas", []))
