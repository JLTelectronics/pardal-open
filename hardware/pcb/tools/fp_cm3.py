import json, os

HIER = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HIER, '..', 'datasheets', 'rockchip')
LIB = os.path.join(HIER, '..', 'libs')
PADS = json.load(open(os.path.join(DS, 'cm3_pads_ioboard.json')))
NAMEN = json.load(open(os.path.join(DS, 'cm3_pinnen.json')))
MIDDEN = ((112.94 + 79.94) / 2, (35.03 + 82.97) / 2)
PAD_L, PAD_W = 1.14, 0.20

def connectoren():
    u, j = PADS['U33'], PADS['J24']
    uit = {'J69': [], 'J68': [], 'J1': []}
    for i, (x, y) in enumerate(u[:200]):
        naam = 'J69' if i < 100 else 'J68'
        uit[naam].append((i % 100 + 1, x - MIDDEN[0], -(y - MIDDEN[1]), True))
    for i, (x, y) in enumerate(j):
        uit['J1'].append((i + 1, x - MIDDEN[0], -(y - MIDDEN[1]), False))
    return uit

def centrum(p):
    xs = [q[1] for q in p]; ys = [q[2] for q in p]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

def footprint(naam, pads):
    cx, cy = centrum(pads)
    xs = [q[1] - cx for q in pads]; ys = [q[2] - cy for q in pads]
    bx, by = max(map(abs, xs)) + 0.9, max(map(abs, ys)) + 0.9
    r = ['(footprint "Radxa_CM3_%s"' % naam, '  (version 20240108) (generator "pardal_fp_cm3")', '  (layer "F.Cu")',
         '  (descr "Radxa CM3 %s: Hirose DF40C-100DS-0.4V(51), padgeometrie van het Radxa CM3 IO board v1.33; '
         'oorsprong = midden connector, positie t.o.v. CM3-midden: (%.3f, %.3f)")' % (naam, cx, cy),
         '  (attr smd)',
         '  (property "Reference" "%s" (at 0 %.2f 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))'
         % ({'J69': 'CN1', 'J68': 'CN2', 'J1': 'CN3'}[naam], -by - 0.8),
         '  (property "Value" "DF40C-100DS-0.4V" (at 0 %.2f 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))' % (by + 0.8)]
    for a, b in (((-bx, -by), (bx, -by)), ((bx, -by), (bx, by)), ((bx, by), (-bx, by)), ((-bx, by), (-bx, -by))):
        r.append('  (fp_line (start %.3f %.3f) (end %.3f %.3f) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))' % (a + b))
    p1 = next(q for q in pads if q[0] == 1)
    r.append('  (fp_circle (center %.3f %.3f) (end %.3f %.3f) (stroke (width 0.2) (type solid)) (fill solid) (layer "F.SilkS"))'
             % (p1[1] - cx + (1.2 if p1[1] - cx > 0 else -1.2) * (1 if p1[3] else 0),
                p1[2] - cy + (0 if p1[3] else (1.2 if p1[2] - cy > 0 else -1.2)),
                p1[1] - cx + (1.2 if p1[1] - cx > 0 else -1.2) * (1 if p1[3] else 0) + 0.15,
                p1[2] - cy + (0 if p1[3] else (1.2 if p1[2] - cy > 0 else -1.2))))
    for nr, x, y, langs_x in sorted(pads):
        w, h = (PAD_L, PAD_W) if langs_x else (PAD_W, PAD_L)
        r.append('  (pad "%d" smd rect (at %.4f %.4f) (size %.3f %.3f) (layers "F.Cu" "F.Paste" "F.Mask"))' % (nr, x - cx, y - cy, w, h))
    r.append(')')
    open(os.path.join(LIB, 'Pardal.pretty', 'Radxa_CM3_%s.kicad_mod' % naam), 'w').write('\n'.join(r) + '\n')
    return cx, cy

def soort(n):
    if n == 'GND' or n.startswith(('VCC_BAT', '+5V', 'USB_5V')):
        return 'passive'
    if n == 'NC':
        return 'no_connect'
    return 'passive'

def symbool(naam):
    pins = NAMEN[naam]
    G = 2.54
    out = ['\t(symbol "Radxa_CM3_%s"' % naam, '\t\t(pin_names (offset 1.016))',
           '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
           '\t\t(property "Reference" "CN" (at 0 2.54 0) (effects (font (size 1.27 1.27))))',
           '\t\t(property "Value" "Radxa CM3 %s" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))' % naam,
           '\t\t(property "Footprint" "Pardal:Radxa_CM3_%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))' % naam,
           '\t\t(property "Datasheet" "datasheets/rockchip/radxa_cm3_datasheet.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
           '\t\t(property "Description" "Radxa CM3 B2B-connector %s (DF40C-100DS-0.4V)" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))' % naam,
           '\t\t(symbol "Radxa_CM3_%s_0_1"' % naam,
           '\t\t\t(rectangle (start -22.86 %.2f) (end 22.86 %.2f) (stroke (width 0.254) (type default)) (fill (type background)))'
           % (G, -51 * G), '\t\t)', '\t\t(symbol "Radxa_CM3_%s_1_1"' % naam]
    for nr in range(1, 101):
        n = pins[str(nr)]['naam'].replace('‑', '-')
        links = nr % 2 == 1
        y = -G * ((nr + 1) // 2)
        x = -25.4 if links else 25.4
        out.append('\t\t\t(pin %s line (at %.2f %.2f %d) (length 2.54) (name "%s" (effects (font (size 1.0 1.0)))) '
                   '(number "%d" (effects (font (size 1.0 1.0)))))' % (soort(n), x, y, 0 if links else 180, n, nr))
    out += ['\t\t)', '\t)']
    return out

def main():
    posities = {}
    for naam, pads in connectoren().items():
        posities[naam] = footprint(naam, pads)
    sym = ['(kicad_symbol_lib', '\t(version 20241209)', '\t(generator "pardal_fp_cm3")', '\t(generator_version "10.0")']
    for naam in ('J69', 'J68', 'J1'):
        sym += symbool(naam)
    sym.append(')')
    open(os.path.join(LIB, 'pardal_cm3.kicad_sym'), 'w').write('\n'.join(sym) + '\n')
    json.dump({k: [round(v[0], 3), round(v[1], 3)] for k, v in posities.items()},
              open(os.path.join(DS, 'cm3_connector_posities.json'), 'w'), indent=1)
    print('CM3-connectoren (midden t.o.v. CM3-midden, KiCad-assen):', {k: tuple(round(c, 2) for c in v) for k, v in posities.items()})

if __name__ == '__main__':
    main()
