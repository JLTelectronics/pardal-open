#!/bin/bash

SP=$DASHPURE/container/herstel
DEV=10.0.0.1
net() { local i="${IFACE:-en9}"; ifconfig "$i" | grep -q "inet 10.0.0.2" || sudo -n ifconfig "$i" 10.0.0.2 netmask 255.255.255.0 up 2>/dev/null; }
wait_net() { for t in $(seq 1 10); do net; ping -c1 -t2 $DEV >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
push() {
  local want; want=$(wc -c <"$1" | tr -d ' ')
  local t got
  for t in 1 2 3 4 5 6; do
    wait_net
    printf "nc -lp 5005 > %s\n" "$2" | nc -w 15 $DEV 2323 >/dev/null 2>&1 &
    sleep 2; cat "$1" | nc -w 8 $DEV 5005; sleep 2
    got=$(printf "wc -c <%s\n" "$2" | nc -w 6 $DEV 2323 2>/dev/null | tr -d ' \r\n')
    [ "$got" = "$want" ] && { echo "  PUSH ok $2 ($got B)"; return 0; }
    echo "  PUSH retry $2: $got/$want"
    sleep 1
  done
  echo "  PUSH FAALDE $2 ($got/$want)"; return 1
}
cmd() { local r t; for t in 1 2 3; do wait_net; r=$(printf "%s\n" "$1" | nc -w 30 $DEV 2323 2>/dev/null); [ -n "$r" ] && { printf "%s\n" "$r"; return 0; }; sleep 2; done; return 1; }
push_apk() {
  local APK="$1" DST="$2" WANT SD ch names got t
  WANT=$(md5 -q "$APK"); SD=$(mktemp -d); split -b 100000 "$APK" "$SD/c_"; names=""
  for ch in "$SD"/c_*; do push "$ch" "/tmp/$(basename $ch)" || { rm -rf "$SD"; return 1; }; names="$names /tmp/$(basename $ch)"; done
  for t in 1 2 3 4 5; do
    got=$(cmd "cat$names > $DST && md5sum $DST" | awk '{print $1}')
    [ "$got" = "$WANT" ] && { cmd "rm -f$names" >/dev/null; echo "  APK ok $DST (md5 $got)"; rm -rf "$SD"; return 0; }
    sleep 2
  done
  rm -rf "$SD"; echo "  APK FAALDE $DST"; return 1
}

echo "=== 1. /bin/ui neutraliseren ==="
cmd 'touch /tmp/flashmodus; echo flashmodus-aan'
cmd 'if [ -f /bin/ui ] && [ ! -f /bin/ui.real ]; then mv /bin/ui /bin/ui.real; printf "#!/bin/sh\nexec /bin/busybox sleep 100000\n" > /bin/ui; chmod +x /bin/ui; fi; for p in $(ps|grep "[b]in/ui"|awk "{print \$1}"); do kill -9 $p; done; echo ui-stub=$(ps|grep -c "[s]leep 100000")'

echo "=== 2. mappen ==="
cmd 'mkdir -p /tmp/vlibs/lib64 /tmp/vlibs/lib; echo ok'

echo "=== 3. scripts + libs pushen ==="
push $DASHPURE/container/droid2.sh /droid2.sh
push $SP/go.sh /tmp/go.sh
push $SP/km_clean.so /tmp/km_clean.so
push $SP/vfix/lib64/libpuresoftkeymasterdevice.so /tmp/vlibs/lib64/libpuresoftkeymasterdevice.so
push $SP/vfix/lib64/libkeymaster4support.so /tmp/vlibs/lib64/libkeymaster4support.so
cmd 'chmod +x /droid2.sh /tmp/go.sh'
echo "=== 3b. Pardal APK chunk-pushen ==="
push_apk $PARDAL/build/Pardal-dash.apk /tmp/pardal.apk
push $SP/DashLauncher.apk /tmp/dashlauncher.apk
[ -f $SP/wifi.conf ] && push $SP/wifi.conf /tmp/dashwifi.conf

echo "=== 4. libp.so maken (mount p53 ro, cp libandroid, dd-patch) ==="
cmd 'mkdir -p /mnt-gsi; umount /mnt-gsi 2>/dev/null; mount -t ext4 -o ro /dev/mmcblk0p53 /mnt-gsi 2>/dev/null; cp /mnt-gsi/system/lib64/libandroid_runtime.so /tmp/libp.so; cp /mnt-gsi/system/lib/libandroid_runtime.so /tmp/libp32.so; cp /mnt-gsi/system/bin/vold /tmp/voldp; cp /mnt-gsi/system/bin/netd /tmp/netdp; umount /mnt-gsi 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/voldp bs=1 seek=728452 conv=notrunc 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/netdp bs=1 seek=308456 conv=notrunc 2>/dev/null; printf "\x00\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/netdp bs=1 seek=312540 conv=notrunc 2>/dev/null; printf "\x20\x00\x80\x52\xc0\x03\x5f\xd6" | dd of=/tmp/libp.so bs=1 seek=1932460 conv=notrunc 2>/dev/null; printf "\xc0\x03\x5f\xd6" | dd of=/tmp/libp.so bs=1 seek=1936928 conv=notrunc 2>/dev/null; printf "\x15\x00\x00\x14" | dd of=/tmp/libp.so bs=1 seek=1935408 conv=notrunc 2>/dev/null; printf "\x01\x20\x70\x47" | dd of=/tmp/libp32.so bs=1 seek=1338136 conv=notrunc 2>/dev/null; printf "\x1c\xe0" | dd of=/tmp/libp32.so bs=1 seek=1339946 conv=notrunc 2>/dev/null; printf "\x1d\xe0" | dd of=/tmp/libp32.so bs=1 seek=1340316 conv=notrunc 2>/dev/null; printf "\x70\x47" | dd of=/tmp/libp32.so bs=1 seek=1341484 conv=notrunc 2>/dev/null; echo "libp=$(wc -c </tmp/libp.so) cff=$(dd if=/tmp/libp.so bs=1 skip=1935408 count=4 2>/dev/null|od -An -tx1) libp32=$(wc -c </tmp/libp32.so) cff32=$(dd if=/tmp/libp32.so bs=1 skip=1339946 count=2 2>/dev/null|od -An -tx1) vold=$(wc -c </tmp/voldp) voldp=$(dd if=/tmp/voldp bs=1 skip=728452 count=4 2>/dev/null|od -An -tx1) netd=$(wc -c </tmp/netdp) netdp=$(dd if=/tmp/netdp bs=1 skip=308456 count=4 2>/dev/null|od -An -tx1)"'

echo "=== 5. verificatie bestanden ==="
cmd 'echo "d2=$(wc -c </droid2.sh) go=$(wc -c </tmp/go.sh) km=$(wc -c </tmp/km_clean.so) vlibs=$(ls /tmp/vlibs/lib64/|wc -l) libp=$(wc -c </tmp/libp.so 2>/dev/null)"'

echo "=== 6. container starten (exact 1x) ==="
cmd 'if [ "$(ps | grep -c "[g]o.sh")" = 0 ] && [ "$(ps | grep -c "[i]nit second_stage")" = 0 ]; then rm -f /tmp/go.done; setsid sh /tmp/go.sh </dev/null >/tmp/go.log 2>&1 & sleep 1; echo container-gestart; else echo "container draait al - niet opnieuw gestart"; fi'
echo "=== RE-SETUP KLAAR ==="
