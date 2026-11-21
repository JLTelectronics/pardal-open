#!/bin/sh
pkill -9 -f "init second" 2>/dev/null; pkill -9 -f unshare 2>/dev/null; pkill -9 klog 2>/dev/null
pkill -9 teed 2>/dev/null; pkill -9 -f "/vendor/bin/" 2>/dev/null; pkill -9 -f "/system/bin/" 2>/dev/null; pkill -9 -f app_process 2>/dev/null; pkill -9 -f "/apex/" 2>/dev/null
sleep 2
sh /droid2.sh > /tmp/droid.out 2>&1
sleep 10
C=/droid
chroot $C /system/bin/setprop ro.crypto.state unencrypted
chroot $C /system/bin/setprop ro.crypto.type none
chroot $C /system/bin/setprop odsign.verification.done 1
chroot $C /system/bin/setprop ro.setupwizard.mode DISABLED
chroot $C /system/bin/setprop persist.sys.setupwizard DISABLED
chroot $C /system/bin/setprop qemu.sf.lcd_density 120
chroot $C /system/bin/setprop ro.sf.lcd_density 120
chroot $C /system/bin/setprop ro.hw_timeout_multiplier 10
chroot $C /system/bin/setprop pm.dexopt.first-boot skip
chroot $C /system/bin/setprop pm.dexopt.boot-after-ota skip
chroot $C /system/bin/setprop pm.dexopt.install skip
chroot $C /system/bin/setprop dalvik.vm.dex2oat-filter verify
chroot $C /system/bin/setprop dalvik.vm.image-dex2oat-filter verify
sleep 1
chroot $C /system/bin/setprop ctl.start bpfloader
sleep 2
GPUN="/droid/dev/mali0 /droid/dev/ion /droid/dev/gpu_memory_bandwidth /droid/dev/mtk_disp_mgr /droid/dev/disp_freq /droid/dev/graphics/fb0"
setsid sh -c 'i=0; while [ $i -lt 40 ]; do for n in '"$GPUN"'; do chmod 666 $n 2>/dev/null; done; chmod 666 /droid/dev/dri/* /droid/dev/dma_heap/* /droid/dev/graphics/* 2>/dev/null; i=$((i+1)); sleep 1; done' </dev/null >/dev/null 2>&1 &
for n in $GPUN; do chmod 666 $n 2>/dev/null; done
chroot $C /system/bin/setprop ctl.start wmt_loader
sleep 3
chroot $C /system/bin/setprop ctl.start wmt_launcher
sleep 5
. /tmp/modem.state 2>/dev/null
if [ "$MODEM" = 1 ]; then XRIL='ccci3|md_minilog|mdlogger'; else XRIL='rild|ril-|mtk-ril|ccci|md_'; fi
HALS=$(awk '/^service /{svc=$2} /^[[:space:]]*class (hal|early_hal|core|main)/{print svc}' $C/vendor/etc/init/*.rc $C/system/etc/init/*.rc 2>/dev/null | grep -viE "wmt_loader|wmt_launcher|c2k|$XRIL|emdlogger|nfc|bluetooth|flashless|camera|cameraserver|drm@|usb@|usb-hal")
for h in $HALS; do chroot $C /system/bin/setprop ctl.start "$h"; done
if [ "$MODEM" = 1 ]; then sleep 5; chroot $C /system/bin/setprop ctl.start vendor.ril-daemon-mtk; echo "RIL gestart" >> /tmp/modem.log; fi
sleep 3
if [ -f /tmp/dashwifi.conf ]; then . /tmp/dashwifi.conf
  chroot $C /system/bin/setprop debug.dash.wifi_ssid "$SSID"; chroot $C /system/bin/setprop debug.dash.wifi_psk "$PSK"; fi
chroot $C /system/bin/setprop ctl.start zygote
setsid sh -c 'chroot /droid /system/bin/logcat -v time DisplayManagerService:V LocalDisplayAdapter:V WindowManager:I SurfaceFlinger:I ActivityManager:V ActivityTaskManager:V UserController:V ActivityManagerService:V SystemServer:V LockSettingsService:V StorageManagerService:V Watchdog:V PackageManager:V vold:V keystore2:I gatekeeperd:V "*:S" > /tmp/boot.log 2>&1' </dev/null >/dev/null 2>&1 &
setsid sh -c '
  C=/droid
  : > /tmp/pardal.log
  i=0; while [ "$(chroot $C /system/bin/getprop sys.boot_completed 2>/dev/null)" != "1" ] && [ $i -lt 180 ]; do sleep 2; i=$((i+1)); done
  echo "boot_completed na ${i}x2s" >> /tmp/pardal.log
  SSPID=$(ps | grep "[s]ystem_server" | awk "{print \$1}" | head -1)
  echo "sspid=$SSPID" >> /tmp/pardal.log
  mkdir -p $C/data/local/tmp 2>/dev/null
  tr "\0" "\n" < /proc/$SSPID/environ 2>/dev/null | grep -E "^(BOOTCLASSPATH|DEX2OATBOOTCLASSPATH|SYSTEMSERVERCLASSPATH|STANDALONE_SYSTEMSERVER_JARS|ANDROID_|PATH|LD_LIBRARY_PATH)=" > $C/data/local/tmp/ssenv
  echo "env-regels=$(wc -l <$C/data/local/tmp/ssenv)" >> /tmp/pardal.log
  cp /tmp/pardal.apk $C/data/local/tmp/pardal.apk 2>>/tmp/pardal.log; chmod 644 $C/data/local/tmp/pardal.apk 2>/dev/null
  echo "apk=$(wc -c <$C/data/local/tmp/pardal.apk 2>/dev/null)B" >> /tmp/pardal.log
  chroot $C /system/bin/sh -c "set -a; . /data/local/tmp/ssenv; set +a; /system/bin/settings put global device_provisioned 1; /system/bin/settings put secure user_setup_complete 1; /system/bin/settings put global device_name Pardal-Dash; /system/bin/settings put secure bluetooth_name Pardal-Dash; /system/bin/cmd bluetooth_manager enable; /system/bin/settings put global bluetooth_on 1; /system/bin/pm install -r -g -t /data/local/tmp/pardal.apk; /system/bin/am start -n com.pardal.app.dash/com.pardal.app.MainActivity" >> /tmp/pardal.log 2>&1
  echo "POST-BOOT klaar" >> /tmp/pardal.log
' </dev/null >/dev/null 2>&1 &
sleep 20
chroot $C /system/bin/logcat -t 400 > /tmp/lc.txt 2>&1
{ echo "LIBPATCH=$(grep -c LIBPATCH /tmp/droid.out)"
  echo "zygote=$(chroot $C /system/bin/getprop init.svc.zygote)"
  echo "boot_completed=$(chroot $C /system/bin/getprop sys.boot_completed)"
  echo "sf-proc=$(ps|grep -c [s]urfaceflinger) ss-proc=$(ps|grep -c [s]ystem_server)"
  echo "allowlist-fouten=$(grep -c 'Not allowlisted' /tmp/lc.txt)"
  echo "logcat-regels=$(wc -l </tmp/lc.txt)"; } > /tmp/st.txt 2>&1
grep -iE "Not allowlisted|Boot is finished|SystemServer|ActivityManager|WindowManager|FATAL EXCEPTION| E AndroidRuntime" /tmp/lc.txt | tail -16 > /tmp/ss.txt 2>&1
echo DONE > /tmp/go.done
