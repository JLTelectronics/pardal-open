import os, shutil, subprocess, sys, time
import pcbnew

HIER = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HIER, '..', 'pardal.kicad_pcb')
BUILD = os.path.join(HIER, '..', 'build')
JAR = os.path.expanduser('~/tools/freerouting/freerouting-2.5.0.jar')
VLAKLAGEN = ('In1.Cu', 'In3.Cu', 'In4.Cu')
JAVA = '/opt/homebrew/opt/openjdk@27/bin/java'

def main():
    passes = sys.argv[1] if len(sys.argv) > 1 else '30'
    os.makedirs(BUILD, exist_ok=True)
    board = pcbnew.LoadBoard(PCB)
    if len(board.GetTracks()) == 0:
        shutil.copy(PCB, os.path.join(BUILD, 'pardal_ongerouteerd.kicad_pcb'))
    dsn, ses = os.path.join(BUILD, 'pardal.dsn'), os.path.join(BUILD, 'pardal.ses')
    kopie = os.path.join(BUILD, 'export.kicad_pcb')
    board.Save(kopie)
    exp = pcbnew.LoadBoard(kopie)
    for fp in list(exp.GetFootprints()):
        if fp.GetReference().startswith('AE'):
            exp.Remove(fp)
    if not pcbnew.ExportSpecctraDSN(exp, dsn):
        sys.exit('DSN-export mislukt')
    tekst = open(dsn).read()
    for laag in VLAKLAGEN:
        tekst = tekst.replace('(layer %s\n      (type signal)' % laag, '(layer %s\n      (type power)' % laag)
    open(dsn, 'w').write(tekst)
    print('DSN:', dsn)
    t = time.time()
    subprocess.run([JAVA, '-jar', JAR, '-de', dsn, '-do', ses, '-mp', passes, '--gui.enabled=false'],
                   check=True, stdout=open(os.path.join(BUILD, 'freerouting.log'), 'w'), stderr=subprocess.STDOUT)
    print('Freerouting klaar in %.0f s' % (time.time() - t))
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit('SES-import mislukt')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print('sporen:', len(board.GetTracks()))

if __name__ == '__main__':
    main()
