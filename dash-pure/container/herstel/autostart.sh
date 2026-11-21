#!/bin/sh

exec >>/tmp/autostart.log 2>&1
echo "== autostart $(date) =="
[ -x /tmp/recovery ] && [ -f /tmp/pardal-splash.raw ] && { setsid /tmp/recovery splash /tmp/pardal-splash.raw </dev/null >/dev/null 2>&1 & }
if grep -q -E "androidboot.mode=charger|boot_mode=8" /proc/cmdline; then echo "KPOC -> herstart naar normaal"; sync; reboot -f; fi
mkdir -p /tmp/vlibs/lib64 /tmp/vlibs/lib
chmod +x /droid2.sh /tmp/go.sh 2>/dev/null
mkdir -p /mnt-gsi; umount /mnt-gsi 2>/dev/null; mount -t ext4 -o ro /dev/mmcblk0p53 /mnt-gsi 2>/dev/null; cp /mnt-gsi/system/lib64/libandroid_runtime.so /tmp/libp.so; cp /mnt-gsi/system/lib/libandroid_runtime.so /tmp/libp32.so; cp /mnt-gsi/system/bin/vold /tmp/voldp; cp /mnt-gsi/system/bin/netd /tmp/netdp; umount /mnt-gsi 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/voldp bs=1 seek=728452 conv=notrunc 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/netdp bs=1 seek=308456 conv=notrunc 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/netdp bs=1 seek=312540 conv=notrunc 2>/dev/null; printf "\x20\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/libp.so bs=1 seek=1932460 conv=notrunc 2>/dev/null; printf "\xc0\x03\x5f\xd6" | dd of=/tmp/libp.so bs=1 seek=1936928 conv=notrunc 2>/dev/null; printf "\x15\x00\x00\x14" | dd of=/tmp/libp.so bs=1 seek=1935408 conv=notrunc 2>/dev/null; printf "\x01\x20\x70\x47" | dd of=/tmp/libp32.so bs=1 seek=1338136 conv=notrunc 2>/dev/null; printf "\x1c\xe0" | dd of=/tmp/libp32.so bs=1 seek=1339946 conv=notrunc 2>/dev/null; printf "\x1d\xe0" | dd of=/tmp/libp32.so bs=1 seek=1340316 conv=notrunc 2>/dev/null; printf "\x70\x47" | dd of=/tmp/libp32.so bs=1 seek=1341484 conv=notrunc 2>/dev/null; echo "libp=$(wc -c </tmp/libp.so) cff=$(dd if=/tmp/libp.so bs=1 skip=1935408 count=4 2>/dev/null|od -An -tx1) libp32=$(wc -c </tmp/libp32.so) cff32=$(dd if=/tmp/libp32.so bs=1 skip=1339946 count=2 2>/dev/null|od -An -tx1) vold=$(wc -c </tmp/voldp) voldp=$(dd if=/tmp/voldp bs=1 skip=728452 count=4 2>/dev/null|od -An -tx1) netd=$(wc -c </tmp/netdp) netdp=$(dd if=/tmp/netdp bs=1 skip=308456 count=4 2>/dev/null|od -An -tx1)"
if [ "$(ps | grep -c "[g]o.sh")" = 0 ] && [ "$(ps | grep -c "[i]nit second_stage")" = 0 ]; then
  rm -f /tmp/go.done; setsid sh /tmp/go.sh </dev/null >/tmp/go.log 2>&1 &
  echo "container gestart"
else
  echo "container draait al"
fi

insmod /tmp/i2c-dev.ko 2>/dev/null; mdev -s 2>/dev/null
cat > /tmp/laadbewaker.sh <<'LAAD'
#!/bin/sh
SLAAP=300; UIT=7200    # 5 min -> scherm uit; 2 uur -> helemaal uit
while [ ! -x /droid/system/bin/i2cset ]; do sleep 5; done
I="chroot /droid /system/bin/i2cset -f -y 6 0x6b"; G="chroot /droid /system/bin/i2cget -f -y 6 0x6b"
BL=/sys/class/leds/lcd-backlight/brightness
log(){ echo "$(date '+%F %T') $*" >> /tmp/laden.log; }
mkdir -p /tmp/stroom; OUD_PG=x; OUD_ST=x; WEG=$(cut -d. -f1 /proc/uptime); UIT_GEDAAN=0; N=0
while true; do
  [ -e /dev/i2c-6 ] || mdev -s
  if [ $((N % 15)) = 0 ]; then
    r5=$($G 0x05 2>/dev/null); r0=$($G 0x00 2>/dev/null)
    if [ -n "$r5" ] && [ $(( r5 & 0x30 )) != 0 ]; then $I 0x05 $(( r5 & 0xcf )) b 2>/dev/null; log "watchdog uit (was $r5)"; fi
    if [ -n "$r0" ] && [ "$r0" != "0x0e" ]; then $I 0x00 0x0e b 2>/dev/null; log "IINDPM 1500mA (was $r0)"; fi
    SFP=$(ps -A -o pid,args | grep "[s]urfaceflinger" | awk '{print $1}' | head -1)
    if [ -n "$SFP" ]; then
      SF=$(awk '/VmRSS|VmSwap/{t+=$2} END{print t+0}' /proc/$SFP/status 2>/dev/null)
      GL=/droid/data/local/tmp/geheugen.log
      if [ $((N % 150)) = 0 ] || [ $(( ${SF:-0} - ${SF_VORIG:-0} )) -gt 20000 ]; then
        echo "$(date '+%F %T') up=$(cut -d. -f1 /proc/uptime) sf=${SF}kB vrij=$(awk '/MemAvailable/{print $2}' /proc/meminfo)kB swapvrij=$(awk '/SwapFree/{print $2}' /proc/meminfo)kB bl=$(cat $BL 2>/dev/null) stroom=$(cat /tmp/stroom/online)" >> $GL
        SF_VORIG=$SF
      fi
      if [ "${SF:-0}" -gt 400000 ] && [ ! -e /tmp/sf-dump-gedaan ]; then
        touch /tmp/sf-dump-gedaan; D=/droid/data/local/tmp/sf-dump-$(date +%m%d-%H%M).txt
        SSP=$(ps -A -o pid,args | grep " system_server" | grep -v grep | awk '{print $1}' | head -1)
        { date; cat /proc/meminfo; echo "== status"; cat /proc/$SFP/status; echo "== fd"; ls -l /proc/$SFP/fd | awk '{print $NF}' | sed 's/[0-9]*//g' | sort | uniq -c | sort -n | tail;
          echo "== smaps-top"; awk '/^[0-9a-f]+-/{n=$NF} /^Rss:/{r[n]+=$2} END{for(k in r) print r[k], k}' /proc/$SFP/smaps | sort -n | tail -15;
          echo "== ps"; ps -A -o pid,args | grep -v "\[";
          for a in "SurfaceFlinger --list" "SurfaceFlinger" "activity activities" "window windows" "power"; do echo "== dumpsys $a"; timeout 20 nsenter -t $SSP -m -p -r -- /system/bin/dumpsys $a 2>&1 | head -1500; done
        } > $D 2>&1
        echo "$(date '+%F %T') DIAGNOSE -> $D" >> $GL
      fi
      if [ "${SF:-0}" -gt 1500000 ]; then
        echo "$(date '+%F %T') surfaceflinger ${SF}kB -> NOODHERSTART" >> $GL; tail -c 200000 $GL > $GL.t && mv $GL.t $GL
        sync; reboot -f
      fi
    fi
  fi
  N=$((N+1))
  r8=$($G 0x08 2>/dev/null)
  PG=0; CS=0; ST=Discharging
  if [ -n "$r8" ]; then
    PG=$(( (r8 >> 2) & 1 )); CS=$(( (r8 >> 3) & 3 ))
    if [ "$PG" = 1 ]; then if [ $CS = 3 ]; then ST=Full; elif [ $CS = 0 ]; then ST="Not charging"; else ST=Charging; fi; fi
  fi
  if [ "$PG" = 0 ]; then
    if [ "$(cat /sys/class/power_supply/charger/online 2>/dev/null)" = 1 ] || [ "$(cat /sys/class/power_supply/usb/online 2>/dev/null)" = 1 ] || [ "$(cat /sys/class/power_supply/ac/online 2>/dev/null)" = 1 ]; then
      PG=1; ST=Charging
    fi
  fi
  if [ "$PG" != "$OUD_PG" ] || [ "$ST" != "$OUD_ST" ]; then
    echo $PG > /tmp/stroom/online; echo "$ST" > /tmp/stroom/status
    echo change > /sys/class/power_supply/battery/uevent 2>/dev/null
    log "stroom=$PG status=$ST (REG08=${r8:-leeg})"
    NU=$(cut -d. -f1 /proc/uptime)
    if [ "$PG" = 1 ] && [ "$OUD_PG" = 0 ]; then
      [ "$(cat $BL 2>/dev/null)" = 0 ] && /tmp/wekker druk && log "stroom erop -> scherm wakker"
    fi
    [ "$PG" = 0 ] && [ "$OUD_PG" != 0 ] && { WEG=$NU; UIT_GEDAAN=0; }
    OUD_PG=$PG; OUD_ST=$ST
  fi
  if [ "$PG" = 0 ] && [ $UIT_GEDAAN = 0 ] && [ $(( $(cut -d. -f1 /proc/uptime) - WEG )) -ge $SLAAP ]; then
    UIT_GEDAAN=1
    if [ "$(cat $BL 2>/dev/null)" != 0 ]; then /tmp/wekker druk; log "5 min geen stroom -> scherm uit"; fi
  fi
  if [ "$PG" = 0 ] && [ $(( $(cut -d. -f1 /proc/uptime) - WEG )) -ge $UIT ]; then
    log "2 uur geen stroom -> uitschakelen"; sync; poweroff -f
  fi
  sleep 2
done
LAAD
chmod +x /tmp/laadbewaker.sh
pkill -f laadbewaker.sh 2>/dev/null; setsid sh /tmp/laadbewaker.sh </dev/null >/dev/null 2>&1 &
echo "stroomwachter gestart"

chmod +x /tmp/wekker; pkill -f wekker 2>/dev/null
setsid /tmp/wekker </dev/null >/dev/null 2>&1 &
echo "aanraak-wekker gestart"

ppid_of() { cut -d' ' -f4 /proc/$1/stat 2>/dev/null; }
for pat in "nc -lp 2323" "telnetd -F -l /bin/sh -p 23"; do
  for p in $(ps | grep "$pat" | grep -v grep | awk '{print $1}'); do
    pp=$(ppid_of $p); [ -n "$pp" ] && [ "$pp" != 1 ] && kill -9 $pp 2>/dev/null; kill -9 $p 2>/dev/null
  done
done
chmod +x /tmp/bindsh
setsid /tmp/bindsh 10.0.0.1 2323 </dev/null >/dev/null 2>&1 &
setsid sh -c 'while true; do telnetd -F -b 10.0.0.1 -l /bin/sh -p 23 2>/dev/null; sleep 2; done' </dev/null >/dev/null 2>&1 &
echo "shell alleen op 10.0.0.1"

setsid sh -c '
  i=0; while [ "$(cat /sys/module/firmware_class/parameters/path 2>/dev/null)" != "/vendor/firmware" ] && [ $i -lt 120 ]; do sleep 2; i=$((i+1)); done
  sleep 2; D=/sys/bus/i2c/drivers/aw87xxx_pa
  if [ -e $D/3-005a ]; then echo 3-005a > $D/unbind; sleep 1; fi
  echo 3-005a > $D/bind 2>/dev/null
  sleep 4; echo "$(date) versterker herkoppeld: $(dmesg | grep -c "acf parse succeed") acf-ok" >> /tmp/audio.log
' </dev/null >/dev/null 2>&1 &
echo "versterker-herkoppeling gepland"

cat > /tmp/containerwachter.sh <<'WACHT'
#!/bin/sh
while [ "$(ps | grep -c "[i]nit second_stage")" = 0 ]; do sleep 2; done
START=$(cut -d. -f1 /proc/uptime)
while [ "$(ps | grep -c "[i]nit second_stage")" != 0 ]; do sleep 2; done
NU=$(cut -d. -f1 /proc/uptime)
PC=$(cat /droid/dev/__properties__/* 2>/dev/null | tr -c "[:print:]" "\n" | grep -v "^$" | grep -B1 -x "sys.powerctl" | head -1)
echo "$(date) ruwe sys.powerctl-waarde: [$PC]" >> /tmp/power.log
echo "$(date) container gestopt na $((NU-START)) s, sys.powerctl=${PC:-onbekend}" >> /tmp/power.log
[ $((NU-START)) -lt 120 ] && { echo "te kort gedraaid -> niets doen" >> /tmp/power.log; exit 0; }
sync; sleep 1
case "$PC" in
  shutdown,*|shutdown) echo "-> poweroff" >> /tmp/power.log; sync; poweroff -f ;;
  *)         echo "-> reboot" >> /tmp/power.log; sync; reboot -f ;;
esac
WACHT
chmod +x /tmp/containerwachter.sh; pkill -f containerwachter 2>/dev/null
setsid sh /tmp/containerwachter.sh </dev/null >/dev/null 2>&1 &
echo "container-wachter gestart"
