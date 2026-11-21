import math, os

HIER = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HIER, '..', 'libs', 'Pardal.pretty')

import sys
sys.path.insert(0, HIER)
from maten import P as _P
_R = _P['print_d'] / 2
R_IN, R_UIT, R_VOED = _R - 5.7, _R - 0.8, _R - 7.0
SPOOR, SPLEET = 0.5, 0.8
MARGE = 1.5
ANTENNES = {'hoofd': (37.0, 36.0, 'hoog')}

def pol(r, a):
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))

def pad(naam, midden, boog, kant='laag'):
    a0, a1 = midden - boog / 2 + MARGE, midden + boog / 2 - MARGE
    da = math.degrees((SPOOR + SPLEET) / R_IN)
    n0 = int((a1 - a0) / da) + 1
    if kant == 'hoog':
        a0, a1, da = a1, a0, -da
    n = n0
    pad = []
    pad.append(pol(R_VOED, a0))
    buiten = False
    for i in range(n):
        a = a0 + i * da
        pad.append(pol(R_IN if not buiten else R_UIT, a))
        buiten = not buiten
        pad.append(pol(R_UIT if buiten else R_IN, a))
    lengte = sum(math.dist(pad[i], pad[i + 1]) for i in range(len(pad) - 1))
    fx, fy = pad[0]
    prims = []
    for (x0, y0), (x1, y1) in zip(pad, pad[1:]):
        prims.append('(gr_line (start %.3f %.3f) (end %.3f %.3f) (width %.2f))'
                     % (x0 - fx, -(y0 - fy), x1 - fx, -(y1 - fy), SPOOR))
    regels = ['(footprint "LTE_meander_%s"' % naam,
              '  (version 20240108) (generator "pardal_fp_antennes")',
              '  (layer "F.Cu")',
              '  (descr "Meander-monopool LTE %s, %d slagen, %.0f mm; oorsprong = midden print")' % (naam, n, lengte),
              '  (attr smd exclude_from_pos_files exclude_from_bom)',
              '  (property "Reference" "AE" (at %.2f %.2f 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))'
              % (pol(R_IN - 2.0, midden)[0], -pol(R_IN - 2.0, midden)[1]),
              '  (property "Value" "LTE %s" (at %.2f %.2f 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))'
              % (naam, pol(R_IN - 3.0, midden)[0], -pol(R_IN - 3.0, midden)[1]),
              '  (pad "1" smd custom (at %.3f %.3f) (size %.2f %.2f) (layers "F.Cu")' % (fx, -fy, SPOOR, SPOOR),
              '    (options (clearance outline) (anchor circle))',
              '    (primitives', *['      ' + p for p in prims], '    )', '  )', ')']
    open(os.path.join(LIB, 'LTE_meander_%s.kicad_mod' % naam), 'w').write('\n'.join(regels) + '\n')
    print('LTE_meander_%s: %d slagen, spoorlengte %.0f mm' % (naam, n, lengte))

if __name__ == '__main__':
    for naam, (m, b, k) in ANTENNES.items():
        pad(naam, m, b, k)
