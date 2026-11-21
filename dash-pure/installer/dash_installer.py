#!/usr/bin/env python3
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HIER)
sys.path.insert(0, HIER)
import partitions as P

_TTY = sys.stdout.isatty()
def _c(code): return code if _TTY else ""
O  = _c("\033[38;5;208m"); GR = _c("\033[38;5;46m"); RD = _c("\033[38;5;196m")
GL = _c("\033[38;5;220m"); DIM = _c("\033[38;5;245m"); B = _c("\033[1m"); X = _c("\033[0m")

def kleur(s, c):
    return {"r": RD, "g": GR, "y": GL, "b": O + B}.get(c, "") + s + X

_banner_getoond = False
def banner():
    global _banner_getoond
    if _banner_getoond:
        return
    _banner_getoond = True
    print(O + B + r"""
   ╔══════════════════════════════════════════════════════╗
   ║   ██████╗  █████╗ ██████╗ ██████╗  █████╗ ██╗         ║
   ║   ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║         ║
   ║   ██████╔╝███████║██████╔╝██║  ██║███████║██║         ║
   ║   ██╔═══╝ ██╔══██║██╔══██╗██║  ██║██╔══██║██║         ║
   ║   ██║     ██║  ██║██║  ██║██████╔╝██║  ██║███████╗    ║
   ║   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝    ║
   ║             D A S H - P U R E                         ║
   ╚══════════════════════════════════════════════════════╝""" + X)

_BREED = 46
def balk(pct, msg):
    vol = pct * _BREED // 100
    print("\n   %s⟦%s%s%s%s⟧%s %s%3d%%%s  %s%s%s" % (
        B, O + "█" * vol + X, DIM, "░" * (_BREED - vol), X + B, X, B, pct, X, O + B, msg, X))

def box(titel, regels):
    W = 54
    def rij(plain, kleurd):
        return "   " + O + B + "│" + X + kleurd + " " * max(0, W - len(plain)) + O + B + "│" + X
    print("\n   " + O + B + "╭" + "─" * W + "╮" + X)
    print(rij("  ✓  " + titel, "  " + GR + B + "✓  " + titel + X))
    print("   " + O + B + "├" + "─" * W + "┤" + X)
    for t in regels:
        print(rij("  ✓ " + t, "  " + GR + "✓" + X + " " + t))
    print("   " + O + B + "╰" + "─" * W + "╯" + X)

def kop(s):    print("\n" + O + B + "   ┏━━ " + s + X)
def ok(s):     print("     " + GR + "✓" + X + " " + s)
def bezig(s):  print("     " + GL + "▸" + X + " " + s)
def waarsch(s):print("     " + GL + "!" + X + " " + s)
def fout(s):   print("     " + RD + "✗ " + s + X)
def prompt(s): print(DIM + "   pardal@dash" + X + ":" + O + "~" + X + DIM + "$" + X + " " + B + s + X)

def vraag_ja(v):
    try:
        return input("\n   " + O + B + "➜" + X + " " + v + " [" + B + "j" + X + "/n]: "
                     ).strip().lower() in ("j", "ja", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False

def vind_mtk():
    kandidaten = [os.environ.get("MTKCLIENT"),
                  os.path.expanduser("~/mtkclient"),
                  "/opt/mtkclient"]
    for k in kandidaten:
        if k and os.path.isfile(os.path.join(k, "mtk.py")):
            py = os.path.join(k, ".venv", "bin", "python")
            if not os.path.isfile(py):
                py = shutil.which("python3") or sys.executable
            return k, py
    return None, None

def mtk_cmd(mtkdir, py, args, titel, brom=True):
    if brom:
        kop("ZET DE DASH NU IN BROM  (dit moet jij doen)")
        print("     " + GL + "①" + X + " USB-kabel mag aangesloten blijven")
        print("     " + GL + "②" + X + " houd  " + B + "rood + blauw + power" + X +
              "  ingedrukt tot het scherm " + B + "ZWART" + X + " wordt")
        print("     " + GL + "③" + X + " laat " + B + "power" + X + " los, houd  " +
              B + "rood + blauw" + X + "  nog " + B + "~10 seconden" + X + " vast")
        print("     " + GL + "④" + X + " daarna pakt mtkclient de verbinding vanzelf — " + DIM + "even geduld" + X)
    bezig("bezig: " + titel + ("" if brom else DIM + "  (blijft 'ie wachten? zelfde BROM-truc)" + X))
    sys.stdout.flush()
    cmd = [py, "mtk.py"] + args
    proc = subprocess.Popen(cmd, cwd=mtkdir)
    try:
        return proc.wait() == 0
    except KeyboardInterrupt:
        proc.terminate()
        return False

def sha256(pad, blok=1 << 20):
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for b in iter(lambda: f.read(blok), b""):
            h.update(b)
    return h.hexdigest()

def schrijf_manifest(map_, namen):
    reg = []
    for n in namen:
        pad = os.path.join(map_, n + ".img")
        if os.path.isfile(pad):
            reg.append((sha256(pad), n + ".img"))
    with open(os.path.join(map_, "MANIFEST.sha256"), "w") as f:
        f.write("# DASH01 back-up-manifest — %s\n" % time.strftime("%Y-%m-%d %H:%M"))
        for h, n in reg:
            f.write("%s  %s\n" % (h, n))
    return len(reg)

def lees_manifest(map_):
    pad = os.path.join(map_, "MANIFEST.sha256")
    uit = []
    if not os.path.isfile(pad):
        return uit
    for r in open(pad):
        r = r.strip()
        if not r or r.startswith("#"):
            continue
        h, _, n = r.partition("  ")
        if n:
            uit.append((h, n.strip()))
    return uit

def cmd_check(a):
    banner()
    balk(10, "Controle van de omgeving")
    mtkdir, py = vind_mtk()
    alles = True
    if mtkdir:
        ok("mtkclient gevonden: " + mtkdir)
    else:
        fout("mtkclient niet gevonden. Zet het in ~/mtkclient of zet $MTKCLIENT.")
        alles = False
    boot = os.path.join(PROJ, "build", "boot-pure.img.recovery")
    if os.path.isfile(boot):
        ok("DASH-PURE boot-image aanwezig: build/boot-pure.img.recovery")
    else:
        waarsch("build/boot-pure.img.recovery ontbreekt (nodig voor 'install').")
    vrij = shutil.disk_usage(a.map or ".").free >> 30
    (ok if vrij >= 70 else waarsch)("vrije schijfruimte: %d GB (volledige back-up ~62 GB)" % vrij)
    print("\n" + P.ESIM_WAARSCHUWING)
    return 0 if alles else 1

def cmd_backup(a):
    kop("Volledige back-up")
    mtkdir, py = vind_mtk()
    if not mtkdir:
        fout("mtkclient niet gevonden."); return 1
    os.makedirs(a.map, exist_ok=True)
    uniekmap = os.path.join(a.map, "uniek")
    os.makedirs(uniekmap, exist_ok=True)

    extra = ["--preloader", a.preloader] if getattr(a, "preloader", None) else []

    namen = P.ALLE_PARTITIES
    if getattr(a, "zonder_userdata", False):
        namen = [n for n in namen if n != "userdata"]

    print("Dit leest de partities van je toestel naar:\n  " + os.path.abspath(a.map))
    if getattr(a, "zonder_userdata", False):
        print("ZONDER userdata (51 GB): alle onvervangbare partities (modem/identiteit,")
        print("bootchain, super) wel. Past op een kleinere schijf; duurt ~3-6 min.")
    else:
        print("Er wordt niets naar het toestel geschreven. Duurt ~15-25 min (super+userdata zijn groot).")
    if not a.ja and not vraag_ja("Back-up starten?"):
        print("Afgebroken."); return 1
    uitlijst = ",".join(namen)
    padlijst = ",".join(os.path.join(a.map, n + ".img") for n in namen)
    if not mtk_cmd(mtkdir, py, ["r", uitlijst, padlijst] + extra, "Alle GPT-partities dumpen"):
        fout("Dumpen mislukt. Niets kapot — probeer opnieuw (koude start)."); return 1

    mtk_cmd(mtkdir, py, ["r", P.PRELOADER, os.path.join(a.map, P.PRELOADER + ".bin"),
                         "--parttype=boot1"] + extra, "Preloader dumpen (BOOT1)")

    kop("Manifest + extra kopie van de unieke partities")
    n = schrijf_manifest(a.map, namen)
    ok("manifest geschreven (%d partities)" % n)
    for u in P.UNIEK:
        src = os.path.join(a.map, u + ".img")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(uniekmap, u + ".img"))
    schrijf_manifest(uniekmap, P.UNIEK)
    ok("tweede kopie van de unieke partities in: uniek/")
    print("\n" + kleur("Bewaar deze map goed. Hiermee kun je ALTIJD terug naar de "
                       "fabrieksstaat van NU.", "b"))
    return cmd_verify(a)

def cmd_verify(a):
    kop("Back-up verifiëren")
    reg = lees_manifest(a.map)
    if not reg:
        fout("Geen MANIFEST.sha256 in " + a.map); return 1
    slecht = 0
    for h, n in reg:
        pad = os.path.join(a.map, n)
        if not os.path.isfile(pad):
            fout("ontbreekt: " + n); slecht += 1; continue
        if sha256(pad) != h:
            fout("hash klopt niet: " + n); slecht += 1
    for u in P.UNIEK:
        pad = os.path.join(a.map, u + ".img")
        if not os.path.isfile(pad) or os.path.getsize(pad) == 0:
            fout("unieke partitie ontbreekt of is leeg: " + u); slecht += 1
    if slecht:
        fout("%d probleem(en). Deze back-up is NIET betrouwbaar." % slecht); return 1
    ok("alle %d partities kloppen; unieke partities aanwezig" % len(reg))
    return 0

def cmd_restore(a):
    banner()
    balk(5, "Terugzetten uit back-up")
    mtkdir, py = vind_mtk()
    if not mtkdir:
        fout("mtkclient niet gevonden."); return 1
    balk(20, "Back-up verifiëren")
    if cmd_verify(a) != 0:
        fout("Back-up verifieert niet — terugzetten geweigerd."); return 1

    if a.alles:
        namen = [n for n in P.ALLE_PARTITIES
                 if os.path.isfile(os.path.join(a.map, n + ".img"))]
        if not a.userdata:
            namen = [n for n in namen if n != "userdata"]
        titel = "ALLE partities terugzetten" + ("" if a.userdata else " (zonder userdata)")
    else:
        namen = [n for n in ["boot_a", "para", "logo"]
                 if os.path.isfile(os.path.join(a.map, n + ".img"))]
        titel = "Terugzetten (boot_a, para, logo) → fabrieks-Android"

    balk(40, titel)
    if len(namen) <= 6:
        for n in namen:
            ok(n)
    else:
        ok("%d partities  (o.a. %s …)" % (len(namen), ", ".join(namen[:4])))
    if not a.ja and not vraag_ja("Deze partities terugschrijven naar het toestel?"):
        fout("afgebroken."); return 1
    padlijst = ",".join(os.path.join(a.map, n + ".img") for n in namen)
    extra = ["--preloader", a.preloader] if getattr(a, "preloader", None) else []
    balk(55, "Schrijven via BROM")
    prompt("mtk.py w " + (namen[0] if len(namen) == 1 else "%d partities" % len(namen)))
    if not mtk_cmd(mtkdir, py, ["w", ",".join(namen), padlijst] + extra, titel):
        fout("terugzetten mislukt."); return 1
    gewist = False
    if "userdata" not in namen:
        balk(80, "userdata wissen — schone fabrieksstart")
        gewist = mtk_cmd(mtkdir, py, ["e", "userdata"] + extra, "userdata wissen", brom=False)
        if not gewist:
            waarsch("userdata wissen lukte niet — doe dan bij de 1e start zelf 'wis data/factory reset'.")
    balk(100, "KLAAR — teruggezet")
    box("Teruggezet naar fabrieksstaat", [
        "Bootchain + logo teruggezet" + (", userdata gewist" if gewist else ""),
        "Koude start → de originele software start weer",
        "Modem / eSIM / IMEI onaangeroerd",
    ])
    return 0

def _mb(pad):
    try:
        return "%.0f MB" % (os.path.getsize(pad) / 1e6)
    except OSError:
        return "?"

def cmd_install(a):
    import install_plan as IP
    echt = getattr(a, "doe_het_echt", False)
    kop("DASH-PURE installeren" + ("" if echt else "  (DROGE PROEF — er wordt niets geschreven)"))

    if cmd_verify(a) != 0:
        fout("Geen geverifieerde back-up in '%s'. Draai eerst:  backup %s" % (a.map, a.map))
        return 1
    ok("geverifieerde back-up aanwezig")

    gsi = a.gsi
    if not gsi:
        kandidaten = [
            os.path.expanduser("~/Downloads"),
            os.path.join(a.map, "gsi"),
        ]
        for kand in kandidaten:
            if os.path.isdir(kand):
                tref = [f for f in os.listdir(kand)
                        if f.endswith(".img") and "vndklite" in f and "arm64" in f]
                if tref:
                    gsi = os.path.join(kand, sorted(tref)[-1]); break

    kop("Preflight — zijn alle bronbestanden aanwezig?")
    alles = True
    if os.path.isfile(IP.BOOT_IMG):
        ok("boot-image: %s (%s)" % (os.path.relpath(IP.BOOT_IMG, PROJ), _mb(IP.BOOT_IMG)))
    else:
        fout("boot-image ontbreekt: " + IP.BOOT_IMG); alles = False
    if os.path.isfile(os.path.join(a.map, "para.img")):
        ok("para uit back-up aanwezig (voor de 2 KB-BCB-wis)")
    else:
        fout("para.img ontbreekt in de back-up"); alles = False
    if gsi and os.path.isfile(gsi):
        ok("GSI: %s (%s)" % (os.path.basename(gsi), _mb(gsi)))
    else:
        fout("GSI niet gevonden. Geef hem op met --gsi <pad>.\n        " + IP.GSI_BRON)
        alles = False
    persist = os.path.join(PROJ, "container", "herstel", "persist.sh")
    (ok if os.path.isfile(persist) else fout)("autostart-bouwer: container/herstel/persist.sh")

    kop("Het plan")
    print("  De unieke modem-/NV-partities en de eSIM blijven ONAANGEROERD.\n")
    for s in IP.plan(a.map, gsi):
        merk = kleur("[%s]" % s["fase"], "b")
        print("  %s  %d. %s" % (merk, s["nr"], s["titel"]))
        print("       %s" % s["detail"])
    print("\n  Tussen fase 1 (BROM) en fase 2 (USB-shell) start de DASH opnieuw op.")

    if not alles:
        fout("Niet alle bronbestanden zijn aanwezig — installeren kan nog niet."); return 1
    if not echt:
        print(kleur("\nDroge proef klaar. Alles staat klaar om te installeren.", "g"))
        print("Echt uitvoeren (op een toestel dat je mág ombouwen):")
        print("  python3 dash_installer.py install %s --gsi <gsi.img> --doe-het-echt" % a.map)
        return 0

    script = os.path.join(HIER, "volledige-install.sh")
    if not os.path.isfile(script):
        fout("volledige-install.sh ontbreekt naast de installer."); return 1
    argv = ["bash", script, os.path.abspath(a.map), os.path.abspath(gsi)]
    if getattr(a, "preloader", None):
        argv.append(os.path.abspath(a.preloader))
    kop("Echte installatie starten (vraagt zo zelf om JA)")
    print("  " + " ".join(argv))
    return subprocess.call(argv)

class _Args:
    map = None; ja = False; preloader = None; gsi = None
    alles = False; userdata = False; zonder_userdata = False; doe_het_echt = False

def _vraag(tekst, default=""):
    try:
        s = input("   " + O + "➜" + X + " " + tekst +
                  ((DIM + " [" + default + "]" + X) if default else "") + ": ").strip()
    except (EOFError, KeyboardInterrupt):
        s = ""
    return s or default

def _ja(tekst, default="n"):
    return _vraag(tekst + " (j/n)", default).lower().startswith("j")

def cmd_menu(_a):
    banner()
    print("\n   " + O + B + "Kies een actie:" + X)
    for n, t, h in [("1", "Controle", "is alles aanwezig?"),
                    ("2", "Back-up maken", "EERST — veilig, nodig om te flashen"),
                    ("3", "Pardal flashen", "installeer DASH-PURE + Pardal"),
                    ("4", "Terug naar fabriek", "restore uit je back-up"),
                    ("5", "Afsluiten", "")]:
        print("     " + O + B + n + ")" + X + " " + ("%-20s" % t) +
              ((DIM + "— " + h + X) if h else ""))
    try:
        keuze = input("\n" + DIM + "   pardal@dash" + X + ":" + O + "~" + X + DIM + "$" +
                      X + " " + B + "keuze [1-5]: " + X).strip()
    except (EOFError, KeyboardInterrupt):
        keuze = "5"
    if keuze in ("5", ""):
        print("   tot ziens."); return 0
    a = _Args()
    a.map = os.path.expanduser(_vraag("Back-upmap", os.path.expanduser("~/dash-backup")))
    pl = os.path.join(a.map, "preloader_boot1.bin")
    if os.path.isfile(pl):
        a.preloader = pl
    if keuze == "1":
        return cmd_check(a)
    if keuze == "2":
        a.zonder_userdata = _ja("userdata (51 GB) overslaan?", "j")
        return cmd_backup(a)
    if keuze == "3":
        a.doe_het_echt = _ja("Echt flashen? (anders droge proef)", "n")
        return cmd_install(a)
    if keuze == "4":
        return cmd_restore(a)
    fout("onbekende keuze."); return 1

def main():
    p = argparse.ArgumentParser(description="DASH01-installer (backup/restore/install via BROM)")
    sub = p.add_subparsers(dest="cmd", required=False)
    for naam, hulp in [("check", "controleer de omgeving"),
                       ("backup", "volledige back-up maken"),
                       ("verify", "back-up verifiëren"),
                       ("restore", "partities terugzetten"),
                       ("install", "DASH-PURE installeren")]:
        s = sub.add_parser(naam, help=hulp)
        s.add_argument("map", nargs="?" if naam == "check" else None,
                       help="back-upmap")
        s.add_argument("--ja", action="store_true", help="geen bevestiging vragen")
        if naam in ("backup", "restore", "install"):
            s.add_argument("--preloader", help="preloader-bin voor DRAM-init (nodig als de "
                           "generieke DA blijft hangen op 'DRAM config needed')")
        if naam == "backup":
            s.add_argument("--zonder-userdata", dest="zonder_userdata", action="store_true",
                           help="userdata (51 GB) overslaan; alle onvervangbare partities wel")
        if naam == "restore":
            s.add_argument("--alles", action="store_true", help="alle partities (niet alleen de bootchain)")
            s.add_argument("--userdata", action="store_true", help="ook userdata (51 GB) terugzetten")
        if naam == "install":
            s.add_argument("--gsi", help="pad naar de GSI-image (anders automatisch gezocht)")
            s.add_argument("--doe-het-echt", dest="doe_het_echt", action="store_true",
                           help="echt schrijven i.p.v. een droge proef")
    a = p.parse_args()
    if not a.cmd:
        return cmd_menu(a)
    if getattr(a, "preloader", None) is None and getattr(a, "map", None):
        pl = os.path.join(a.map, "preloader_boot1.bin")
        if os.path.isfile(pl):
            a.preloader = pl
    return {"check": cmd_check, "backup": cmd_backup, "verify": cmd_verify,
            "restore": cmd_restore, "install": cmd_install}[a.cmd](a)

if __name__ == "__main__":
    sys.exit(main())
