#!/bin/bash

H=$DASHPURE/container/herstel; SP=$H; DEV=10.0.0.1
AUTO_BLK=917504
sed -n "/^net()/,/^echo \"=== 1/p" $H/resetup.sh | sed "$ d" > /tmp/dash_fn.$$; source /tmp/dash_fn.$$; rm -f /tmp/dash_fn.$$
W=$(mktemp -d); mkdir -p $W/tmp/vlibs
cp $DASHPURE/container/droid2.sh $W/droid2.sh
cp $H/go.sh $H/autostart.sh $H/km_clean.so $W/tmp/
cp $H/i2c-dev.ko $H/bindsh $H/wekker $H/e2fsck $H/recovery $H/pardal-splash.raw $H/pardal-boot.zip $W/tmp/
cp -R $H/vfix/. $W/tmp/vlibs/
cp $PARDAL/build/Pardal-dash.apk $W/tmp/pardal.apk
cp $H/DashLauncher.apk $W/tmp/dashlauncher.apk
[ -f $H/wifi.conf ] && cp $H/wifi.conf $W/tmp/dashwifi.conf
chmod 755 $W/droid2.sh $W/tmp/go.sh $W/tmp/autostart.sh $W/tmp/recovery $W/tmp/wekker $W/tmp/bindsh $W/tmp/e2fsck
COPYFILE_DISABLE=1 tar -C $W --format ustar -czf $W.tgz droid2.sh tmp
LEN=$(wc -c <$W.tgz | tr -d ' '); MD5=$(md5 -q $W.tgz); rm -rf $W
echo "pakket: $LEN B md5 $MD5"
P53=$(cmd 'cat /sys/block/mmcblk0/mmcblk0p53/size' | tr -dc 0-9)
NEED=$(( (AUTO_BLK + 1 + LEN/4096 + 1) * 8 ))
[ -n "$P53" ] && [ "$P53" -gt "$NEED" ] || { echo "STOP: p53 te klein of onbekend ($P53 < $NEED sectoren)"; exit 1; }
WWW=$(mktemp -d); cp $W.tgz $WWW/auto.tgz
( cd $WWW && exec python3 -m http.server 8765 --bind 10.0.0.2 ) >/dev/null 2>&1 & HP=$!; sleep 1
got=""; for t in 1 2 3 4 5 6; do got=$(cmd "rm -f /tmp/auto.tgz; wget -q -O /tmp/auto.tgz http://10.0.0.2:8765/auto.tgz; md5sum /tmp/auto.tgz" | awk '{print $1}'); [ "$got" = "$MD5" ] && break; sleep 2; done
kill $HP 2>/dev/null; rm -rf $WWW
[ "$got" = "$MD5" ] || { echo "STOP: md5 op device klopt niet ($got)"; exit 1; }
rm -f $W.tgz $W.c_*
cmd "printf 'DPAUTO01\n$LEN\n$MD5\n' > /tmp/auto.hdr; dd if=/dev/zero bs=4096 count=1 2>/dev/null | dd of=/tmp/auto.hdr bs=1 seek=\$(wc -c </tmp/auto.hdr) conv=notrunc 2>/dev/null; dd if=/tmp/auto.hdr of=/dev/mmcblk0p53 bs=4096 seek=$AUTO_BLK count=1 conv=notrunc 2>/dev/null; dd if=/tmp/auto.tgz of=/dev/mmcblk0p53 bs=4096 seek=$((AUTO_BLK+1)) conv=notrunc 2>/dev/null; sync; echo geschreven"
chk=$(cmd "dd if=/dev/mmcblk0p53 bs=4096 skip=$((AUTO_BLK+1)) count=$((LEN/4096+1)) 2>/dev/null | head -c $LEN | md5sum" | awk '{print $1}')
hdr=$(cmd "dd if=/dev/mmcblk0p53 bs=4096 skip=$AUTO_BLK count=1 2>/dev/null | head -3 | tr '\n' ' '")
echo "header op p53: $hdr"
[ "$chk" = "$MD5" ] && echo "PERSIST OK (p53 blok $AUTO_BLK, $LEN B)" || { echo "PERSIST FOUT: teruggelezen md5 $chk"; exit 1; }
