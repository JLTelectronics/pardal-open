import json, os

HIER = os.path.dirname(os.path.abspath(__file__))
PRO = os.path.join(HIER, '..', 'pardal.kicad_pro')

KLASSEN = {
    'Default': (0.10, 0.12, 0.45, 0.25, None, None),
    'VBAT': (0.15, 0.80, 0.60, 0.30, None, None),
    'VOEDING': (0.15, 0.40, 0.60, 0.30, None, None),
    'RF50': (0.20, 0.18, 0.45, 0.25, None, None),
    'USB90': (0.12, 0.13, 0.45, 0.25, 0.13, 0.15),
    'MIPI100': (0.12, 0.10, 0.45, 0.25, 0.10, 0.18),
}
PATRONEN = [
    ('VBAT*', 'VBAT'), ('BAT_N', 'VBAT'), ('VBUS', 'VBAT'), ('QI_5V', 'VOEDING'), ('+2V85', 'VOEDING'), ('DISP_5V', 'VOEDING'), ('DISP_SW', 'VOEDING'), ('+3V3_DISP', 'VOEDING'),
    ('MOT_N', 'VOEDING'), ('ANT_*', 'RF50'), ('USB_D*', 'USB90'), ('MDM_USB_D*', 'USB90'), ('DSI_D*', 'MIPI100'), ('DSI_CLK*', 'MIPI100'),
]

def klasse_json(naam, waarden, sjabloon):
    clr, tw, vd, vh, dw, dg = waarden
    k = dict(sjabloon)
    k.update({'name': naam, 'clearance': clr, 'track_width': tw, 'via_diameter': vd, 'via_drill': vh,
              'microvia_diameter': 0.3, 'microvia_drill': 0.1})
    if dw:
        k['diff_pair_width'], k['diff_pair_gap'], k['diff_pair_via_gap'] = dw, dg, 0.25
    return k

def main():
    pro = json.load(open(PRO))
    ns = pro.setdefault('net_settings', {})
    oud = {c['name']: c for c in ns.get('classes', [])}
    sjabloon = oud.get('Default', {'bus_width': 12, 'line_style': 0, 'pcb_color': 'rgba(0, 0, 0, 0.000)',
                                   'priority': 2147483647, 'schematic_color': 'rgba(0, 0, 0, 0.000)', 'wire_width': 6})
    ns['classes'] = [klasse_json(n, w, sjabloon) for n, w in KLASSEN.items()]
    for i, c in enumerate(ns['classes'][1:]):
        c['priority'] = i
    ns['netclass_patterns'] = [{'netclass': k, 'pattern': p} for p, k in PATRONEN]
    ns.pop('netclass_assignments', None)
    rules = pro.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rules', {})
    rules.update({'min_clearance': 0.09, 'min_track_width': 0.09, 'min_via_diameter': 0.45, 'min_through_hole_diameter': 0.2,
                  'min_hole_clearance': 0.2, 'min_copper_edge_clearance': 0.3, 'min_hole_to_hole': 0.25})
    json.dump(pro, open(PRO, 'w'), indent=2)
    print('netklassen:', ', '.join(KLASSEN), '| patronen:', len(PATRONEN))

if __name__ == '__main__':
    main()
