import os

HIER = os.path.dirname(os.path.abspath(__file__))
UIT = os.path.join(HIER, '..', 'libs', 'pardal.kicad_sym')
G = 2.54

VOEDING = ['GND', 'VBAT', 'VBUS', '+3V3', '+1V8', '+3V3_DISP', 'DISP_5V', 'QI_5V']

def voedingssymbool(net):
    n = 'PWR_' + net
    if net == 'GND':
        g = ['\t\t\t(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) '
             '(stroke (width 0) (type default)) (fill (type none)))']
        hoek, vy = 270, -3.81
    else:
        g = ['\t\t\t(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
             '\t\t\t(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))',
             '\t\t\t(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))']
        hoek, vy = 90, 3.556
    return ['\t(symbol "%s"' % n, '\t\t(power)', '\t\t(pin_numbers (hide yes))', '\t\t(pin_names (offset 0) (hide yes))',
            '\t\t(exclude_from_sim no) (in_bom no) (on_board yes)',
            '\t\t(property "Reference" "#PWR" (at 0 -6.35 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            '\t\t(property "Value" "%s" (at 0 %.3f 0) (effects (font (size 1.27 1.27))))' % (net, vy),
            '\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            '\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            '\t\t(property "Description" "voedingssymbool %s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))' % net,
            '\t\t(symbol "%s_0_1"' % n] + g + ['\t\t)',
            '\t\t(symbol "%s_1_1"' % n,
            '\t\t\t(pin power_in line (at 0 0 %d) (length 0) (name "%s" (effects (font (size 1.27 1.27)))) '
            '(number "1" (effects (font (size 1.27 1.27)))))' % (hoek, net), '\t\t)', '\t)']

def euicc():
    links = [('8', 'VCC', 'power_in'), ('7', 'RST', 'input'), ('6', 'CLK', 'input'), ('3', 'I/O', 'bidirectional')]
    rechts = [('1', 'GND', 'power_in'), ('9', 'EP', 'passive'), ('2', 'VPP', 'no_connect'), ('4', 'NC', 'no_connect'),
              ('5', 'NC', 'no_connect')]
    o = ['\t(symbol "eUICC_MFF2"', '\t\t(pin_names (offset 1.016))', '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
         '\t\t(property "Reference" "U" (at 0 8.89 0) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Value" "eUICC_MFF2" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))',
         '\t\t(property "Footprint" "Package_DFN_QFN:DFN-8-1EP_6x5mm_P1.27mm_EP2x2mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '\t\t(property "Description" "eUICC (GSMA SGP.22) in MFF2-behuizing" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '\t\t(symbol "eUICC_MFF2_0_1"',
         '\t\t\t(rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))',
         '\t\t)', '\t\t(symbol "eUICC_MFF2_1_1"']
    for i, (nr, nm, t) in enumerate(links):
        o.append('\t\t\t(pin %s line (at -10.16 %.2f 0) (length 2.54) (name "%s" (effects (font (size 1.27 1.27)))) '
                 '(number "%s" (effects (font (size 1.27 1.27)))))' % (t, 5.08 - i * 2.54, nm, nr))
    for i, (nr, nm, t) in enumerate(rechts):
        o.append('\t\t\t(pin %s line (at 10.16 %.2f 180) (length 2.54) (name "%s" (effects (font (size 1.27 1.27)))) '
                 '(number "%s" (effects (font (size 1.27 1.27)))))' % (t, 5.08 - i * 2.54, nm, nr))
    o += ['\t\t)', '\t)']
    return o

def main():
    out = ['(kicad_symbol_lib', '\t(version 20241209)', '\t(generator "pardal_sym")', '\t(generator_version "10.0")']
    out += euicc() + [l for net in VOEDING for l in voedingssymbool(net)]
    out.append(')')
    os.makedirs(os.path.dirname(UIT), exist_ok=True)
    open(UIT, 'w').write('\n'.join(out) + '\n')

if __name__ == '__main__':
    main()
