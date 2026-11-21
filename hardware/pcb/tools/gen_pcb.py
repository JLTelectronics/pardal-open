import ast, json, math, os, re, sys
import pcbnew

HIER = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HIER, '..', 'pardal.kicad_pcb')
KICAD_FP = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'

sys.path.insert(0, HIER)
from maten import P
mm = pcbnew.FromMM

OX, OY = 148.5, 105.0

def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))

def pol(r, graden):
    a = math.radians(graden)
    return r * math.cos(a), r * math.sin(a)

def lijn(board, a, b, laag, breedte=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))
    s.SetLayer(laag)
    s.SetWidth(mm(breedte))
    board.Add(s)

def cirkel(board, x, y, d, laag, breedte=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(pt(x, y))
    s.SetEnd(pt(x + d / 2, y))
    s.SetLayer(laag)
    s.SetWidth(mm(breedte))
    board.Add(s)

def rechthoek(board, cx, cy, l, w, laag, breedte=0.12):
    hoeken = [(cx - l / 2, cy - w / 2), (cx + l / 2, cy - w / 2), (cx + l / 2, cy + w / 2), (cx - l / 2, cy + w / 2)]
    for i in range(4):
        lijn(board, hoeken[i], hoeken[(i + 1) % 4], laag, breedte)

def sector(board, naam, midden, boog, r0, r1):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    z.SetZoneName('Antenne ' + naam)
    n = 24
    a0, a1 = midden - boog / 2, midden + boog / 2
    punten = [pol(r1, a0 + (a1 - a0) * i / n) for i in range(n + 1)] + \
             [pol(r0, a1 - (a1 - a0) * i / n) for i in range(n + 1)]
    ol = z.Outline()
    ol.NewOutline()
    for x, y in punten:
        ol.Append(mm(OX + x), mm(OY - y))
    board.Add(z)

def gat(board, x, y, ref, naam='MountingHole_2.2mm_M2_Pad_Via'):
    fp = pcbnew.FootprintLoad(os.path.join(KICAD_FP, 'MountingHole.pretty'), naam)
    fp.SetReference(ref)
    fp.SetPosition(pt(x, y))
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY)
    board.Add(fp)

MIC1_X, MIC1_Y = -30.0, -35.0
MIC2_X, MIC2_Y = -18.0, -33.5
EDL_X, EDL_Y = -6.0, -30.0
ALS_HOEK, ALS_R = 60.0, 39.5
ANTENNES = (('GNSS', 90, 30), ('LTE hoofd', 37, 36), ('WiFi/BT', 320, 40))
CM3_X, CM3_Y = P['cm3_x'], P['cm3_y']
MDM_X, MDM_Y = P['mdm_x'], P['mdm_y']
CM3_CON = json.load(open(os.path.join(HIER, '..', 'datasheets', 'rockchip', 'cm3_connector_posities.json')))
CM3_GATEN = ((-16.5, -24.0), (16.5, -24.0), (-16.5, 24.0), (16.5, 24.0))

LOKAAL = {'Pardal': os.path.join(HIER, '..', 'libs', 'Pardal.pretty'), 'lcsc': os.path.join(HIER, '..', 'libs', 'lcsc.pretty')}
NETLIST = os.path.join(HIER, '..', 'build', 'pardal.net')

def vaste_plaatsen():
    r = P['print_d'] / 2
    return {
        'CN1': (CM3_X + CM3_CON['J69'][0], CM3_Y - CM3_CON['J69'][1], 0, 'F'),
        'CN2': (CM3_X + CM3_CON['J68'][0], CM3_Y - CM3_CON['J68'][1], 0, 'F'),
        'CN3': (CM3_X + CM3_CON['J1'][0], CM3_Y - CM3_CON['J1'][1], 0, 'F'),
        'U2': (MDM_X, MDM_Y, 90, 'F'),
        'SW3': (P['knop_x'], P['knop_y'], 0, 'F'),
        'J2': (0, -(r - 2.4), 0, 'B'),
        'SW1': (r - 2.5, 0, 90, 'B'),
        'SW2': (-(r - 2.5), 0, 270, 'B'),
        'J3': (-1.5, -33.5, 0, 'B'),
        'J4': (25, -33.5, 0, 'B'),
        'J5': (39, 0, 90, 'B'),
        'J1': (-12, 22.5, 180, 'B'),
        'J6': (-40, -15, 0, 'F'),
        'J10': (8.5, 45.0, 0, 'F'),
        'SW4': (EDL_X, EDL_Y, 0, 'F'),
        'J9': (6.0, -27.0, 0, 'F'),
        'MK1': (MIC1_X, MIC1_Y, 0, 'F'),
        'MK2': (MIC2_X, MIC2_Y, 0, 'F'),
    }

def laad_fp(fpid):
    lib, naam = fpid.split(':', 1)
    pad = LOKAAL.get(lib, os.path.join(KICAD_FP, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(pad, naam)
    if fp is None:
        raise RuntimeError('footprint niet gevonden: ' + fpid)
    return fp

def printrand(board):
    import math
    r, b, y0 = P['print_d'] / 2, P['gps_b'] / 2 + 0.6, P['gps_y0'] - 0.4
    yc = math.sqrt(r * r - b * b)
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(pt(b, yc), pt(0, -r), pt(-b, yc))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    board.Add(s)
    lijn(board, (-b, yc), (-b, y0), pcbnew.Edge_Cuts)
    lijn(board, (-b, y0), (b, y0), pcbnew.Edge_Cuts)
    lijn(board, (b, y0), (b, yc), pcbnew.Edge_Cuts)

def onderdelen(board):
    import sys
    sys.path.insert(0, HIER)
    import kilib
    tree = kilib.parse(open(NETLIST).read())
    comps = kilib.find1(tree, 'components')
    nets = kilib.find1(tree, 'nets')
    padnet = {}
    for n in kilib.find(nets, 'net'):
        naam = str(kilib.find1(n, 'name')[1]).lstrip('/')
        for nd in kilib.find(n, 'node'):
            padnet[(str(kilib.find1(nd, 'ref')[1]), str(kilib.find1(nd, 'pin')[1]))] = naam
    netobj = {}

    def net(naam):
        if naam not in netobj:
            ni = pcbnew.NETINFO_ITEM(board, naam)
            board.Add(ni)
            netobj[naam] = ni
        return netobj[naam]

    vast = vaste_plaatsen()
    los_x, los_y, kolom = 60.0, 40.0, 0
    for c in kilib.find(comps, 'comp'):
        ref = str(kilib.find1(c, 'ref')[1])
        if ref.startswith('#'):
            continue
        fpid = str(kilib.find1(c, 'footprint')[1])
        fp = laad_fp(fpid)
        lib, naam = fpid.split(':', 1)
        fp.SetFPID(pcbnew.LIB_ID(lib, naam))
        sp = str(kilib.find1(kilib.find1(c, 'sheetpath'), 'tstamps')[1])
        ts = kilib.find1(c, 'tstamps')
        fp.SetPath(pcbnew.KIID_PATH(sp + str(ts[1])))
        fp.SetReference(ref)
        fp.SetValue(str(kilib.find1(c, 'value')[1]))
        for pr in kilib.find(c, 'property'):
            if str(kilib.find1(pr, 'name')[1]) == 'dnp':
                fp.SetDNP(True)
                fp.SetExcludedFromBOM(True)
        velden = kilib.find1(c, 'fields')
        for v in (kilib.find(velden, 'field') if velden else []):
            if str(v[1][1]) == 'LCSC' and len(v) > 2:
                fp.SetField('LCSC', str(v[2]))
                f = fp.GetField('LCSC')
                if f:
                    f.SetVisible(False)
        for pad in fp.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        board.Add(fp)
        if ref in vast:
            x, y, rot, zijde = vast[ref]
            fp.SetPosition(pt(x, y))
            if zijde == 'B':
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(rot)
            if ref in ('SW1', 'SW2'):
                c0 = pt(0, 0)
                def afst(nr):
                    ps = [p.GetPosition() for p in fp.Pads() if p.GetNumber() == nr]
                    return sum(((q.x - c0.x) ** 2 + (q.y - c0.y) ** 2) ** 0.5 for q in ps) / len(ps)
                if afst('MP') < afst('1'):
                    fp.SetOrientationDegrees(rot + 180)
            if ref == 'J2':
                c0 = pt(0, 0)
                def d(nr):
                    ps = [p.GetPosition() for p in fp.Pads() if p.GetNumber() == nr]
                    return min(((q.x - c0.x) ** 2 + (q.y - c0.y) ** 2) ** 0.5 for q in ps)
                if d('A1') > d('SH'):
                    fp.SetOrientationDegrees(rot + 180)
                for _ in range(60):
                    ver = max(((p.GetPosition().x - c0.x) ** 2 + (p.GetPosition().y - c0.y) ** 2) ** 0.5
                              + max(p.GetSize().x, p.GetSize().y) / 2 for p in fp.Pads() if p.GetNumber() == 'SH')
                    if ver <= pcbnew.FromMM(P['print_d'] / 2 - 0.6):
                        break
                    fp.Move(pcbnew.VECTOR2I(0, -pcbnew.FromMM(0.1)))
        else:
            fp.SetPosition(pt(los_x + kolom * 6, los_y))
            los_y -= 4
            if los_y < -40:
                los_y, kolom = 40.0, kolom + 1
    plaats_klein(board, vast)
    vlakken(board, net)
    print('footprints:', len(board.GetFootprints()), 'netten:', len(netobj))

ACCU = (-25.5, -17.5, 25.5, 17.5)
CLUSTERS = {
    'cm3': ('F', -17.0, -26.5, 9.0),
    'modem_f': ('F', 8.6, 22.5, 6.0),
    'modem_b': ('F', 46.0, 4.0, 6.0),
    'usb': ('B', -14.0, -40.0, 10.0),
    'accu': ('B', -24.0, 26.0, 6.0),
    'qi': ('F', 22.0, -32.0, 8.0),
    'boost': ('B', 12.0, -36.0, 14.0),
    'sim': ('B', 26.5, 16.0, 6.0),
    'als': ('F', 23.0, 30.0, 5.0),
    'imu': ('F', -10.0, 44.0, 12.0),
    'mag': ('F', -30.0, 42.0, 6.0),
    'amp': ('F', -49.0, -8.0, 9.0),
    'motor': ('F', -37.0, -39.0, 6.0),
    'mic1': ('F', -38.0, -28.0, 6.0),
    'mic2': ('F', -15.0, -40.0, 8.0),
    'ant_MAIN': ('F', 25.5, 38.0, 6.0),
    'ant_GNSS': ('F', 12.0, 46.0, 7.0),
    'ant_WIFI': ('F', 38.0, -33.5, 5.0),
}
GROEP_CLUSTER = {
    'Toetsen + herstelmodus (SARADC_VIN0)': 'cm3', 'Ontkoppeling VBAT modem': 'modem_f', 'Aan/uit + reset modem': 'modem_b',
    'SIM: eUICC (MFF2) + nano-SIM': 'sim', 'Accu': 'accu', 'USB-C (laden + data, ESD)': 'usb',
    'Qi-ontvanger (los bordje, 5 V)': 'qi', 'Aansluiting Waveshare-bordje': 'boost',
    '5 V-boost voor het bordje (TPS61023)': 'boost', '3,3 V voor de DSI-connector (ME6211)': 'boost',
    'Sensor-I2C pull-ups': 'imu', 'Licht + nabijheid (STK3311-X, 0x48)': 'als', 'IMU 6-assig (LSM6DS3TR-C, 0x6A)': 'imu',
    'Kompas (MMC5603NJ, 0x30)': 'mag', 'Luidsprekerversterker (NS4150B)': 'amp', 'Trilmotor (soldeerpads)': 'motor',
    'LTE hoofd': 'ant_MAIN', 'GNSS (externe patch)': 'ant_GNSS', 'Wi-Fi / BT (naar CM3)': 'ant_WIFI',
}
VAST = ('CN1', 'CN2', 'CN3', 'U2', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J9', 'J10', 'SW1', 'SW2', 'SW3', 'SW4', 'MK1', 'MK2')

def cluster_van(design):
    uit = {}
    for sname, sh in design.SHEETS.items():
        for c in sh['comps']:
            ref, nets, g = c['ref'], set(c['pins'].values()), c.get('groep', '')
            if ref.startswith('#') or ref in VAST:
                continue
            if g.startswith('Microfoons'):
                uit[ref] = 'mic2' if nets & {'MIC2', 'MIC_CM3', 'MIC_VDD2'} else 'mic1'
            elif g in GROEP_CLUSTER:
                uit[ref] = GROEP_CLUSTER[g]
    return uit

def plaats_klein(board, vast):
    import sys, math
    sys.path.insert(0, HIER)
    import design
    clusters = cluster_van(design)
    bezet = {'F': [(CM3_X - 20.6, CM3_Y - 28.0, CM3_X + 20.6, CM3_Y + 28.0)],
             'B': [tuple(ACCU)] + [(CM3_X + gx - 3.2, CM3_Y + gy - 3.2, CM3_X + gx + 3.2, CM3_Y + gy + 3.2)
                                   for gx, gy in CM3_GATEN]}
    bezet['F'].append((P['qi_x'] - P['qi_b'] / 2 - 0.5, P['qi_y'] - P['qi_l'] / 2 - 0.5,
                       P['qi_x'] + P['qi_b'] / 2 + 0.5, P['qi_y'] + P['qi_l'] / 2 + 0.5))
    rk = (P['knop_d'] + 2.4) / 2 + 0.4
    bezet['F'].append((P['knop_x'] - rk, P['knop_y'] - rk, P['knop_x'] + rk, P['knop_y'] + rk))
    rt = P['tril_d'] / 2 + 0.5
    bezet['F'].append((P['tril_x'] - rt, P['tril_y'] - rt, P['tril_x'] + rt, P['tril_y'] + rt))

    def box(fp):
        bb = fp.GetBoundingBox(False)
        x0, x1 = pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetRight()) - OX
        y0, y1 = OY - pcbnew.ToMM(bb.GetBottom()), OY - pcbnew.ToMM(bb.GetTop())
        return x0 - 0.15, y0 - 0.15, x1 + 0.15, y1 + 0.15

    def in_antennezone(x, y, marge=0.6):
        r = math.hypot(x, y)
        if r < P['ant_r'] - marge:
            return False
        a = math.degrees(math.atan2(y, x)) % 360
        for _, midden, boog in ANTENNES:
            d = (a - midden + 180) % 360 - 180
            if abs(d) <= boog / 2 + math.degrees(marge / max(r, 1)):
                return True
        return False

    def vrij(zijde, b):
        if max(math.hypot(x, y) for x in (b[0], b[2]) for y in (b[1], b[3])) > P['print_d'] / 2 - 0.8:
            return False
        punten = [(b[0] + (b[2] - b[0]) * i / 4, b[1] + (b[3] - b[1]) * j / 4) for i in range(5) for j in range(5)]
        if any(in_antennezone(x, y) for x, y in punten):
            return False
        return all(b[2] <= o[0] or b[0] >= o[2] or b[3] <= o[1] or b[1] >= o[3] for o in bezet[zijde])

    los = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fpid = str(fp.GetFPID().GetUniStringLibItemName())
        if fpid.startswith('LTE_meander'):
            fp.SetPosition(pt(0, 0))
            for pd in fp.Pads():
                q = pd.GetPosition()
                vx, vy = pcbnew.ToMM(q.x) - OX, OY - pcbnew.ToMM(q.y)
                bezet['F'].append((vx - 0.6, vy - 0.6, vx + 0.6, vy + 0.6))
            continue
        if fpid in ('ANT-SMD_L10.0-W3.2',):
            hoek = 320.0
            ra = P['print_d'] / 2 - 5.0
            fp.SetPosition(pt(ra * math.cos(math.radians(hoek)), ra * math.sin(math.radians(hoek))))
            fp.SetOrientationDegrees(hoek - 90)
        elif fp.GetValue() == 'STK3311-X':
            fp.SetPosition(pt(ALS_R * math.cos(math.radians(ALS_HOEK)), ALS_R * math.sin(math.radians(ALS_HOEK))))
        elif not (ref in vast or ref.startswith('H')) and ref in clusters:
            los.append(fp)
            continue
        zijden = ('F', 'B') if any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads()) else \
                 (('B',) if fp.IsFlipped() else ('F',))
        for z in zijden:
            bezet[z].append(box(fp))
        if ref == 'J5':
            x0_, y0_, x1_, y1_ = box(fp)
            bezet['B'].append((x0_ - 1.5, y0_ - 1.5, x1_ + 1.5, y1_ + 1.5))
    def plaats_raster(fp):
            naam = clusters[fp.GetReference()]
            zijde, x0, y0, breed = CLUSTERS[naam]
            if zijde == 'B' and not fp.IsFlipped():
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetPosition(pt(0, 0))
            b0 = box(fp)
            w, h = b0[2] - b0[0], b0[3] - b0[1]
            dx, dy = -b0[0], -b0[1]
            geplaatst = False
            for stap in range(400):
                rij, kol = divmod(stap, max(1, int(breed / 0.5)))
                x, y = x0 + kol * 0.5, y0 - h - rij * 0.5
                if x + w > x0 + breed + 0.01:
                    continue
                b = (x, y, x + w, y + h)
                if vrij(zijde, b):
                    fp.SetPosition(pt(x + dx, y + dy))
                    bezet[zijde].append(box(fp))
                    geplaatst = True
                    break
            if not geplaatst:
                for rr in [i * 0.5 for i in range(1, 40)]:
                    for k in range(int(8 + rr * 4)):
                        a = 2 * math.pi * k / int(8 + rr * 4)
                        x, y = x0 + rr * math.cos(a), y0 - h + rr * math.sin(a)
                        b = (x, y, x + w, y + h)
                        if vrij(zijde, b):
                            fp.SetPosition(pt(x + dx, y + dy))
                            bezet[zijde].append(box(fp))
                            geplaatst = True
                            break
                    if geplaatst:
                        break
            if not geplaatst:
                print('GEEN PLEK in cluster', naam, 'voor', fp.GetReference())

    GLOBAAL = {'GND', 'VBAT', 'VBUS', 'BAT_N', '+3V3', '+1V8'}
    EIGENAAR = {'Ontkoppeling VBAT modem': 'U2', 'Aan/uit + reset modem': 'U2', 'Accu': 'J1'}
    groep_van = {c['ref']: c.get('groep', '') for sh in design.SHEETS.values() for c in sh['comps']}
    alle = {f.GetReference(): f for f in board.GetFootprints()}
    geplaatst = {r for r in alle if r not in {f.GetReference() for f in los}}
    padnetten = {}
    for f in board.GetFootprints():
        for pd in f.Pads():
            padnetten.setdefault(pd.GetNetname(), []).append((f.GetReference(), pd))

    def passief(ref):
        return ref[:1] in ('R', 'C', 'L') or ref[:2] in ('FB', 'TP') or (ref[:1] == 'D' and ref != 'D3')

    def kandidaten(fp):
        ref, g = fp.GetReference(), groep_van.get(fp.GetReference(), '')
        uit = []
        for pd in fp.Pads():
            n = pd.GetNetname()
            if not n or n.startswith('unconnected'):
                continue
            for r2, p2 in padnetten.get(n, []):
                if r2 == ref:
                    continue
                zelfde = groep_van.get(r2) == g or EIGENAAR.get(g) == r2
                if n in GLOBAAL and not (zelfde and not passief(r2)):
                    continue
                score = (0 if not passief(r2) else 1) + (0 if zelfde else 2) + (3 if n in GLOBAAL else 0) + \
                    (1 if r2.startswith('CN') else 0)
                q = p2.GetPosition()
                uit.append((score, r2, (pcbnew.ToMM(q.x) - OX, OY - pcbnew.ToMM(q.y))))
        return uit

    def lengte(fp, pads, dx, dy, ax, ay):
        ref = fp.GetReference()
        tot = min(math.hypot(px + dx - ax, py + dy - ay) for px, py, _ in pads) if pads else 0
        for px, py, n in pads:
            if not n or n == 'GND' or n.startswith('unconnected'):
                continue
            ds = [math.hypot(px + dx - (pcbnew.ToMM(q.GetPosition().x) - OX), py + dy - (OY - pcbnew.ToMM(q.GetPosition().y)))
                  for r2, q in padnetten.get(n, []) if r2 != ref and r2 in geplaatst]
            if ds:
                tot += min(ds)
        return tot

    def plaats_bij(fp, ax, ay):
        naam = clusters[fp.GetReference()]
        zijde = CLUSTERS[naam][0]
        if zijde == 'B' and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        rot0 = fp.GetOrientationDegrees()
        vormen = []
        for dr in (0, 90, 180, 270):
            fp.SetOrientationDegrees(rot0 + dr)
            fp.SetPosition(pt(0, 0))
            b0 = box(fp)
            pads = [(pcbnew.ToMM(p.GetPosition().x) - OX, OY - pcbnew.ToMM(p.GetPosition().y), p.GetNetname())
                    for p in fp.Pads()]
            vormen.append((rot0 + dr, b0, pads))
        beste, eerste = None, None
        for rr in [i * 0.25 for i in range(0, 120)]:
            if eerste is not None and rr > eerste + 1.0:
                break
            n = max(1, int(6 + rr * 8))
            for k in range(n):
                a = 2 * math.pi * k / n
                cx, cy = ax + rr * math.cos(a), ay + rr * math.sin(a)
                for rot, b0, pads in vormen:
                    w, h = b0[2] - b0[0], b0[3] - b0[1]
                    b = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                    if not vrij(zijde, b):
                        continue
                    dx, dy = cx - w / 2 - b0[0], cy - h / 2 - b0[1]
                    d = lengte(fp, pads, dx, dy, ax, ay)
                    if beste is None or d < beste[0] - 1e-6:
                        beste = (d, rot, dx, dy)
                    if eerste is None:
                        eerste = rr
        if beste is None:
            fp.SetOrientationDegrees(rot0)
            return False
        _, rot, dx, dy = beste
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pt(dx, dy))
        bezet[zijde].append(box(fp))
        return True

    def plaats_rij(fp, aref, ax, ay):
        ref = fp.GetReference()
        zijde = CLUSTERS[clusters[ref]][0]
        if zijde == 'B' and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        x0, y0, x1, y1 = box(alle[aref])
        if not (x0 - 0.5 <= ax <= x1 + 0.5 and y0 - 0.5 <= ay <= y1 + 0.5) or (x1 - x0) > 40 or (y1 - y0) > 40:
            return False
        afst = {'L': ax - x0, 'R': x1 - ax, 'O': ay - y0, 'B': y1 - ay}
        kant = min(afst, key=afst.get)
        vormen = []
        for rot in ((0, 180) if kant in 'LR' else (90, 270)):
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pt(0, 0))
            b0 = box(fp)
            pads = [(pcbnew.ToMM(q.GetPosition().x) - OX, OY - pcbnew.ToMM(q.GetPosition().y), q.GetNetname())
                    for q in fp.Pads()]
            vormen.append((rot, b0, pads))
        stappen = [0.0] + [v * z for v in [i * 0.25 for i in range(1, 49)] for z in (1, -1)]
        volgorde = sorted(((rij, stap) for rij in range(4) for stap in stappen if abs(stap) <= 6),
                          key=lambda t: t[0] * 1.2 + abs(t[1]))
        for rij, stap in volgorde:
            beste = None
            for rot, b0, pads in vormen:
                w, h = b0[2] - b0[0], b0[3] - b0[1]
                if kant in 'LR':
                    cy = round((ay + stap) * 4) / 4
                    cx = x0 - w / 2 - rij * w if kant == 'L' else x1 + w / 2 + rij * w
                else:
                    cx = round((ax + stap) * 4) / 4
                    cy = y0 - h / 2 - rij * h if kant == 'O' else y1 + h / 2 + rij * h
                b = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                if not vrij(zijde, b):
                    continue
                dx, dy = cx - w / 2 - b0[0], cy - h / 2 - b0[1]
                d = lengte(fp, pads, dx, dy, ax, ay)
                if beste is None or d < beste[0]:
                    beste = (d, rot, dx, dy)
            if beste:
                _, rot, dx, dy = beste
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(pt(dx, dy))
                bezet[zijde].append(box(fp))
                return True
        return False

    def met_netten(*netten):
        for f in los:
            if {q.GetNetname() for q in f.Pads()} == set(netten):
                return f
        return None

    def pad_xy(ref, net):
        for q in alle[ref].Pads():
            if q.GetNetname() == net:
                return pcbnew.ToMM(q.GetPosition().x) - OX, OY - pcbnew.ToMM(q.GetPosition().y)
        return None

    def zet(f, x, y, langs_x):
        zijde = CLUSTERS[clusters[f.GetReference()]][0]
        if zijde == 'B' and not f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(0 if langs_x else 90)
        f.SetPosition(pt(0, 0))
        b0 = box(f)
        w, h = b0[2] - b0[0], b0[3] - b0[1]
        b = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        if not vrij(zijde, b):
            if os.environ.get('PARDAL_DEBUG'):
                print('RF-keten: geen plek voor', f.GetReference(), 'op', (round(x, 2), round(y, 2)), zijde,
                      [o for o in bezet[zijde] if not (b[2] <= o[0] or b[0] >= o[2] or b[3] <= o[1] or b[1] >= o[3])])
            return False
        f.SetPosition(pt(x - w / 2 - b0[0], y - h / 2 - b0[1]))
        bezet[zijde].append(box(f))
        geplaatst.add(f.GetReference())
        los.remove(f)
        return True

    def keten(doel, bron, stappen, n_kant=1):
        dx, dy = bron[0] - doel[0], bron[1] - doel[1]
        ux, uy = ((1 if dx > 0 else -1), 0) if abs(dx) >= abs(dy) else (0, (1 if dy > 0 else -1))
        nx, ny = -uy * n_kant, ux * n_kant
        for f, a, z in stappen:
            if f is None:
                continue
            x, y = doel[0] + ux * a + nx * z, doel[1] + uy * a + ny * z
            in_lijn = (z == 0)
            zet(f, round(x * 4) / 4, round(y * 4) / 4, (ux != 0) == in_lijn)

    def bron_pin(net):
        for r2, q in padnetten.get(net, []):
            if r2 == 'U2':
                return pcbnew.ToMM(q.GetPosition().x) - OX, OY - pcbnew.ToMM(q.GetPosition().y)

    voed = pad_xy('AE1', 'ANT_MAIN_PCB') if 'AE1' in alle else None
    if voed and bron_pin('ANT_MAIN_M'):
        keten(voed, bron_pin('ANT_MAIN_M'), [
            (met_netten('ANT_MAIN', 'ANT_MAIN_PCB'), 2.6, 0),
            (met_netten('ANT_MAIN', 'GND'), 3.8, 1.9),
            (met_netten('ANT_MAIN_M', 'ANT_MAIN'), 5.0, 0),
            (met_netten('ANT_MAIN_M', 'GND'), 6.2, 1.9),
            (met_netten('ANT_MAIN', 'ANT_MAIN_UFL'), 3.8, -1.9),
            (next((f for f in los if f.GetReference() == 'J7'), None), 8.0, -2.8)])
    j10 = pad_xy('J10', 'ANT_GNSS') if 'J10' in alle else None
    if j10 and bron_pin('ANT_GNSS_M'):
        keten(j10, bron_pin('ANT_GNSS_M'), [
            (met_netten('ANT_GNSS_M', 'ANT_GNSS'), 5.1, 0),
            (met_netten('ANT_GNSS', 'GND'), 4.4, 1.9),
            (met_netten('ANT_GNSS_M', 'GND'), 5.8, 1.9)], n_kant=-1)

    def klein(f):
        b_ = box(f)
        return f.GetReference()[0] in 'RC' and not f.GetReference().startswith('CN') and \
            max(b_[2] - b_[0], b_[3] - b_[1]) < 2.3

    def anker(f):
        kand = kandidaten(f)
        klaar = [k for k in kand if k[1] in geplaatst]
        if not klaar:
            return None
        best = min(k[0] for k in klaar)
        if any(k[1] not in geplaatst and k[0] < best for k in kand):
            return None
        o = CLUSTERS[clusters[f.GetReference()]]
        return min((k for k in klaar if k[0] == best), key=lambda k: math.hypot(k[2][0] - o[1], k[2][1] - o[2]))

    def vormen_van(f, rots):
        uit = []
        for rot in rots:
            f.SetOrientationDegrees(rot)
            f.SetPosition(pt(0, 0))
            b0 = box(f)
            pads = [(pcbnew.ToMM(q.GetPosition().x) - OX, OY - pcbnew.ToMM(q.GetPosition().y), q.GetNetname())
                    for q in f.Pads()]
            uit.append((rot, b0, pads))
        return uit

    def leg(f, rot, b0, cx, cy, zijde):
        f.SetOrientationDegrees(rot)
        f.SetPosition(pt(cx - (b0[0] + b0[2]) / 2, cy - (b0[1] + b0[3]) / 2))
        bezet[zijde].append(box(f))
        geplaatst.add(f.GetReference())

    def rij_langs(items, kant, rand, zijde):
        lr = kant in 'LR'
        rots = (0, 180) if lr else (90, 270)
        info = []
        for f, langs in items:
            if zijde == 'B' and not f.IsFlipped():
                f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            vs = vormen_van(f, rots)
            b0 = vs[0][1]
            diep, breed = (b0[2] - b0[0], b0[3] - b0[1]) if lr else (b0[3] - b0[1], b0[2] - b0[0])
            info.append([f, langs, vs, diep, math.ceil(breed * 4) / 4])
        info.sort(key=lambda t: t[1])
        pos = []
        for i, t in enumerate(info):
            pos.append(t[1] if i == 0 else max(t[1], pos[-1] + (info[i - 1][4] + t[4]) / 2))
        schuif = sum(t[1] - q for t, q in zip(info, pos)) / len(pos)
        pos = [round((q + schuif) * 4) / 4 for q in pos]
        diep = max(t[3] for t in info)
        teken = -1 if kant in 'LO' else 1
        for uit in [i * 0.25 for i in range(0, 17)]:
            for opzij in [0.0] + [v * z for v in [i * 0.5 for i in range(1, 9)] for z in (1, -1)]:
                lijn = rand + teken * (diep / 2 + uit)
                vakken = []
                for t, q in zip(info, pos):
                    q2 = q + opzij
                    cx, cy = (lijn, q2) if lr else (q2, lijn)
                    w, h = (t[3], t[4]) if lr else (t[4], t[3])
                    vakken.append((cx - w / 2 + 0.15, cy - h / 2 + 0.15, cx + w / 2 - 0.15, cy + h / 2 - 0.15))
                ok = all(vrij(zijde, v) for v in vakken) and all(
                    vakken[i][2] <= vakken[j][0] or vakken[i][0] >= vakken[j][2] or vakken[i][3] <= vakken[j][1] or
                    vakken[i][1] >= vakken[j][3] for i in range(len(vakken)) for j in range(i + 1, len(vakken)))
                if not ok:
                    continue
                for t, q in zip(info, pos):
                    f, _, vs, _, _ = t
                    cx, cy = (lijn, q + opzij) if lr else (q + opzij, lijn)
                    beste = min(vs, key=lambda v: lengte(f, v[2], cx - (v[1][0] + v[1][2]) / 2, cy - (v[1][1] + v[1][3]) / 2,
                                                         *( (rand, cy) if lr else (cx, rand) )))
                    leg(f, beste[0], beste[1], cx, cy, zijde)
                return True
        return False

    def blok(fs, x0, y0, zijde):
        fs = sorted(fs, key=lambda f: (sorted(q.GetNetname() for q in f.Pads()), f.GetReference()))
        info = []
        for f in fs:
            if zijde == 'B' and not f.IsFlipped():
                f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            v = vormen_van(f, (90,))[0]
            info.append((f, v, math.ceil((v[1][2] - v[1][0]) * 4) / 4, math.ceil((v[1][3] - v[1][1]) * 4) / 4))
        n = max(1, math.ceil(math.sqrt(len(info) * 1.5)))
        sw, sh = max(t[2] for t in info), max(t[3] for t in info)
        for rr in [i * 0.5 for i in range(0, 30)]:
            for k in range(max(1, int(rr * 6))):
                a_ = 2 * math.pi * k / max(1, int(rr * 6))
                bx, by = round((x0 + rr * math.cos(a_)) * 4) / 4, round((y0 + rr * math.sin(a_)) * 4) / 4
                plek = [(bx + (i % n) * sw + sw / 2, by - (i // n) * sh - sh / 2) for i in range(len(info))]
                if all(vrij(zijde, (cx - sw / 2 + 0.15, cy - sh / 2 + 0.15, cx + sw / 2 - 0.15, cy + sh / 2 - 0.15))
                       for cx, cy in plek):
                    for (f, v, _, _), (cx, cy) in zip(info, plek):
                        leg(f, v[0], v[1], cx, cy, zijde)
                    return True
        return False

    def zet_t(ref, x, y, rot, net=None, naar=None, alle4=False):
        f = next((g for g in los if g.GetReference() == ref), None)
        if f is None:
            return False
        zijde = CLUSTERS[clusters[ref]][0]
        if zijde == 'B' and not f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        beste = None
        for r_ in ((rot, rot + 90, rot + 180, rot + 270) if alle4 else (rot, rot + 180) if net else (rot,)):
            f.SetOrientationDegrees(r_)
            f.SetPosition(pt(x, y))
            d = 0
            if net:
                q = next(q for q in f.Pads() if q.GetNetname() == net)
                d = math.hypot(pcbnew.ToMM(q.GetPosition().x) - OX - naar[0], OY - pcbnew.ToMM(q.GetPosition().y) - naar[1])
            if beste is None or d < beste[0]:
                beste = (d, r_)
        f.SetOrientationDegrees(beste[1])
        f.SetPosition(pt(x, y))
        bezet[zijde].append(box(f))
        geplaatst.add(ref)
        return True

    def sjabloon_boost(ox, oy):
        refs = ['U5', 'L1', 'C17', 'C18', 'C19', 'R18', 'R19', 'R20', 'U6', 'C20', 'C21']
        if not all(any(g.GetReference() == r for g in los) for r in refs):
            return False
        zet_t('U5', ox, oy, 90)
        zet_t('L1', ox + 1.07, oy - 2.4, 0, 'DISP_SW', (ox, oy - 0.75))
        zet_t('C17', ox + 2.25, oy + 0.6, 90, 'VBAT', (ox + 0.5, oy + 0.75))
        zet_t('C18', ox - 2.0, oy - 0.6, 90, 'DISP_5V', (ox - 0.5, oy - 0.75))
        zet_t('C19', ox - 3.6, oy - 0.6, 90, 'DISP_5V', (ox - 0.5, oy - 0.75))
        zet_t('R18', ox - 1.25, oy + 2.3, 90, 'DISP_FB', (ox - 0.5, oy + 0.75))
        zet_t('R19', ox - 0.1, oy + 2.3, 90, 'DISP_FB', (ox - 0.5, oy + 0.75))
        zet_t('R20', ox + 1.05, oy + 2.3, 90, 'DISP_5V_EN', (ox, oy + 0.75))
        zet_t('U6', ox - 7.0, oy - 0.2, 90)
        zet_t('C20', ox - 9.4, oy - 0.2, 90, 'DISP_5V', (ox - 8.15, oy))
        zet_t('C21', ox - 5.85, oy - 2.9, 90, '+3V3_DISP', (ox - 5.85, oy - 1.15))
        return True

    sjabloon_boost(17.0, -38.5)

    def sjabloon_usb():
        if not all(any(g.GetReference() == r for g in los) for r in ('U4', 'R12', 'R13', 'C16', 'D2', 'R14', 'R15')):
            return False
        cc1 = pad_xy('J2', 'CC1'); cc2 = pad_xy('J2', 'CC2'); vb = pad_xy('J2', 'VBUS')
        y = cc1[1] + 2.7
        zet_t('U4', 0.2, y + 1.6, 180)
        zet_t('R12', cc1[0] + 2.6, y, 90, 'CC1', cc1)
        zet_t('R13', cc2[0] - 2.1, y, 90, 'CC2', cc2)
        zet_t('C16', cc2[0] - 3.4, y, 90, 'VBUS', vb)
        zet_t('D2', cc2[0] - 6.3, y + 0.4, 90, 'VBUS', vb)
        zet_t('R14', cc1[0] + 3.8, y, 90, 'VBUS', vb)
        zet_t('R15', cc1[0] + 5.0, y, 90, 'VBUS_DET', (cc1[0] + 3.8, y + 1))
        return True

    sjabloon_usb()

    def alles_los(*refs):
        return all(any(g.GetReference() == r for g in los) for r in refs)

    def sjabloon_amp():
        if not alles_los('U10', 'R24', 'C28', 'R25', 'R26', 'R27', 'C29', 'C30', 'C31', 'C26', 'C27'):
            return
        ux, uy = -38.5, -9.0
        zet_t('U10', ux, uy, 270)
        st = 1.05
        for i, (ref, net) in enumerate((('R24', 'SPK_EN'), ('C28', 'AMP_BYP'), ('R25', 'AMP_INP'), ('R26', 'AMP_INP'),
                                        ('R27', 'AMP_INN'))):
            zet_t(ref, ux - 3.9, uy + 2.1 - i * st, 0, net, (ux, uy))
        for ref, net, i in (('C29', 'AUD_L_C', 2), ('C30', 'MDM_SPK_PC', 3), ('C31', 'MDM_SPK_NC', 4)):
            zet_t(ref, ux - 5.95, uy + 2.1 - i * st, 0, net, (ux, uy))
        zet_t('C27', ux + 3.7, uy - 0.35, 0, 'VBAT', (ux, uy))
        zet_t('C26', ux + 4.4, uy + 1.4, 0, 'VBAT', (ux, uy))

    def sjabloon_mic(mk, rij):
        if not alles_los(*[r for r, _ in rij]) or mk not in alle:
            return
        mx, my = pad_xy(mk, 'GND')[0] + 0.53, pad_xy(mk, 'GND')[1] + 0.99
        for i, (ref, net) in enumerate(rij):
            zet_t(ref, mx + 1.6 - i * 1.05, my + 2.7, 90, net, (mx, my))

    def sjabloon_motor(ox, oy):
        if not alles_los('TP7', 'TP8', 'D4', 'Q3', 'R28'):
            return
        zet_t('TP7', ox, oy + 1.6, 0)
        zet_t('TP8', ox, oy - 1.6, 0)
        zet_t('D4', ox - 2.9, oy, 90, 'VBAT', (ox, oy + 1.6))
        zet_t('Q3', ox - 6.0, oy - 1.4, 0, 'MOT_N', (ox, oy - 1.6), alle4=True)
        zet_t('R28', ox - 6.0, oy + 1.4, 0, 'MOT_EN', (ox - 6.0, oy - 1.4))

    def sjabloon_sim():
        if not alles_los('R8', 'C13', 'R9', 'C14', 'R10', 'C15', 'R11', 'R6', 'C11', 'R7', 'C12') or 'U3' not in alle:
            return
        zet_t('U3', 43.0, 12.1, -90)
        vdd = pad_xy('U3', 'ESIM_VDD')
        x0, y0 = vdd[0] - 1.6, vdd[1] + 5.4
        for i, (ref, net) in enumerate((('R10', 'SIM_IO'), ('C15', 'SIM_IO'), ('R9', 'SIM_CLK'), ('C14', 'SIM_CLK'),
                                        ('R8', 'SIM_RST'), ('C13', 'SIM_RST'))):
            zet_t(ref, x0 - i * 1.05, y0, 90, net, (vdd[0], y0 - 3))
        for i, (ref, net) in enumerate((('R6', 'ESIM_VDD'), ('C11', 'ESIM_VDD'), ('R11', 'SIM_IO'))):
            zet_t(ref, x0 - i * 1.05, y0 - 2.3, 90, net, (vdd[0], vdd[1]))
        p1 = pad_xy('J5', 'NSIM_VDD')
        zet_t('R7', p1[0] + 3.3, p1[1] - 0.6, 0, 'NSIM_VDD', p1)
        zet_t('C12', p1[0] + 3.3, p1[1] + 0.5, 0, 'NSIM_VDD', p1)

    sjabloon_amp()
    sjabloon_mic('MK1', (('FB1', 'MIC_VDD1'), ('C32', 'MIC_VDD1'), ('C34', 'MIC1'), ('C35', 'MDM_MIC_P'),
                         ('C36', 'MDM_MIC_N'), ('C37', 'MDM_MIC_N')))
    sjabloon_mic('MK2', (('FB2', 'MIC_VDD2'), ('C33', 'MIC_VDD2'), ('C38', 'MIC2')))
    sjabloon_motor(-26.9, -39.7)
    if alles_los('R1', 'R2', 'C1'):
        for i, (ref, net) in enumerate((('R1', 'KEY_ADC'), ('C1', 'KEY_ADC'), ('R2', 'KEY_ADC'))):
            zet_t(ref, -18.0 + i * 1.05, -26.6, 90, net, (-17.0, -20.0))
    sjabloon_sim()

    for ronde in range(4):
        for f in [f for f in los if not passief(f.GetReference()) and f.GetReference() not in geplaatst]:
            an = anker(f) or (None if ronde < 3 else (9, '', (CLUSTERS[clusters[f.GetReference()]][1], CLUSTERS[clusters[f.GetReference()]][2])))
            if not an:
                continue
            o = CLUSTERS[clusters[f.GetReference()]]
            ax, ay = an[2]
            if an[0] >= 1 or an[1] == '':
                ax, ay = o[1], o[2] - 1.0
            if plaats_bij(f, ax, ay):
                geplaatst.add(f.GetReference())
    for ronde in range(4):
        for f in sorted([f for f in los if passief(f.GetReference()) and not klein(f) and f.GetReference() not in geplaatst],
                        key=lambda f: ({'L': 0, 'C': 1, 'D': 2}.get(f.GetReference()[0], 3), f.GetReference())):
            an = anker(f)
            if an and plaats_bij(f, *an[2]):
                geplaatst.add(f.GetReference())
    import collections
    rijen = collections.defaultdict(list)
    cm3_blok = collections.defaultdict(list)
    for f in [f for f in los if klein(f) and f.GetReference() not in geplaatst]:
        an = anker(f)
        if not an or passief(an[1]):
            continue
        if an[1].startswith('CN'):
            cm3_blok[groep_van.get(f.GetReference(), '')].append(f)
            continue
        x0, y0, x1, y1 = box(alle[an[1]])
        ax, ay = an[2]
        afst = {'L': ax - x0, 'R': x1 - ax, 'O': ay - y0, 'B': y1 - ay}
        kant = min(afst, key=afst.get)
        zijde = CLUSTERS[clusters[f.GetReference()]][0]
        rijen[(an[1], kant, zijde)].append((f, ay if kant in 'LR' else ax))
    per_ic = collections.defaultdict(list)
    for (aref, kant, zijde), items in list(rijen.items()):
        x0, y0, x1, y1 = box(alle[aref])
        if max(x1 - x0, y1 - y0) <= 6.5:
            per_ic[(aref, zijde)] += [(f, kant) for f, _ in items]
            del rijen[(aref, kant, zijde)]

    def pinlangs(f, aref, kant):
        an = anker(f)
        return an[2][1] if kant in 'LR' else an[2][0]

    for (aref, zijde), lijst in per_ic.items():
        x0, y0, x1, y1 = box(alle[aref])
        telling = collections.Counter(k for _, k in lijst)
        gelukt = False
        for kant in sorted('LROB', key=lambda k: -telling.get(k, 0)):
            rand = {'L': x0, 'R': x1, 'O': y0, 'B': y1}[kant]
            items = [(f, pinlangs(f, aref, kant)) for f, _ in lijst]
            if rij_langs(items, kant, rand, zijde):
                gelukt = True
                break
            helft = (len(items) + 1) // 2
            items.sort(key=lambda t: t[1])
            if len(items) > 1 and rij_langs(items[:helft], kant, rand, zijde):
                if rij_langs(items[helft:], kant, rand, zijde):
                    gelukt = True
                    break
        if not gelukt:
            for f, k in lijst:
                if f.GetReference() not in geplaatst:
                    rijen[(aref, k, zijde)].append((f, pinlangs(f, aref, k)))
    for (aref, kant, zijde), items in sorted(rijen.items(), key=lambda kv: -len(kv[1])):
        items = [t for t in items if t[0].GetReference() not in geplaatst]
        if not items:
            continue
        x0, y0, x1, y1 = box(alle[aref])
        rand = {'L': x0, 'R': x1, 'O': y0, 'B': y1}[kant]
        if not rij_langs(items, kant, rand, zijde):
            helft = (len(items) + 1) // 2
            items.sort(key=lambda t: t[1])
            if rij_langs(items[:helft], kant, rand, zijde):
                rij_langs(items[helft:], kant, rand, zijde)
    for g, fs in cm3_blok.items():
        fs = [f for f in fs if f.GetReference() not in geplaatst]
        if fs:
            z, cx0, cy0, _ = CLUSTERS[clusters[fs[0].GetReference()]]
            blok(fs, cx0, cy0, z)
    for ronde in range(3):
        for f in [f for f in los if klein(f) and f.GetReference() not in geplaatst]:
            an = anker(f)
            if not an or not passief(an[1]):
                continue
            partner = alle[an[1]]
            x0, y0, x1, y1 = box(partner)
            px, py = (x0 + x1) / 2, (y0 + y1) / 2
            zijde = CLUSTERS[clusters[f.GetReference()]][0]
            if zijde == 'B' and not f.IsFlipped():
                f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            rot = partner.GetOrientationDegrees()
            v = vormen_van(f, (rot, rot + 180))
            liggend = (x1 - x0) > (y1 - y0)
            gelukt = False
            for afst_ in [i * 0.25 for i in range(0, 12)]:
                for richting in ((1, 0), (-1, 0)) if liggend else ((0, 1), (0, -1)):
                    w = v[0][1][2] - v[0][1][0]; h = v[0][1][3] - v[0][1][1]
                    cx = px + richting[0] * ((x1 - x0) / 2 + w / 2 + afst_)
                    cy = py + richting[1] * ((y1 - y0) / 2 + h / 2 + afst_)
                    if vrij(zijde, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)):
                        beste = min(v, key=lambda q: lengte(f, q[2], cx - (q[1][0] + q[1][2]) / 2, cy - (q[1][1] + q[1][3]) / 2, px, py))
                        leg(f, beste[0], beste[1], cx, cy, zijde)
                        gelukt = True
                        break
                if gelukt:
                    break
    open_ = [f for f in los if f.GetReference() not in geplaatst]
    for ronde in range(4):
        rest = []
        for f in open_:
            an = anker(f)
            if not an and ronde < 3:
                rest.append(f)
                continue
            if an and ((klein(f) and plaats_rij(f, an[1], *an[2])) or plaats_bij(f, *an[2])):
                geplaatst.add(f.GetReference())
            elif not an:
                plaats_raster(f)
                geplaatst.add(f.GetReference())
            else:
                rest.append(f)
        open_ = rest
    for f in open_:
        print('GEEN PLEK voor', f.GetReference())

    for fp in board.GetFootprints():
        if fp.GetReference()[:1] in ('R', 'C', 'L', 'D', 'T', 'A') or fp.GetReference().startswith('U') and fp.GetReference() != 'U2':
            ref = fp.Reference()
            ref.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Value().SetVisible(False)

def vlakken(board, net):
    import math
    r = P['print_d'] / 2 - 0.4
    for laag, naam, prio in ((pcbnew.In1_Cu, 'GND', 1), (pcbnew.In4_Cu, 'GND', 1), (pcbnew.In3_Cu, 'VBAT', 1)):
        z = pcbnew.ZONE(board)
        z.SetLayer(laag)
        z.SetNet(net(naam))
        z.SetAssignedPriority(prio)
        z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetLocalClearance(pcbnew.FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        ol = z.Outline()
        ol.NewOutline()
        for i in range(72):
            a = 2 * math.pi * i / 72
            ol.Append(pcbnew.FromMM(OX + r * math.cos(a)), pcbnew.FromMM(OY - r * math.sin(a)))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

def main():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    r = P['print_d'] / 2
    printrand(board)

    for i, h in enumerate((15, 165, 285)):
        gat(board, *pol(P['print_schroef_r'], h), 'H%d' % (i + 1))

    for naam, midden, boog in ANTENNES:
        sector(board, naam, midden, boog, P['ant_r'], r)

    F, B = pcbnew.F_Fab, pcbnew.B_Fab
    rechthoek(board, CM3_X, CM3_Y, 40.1, 55.0, F, 'Radxa CM3 (40x55, 4,5 mm hoog): niets eronder')
    for i, (gx, gy) in enumerate(CM3_GATEN):
        gat(board, CM3_X + gx, CM3_Y + gy, 'H%d' % (i + 4), 'MountingHole_2.7mm_M2.5_Pad_Via')
    rechthoek(board, P['knop_x'], P['knop_y'], P['aan_tact'], P['aan_tact'], F)
    cirkel(board, P['tril_x'], P['tril_y'], P['tril_d'], F)
    rechthoek(board, P['qi_x'], P['qi_y'], P['qi_b'], P['qi_l'], F)
    cirkel(board, 0, 0, P['ms_d_uit'], pcbnew.Cmts_User)
    cirkel(board, 0, 0, P['qi_d'], pcbnew.Cmts_User)

    rechthoek(board, 0, 0, ACCU[2] - ACCU[0], ACCU[3] - ACCU[1], B)

    onderdelen(board)
    board.Save(PCB)
    print('geschreven:', os.path.normpath(PCB))

if __name__ == '__main__':
    main()
