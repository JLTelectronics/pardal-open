#!/bin/sh

D=/droid
pkill -9 -f "init second" 2>/dev/null; pkill -9 unshare 2>/dev/null; sleep 1
umount -l /droid/system/etc/init 2>/dev/null; umount -l /droid/linkerconfig 2>/dev/null
for m in $D/dev/pts $D/dev $D/proc $D/sys $D/vendor $D/data $D/metadata $D/mnt $D; do umount -l $m 2>/dev/null; done
umount -l /over 2>/dev/null; umount /gsi 2>/dev/null; losetup -d /dev/loop4 2>/dev/null
mkdir -p /droid; mount -t ext4 -o ro /dev/mmcblk0p53 $D
[ -f /tmp/libp.so ] && mount --bind /tmp/libp.so $D/system/lib64/libandroid_runtime.so 2>/dev/null && echo "LIBPATCH: bind OK"
rm -rf /tmp/initdir; cp -a $D/system/etc/init /tmp/initdir
sed -i -e '/mount none \/linkerconfig/d' -e '/bootstrap\/linkerconfig/d' \
  -e '/\/linkerconfig\/bootstrap\/ld.config/d' -e '/\/linkerconfig\/default\/ld.config/d' \
  -e 's/ encryption=[^ ]*//g' -e 's/ keydirectory=[^ ]*//g' \
  -e '/mount tracefs tracefs/d' /tmp/initdir/hw/*.rc 2>/dev/null
sed -i -e '/mount tracefs tracefs/d' -e '/mount debugfs debugfs/d' /tmp/initdir/*.rc 2>/dev/null
sed -i -e '/onrestart restart zygote/d' /tmp/initdir/netd.rc 2>/dev/null
for rc in /tmp/initdir/*.rc; do case "$rc" in */init.zygote*) ;; *) sed -i -e '/onrestart restart zygote/d' "$rc" 2>/dev/null;; esac; done
sed -i -e '/restart zygote$/d' /tmp/initdir/hw/init.zygote64_32.rc 2>/dev/null
echo "ZYGCASCADE: $(grep -c 'restart zygote$' /tmp/initdir/hw/init.zygote64_32.rc 2>/dev/null) resterend (verwacht 0)"
cat > /tmp/initdir/aa-linkerconfig.rc <<'RC'
on early-init
    mount tmpfs tmpfs /sys/kernel/tracing
    mkdir /sys/kernel/tracing/trace_marker 0755 root root
    mount tmpfs tmpfs /sys/kernel/debug/tracing
    mkdir /sys/kernel/debug/tracing/trace_marker 0755 root root

on init
    mount tmpfs tmpfs /linkerconfig mode=0755
    exec -- /apex/com.android.runtime/bin/linkerconfig --target /linkerconfig
    chmod 644 /linkerconfig/ld.config.txt
    mkdir /data/dalvik-cache 0771 root root
    mkdir /data/dalvik-cache/arm64 0771 root root
    mkdir /data/dalvik-cache/arm 0771 root root
    mkdir /data/system 0775 system system
    mkdir /data/system/environ 0775 system system
    mkdir /data/system_de 0770 system system
    mkdir /data/misc 01771 system misc
    mkdir /data/local 0751 root root
    mkdir /data/local/tmp 0771 shell shell
    mkdir /data/data 0771 system system
    mkdir /data/user 0711 system system
    symlink /data/data /data/user/0
    mkdir /data/user_de 0711 system system
    mkdir /data/user_de/0 0711 system system
    mkdir /data/misc_de 01771 root root
    mkdir /data/misc_de/0 0770 system system
    mkdir /data/misc_ce 01771 root root
    mkdir /data/misc_ce/0 0770 system system
    mkdir /data/system_ce 0770 system system
    mkdir /data/system_ce/0 0770 system system
    mkdir /data/system_de/0 0770 system system
    mkdir /data/app 0771 system system
    mkdir /data/app-private 0771 system system
    mkdir /data/media 0770 media_rw media_rw
    mkdir /data/media/0 0770 media_rw media_rw
    mkdir /data/vendor_de 0711 root root
    mkdir /data/vendor_de/0 0771 root root
    mkdir /data/vendor_ce 0711 root root
    mkdir /data/vendor_ce/0 0771 root root
    mkdir /data/vendor/audiohal 0771 audioserver audioserver
    mkdir /data/vendor/audiohal/audio_param 0771 audioserver audioserver
    mkdir /data/misc/credstore 0770 credstore credstore
    mkdir /data/misc/user 0771 system system
    mkdir /data/misc/user/0 0771 system system
    mkdir /data/misc/installd 0700 root root
    mkdir /data/misc/profiles 0771 system system
    mkdir /data/misc/profiles/cur 0771 system system
    mkdir /data/misc/profiles/cur/0 0771 system system
    mkdir /data/misc/profiles/ref 0771 system system
    mkdir /data/misc_de/0/installd 0700 root root
    mkdir /data/misc_ce/0/installd 0700 root root
    mkdir /data/system/users 0775 system system
    mkdir /data/system_de/0/installd 0700 root root
    mkdir /data/system_ce/0/installd 0700 root root
    mkdir /data/user_de/0/com.android.providers.settings 0751 system system
    mkdir /data/user_de/0/com.android.providers.settings/databases 0771 system system
    exec -- /apex/com.android.sdkext/bin/derive_classpath /data/system/environ/classpath
    load_exports /data/system/environ/classpath
RC
mount --bind /tmp/initdir $D/system/etc/init
mount -t tmpfs tmpfs $D/linkerconfig
: > $D/system/etc/init/hw/init.usb.configfs.rc
: > $D/system/etc/init/hw/init.usb.rc
mount -t proc proc $D/proc; mount -t sysfs sys $D/sys; mount -t tmpfs tmpfs $D/dev
mkdir -p /tmp/stroom; [ -s /tmp/stroom/online ] || echo 0 > /tmp/stroom/online; [ -s /tmp/stroom/status ] || echo Discharging > /tmp/stroom/status
mount --bind /tmp/stroom/online $D/sys/class/power_supply/ac/online 2>/dev/null && \
mount --bind /tmp/stroom/status $D/sys/class/power_supply/battery/status 2>/dev/null && echo "LAADSTATUS: bind OK"
mount -t tmpfs tmpfs $D/sys/kernel/tracing 2>/dev/null; mount -t tmpfs tmpfs $D/sys/kernel/debug/tracing 2>/dev/null
mkdir -p $D/dev/pts $D/dev/socket $D/dev/binderfs
mount -t devpts devpts $D/dev/pts; mount -t binder binder $D/dev/binderfs 2>/dev/null
mkdir -p $D/sys/fs/bpf 2>/dev/null; mount -t bpf bpf $D/sys/fs/bpf 2>/dev/null && echo "BPFFS: gemount"
umount -l $D/data 2>/dev/null; losetup -d /dev/loop12 2>/dev/null
mkdir -p $D/dev/block; mknod $D/dev/block/loop12 b 7 12 2>/dev/null; mknod /dev/loop12 b 7 12 2>/dev/null
DATA_OFF=4294967296; DATA_BLOCKS=4194304
DATA_OK=0
if [ "${DASH_DATA_RAM:-0}" != 1 ] && losetup -o $DATA_OFF /dev/loop12 /dev/mmcblk0p53 2>/dev/null; then
  MAG=$(dd if=/dev/loop12 bs=1 skip=1080 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
  if [ "$MAG" != "53ef" ]; then
    echo "DATA: geen bestandssysteem -> eerste keer formatteren (16 GiB ext4)"
    chroot $D /system/bin/mke2fs -t ext4 -b 4096 -L userdata -E nodiscard /dev/block/loop12 $DATA_BLOCKS >/tmp/data-mkfs.log 2>&1
    MAG=$(dd if=/dev/loop12 bs=1 skip=1080 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    if [ "$MAG" != "53ef" ]; then
      echo "DATA: chroot-mke2fs lukte niet -> host-mke2fs op p53 (blijvend)"
      mke2fs -b 4096 -L userdata /dev/loop12 $DATA_BLOCKS >>/tmp/data-mkfs.log 2>&1
    fi
  else
    FSCK=/tmp/e2fsck; [ -x $FSCK ] || FSCK="chroot $D /system/bin/e2fsck"
    $FSCK -p /dev/loop12 >/tmp/data-fsck.log 2>&1; echo "DATA: e2fsck rc=$? ($(tail -1 /tmp/data-fsck.log))"
  fi
  mount -t ext4 -o user_xattr,noatime /dev/loop12 $D/data 2>/dev/null && DATA_OK=1
fi
if [ "$DATA_OK" = 1 ]; then
  echo "DATA-EXT4: BLIJVEND op p53+4GiB ($(df -h $D/data 2>/dev/null|tail -1|awk '{print $2" totaal, "$3" gebruikt"}'))"
else
  losetup -d /dev/loop12 2>/dev/null
  rm -f /data-ext4.img
  truncate -s 1200M /data-ext4.img 2>/dev/null || dd if=/dev/zero of=/data-ext4.img bs=1M count=640 2>/dev/null
  mke2fs -F -b 4096 -L userdata /data-ext4.img 2>/dev/null
  losetup /dev/loop12 /data-ext4.img 2>/dev/null
  mount -t ext4 -o user_xattr /dev/loop12 $D/data 2>/dev/null && echo "DATA-EXT4: RAM (niet blijvend)"
fi
chmod 0771 $D/data 2>/dev/null; chown 1000:1000 $D/data 2>/dev/null
mount -t tmpfs tmpfs $D/metadata; mount -t tmpfs tmpfs $D/mnt 2>/dev/null
for n in "null c 1 3" "zero c 1 5" "urandom c 1 9" "random c 1 8" "kmsg c 1 11" "tty c 5 0" "ashmem c 10 48"; do mknod $D/dev/$n 2>/dev/null; done
chmod 666 $D/dev/null $D/dev/zero $D/dev/urandom $D/dev/random $D/dev/ashmem $D/dev/kmsg
for b in binder hwbinder vndbinder; do ln -sf /dev/binderfs/$b $D/dev/$b; done
mkdir -p $D/dev/block
mknod $D/dev/device-mapper c 10 236 2>/dev/null; chmod 660 $D/dev/device-mapper
mknod $D/dev/loop-control c 10 237 2>/dev/null; chmod 660 $D/dev/loop-control
i=0; while [ $i -lt 16 ]; do mknod $D/dev/block/loop$i b 7 $((i*8)) 2>/dev/null; mknod $D/dev/loop$i b 7 $((i*8)) 2>/dev/null; i=$((i+1)); done
i=0; while [ $i -lt 16 ]; do mknod $D/dev/block/dm-$i b 252 $i 2>/dev/null; i=$((i+1)); done
chmod 660 $D/dev/block/* $D/dev/loop* 2>/dev/null
mkdir -p $D/apex; mount -t tmpfs tmpfs $D/apex 2>/dev/null
losetup -o 1922039808 /dev/loop5 /dev/mmcblk0p52 2>/dev/null; mount -t ext4 -o ro /dev/loop5 $D/vendor 2>/dev/null
[ -f /tmp/km_clean.so ] && mount --bind /tmp/km_clean.so $D/vendor/lib64/libkeymaster_messages.so 2>/dev/null && echo "KMPATCH: bind OK"
printf '/dev/block/by-name/userdata /data ext4 noatime,nosuid,nodev wait,formattable,encryptable=footer\n' > /tmp/fstab.min
printf '/dev/block/by-name/misc /misc emmc defaults defaults\n' >> /tmp/fstab.min
for fs in $D/vendor/etc/fstab.mt8788 $D/vendor/etc/fstab.mt6771; do
  [ -f "$fs" ] && mount --bind /tmp/fstab.min "$fs" 2>/dev/null && echo "FSTAB: $fs gebonden"
done
[ -f /misc-fake.img ] || dd if=/dev/zero of=/misc-fake.img bs=1M count=4 2>/dev/null
mknod /dev/loop6 b 7 48 2>/dev/null; mknod $D/dev/block/loop6 b 7 48 2>/dev/null
losetup /dev/loop6 /misc-fake.img 2>/dev/null
mkdir -p $D/dev/block/by-name 2>/dev/null
ln -sf /dev/block/loop6 $D/dev/block/by-name/misc 2>/dev/null
echo "MISC: nep-BCB loop6 -> $(losetup -a 2>/dev/null|grep -c loop6) gebonden"
if [ -d /tmp/vlibs ]; then
  n=0; cd /tmp/vlibs; for f in $(find . -type f 2>/dev/null); do
    rel=${f#./}; [ -f "$D/vendor/$rel" ] && mount --bind "/tmp/vlibs/$rel" "$D/vendor/$rel" 2>/dev/null && n=$((n+1))
  done; cd /; echo "VLIBS: $n schone libs gebonden"
fi
printf '#!/system/bin/sh\nexec /system/bin/sleep 2000000\n' > /tmp/halstub 2>/dev/null; chmod 755 /tmp/halstub 2>/dev/null
for b in camerahalserver android.hardware.drm@1.4-service.clearkey android.hardware.drm@1.4-service.widevine android.hardware.usb@1.2-service-mediatek; do
  [ -f "$D/vendor/bin/hw/$b" ] && mount --bind /tmp/halstub "$D/vendor/bin/hw/$b" 2>/dev/null && echo "HALSTUB: $b"
done
MODEM=0
if [ "${DASH_MODEM:-1}" = 1 ] && grep -q "^E" /sys/kernel/ccci/md_en 2>/dev/null; then
  MODEM=1
  pdev() { for p in /sys/block/mmcblk0/mmcblk0p*; do grep -q "PARTNAME=$1$" $p/uevent && { echo /dev/$(basename $p); return; }; done; }
  MOUNTED=""
  for m in protect1:protect_f protect2:protect_s nvdata:nvdata nvcfg:nvcfg persist:persist; do
    part=${m%%:*}; dir=$D/mnt/vendor/${m##*:}; dev=$(pdev $part)
    [ -n "$dev" ] && [ ! -b "$dev" ] && { mm=$(cat /sys/class/block/$(basename $dev)/dev); mknod $dev b ${mm%%:*} ${mm##*:} 2>/dev/null; }
    mkdir -p $dir
    if [ -n "$dev" ] && mount -t ext4 -o noatime,nosuid,nodev,noauto_da_alloc,commit=1,nodelalloc $dev $dir 2>/dev/null; then
      MOUNTED="$MOUNTED $dir"
    else
      echo "MODEM: mount $part ($dev) MISLUKT -> modem uit"; MODEM=0; break
    fi
  done
  if [ "$MODEM" = 1 ]; then
    chown 1000:1000 $D/mnt/vendor/protect_f $D/mnt/vendor/protect_s; chmod 0770 $D/mnt/vendor/protect_f $D/mnt/vendor/protect_s
    chown 0:1000 $D/mnt/vendor/nvdata; chmod 0771 $D/mnt/vendor/nvdata
    echo "MODEM: AAN (NV-mounts:$MOUNTED)"
  else
    for d in $MOUNTED; do umount $d 2>/dev/null; done
  fi
else
  echo "MODEM: uit (md_en=$(cat /sys/kernel/ccci/md_en 2>/dev/null))"
fi
if [ "$MODEM" = 1 ]; then
  STUBS="bip md_minilog mdlogger emdlogger1 emdlogger2 emdlogger3 viarild netdiag_server wfca ims_rtp_mgr imsm vowifi vowifid epdg_wod volte_imsm volte_imcb rngd dumpstate"
else
  STUBS="muxreport bip volte_md_status volte_imcb ccci_mdinit ccci_fsd ccci_rpcd md_minilog mdlogger emdlogger1 emdlogger2 emdlogger3 gsm0710muxd viarild mtkfusionrild netdiag_server wfca ims_rtp_mgr imsm vowifi vowifid epdg_wod volte_imsm rngd dumpstate"
fi
for b in $STUBS; do
  for d in "$D/vendor/bin/$b" "$D/system/vendor/bin/$b" "$D/vendor/bin/hw/$b" "$D/system/bin/$b"; do
    [ -f "$d" ] && mount --bind /tmp/halstub "$d" 2>/dev/null && echo "MODEMSTUB: $b"
  done
done
if [ "$MODEM" = 0 ]; then
  for n in ccci_aud ccci_aud_dsp ccci_rpc ccci_md1_tty0 ccci1_aud ccci_smem ccci_smem_dump ccci_md1_smem ccci0_smem; do mknod "$D/dev/$n" c 1 3 2>/dev/null; chmod 666 "$D/dev/$n" 2>/dev/null; done
fi
echo "MODEM=$MODEM" > /tmp/modem.state
mkdir -p /vendor/firmware 2>/dev/null; mount --bind $D/vendor/firmware /vendor/firmware 2>/dev/null
echo -n /vendor/firmware > /sys/module/firmware_class/parameters/path 2>/dev/null
echo "FW-PATH: $(cat /sys/module/firmware_class/parameters/path) host-files=$(ls /vendor/firmware 2>/dev/null | wc -l)"
for z in bootanimation.zip bootanimation-dark.zip; do
  [ -f /tmp/pardal-boot.zip ] && [ -f $D/system/product/media/$z ] && mount --bind /tmp/pardal-boot.zip $D/system/product/media/$z && echo "BOOTANIM: $z -> Pardal"
done
for cam in "$D/system/product/app/Aperture" "$D/system/product/app/ApertureLensLauncher" "$D/product/app/Aperture" "$D/product/app/ApertureLensLauncher"; do
  [ -d "$cam" ] && { mkdir -p /tmp/leeg_cam; mount --bind /tmp/leeg_cam "$cam" 2>/dev/null && echo "CAMERA-HIDE: $cam"; }
done
for x in $D/system/etc/permissions/android.hardware.camera*.xml $D/vendor/etc/permissions/android.hardware.camera*.xml; do
  [ -f "$x" ] && { printf '<permissions/>\n' > /tmp/leeg_perm.xml; mount --bind /tmp/leeg_perm.xml "$x" 2>/dev/null && echo "CAMERA-FEAT-HIDE: $x"; }
done
printf '<?xml version="1.0" encoding="utf-8"?>\n<permissions></permissions>\n' > /tmp/emptyperm.xml 2>/dev/null
for d in "$D/system/etc/permissions" "$D/vendor/etc/permissions" "$D/product/etc/permissions" "$D/system_ext/etc/permissions" "$D/odm/etc/permissions"; do
  for f in android.hardware.usb.host.xml com.android.future.usb.accessory.xml android.hardware.usb.accessory.xml; do
    [ -f "$d/$f" ] && mount --bind /tmp/emptyperm.xml "$d/$f" 2>/dev/null && echo "USBFEAT-HIDE: $d/$f"
  done
done
if [ -f /tmp/pardal.apk ] && [ -d "$D/system/app/BasicDreams" ]; then
  mkdir -p /tmp/pardalapp 2>/dev/null; cp /tmp/pardal.apk /tmp/pardalapp/Pardal.apk 2>/dev/null; chmod 644 /tmp/pardalapp/Pardal.apk 2>/dev/null
  mount --bind /tmp/pardalapp "$D/system/app/BasicDreams" 2>/dev/null && echo "PARDAL-SYSAPP: gebonden over BasicDreams ($(wc -c </tmp/pardalapp/Pardal.apk 2>/dev/null)B)"
fi
DP="$D/system/product/etc/default-permissions"
if [ -d "$DP" ]; then
  rm -rf /tmp/defperm; mkdir -p /tmp/defperm; cp -a $DP/. /tmp/defperm/
  cat > /tmp/defperm/dash-default-permissions.xml <<'DPX'
<?xml version="1.0" encoding="utf-8"?>
<exceptions>
    <exception package="com.jlt.dashlauncher">
        <permission name="android.permission.READ_PHONE_STATE" fixed="false"/>
        <permission name="android.permission.ACCESS_FINE_LOCATION" fixed="false"/>
        <permission name="android.permission.ACCESS_COARSE_LOCATION" fixed="false"/>
    </exception>
    <exception package="com.pardal.app.dash">
        <permission name="android.permission.ACCESS_FINE_LOCATION" fixed="false"/>
        <permission name="android.permission.ACCESS_COARSE_LOCATION" fixed="false"/>
        <permission name="android.permission.ACCESS_BACKGROUND_LOCATION" fixed="false"/>
        <permission name="android.permission.READ_PHONE_STATE" fixed="false"/>
        <permission name="android.permission.POST_NOTIFICATIONS" fixed="false"/>
        <permission name="android.permission.RECORD_AUDIO" fixed="false"/>
    </exception>
</exceptions>
DPX
  mount --bind /tmp/defperm "$DP" 2>/dev/null && echo "DEFPERM: $(ls /tmp/defperm | wc -l) bestanden"
fi
printf '# uitgeschakeld door DASH-PURE (USB is van Pure)\n' > /tmp/leeg.rc
for rc in $D/system/etc/init/hw/init.usb.configfs.rc $D/system/etc/init/hw/init.usb.rc $D/vendor/etc/init/hw/init.mt6771.usb.rc $D/vendor/etc/init/hw/init.mt8788.usb.rc; do
  [ -f "$rc" ] && mount --bind /tmp/leeg.rc "$rc" 2>/dev/null && echo "USB-RC-UIT: $rc"
done
if [ "${DASH_WIZARD:-0}" != 1 ]; then
  n=0
  for bp in "$D/system/build.prop" "$D/system/product/etc/build.prop"; do
    [ -f "$bp" ] || continue
    t=/tmp/bp_$n; sed 's/^ro\.setupwizard\.mode=.*/ro.setupwizard.mode=DISABLED/' "$bp" > $t 2>/dev/null
    grep -q "^ro.setupwizard.mode=" $t || echo "ro.setupwizard.mode=DISABLED" >> $t
    mount --bind $t "$bp" 2>/dev/null && n=$((n+1))
  done
  echo "WIZARD-MODE: DISABLED in $n build.prop(s)"
  for w in "$D/system/system_ext/priv-app/LineageSetupWizard" "$D/system_ext/priv-app/LineageSetupWizard"; do
    [ -d "$w" ] && { mkdir -p /tmp/leeg_wiz; mount --bind /tmp/leeg_wiz "$w" 2>/dev/null && echo "WIZARD-HIDE: $w"; }
  done
fi
if [ -f /tmp/dashlauncher.apk ] && [ -d "$D/system/app/EasterEgg" ]; then
  mkdir -p /tmp/dashlauncherapp; cp /tmp/dashlauncher.apk /tmp/dashlauncherapp/DashLauncher.apk; chmod 644 /tmp/dashlauncherapp/DashLauncher.apk
  mount --bind /tmp/dashlauncherapp "$D/system/app/EasterEgg" 2>/dev/null && echo "DASHLAUNCHER-SYSAPP: gebonden over EasterEgg ($(wc -c </tmp/dashlauncherapp/DashLauncher.apk)B)"
  if [ "${DASH_STOCKLAUNCHER:-0}" != 1 ]; then
    for l in "$D/system/system_ext/priv-app/TrebuchetQuickStep" "$D/system_ext/priv-app/TrebuchetQuickStep"; do
      [ -d "$l" ] && { mkdir -p /tmp/leeg_l3; mount --bind /tmp/leeg_l3 "$l" 2>/dev/null && echo "LAUNCHER-HIDE: $l"; }
    done
  fi
fi
VDBP="$D/vendor/vendor_dlkm/etc/build.prop"
if [ "${DASH_QIN3:-0}" = 1 ] && [ -f "$VDBP" ] && grep -q "vendor_dlkm.model=DASH01" "$VDBP" 2>/dev/null; then
  sed 's/vendor_dlkm\.model=DASH01/vendor_dlkm.model=QIN3ULTRA/' "$VDBP" > /tmp/vdlkm_bp 2>/dev/null
  mount --bind /tmp/vdlkm_bp "$VDBP" 2>/dev/null && echo "MODEL-OVERRIDE: vendor_dlkm.model DASH01->QIN3ULTRA ($(grep -c QIN3ULTRA /tmp/vdlkm_bp))"
fi
[ -f /tmp/libp32.so ] && mount --bind /tmp/libp32.so "$D/system/lib/libandroid_runtime.so" 2>/dev/null && echo "LIBP32: 32-bit libandroid gepatcht gebonden"
[ -f /tmp/voldp ] && mount --bind /tmp/voldp "$D/system/bin/vold" 2>/dev/null && echo "VOLDP: vold fscrypt_is_native->false gebonden"
[ -f /tmp/netdp ] && mount --bind /tmp/netdp "$D/system/bin/netd" 2>/dev/null && echo "NETDP: netd setGlobalAlert->0 gebonden"
mkdir -p $D/sys/fs/selinux
mount -t selinuxfs selinuxfs $D/sys/fs/selinux 2>/dev/null
if [ "$(cat $D/sys/fs/selinux/policy 2>/dev/null | wc -c)" -lt 1000 ]; then
  VP=$D/vendor/etc/selinux/precompiled_sepolicy
  if [ -f "$VP" ]; then
    SZ=$(wc -c <"$VP")
    dd if="$VP" of=$D/sys/fs/selinux/load bs=$SZ count=1 2>/tmp/polload.err
    echo "PERM-LOAD: vendor-policy policy-nu=$(cat $D/sys/fs/selinux/policy 2>/dev/null | wc -c)B (>0 = geladen)"
  else
    echo "PERM-LOAD: GEEN vendor precompiled_sepolicy gevonden op $VP"
  fi
fi
echo 0 > $D/sys/fs/selinux/enforce 2>/tmp/setenf.err
echo "SETENFORCE: enforce-nu=$(cat $D/sys/fs/selinux/enforce 2>/dev/null) err=[$(cat /tmp/setenf.err 2>/dev/null)]"
sleep 1
if [ "$1" = "apex" ]; then
  echo "=== apexd handmatig (geen init, geen reboot) ==="
  chroot $D /system/bin/apexd --bootstrap > /tmp/apexd.log 2>&1
  echo "apexd-exit=$? ==="
  echo "--- /apex na apexd ---"; ls $D/apex/ 2>/dev/null
  echo "--- apexd.log (laatste 25) ---"; tail -25 /tmp/apexd.log
else
  chroot $D /system/bin/apexd --bootstrap >/dev/null 2>&1
  mkdir -p $D/linkerconfig
  chroot $D /apex/com.android.runtime/bin/linkerconfig --target /linkerconfig >/dev/null 2>&1
  echo "ld.config: $(wc -c < $D/linkerconfig/ld.config.txt 2>/dev/null)B"
  for f in $(grep -rl reboot_on_failure $D/system/etc/init 2>/dev/null); do sed -i "/reboot_on_failure/d" $f; done
  if [ -e /tmp/klog ]; then pkill -9 klog 2>/dev/null; setsid sh -c "/tmp/klog /tmp/ilog" </dev/null >/dev/null 2>&1 & sleep 1; fi
  NSFLAG=""; [ "${DASH_NETNS:-0}" = 1 ] && NSFLAG="-n"
  echo "NETNS: ${NSFLAG:-gedeeld met host}"
  if [ -z "$NSFLAG" ]; then
    pkill -f usb0-bewaker 2>/dev/null
    cat > /tmp/usb0-bewaker.sh <<'BEWAKER'
#!/bin/sh
IPT="chroot /droid /system/bin/iptables -w"
while true; do
  ip link set usb0 up 2>/dev/null
  ip addr show usb0 2>/dev/null | grep -q "inet 10.0.0.1/" || { ip addr add 10.0.0.1/24 dev usb0 2>/dev/null; echo "$(date) adres terug" >> /tmp/usb0.log; }
  IPR="chroot /droid /system/bin/ip"
  if [ -x /droid/system/bin/ip ]; then
    $IPR rule show 2>/dev/null | grep -q "^90:.*10.0.0.0/24" || { $IPR rule add to 10.0.0.0/24 lookup main prio 90 2>/dev/null && echo "$(date) rule-to" >> /tmp/usb0.log; }
    $IPR rule show 2>/dev/null | grep -q "^91:.*10.0.0.1" || { $IPR rule add from 10.0.0.1 lookup main prio 91 2>/dev/null && echo "$(date) rule-from" >> /tmp/usb0.log; }
    $IPR route show table main 2>/dev/null | grep -q "10.0.0.0/24 dev usb0" || $IPR route add 10.0.0.0/24 dev usb0 table main 2>/dev/null
  fi
  G=/config/usb_gadget/g1
  NOW=$(cut -d. -f1 /proc/uptime); FIXES=${FIXES:-0}; LAST=${LAST:-0}
  if [ -f /tmp/flashmodus ] && [ -f $G/idProduct ] && [ "$(cat $G/idProduct)" != "0x4ee7" ] && [ "$FIXES" -lt 5 ] && [ $((NOW-LAST)) -ge 60 ]; then
    FIXES=$((FIXES+1)); LAST=$NOW
    U=$(ls /sys/class/udc | head -1)
    echo "" > $G/UDC; sleep 1
    echo 0x18d1 > $G/idVendor; echo 0x4ee7 > $G/idProduct; echo DASH-PURE-NET > $G/strings/0x409/product
    for f in $G/configs/*/*; do [ -L "$f" ] && [ "$(basename $f)" != ecm.0 ] && rm -f "$f"; done
    [ -e $G/configs/c.1/ecm.0 ] || ln -s $G/functions/ecm.0 $G/configs/c.1/ 2>/dev/null
    echo $U > $G/UDC; sleep 1
    for rs in /sys/class/usb_role/*/role; do echo device > $rs 2>/dev/null; done
    echo "$(date) USB-identiteit teruggezet ($FIXES/5)" >> /tmp/usb0.log
  fi
  if [ -f /tmp/flashmodus ]; then
    for rs in /sys/class/usb_role/*/role; do
      [ -f "$rs" ] || continue
      R=$(cat $rs 2>/dev/null)
      [ "$R" != "device" ] && { echo device > $rs 2>/dev/null; echo "$(date) usb-rol was '$R' -> device" >> /tmp/usb0.log; }
    done
  fi
  T=$((T+1)); if [ $((T%5)) = 0 ] && [ -d /droid/data/local/tmp ]; then
    ST="$(cat /sys/class/net/usb0/operstate 2>/dev/null) $(ip addr show usb0 2>/dev/null | grep -o "inet [0-9./]*") udc=$(cat /sys/class/udc/*/state 2>/dev/null) rol=$(cat /sys/class/usb_role/*/role 2>/dev/null | head -1) idp=$(cat $G/idProduct 2>/dev/null) cfg=$(ls $G/configs/c.1 2>/dev/null | tr "\n" ,) rx=$(cat /sys/class/net/usb0/statistics/rx_packets 2>/dev/null) tx=$(cat /sys/class/net/usb0/statistics/tx_packets 2>/dev/null)"
    KORT="${ST%% rx=*}"
    if [ "$KORT" != "$VORIG" ]; then echo "$(date) up=$(cut -d. -f1 /proc/uptime) $ST" >> /droid/data/local/tmp/usb0-diag.log; VORIG="$KORT"; fi
  fi
  sleep 2
done
BEWAKER
    chmod +x /tmp/usb0-bewaker.sh
    setsid sh /tmp/usb0-bewaker.sh </dev/null >/dev/null 2>&1 &
    echo "USB0-BEWAKER: gestart"
  fi
  setsid sh -c "unshare -p $NSFLAG -f --propagation private --mount-proc=$D/proc sh -c 'mount -t tmpfs tmpfs /droid/sys/kernel/tracing 2>/dev/null; mkdir -p /droid/sys/kernel/tracing/trace_marker 2>/dev/null; mount -t tmpfs tmpfs /droid/sys/kernel/debug 2>/dev/null; exec chroot /droid /system/bin/init second_stage'"</dev/null >/tmp/android.log 2>&1 &
  echo "init-launcher=$! (losgekoppeld; log in /tmp/ilog)"
fi
