#!/bin/sh

D=/droid
pkill -9 -f "init second" 2>/dev/null; pkill -9 unshare 2>/dev/null; sleep 1
for m in $D/dev/pts $D/dev $D/proc $D/sys $D/vendor $D/data $D/metadata $D/mnt $D; do umount -l $m 2>/dev/null; done
umount -l /over 2>/dev/null; umount /gsi 2>/dev/null; losetup -d /dev/loop4 2>/dev/null
mkdir -p /gsi; mount -t ext4 -o ro /dev/mmcblk0p53 /gsi
mkdir -p /over /droid; mount -t tmpfs tmpfs /over; mkdir -p /over/up /over/work
mount -t overlay overlay -o lowerdir=/gsi,upperdir=/over/up,workdir=/over/work $D
: > $D/system/etc/init/hw/init.usb.configfs.rc
: > $D/system/etc/init/hw/init.usb.rc
mount -t proc proc $D/proc; mount -t sysfs sys $D/sys; mount -t tmpfs tmpfs $D/dev
mkdir -p $D/dev/pts $D/dev/socket $D/dev/binderfs
mount -t devpts devpts $D/dev/pts; mount -t binder binder $D/dev/binderfs 2>/dev/null
mount -t tmpfs tmpfs $D/data; mount -t tmpfs tmpfs $D/metadata; mount -t tmpfs tmpfs $D/mnt 2>/dev/null
for n in "null c 1 3" "zero c 1 5" "urandom c 1 9" "random c 1 8" "kmsg c 1 11" "tty c 5 0" "ashmem c 10 48"; do mknod $D/dev/$n 2>/dev/null; done
chmod 666 $D/dev/null $D/dev/zero $D/dev/urandom $D/dev/random $D/dev/ashmem $D/dev/kmsg
for b in binder hwbinder vndbinder; do ln -sf /dev/binderfs/$b $D/dev/$b; done
mkdir -p $D/dev/block
mknod $D/dev/device-mapper c 10 236 2>/dev/null; chmod 660 $D/dev/device-mapper
mknod $D/dev/loop-control c 10 237 2>/dev/null; chmod 660 $D/dev/loop-control
i=0; while [ $i -lt 16 ]; do mknod $D/dev/block/loop$i b 7 $i 2>/dev/null; mknod $D/dev/loop$i b 7 $i 2>/dev/null; i=$((i+1)); done
i=0; while [ $i -lt 16 ]; do mknod $D/dev/block/dm-$i b 252 $i 2>/dev/null; i=$((i+1)); done
chmod 660 $D/dev/block/* $D/dev/loop* 2>/dev/null
mkdir -p $D/apex; mount -t tmpfs tmpfs $D/apex 2>/dev/null
losetup -o 1922039808 /dev/loop5 /dev/mmcblk0p52 2>/dev/null; mount -t ext4 -o ro /dev/loop5 $D/vendor 2>/dev/null
mkdir -p $D/sys/fs/selinux
mount -t selinuxfs selinuxfs $D/sys/fs/selinux 2>/dev/null
if [ "$(cat $D/sys/fs/selinux/policy 2>/dev/null | wc -c)" -lt 1000 ]; then
  dd if=/dev/mmcblk0p53 bs=4096 skip=786432 count=241 2>/dev/null | head -c 985462 > /tmp/sp.bin
  dd if=/tmp/sp.bin of=$D/sys/fs/selinux/load bs=985462 count=1 2>/tmp/polload.err
  echo "PERM-LOAD: policy-nu=$(cat $D/sys/fs/selinux/policy 2>/dev/null | wc -c)B (>0 = permissive geladen)"
fi
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
  setsid sh -c "unshare -p -f --mount-proc=$D/proc chroot $D /system/bin/init second_stage" </dev/null >/tmp/android.log 2>&1 &
  echo "init-launcher=$! (losgekoppeld; log in /tmp/ilog)"
fi
