import gzip
import io
import logging
import math
import struct
import threading
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

log = logging.getLogger("roadping.msi")
LOC_URL = "https://opendata.ndw.nu/ndw_msi_shapefiles_latest.zip"
LIVE_URL = "https://opendata.ndw.nu/Matrixsignaalinformatie.xml.gz"
UA = {"User-Agent": "Pardal-server (open-source)"}
STATES = {"blank": 1, "speedlimit": 2, "lane_closed": 3, "lane_closed_ahead": 4,
          "restriction_end": 5, "lane_open": 6}

_lock = threading.Lock()
_locs = {}
_locs_at = 0
_live = {}
_live_at = 0
_wanted = 0

def _get(url, timeout=90):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read(200 * 1024 * 1024)

def _field(rec, off, ln):
    return rec[off:off + ln].decode("latin-1").strip()

def load_locations():
    global _locs, _locs_at
    z = zipfile.ZipFile(io.BytesIO(_get(LOC_URL)))
    shp = dbf = None
    for n in z.namelist():
        if n.lower().endswith(".shp"):
            shp = z.read(n)
        elif n.lower().endswith(".dbf"):
            dbf = z.read(n)
    if not shp or not dbf:
        raise ValueError("MSI-shapefile onvolledig")
    n = struct.unpack_from("<I", dbf, 4)[0]
    hlen, rlen = struct.unpack_from("<HH", dbf, 8)
    names, lens = [], []
    o = 32
    while dbf[o] != 0x0D:
        names.append(dbf[o:o + 11].split(b"\0")[0].decode("latin-1").lower())
        lens.append(dbf[o + 16])
        o += 32
    offs, p = [], 1
    for ln in lens:
        offs.append(p)
        p += ln

    def col(name):
        return names.index(name) if name in names else -1
    cu, cr, cc, ck, cb, cl = (col(x) for x in ("uuid", "road", "carriagew0", "km", "bearing", "lane"))
    if cu < 0 or cb < 0:
        raise ValueError("MSI-dbf: kolommen ontbreken")
    out = {}
    pos = 100
    for i in range(n):
        if pos + 8 > len(shp):
            break
        words = struct.unpack_from(">I", shp, pos + 4)[0]
        c = pos + 8
        pos = c + words * 2
        if struct.unpack_from("<i", shp, c)[0] != 1:
            continue
        x, y = struct.unpack_from("<dd", shp, c + 4)
        rec = dbf[hlen + i * rlen: hlen + (i + 1) * rlen]
        uuid = _field(rec, offs[cu], lens[cu])
        try:
            brg = float(_field(rec, offs[cb], lens[cb]))
        except ValueError:
            continue
        if not uuid:
            continue
        portal = "".join(_field(rec, offs[k], lens[k]) if k >= 0 else "" for k in (cr, cc, ck))
        lane = 0
        if cl >= 0:
            try:
                lane = max(0, min(20, int(float(_field(rec, offs[cl], lens[cl])))))
            except ValueError:
                pass
        out[uuid] = (round(y, 6), round(x, 6), round(brg, 1), portal, lane)
    with _lock:
        _locs = out
        _locs_at = time.time()
    log.warning("msi: %d borden", len(out))

def load_live():
    global _live, _live_at
    raw = _get(LIVE_URL)
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    live = {}
    uuid = disp = spd = None
    in_sign = in_disp = False
    for ev, el in ET.iterparse(io.BytesIO(raw), events=("start", "end")):
        tag = el.tag.rsplit("}", 1)[-1]
        if ev == "start":
            if tag == "event":
                uuid = disp = spd = None
            elif tag == "sign_id":
                in_sign = True
            elif tag == "display":
                in_disp = True
            elif in_disp and disp is None:
                disp = tag
        else:
            if tag == "uuid" and in_sign:
                uuid = (el.text or "").strip()
            elif tag == "speedlimit" and in_disp:
                spd = (el.text or "").strip()
            elif tag == "sign_id":
                in_sign = False
            elif tag == "display":
                in_disp = False
            elif tag == "event":
                if uuid and disp:
                    s = STATES.get(disp, 0)
                    v = 0
                    if s == 2 and spd:
                        try:
                            v = int(spd)
                        except ValueError:
                            pass
                    live[uuid] = (s, v)
                el.clear()
    with _lock:
        _live = live
        _live_at = time.time()

def _worker():
    last_loc_try = 0
    while True:
        now = time.time()
        if now - _locs_at > 7 * 86400 and now - last_loc_try > 3600:
            last_loc_try = now
            try:
                load_locations()
            except Exception as e:
                log.warning("msi-locaties: %s", e)
        if _locs and now - _wanted < 900 and now - _live_at >= 60:
            try:
                load_live()
            except Exception as e:
                log.warning("msi-live: %s", e)
        time.sleep(10)

def start():
    threading.Thread(target=_worker, daemon=True).start()

def near(lat, lon, radius_m):
    global _wanted
    _wanted = time.time()
    with _lock:
        if not _live or time.time() - _live_at > 600:
            return None, _live_at
        dl = radius_m / 110540.0
        dk = radius_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
        out = []
        for uuid, (la, lo, brg, portal, lane) in _locs.items():
            if abs(la - lat) > dl or abs(lo - lon) > dk:
                continue
            st, sp = _live.get(uuid, (0, 0))
            out.append([la, lo, brg, portal, lane, st, sp])
        return out, _live_at
