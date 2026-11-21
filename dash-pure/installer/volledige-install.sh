#!/bin/bash

set -u

BACKUP="${1:?back-upmap ontbreekt}"
GSI="${2:?GSI-image ontbreekt}"
PRELOADER="${3:-}"

PROJ="${DASH_PROJ:-$DASHPURE}"
H="$PROJ/container/herstel"
MTK="${MTKCLIENT:-$HOME/mtkclient}"
MTKPY="$MTK/.venv/bin/python"; [ -x "$MTKPY" ] || MTKPY="$(command -v python3)"
IFACE="${IFACE:-en9}"
DEV=10.0.0.1; HOSTIP=10.0.0.2; SHPORT=2323
BOOT="$PROJ/build/boot-pure.img.recovery"
LOGO_TOOL="$PROJ/tools/logo/mk_pardal_logo.py"

if [ -t 1 ]; then
  O=$'\033[38;5;208m'; GR=$'\033[38;5;46m'; RD=$'\033[38;5;196m'; GL=$'\033[38;5;220m'
  DIM=$'\033[38;5;245m'; B=$'\033[1m'; X=$'\033[0m'
else
  O=; GR=; RD=; GL=; DIM=; B=; X=
fi
BREED=46

banner(){
  printf '%s' "$O$B"
  cat <<'EOF'
   ╔══════════════════════════════════════════════════════╗
   ║   ██████╗  █████╗ ██████╗ ██████╗  █████╗ ██╗         ║
   ║   ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║         ║
   ║   ██████╔╝███████║██████╔╝██║  ██║███████║██║         ║
   ║   ██╔═══╝ ██╔══██║██╔══██╗██║  ██║██╔══██║██║         ║
   ║   ██║     ██║  ██║██║  ██║██████╔╝██║  ██║███████╗    ║
   ║   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝    ║
   ║             D A S H - P U R E   ·   i n s t a l l     ║
   ╚══════════════════════════════════════════════════════╝
EOF
  printf '%s' "$X"
}
prompt(){ printf '%s\n' "${DIM}   pardal@dash${X}:${O}~${X}${DIM}\$${X} ${B}$*${X}"; }
sectie(){ printf '\n%s\n' "${O}${B}   ┏━━ $* ${X}"; }
ok(){    printf '     %s✓%s %s\n' "$GR" "$X" "$*"; }
bezig(){ printf '     %s▸%s %s\n' "$GL" "$X" "$*"; }
info(){  printf '     %s│%s %s\n' "$DIM" "$X" "${DIM}$*${X}"; }
stop(){  printf '\n     %s✗ STOP: %s%s\n' "$RD" "$*" "$X"; exit 1; }

balk(){
  local pct="$1" msg="$2" vol=$(( $1 * BREED / 100 )) i vul="" leeg=""
  i=0; while [ $i -lt "$vol" ]; do vul="${vul}█"; i=$((i+1)); done
  while [ $i -lt $BREED ]; do leeg="${leeg}░"; i=$((i+1)); done
  printf '\n   %s⟦%s%s%s%s⟧%s %s%3d%%%s  %s%s%s\n' \
    "$B" "$O$vul$X" "$DIM" "$leeg" "$X$B" "$X" "$B" "$pct" "$X" "$O$B" "$msg" "$X"
}

clear 2>/dev/null; echo; banner; echo

balk 2 "Controle vooraf"
prompt "check back-up, GSI, boot-image, mtkclient"
[ -f "$MTK/mtk.py" ]            || stop "mtkclient niet gevonden in $MTK"
[ -f "$BOOT" ]                 || stop "boot-image ontbreekt: $BOOT"
[ -f "$BACKUP/para.img" ]      || stop "para.img ontbreekt in de back-up (draai eerst: backup)"
[ -f "$BACKUP/logo.img" ]      || stop "logo.img ontbreekt in de back-up"
[ -f "$GSI" ]                 || stop "GSI-image niet gevonden: $GSI"
[ -f "$BACKUP/MANIFEST.sha256" ] || stop "geen MANIFEST.sha256 — back-up niet geverifieerd"
command -v python3 >/dev/null  || stop "python3 ontbreekt"
ok "back-up, GSI, boot-image en mtkclient aanwezig"

PLARG=(); [ -n "$PRELOADER" ] && { [ -f "$PRELOADER" ] || stop "preloader niet gevonden: $PRELOADER"; PLARG=(--preloader "$PRELOADER"); }

echo
info "Dit SCHRIJFT straks:  Fase 1 (BROM) boot_a·para·logo·userdata<-GSI"
info "                      Fase 2 (shell) autostart-pakket op p53"
info "Modem-/identiteitspartities en de eSIM blijven onaangeroerd."
printf '\n   %s➜%s Typ %sJA%s om door te gaan: ' "$O$B" "$X" "$B" "$X"; read -r A
[ "$A" = "JA" ] || stop "afgebroken"

balk 8 "Fase 1 · bronbestanden klaarzetten"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
cp "$BACKUP/para.img" "$WORK/para-bcb.img"
dd if=/dev/zero of="$WORK/para-bcb.img" bs=1 count=2048 conv=notrunc 2>/dev/null
ok "para: eerste 2 KB (BCB) genuld, rest exact uit je back-up"
python3 "$LOGO_TOOL" "$BACKUP/logo.img" "$WORK/pardal-logo.img" "$WORK/logo-preview.png" \
  || stop "logo bouwen mislukt (PIL/Helvetica nodig)"
[ "$(wc -c <"$WORK/pardal-logo.img")" = "$(wc -c <"$BACKUP/logo.img")" ] \
  || stop "logo-image niet exact even groot — niet flashen"
ok "Pardal-logo opgebouwd uit je eigen logo-partitie"

balk 15 "Fase 1 · schrijven via BROM  (boot_a · para · logo · GSI)"
sectie "ZET DE DASH IN BROM (USB mag blijven zitten)"
info "houd  rood + blauw + power  ingedrukt tot het scherm zwart wordt,"
info "laat power los en houd  rood + blauw  nog ~10 s vast."
info "De GSI (~2,6 GB) gaat mee; dit duurt een paar minuten (zie mtkclient)."
prompt "mtk.py w boot_a,para,logo,userdata ..."
( cd "$MTK" && "$MTKPY" mtk.py w boot_a,para,logo,userdata \
    "$BOOT,$WORK/para-bcb.img,$WORK/pardal-logo.img,$GSI" "${PLARG[@]}" ) \
  || stop "BROM-schrijven mislukt — niets kapot (BROM herstelt altijd). Probeer opnieuw."
ok "boot_a + para + logo + GSI(userdata) geschreven"

balk 55 "Koude start · wachten tot DASH-PURE opkomt"
sectie "KOUDE START"
info "Zet de DASH uit en weer aan (USB-C aangesloten laten)."
info "Je ziet het Pardal-logo; daarna komt DASH-PURE op ($DEV:$SHPORT)."

net(){ ifconfig "$IFACE" 2>/dev/null | grep -q "inet $HOSTIP" || sudo -n ifconfig "$IFACE" "$HOSTIP" netmask 255.255.255.0 up 2>/dev/null; }
wait_net(){ for _ in $(seq 1 90); do net; ping -c1 -t2 "$DEV" >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
cmd(){ printf '%s\n' "$1" | nc -w 30 "$DEV" "$SHPORT" 2>/dev/null; }

bezig "wachten op $DEV (max ~3 min) ..."
wait_net || stop "geen contact met $DEV op interface $IFACE.
       - Staat de DASH aan en via USB verbonden?
       - Andere interface? Draai met:  IFACE=enX ./volledige-install.sh ...
       - Interface opzetten vereist sudo (ifconfig $IFACE $HOSTIP)."
ok "contact met DASH-PURE"
cmd "touch /tmp/flashmodus" >/dev/null 2>&1

balk 62 "Fase 2 · GSI op p53 verifiëren"
MNT="$(cmd "mkdir -p /mnt-gsi; umount /mnt-gsi 2>/dev/null; mount -t ext4 -o ro /dev/mmcblk0p53 /mnt-gsi 2>/dev/null && [ -f /mnt-gsi/system/bin/vold ] && echo GSI-OK; umount /mnt-gsi 2>/dev/null")"
echo "$MNT" | grep -q GSI-OK || stop "GSI-verificatie mislukt (p53 mount of /system/bin/vold ontbreekt)"
ok "GSI op p53 geverifieerd (ext4 + /system/bin/vold)"

balk 70 "Fase 2 · container opzetten  (scripts · libs · Pardal-APK · patches)"
prompt "resetup.sh"
IFACE="$IFACE" bash "$H/resetup.sh" || stop "resetup.sh mislukt"
ok "container opgezet"

balk 88 "Fase 2 · autostart blijvend wegschrijven naar p53"
prompt "persist.sh"
IFACE="$IFACE" bash "$H/persist.sh" || stop "persist.sh mislukt"
ok "autostart-pakket geschreven en geverifieerd"

balk 100 "KLAAR"
cat <<EOF

   ${O}${B}╭──────────────────────────────────────────────────────╮${X}
   ${O}${B}│${X}  ${GR}${B}✓  DASH-PURE + Pardal geïnstalleerd${X}                   ${O}${B}│${X}
   ${O}${B}├──────────────────────────────────────────────────────┤${X}
   ${O}${B}│${X}  ${GR}✓${X} Pardal + launcher  ${DIM}(naam: Pardal-Dash)${X}             ${O}${B}│${X}
   ${O}${B}│${X}  ${GR}✓${X} USB-C laden  ${DIM}én laden via de pogo-pins${X}            ${O}${B}│${X}
   ${O}${B}│${X}  ${GR}✓${X} Blijvende opslag  ${DIM}(instellingen · wifi · kaart)${X}    ${O}${B}│${X}
   ${O}${B}│${X}  ${GR}✓${X} Wifi  ${DIM}één keer instellen → blijft + herverbindt${X}   ${O}${B}│${X}
   ${O}${B}│${X}  ${GR}✓${X} Bluetooth standaard aan                            ${O}${B}│${X}
   ${O}${B}│${X}  ${GR}✓${X} Eigen eSIM/modem onaangeroerd                      ${O}${B}│${X}
   ${O}${B}╰──────────────────────────────────────────────────────╯${X}

   ${O}${B}┏━━ BELANGRIJK — DOE NU EEN KOUDE START${X}
     ${GL}①${X} Zet de DASH ${B}helemaal uit en weer aan${X} ${DIM}(normaal opstarten)${X}
        ${DIM}→ pas dán laadt de laad-driver + stroomwachter en start Pardal echt${X}
     ${GL}②${X} ${B}Wifi:${X} verbind één keer via Instellingen ${DIM}(blijft daarna bewaard)${X}
     ${GL}③${X} ${B}USB-laden:${X} oplader erin; laadt 'ie niet → kabel even los + vast
     ${GL}④${X} ${B}Dock/pogo-laden:${X} werkt na de koude start

   ${DIM}Terug naar fabriek:${X} python3 dash_installer.py restore "$BACKUP"
EOF
