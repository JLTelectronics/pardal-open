AUTO_BLK=917504
AUTO=0
HDR=$($BB dd if=/dev/mmcblk0p53 bs=4096 skip=$AUTO_BLK count=1 2>/dev/null | $BB head -3)
if [ "$(echo "$HDR" | $BB sed -n 1p)" = "DPAUTO01" ]; then
  LEN=$(echo "$HDR" | $BB sed -n 2p); MD5=$(echo "$HDR" | $BB sed -n 3p)
  $BB dd if=/dev/mmcblk0p53 bs=4096 skip=$((AUTO_BLK+1)) count=$((LEN/4096+1)) 2>/dev/null | $BB head -c "$LEN" > /tmp/auto.tgz
  if [ "$($BB md5sum /tmp/auto.tgz | $BB cut -d' ' -f1)" = "$MD5" ] && $BB tar -xzf /tmp/auto.tgz -C / 2>/dev/kmsg; then
    echo "AUTOSTART: pakket ok ($LEN B)" > /dev/kmsg
    KEUZE=0
    if [ -x /tmp/recovery ]; then
      /tmp/recovery countdown 3; KEUZE=$?
    else
      [ -e /dev/input/event2 ] && $BB timeout 3 $BB head -c 1 /dev/input/event2 >/dev/null 2>&1 && KEUZE=2
    fi
    if [ "$KEUZE" = 0 ]; then
      echo "AUTOSTART: start Android" > /dev/kmsg
      $BB sh /tmp/autostart.sh && AUTO=1
    else
      echo "AUTOSTART: keuze $KEUZE -> Pure-UI" > /dev/kmsg
    fi
  else
    echo "AUTOSTART: pakket ongeldig -> Pure-UI" > /dev/kmsg
  fi
fi
if [ "$AUTO" = 1 ]; then
  while true; do $BB sleep 3600; done
fi
while true; do /bin/ui 2>/dev/kmsg; $BB sleep 1; done
