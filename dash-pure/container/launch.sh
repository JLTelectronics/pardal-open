#!/bin/sh

set -x
G=/gsi
LOG=/tmp/android.log
exec >$LOG 2>&1
echo "=== container start $(date) ==="

mount -t proc proc        $G/proc
mount -t sysfs sys        $G/sys
mount -t tmpfs tmpfs      $G/dev
mkdir -p $G/dev/pts $G/dev/socket
mount -t devpts devpts    $G/dev/pts
mount -t tmpfs tmpfs      $G/mnt
mount -t tmpfs tmpfs      $G/data
mount -t tmpfs tmpfs      $G/metadata

mkdir -p $G/dev/binderfs
mount -t binder binder    $G/dev/binderfs 2>/dev/null || \
  mount -t binderfs binder $G/dev/binderfs 2>/dev/null
ls -l $G/dev/binderfs
mknod $G/dev/null c 1 3;  chmod 666 $G/dev/null
mknod $G/dev/zero c 1 5;  chmod 666 $G/dev/zero
mknod $G/dev/random c 1 8; mknod $G/dev/urandom c 1 9; chmod 666 $G/dev/random $G/dev/urandom
mknod $G/dev/ashmem c 10 48 2>/dev/null; chmod 666 $G/dev/ashmem 2>/dev/null
mknod $G/dev/kmsg c 1 11;  chmod 666 $G/dev/kmsg
mknod $G/dev/tty c 5 0;    chmod 666 $G/dev/tty
ln -sf /dev/binderfs/binder   $G/dev/binder
ln -sf /dev/binderfs/hwbinder $G/dev/hwbinder
ln -sf /dev/binderfs/vndbinder $G/dev/vndbinder

mkdir -p $G/vendor
losetup -o 1922039808 /dev/loop5 /dev/mmcblk0p52 2>/dev/null
mount -t ext4 -o ro /dev/loop5 $G/vendor 2>&1

echo "=== mounts klaar, start Android-init ==="
cd $G
chroot $G /system/bin/init second_stage &
IPID=$!
echo "init-pid=$IPID"
sleep 8
echo "=== na 8s: processen ==="
chroot $G /system/bin/toybox ps -A 2>/dev/null | head -30 || ps | head -30
echo "=== einde fase1 ==="
