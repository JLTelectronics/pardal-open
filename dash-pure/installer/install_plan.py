import os

HIER = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HIER)

PARA_NUL_BYTES = 2048
AUTO_BLK = 917504
P53 = "/dev/mmcblk0p53"
BOOT_IMG = os.path.join(PROJ, "build", "boot-pure.img.recovery")
LOGO_TOOL = os.path.join(PROJ, "tools", "logo", "mk_pardal_logo.py")

GSI_BRON = ("LineageOS 20 GSI (arm64_bgN, vndklite), officieel te downloaden bij "
            "de LineageOS-GSI-builds. Verwachte bestandsnaam: "
            "lineage-20.0-*-arm64_bgN-vndklite-signed.img (~2,6 GB).")

def plan(backupmap, gsi_pad):
    return [
        {
            "fase": "BROM",
            "nr": 1,
            "titel": "Eigen boot flashen",
            "detail": "boot_a  <-  %s" % os.path.relpath(BOOT_IMG, PROJ),
            "schrijft": "boot_a",
            "bron": BOOT_IMG,
        },
        {
            "fase": "BROM",
            "nr": 2,
            "titel": "para-BCB wissen (eerste 2 KB)",
            "detail": "para: eerste %d bytes op nul, rest ongewijzigd (uit je back-up)"
                      % PARA_NUL_BYTES,
            "schrijft": "para",
            "bron": os.path.join(backupmap, "para.img"),
        },
        {
            "fase": "BROM",
            "nr": 3,
            "titel": "Pardal-bootlogo flashen",
            "detail": "logo  <-  Pardal-logo, opgebouwd uit je eigen logo.img (idx 0+16)",
            "schrijft": "logo",
            "bron": os.path.join(backupmap, "logo.img"),
        },
        {
            "fase": "BROM",
            "nr": 4,
            "titel": "GSI naar userdata (p53) schrijven",
            "detail": "userdata (%s) begin  <-  %s (raw ext4, via BROM)"
                      % (P53, os.path.basename(gsi_pad) if gsi_pad else "<GSI>"),
            "schrijft": "userdata",
            "bron": gsi_pad,
        },
        {
            "fase": "USB-shell",
            "nr": 5,
            "titel": "Autostart-pakket schrijven (Pardal + launcher + scripts)",
            "detail": "%s blok %d (3,5 GiB)  <-  container/herstel/persist.sh"
                      % (P53, AUTO_BLK),
            "schrijft": "p53 (blok %d)" % AUTO_BLK,
            "bron": os.path.join(PROJ, "container", "herstel", "persist.sh"),
        },
    ]
