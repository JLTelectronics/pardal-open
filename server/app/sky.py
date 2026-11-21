import gzip
import json
import logging
import math
import os
import re
import threading
import time
import urllib.request

log = logging.getLogger("roadping.sky")
UA = {"User-Agent": "Pardal-server (open-source)", "Accept-Encoding": "gzip"}

CENTER = (52.2, 5.3)
ADSB_URL = "https://api.adsb.lol/v2/point/%.1f/%.1f/200" % CENTER
LOCAL_URL = os.environ.get("ROADPING_ADSB_URL", "")
SONDE_URL = "https://api.v2.sondehub.org/sondes?lat=%.1f&lon=%.1f&distance=450000&last=10800" % CENTER
PRED_URL = "https://api.v2.sondehub.org/predictions?vehicles="

HELI_TYPES = {"EC35", "EC45", "H145", "EC30", "EC20", "EC25", "EC55", "EC75", "EC135", "A139", "A169",
              "A109", "A119", "AS50", "AS55", "AS65", "AS32", "S92", "S76", "B06", "B407", "B429",
              "R44", "R22", "R66", "NH90", "H160", "H175", "AS3B", "EH10", "CH47", "H47", "H64",
              "MD52", "MD60", "B505", "G2CA", "EXPL", "AW09", "H130", "H125", "H135"}

_lock = threading.Lock()
_helis = []
_sondes = []
_updated = {"helis": 0, "sondes": 0}
_pred = {}

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(20 * 1024 * 1024)
        if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
    return json.loads(data)

def classify(cs, reg, typ):
    cs = (cs or "").upper().replace(" ", "")
    reg = (reg or "").upper()
    if cs.startswith(("LIFELN", "LIFE", "CHX", "HEMS", "MMT", "SAMU", "DRF", "ADAC")) or \
            reg in ("PH-ELP", "PH-HVB", "PH-ULP", "PH-MAA", "PH-DOC", "PH-LLN", "PH-TTY", "PH-MMT"):
        return "traumaheli"
    if cs.startswith(("POLITIE", "POLICE", "POL", "PPH", "PHPX", "ZEPPELIN", "HUMMEL", "EDELWEISS")) or \
            reg.startswith("PH-PX") or cs.startswith("PHPX"):
        return "politie"
    if cs.startswith(("SAR", "KUSTW", "RESCUE", "COASTGUARD")) or reg.startswith("PH-SAR"):
        return "kustwacht"
    return "helikopter"

def _adsb():
    url = LOCAL_URL or ADSB_URL
    d = _get(url)
    ac = d.get("ac") or d.get("aircraft") or []
    out = []
    for a in ac:
        lat, lon = a.get("lat"), a.get("lon")
        if lat is None or lon is None:
            continue
        typ = (a.get("t") or "").upper()
        if a.get("category") != "A7" and typ not in HELI_TYPES:
            continue
        alt = a.get("alt_baro")
        if alt == "ground":
            alt = 0
        if (a.get("seen_pos") or 0) > 60:
            continue
        cs = (a.get("flight") or "").strip()
        reg = (a.get("r") or "").strip()
        out.append({"id": a.get("hex", ""), "kind": classify(cs, reg, typ), "cs": cs, "reg": reg,
                    "type": typ, "lat": round(lat, 4), "lon": round(lon, 4),
                    "alt": int(alt * 0.3048) if isinstance(alt, (int, float)) else None,
                    "kmh": int(a["gs"] * 1.852) if isinstance(a.get("gs"), (int, float)) else None,
                    "trk": int(a["track"]) if isinstance(a.get("track"), (int, float)) else None})
    return out

def _landing(serials, now):
    todo = [s for s in serials if now - _pred.get(s, (0, None))[0] > 300]
    if todo:
        try:
            for p in _get(PRED_URL + ",".join(todo[:20])):
                data = p.get("data")
                if isinstance(data, str):
                    data = json.loads(data)
                if data:
                    last = data[-1]
                    lo = last["lon"] - 360 if last["lon"] > 180 else last["lon"]
                    _pred[p.get("vehicle")] = (now, (round(last["lat"], 4), round(lo, 4)))
        except Exception as e:
            log.info("sondehub-voorspelling: %s", e)
        for s in todo:
            if _pred.get(s, (0,))[0] != now:
                _pred[s] = (now, _pred.get(s, (0, None))[1])
    for s in list(_pred):
        if s not in serials and now - _pred[s][0] > 3600:
            del _pred[s]
    return {s: _pred.get(s, (0, None))[1] for s in serials}

def _iso(s):
    from datetime import datetime
    try:
        return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def _sondes_fetch(now):
    d = _get(SONDE_URL)
    out = []
    for serial, v in (d or {}).items():
        t = _iso(v.get("datetime", ""))
        if not t or now - t > 3 * 3600 or v.get("lat") is None:
            continue
        out.append({"id": serial, "type": v.get("type") or v.get("subtype") or "",
                    "lat": round(v["lat"], 4), "lon": round(v["lon"], 4),
                    "alt": int(v.get("alt") or 0), "vz": round(v.get("vel_v") or 0, 1),
                    "mhz": round(v.get("frequency") or 0, 3), "time": int(t * 1000)})
    land = _landing([s["id"] for s in out if now - s["time"] / 1000 < 1800 and s["alt"] > 500], now)
    for s in out:
        s["land"] = land.get(s["id"])
    out.sort(key=lambda s: -s["time"])
    return out[:40]

def _worker():
    global _helis, _sondes
    last_sonde = 0
    while True:
        now = time.time()
        try:
            h = _adsb()
            with _lock:
                _helis = h
                _updated["helis"] = int(now * 1000)
        except Exception as e:
            log.warning("adsb: %s", e)
            with _lock:
                if now - _updated["helis"] / 1000 > 120:
                    _helis = []
        if now - last_sonde >= 60:
            last_sonde = now
            try:
                s = _sondes_fetch(now)
                with _lock:
                    _sondes = s
                    _updated["sondes"] = int(now * 1000)
            except Exception as e:
                log.warning("sondehub: %s", e)
        time.sleep(15)

def start():
    threading.Thread(target=_worker, daemon=True).start()

def snapshot():
    with _lock:
        return {"helis": list(_helis), "sondes": list(_sondes), "updated": dict(_updated),
                "own_receiver": bool(LOCAL_URL)}

def helis_near(lat, lon, radius_m):
    out = []
    with _lock:
        for h in _helis:
            dy = (h["lat"] - lat) * 110540.0
            dx = (h["lon"] - lon) * 111320.0 * math.cos(math.radians(lat))
            if dx * dx + dy * dy <= radius_m * radius_m:
                out.append(dict(h))
    return out
