import math, os, sys, uuid
from collections import defaultdict, OrderedDict

sys.path.insert(0, os.path.dirname(__file__))
import kilib
from kilib import Q, dump, get_symbol
import design

PROJ = kilib.PROJ
NAME = "pardal"
NS = uuid.UUID("2b7f1e40-6d1a-4c55-9a0e-5a7da1da5001")
G = 2.54
STOMP = 2.54
VOEDING = ['GND', 'VBAT', 'VBUS', '+3V3', '+1V8', '+3V3_DISP', 'DISP_5V', 'QI_5V']
RECHTOP = ('Device:R', 'Device:C', 'Device:L', 'Device:FerriteBead')
PAPIER = [("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]
_pwr = [0]

def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))

def eff(size=1.27, justify=None, hide=False):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e

def rnd(v):
    return round(v / G) * G

def prop(key, val, x, y, hide=False, just=None, size=1.27):
    return ["property", Q(key), Q(val), ["at", round(x, 2), round(y, 2), 0], eff(size, just, hide)]

def tekstbreedte(t, size=1.27):
    return len(t) * size * 0.78 + 1.5

def wire(a, b, *sleutel):
    return ["wire", ["pts", ["xy", round(a[0], 2), round(a[1], 2)], ["xy", round(b[0], 2), round(b[1], 2)]],
            ["stroke", ["width", 0], ["type", "default"]], ["uuid", Q(uid(*sleutel))]]

RICHTING = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
LABELHOEK = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}

class Unit:

    def __init__(self, sname, c, unit, alle, scope, root_uuid, sheet_uuid):
        self.items, self.lib_ids = [], {c["lib"]}
        ref, lib = c["ref"], c["lib"]
        ps = [p for p in alle if p[0] in (0, unit)]
        rot = 0
        if lib in RECHTOP and len(c["pins"]) == 2:
            n1, n2 = c["pins"].get("1"), c["pins"].get("2")
            if n1 == "GND" or (n2 in VOEDING and n2 != "GND"):
                rot = 180
        pinpos = []
        for p in ps:
            _, nr, naam, soort, px, py, hoek, _l = p
            if rot == 180:
                px, py, hoek = -px, -py, (hoek + 180) % 360
            pinpos.append((nr, soort, px, -py, int(hoek) % 360))
        xs = [q[2] for q in pinpos] or [0]
        ys = [q[3] for q in pinpos] or [0]
        bx0, bx1, by0, by1 = min(xs + [-G]), max(xs + [G]), min(ys + [-G]), max(ys + [G])
        self.ext = [bx0, bx1, by0, by1]
        dnp = "yes" if c.get("dnp") else "no"
        in_bom = "no" if (ref.startswith("#") or lib == "Connector:TestPoint" or c.get("dnp")
                          or c["fp"].startswith(("TestPoint:", "Pardal:LTE", "Pardal:UART"))) else "yes"
        if lib in RECHTOP:
            pr = [prop("Reference", ref, 2.54, -1.27, just="left", hide=ref.startswith("#")),
                  prop("Value", c["value"], 2.54, 1.27, just="left")]
            self._grow(2.54, tekstbreedte(max(ref, c["value"], key=len)) + 2.54, -2.5, 2.5)
        else:
            pr = [prop("Reference", ref, (bx0 + bx1) / 2, by0 - 1.8, hide=ref.startswith("#")),
                  prop("Value", c["value"], (bx0 + bx1) / 2, by1 + 1.8)]
            w = tekstbreedte(max(ref, c["value"], key=len)) / 2
            self._grow(-w, w, by0 - 3, by1 + 3)
        sym = ["symbol", ["lib_id", Q(lib)], ["at", 0, 0, rot], ["unit", unit], ["exclude_from_sim", "no"],
               ["in_bom", in_bom], ["on_board", "no" if ref.startswith("#") else "yes"], ["dnp", dnp],
               ["uuid", Q(uid(sname, ref, unit))]] + pr + [
               prop("Footprint", c["fp"], 0, 0, hide=True), prop("Datasheet", "", 0, 0, hide=True)]
        if c.get("lcsc"):
            sym.append(prop("LCSC", c["lcsc"], 0, 0, hide=True))
        for p in ps:
            sym.append(["pin", Q(p[1]), ["uuid", Q(uid(sname, ref, unit, "pin", p[1]))]])
        sym.append(["instances", ["project", Q(NAME), ["path", Q("/%s/%s" % (root_uuid, sheet_uuid)),
                                                      ["reference", Q(ref)], ["unit", unit]]]])
        self.items.append(sym)
        for nr, soort, ex, ey, hoek in pinpos:
            net = c["pins"].get(nr)
            if net is None:
                if soort != "no_connect":
                    self.items.append(["no_connect", ["at", ex, ey], ["uuid", Q(uid(sname, ref, unit, "nc", nr))]])
                continue
            d = RICHTING[hoek]
            px, py = ex + d[0] * STOMP, ey + d[1] * STOMP
            self.items.append(wire((ex, ey), (px, py), sname, ref, unit, "w", nr))
            if net in VOEDING:
                self._voeding(net, px, py, d, sname, root_uuid, sheet_uuid, (ref, unit, nr))
            else:
                self._label(net, True, px, py, d, sname, (ref, unit, nr))

    def _grow(self, x0, x1, y0, y1):
        e = self.ext
        self.ext = [min(e[0], x0), max(e[1], x1), min(e[2], y0), max(e[3], y1)]

    def _voeding(self, net, x, y, d, sname, root_uuid, sheet_uuid, sleutel):
        gnd = net == "GND"
        rot = 180 if (gnd and d == (0, -1)) or (not gnd and d == (0, 1)) else 0
        omlaag = (gnd and rot == 0) or (not gnd and rot == 180)
        vy = y + 3.81 if omlaag else y - 3.81
        _pwr[0] += 1
        ref = "#PWR%03d" % _pwr[0]
        lib = "pardal:PWR_" + net
        self.lib_ids.add(lib)
        self.items.append(["symbol", ["lib_id", Q(lib)], ["at", x, y, rot], ["unit", 1], ["exclude_from_sim", "no"],
                           ["in_bom", "no"], ["on_board", "yes"], ["dnp", "no"],
                           ["uuid", Q(uid(sname, "pwr", *sleutel))],
                           prop("Reference", ref, x, y, hide=True), prop("Value", net, x, vy),
                           prop("Footprint", "", x, y, hide=True), prop("Datasheet", "", x, y, hide=True),
                           ["pin", Q("1"), ["uuid", Q(uid(sname, "pwr", *sleutel, "pin"))]],
                           ["instances", ["project", Q(NAME), ["path", Q("/%s/%s" % (root_uuid, sheet_uuid)),
                                                              ["reference", Q(ref)], ["unit", 1]]]]])
        w = tekstbreedte(net) / 2
        self._grow(x - w, x + w, min(y, vy) - 1.5, max(y, vy) + 1.5)

    def _label(self, net, globaal, x, y, d, sname, sleutel):
        rot = LABELHOEK[d]
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[rot]
        if globaal:
            self.items.append(["global_label", Q(net), ["shape", "bidirectional"], ["at", x, y, rot],
                               ["fields_autoplaced", "yes"], eff(1.27, just),
                               ["uuid", Q(uid(sname, "lbl", *sleutel))],
                               ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0],
                                eff(1.0, hide=True)]])
        else:
            self.items.append(["label", Q(net), ["at", x, y, rot], ["fields_autoplaced", "yes"], eff(1.27, just),
                               ["uuid", Q(uid(sname, "lbl", *sleutel))]])
        w = tekstbreedte(net) + (3 if globaal else 0)
        ex, ey = x + d[0] * w, y + d[1] * w
        self._grow(min(x, ex) - 1, max(x, ex) + 1, min(y, ey) - 1, max(y, ey) + 1)

    def verschuif(self, dx, dy):
        def mv(node):
            if isinstance(node, list) and node:
                if node[0] in ("at", "xy") and len(node) >= 3:
                    node[1] = round(node[1] + dx, 2)
                    node[2] = round(node[2] + dy, 2)
                    return
                for e in node[1:]:
                    mv(e)
        for it in self.items:
            mv(it)
        return self.items

    @property
    def w(self):
        return self.ext[1] - self.ext[0]

    @property
    def h(self):
        return self.ext[3] - self.ext[2]

def plaats_rijen(blokken, maxw, x0, y0, tussen):
    x, y, rij_h, breed = x0, y0, 0, 0
    for w, h, plaats in blokken:
        if x > x0 and x + w > x0 + maxw:
            x, y, rij_h = x0, y + rij_h + tussen, 0
        plaats(x, y)
        x += w + tussen
        rij_h = max(rij_h, h)
        breed = max(breed, x - tussen - x0)
    return breed, y + rij_h - y0

def build_sheet(sname, sh, root_uuid, sheet_uuid, scope):
    items, libs = [], set()
    groepen = OrderedDict()
    for c in sh["comps"]:
        groepen.setdefault(c.get("groep", sh["title"]), []).append(c)
    gblokken = []
    for gi, (gnaam, comps) in enumerate(groepen.items()):
        units = []
        for c in comps:
            alle = kilib.pins(c["lib"])
            for unit in sorted({p[0] for p in alle if p[0] > 0}) or [1]:
                u = Unit(sname, c, unit, alle, scope, root_uuid, sheet_uuid)
                units.append(u)
                libs |= u.lib_ids
        opp = sum(u.w * u.h for u in units)
        maxw = max(90, max(u.w for u in units) + 4, math.sqrt(opp) * 1.6)
        gblokken.append((gi, gnaam, units, maxw))

    rand, titel_h = 5.08, 7.62
    groot = []
    for gi, gnaam, units, maxw in gblokken:
        bw, bh = plaats_rijen([(u.w, u.h, lambda x, y: None) for u in units], maxw, 0, 0, 5.08)
        bw = max(bw, tekstbreedte(gnaam, 2.0) + 4)
        groot.append((rnd(bw + 2 * rand + G), rnd(bh + 2 * rand + titel_h + G), gi, gnaam, units, maxw))

    def plaats_groep(gi, gnaam, units, maxw, bw, bh):
        def f(x, y):
            x, y = rnd(x), rnd(y)
            items.append(["rectangle", ["start", x, y], ["end", round(x + bw, 2), round(y + bh, 2)],
                          ["stroke", ["width", 0.3], ["type", "dash"]], ["fill", ["type", "none"]],
                          ["uuid", Q(uid(sname, "kader", gi))]])
            items.append(["text", Q(gnaam), ["exclude_from_sim", "no"], ["at", x + 2.54, y + 4.5, 0],
                          eff(2.0, "left"), ["uuid", Q(uid(sname, "gtitel", gi))]])

            def zet(u):
                return lambda ux, uy: items.extend(u.verschuif(rnd(ux - u.ext[0] + 1.27), rnd(uy - u.ext[2] + 1.27)))
            plaats_rijen([(u.w + G, u.h + G, zet(u)) for u in units], maxw, x + rand, y + rand + titel_h, 2.54)
        return f

    notes = sh["notes"]
    items.append(["text", Q(sh["title"]), ["exclude_from_sim", "no"], ["at", 25.4, 15.24, 0], eff(3.0, "left"),
                  ["uuid", Q(uid(sname, "titel"))]])
    y0 = 25.4 + len(notes) * 2.6 + 7.62
    totaal = sum(b[0] * b[1] for b in groot)
    bladw = max(max(b[0] for b in groot), math.sqrt(totaal) * 1.5, 360)
    breed, hoog = plaats_rijen([(bw, bh, plaats_groep(gi, gn, us, mw, bw, bh)) for bw, bh, gi, gn, us, mw in groot],
                               bladw, 25.4, y0, 10.16)
    nodig_w, nodig_h = breed + 50.8, y0 + hoog + 45
    papier = next((p for p in PAPIER if p[1] >= nodig_w and p[2] >= nodig_h), PAPIER[-1])
    doc = ["kicad_sch", ["version", 20250114], ["generator", Q("pardal_gen_sch")], ["generator_version", Q("9.0")],
           ["uuid", Q(sheet_uuid)], ["paper", Q(papier[0])],
           ["title_block", ["title", Q("Pardal Dash rev B - " + sh["title"])], ["company", Q("Pardal")]],
           ["lib_symbols"] + [get_symbol(k) for k in sorted(libs)]] + items
    open(os.path.join(PROJ, sname + ".kicad_sch"), "w").write(dump(doc) + "\n")
    return papier[0]

BLOKPLAATS = {
    "module": (160, 120, 100, 60),
    "antennes": (160, 40, 100, 50),
    "voeding": (25, 55, 100, 55),
    "bediening": (25, 160, 100, 55),
    "scherm": (295, 55, 100, 55),
    "sensoren": (295, 160, 100, 60),
}

def main():
    root_uuid = uid("root")
    netten_per_blad = defaultdict(set)
    for sname, sh in design.SHEETS.items():
        for c in sh["comps"]:
            if not c["ref"].startswith("#"):
                netten_per_blad[sname] |= set(c["pins"].values())
    scope = defaultdict(int)
    for sname, nets in netten_per_blad.items():
        for n in nets:
            scope[n] += 1
    _pwr[0] = 0
    blocks, papier = [], {}
    for i, (sname, sh) in enumerate(design.SHEETS.items()):
        su = uid("sheet", sname)
        papier[sname] = build_sheet(sname, sh, root_uuid, su, scope)
        blocks.append((sname, sh, su, i))
    items = []
    for sname, sh, su, i in blocks:
        x, y, b, h = BLOKPLAATS.get(sname, (25.4 + (i % 3) * 120, 230, 100, 40))
        items.append(["sheet", ["at", x, y], ["size", b, h], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                      ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                      ["stroke", ["width", 0.3], ["type", "solid"]], ["fill", ["color", 255, 255, 225, 1.0]],
                      ["uuid", Q(su)],
                      ["property", Q("Sheetname"), Q(sh["title"]), ["at", x, y - 0.7, 0], eff(1.5, "left bottom")],
                      ["property", Q("Sheetfile"), Q(sname + ".kicad_sch"), ["at", x, y + h + 0.6, 0],
                       eff(1.1, "left top")],
                      ["instances", ["project", Q(NAME), ["path", Q("/" + root_uuid), ["page", Q(str(i + 2))]]]]])
    mx, my, mb, mh = BLOKPLAATS["module"]
    mcx, mcy = mx + mb / 2, my + mh / 2
    for sname, sh, su, i in blocks:
        if sname == "module" or sname not in BLOKPLAATS:
            continue
        x, y, b, h = BLOKPLAATS[sname]
        cx, cy = x + b / 2, y + h / 2
        gedeeld = sorted(n for n in netten_per_blad[sname] & netten_per_blad["module"] if n not in VOEDING)
        if cx < mx:
            a, e = (mx, mcy + (cy - mcy) * 0.4), (x + b, cy)
        elif cx > mx + mb:
            a, e = (mx + mb, mcy + (cy - mcy) * 0.4), (x, cy)
        else:
            a, e = (mcx, my), (cx, y + h)
        items.append(["polyline", ["pts", ["xy", round(a[0], 2), round(a[1], 2)], ["xy", round(e[0], 2), round(e[1], 2)]],
                      ["stroke", ["width", 0.5], ["type", "solid"]], ["fill", ["type", "none"]],
                      ["uuid", Q(uid("root", "lijn", sname))]])
        regels, regel = [], ""
        for n in gedeeld:
            if regel and len(regel) + len(n) > 30:
                regels.append(regel.rstrip(", "))
                regel = ""
            regel += n + ", "
        if regel:
            regels.append(regel.rstrip(", "))
        if a[0] == mcx:
            tx, ty, just = mcx + 3, (a[1] + e[1]) / 2 - 2, "left"
        else:
            tx, ty, just = (a[0] + e[0]) / 2, max(a[1], e[1]) + 2, "top"
        items.append(["text", Q("\n".join(regels)), ["exclude_from_sim", "no"],
                      ["at", round(tx, 2), round(ty, 2), 0], eff(1.0, just), ["uuid", Q(uid("root", "netten", sname))]])
    items.append(["text", Q("PARDAL DASH rev B - HOOFDSCHEMA"), ["exclude_from_sim", "no"], ["at", 25.4, 14, 0],
                  eff(3.5, "left"), ["uuid", Q(uid("root", "titel"))]])
    doc = ["kicad_sch", ["version", 20250114], ["generator", Q("pardal_gen_sch")], ["generator_version", Q("9.0")],
           ["uuid", Q(sheet_uuid)], ["paper", Q(papier[0])],
           ["title_block", ["title", Q("Pardal Dash rev B - " + sh["title"])], ["company", Q("Pardal")]],
           ["lib_symbols"] + [get_symbol(k) for k in sorted(libs)]] + items
    open(os.path.join(PROJ, sname + ".kicad_sch"), "w").write(dump(doc) + "\n")
    return papier[0]

BLOKPLAATS = {
    "module": (160, 120, 100, 60),
    "antennes": (160, 40, 100, 50),
    "voeding": (25, 55, 100, 55),
    "bediening": (25, 160, 100, 55),
    "scherm": (295, 55, 100, 55),
    "sensoren": (295, 160, 100, 60),
}

def main():
    root_uuid = uid("root")
    netten_per_blad = defaultdict(set)
    for sname, sh in design.SHEETS.items():
        for c in sh["comps"]:
            if not c["ref"].startswith("#"):
                netten_per_blad[sname] |= set(c["pins"].values())
    scope = defaultdict(int)
    for sname, nets in netten_per_blad.items():
        for n in nets:
            scope[n] += 1
    _pwr[0] = 0
    blocks, papier = [], {}
    for i, (sname, sh) in enumerate(design.SHEETS.items()):
        su = uid("sheet", sname)
        papier[sname] = build_sheet(sname, sh, root_uuid, su, scope)
        blocks.append((sname, sh, su, i))
    items = []
    for sname, sh, su, i in blocks:
        x, y, b, h = BLOKPLAATS.get(sname, (25.4 + (i % 3) * 120, 230, 100, 40))
        items.append(["sheet", ["at", x, y], ["size", b, h], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                      ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                      ["stroke", ["width", 0.3], ["type", "solid"]], ["fill", ["color", 255, 255, 225, 1.0]],
                      ["uuid", Q(su)],
                      ["property", Q("Sheetname"), Q(sh["title"]), ["at", x, y - 0.7, 0], eff(1.5, "left bottom")],
                      ["property", Q("Sheetfile"), Q(sname + ".kicad_sch"), ["at", x, y + h + 0.6, 0],
                       eff(1.1, "left top")],
                      ["instances", ["project", Q(NAME), ["path", Q("/" + root_uuid), ["page", Q(str(i + 2))]]]]])
    mx, my, mb, mh = BLOKPLAATS["module"]
    mcx, mcy = mx + mb / 2, my + mh / 2
    for sname, sh, su, i in blocks:
        if sname == "module" or sname not in BLOKPLAATS:
            continue
        x, y, b, h = BLOKPLAATS[sname]
        cx, cy = x + b / 2, y + h / 2
        gedeeld = sorted(n for n in netten_per_blad[sname] & netten_per_blad["module"] if n not in VOEDING)
        if cx < mx:
            a, e = (mx, mcy + (cy - mcy) * 0.4), (x + b, cy)
        elif cx > mx + mb:
            a, e = (mx + mb, mcy + (cy - mcy) * 0.4), (x, cy)
        else:
            a, e = (mcx, my), (cx, y + h)
        items.append(["polyline", ["pts", ["xy", round(a[0], 2), round(a[1], 2)], ["xy", round(e[0], 2), round(e[1], 2)]],
                      ["stroke", ["width", 0.5], ["type", "solid"]], ["fill", ["type", "none"]],
                      ["uuid", Q(uid("root", "lijn", sname))]])
        regels, regel = [], ""
        for n in gedeeld:
            if regel and len(regel) + len(n) > 30:
                regels.append(regel.rstrip(", "))
                regel = ""
            regel += n + ", "
        if regel:
            regels.append(regel.rstrip(", "))
        if a[0] == mcx:
            tx, ty, just = mcx + 3, (a[1] + e[1]) / 2 - 2, "left"
        else:
            tx, ty, just = (a[0] + e[0]) / 2, max(a[1], e[1]) + 2, "top"
        items.append(["text", Q("\n".join(regels)), ["exclude_from_sim", "no"],
                      ["at", round(tx, 2), round(ty, 2), 0], eff(1.0, just), ["uuid", Q(uid("root", "netten", sname))]])
    items.append(["text", Q("PARDAL DASH rev B - HOOFDSCHEMA"), ["exclude_from_sim", "no"], ["at", 25.4, 14, 0],
                  eff(3.5, "left"), ["uuid", Q(uid("root", "titel"))]])
    items.append(["text", Q("Ronde print Ø112 met de Radxa CM3 (RK3566, Android, wifi/BT) + Quectel EC200U-EU (LTE Cat 1 + GNSS) en het Waveshare 3.4\" DSI-scherm.\n"
                            "Dubbelklik op een blok om het blad te openen. Lijnen = signalen tussen module en blad (voeding via VBAT/+1V8/GND).\n"
                            "Gegenereerd door tools/gen_sch.py uit tools/design.py - niet met de hand aanpassen."),
                  ["exclude_from_sim", "no"], ["at", 25.4, 19, 0], eff(1.4, "left top"), ["uuid", Q(uid("root", "tekst"))]])
    doc = ["kicad_sch", ["version", 20250114], ["generator", Q("pardal_gen_sch")], ["generator_version", Q("9.0")],
           ["uuid", Q(root_uuid)], ["paper", Q("A3")],
           ["title_block", ["title", Q("Pardal Dash rev B - hoofdschema")], ["company", Q("Pardal")]],
           ["lib_symbols"]] + items + [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]]]
    open(os.path.join(PROJ, NAME + ".kicad_sch"), "w").write(dump(doc) + "\n")
    print("schema's geschreven:", NAME + ".kicad_sch +", ", ".join("%s (%s)" % (b[0], papier[b[0]]) for b in blocks))

if __name__ == "__main__":
    main()
