# DASH-PURE

DASH-PURE is a small custom boot system for the DASH01 (MediaTek MT6771, round 480×480 screen).
It boots a minimal Linux userland ("Pure") from `boot_a` and starts **Android 13 (LineageOS GSI)** in a
container, with a custom launcher and Pardal. Ignition on → Pardal logo → Pardal.

> **Just want to install it?** Follow the [installation guide](../docs/DASH01-INSTALLEREN.md) and use the
> [installer](installer/). The rest of this page is for people who want to build or change DASH-PURE.

## What works
4G (with your own data eSIM), Bluetooth tethering, GPS, Wi-Fi, sound, charging and battery percentage, wake on touch, automatic
start of Pardal when power is applied, screen off after 5 min without power and power-off after 2 hours.
Custom boot logo, boot animation and a recovery screen.

## Folder layout

| Folder | Contents |
|---|---|
| [`installer/`](installer) | `dash_installer.py`: check · backup · verify · install · restore. |
| `initramfs/` | The Pure `/init` and the autostart hook that loads the autostart package at boot. |
| `container/` | `droid2.sh` builds the Android container (mounts, binds, stubs). |
| `container/herstel/` | Everything that goes onto the device: `go.sh`, `autostart.sh`, `persist.sh`, boot animation, splash. |
| `container/herstel/bediening/` | Remote tap/swipe helpers for testing over USB. |
| `src/` | Small static C programs: recovery screen, touch waker, USB-only shell listener, framebuffer UI. |
| `tools/` | Build helpers: boot-image repack, C cross-compile, push to device, logo/splash generator. |

## How it boots

1. The stock preloader and bootloader load `boot_a`: kernel + the Pure ramdisk.
2. Pure `/init` brings up `/proc`, `/sys`, the watchdog, the backlight and a USB network (`usb0` = `10.0.0.1`).
3. The autostart hook reads the **autostart package** from the userdata partition, checks its md5 and runs
   `autostart.sh`. A recovery screen is shown for 3 seconds: tap it for the recovery menu.
4. `go.sh` → `droid2.sh` starts Android `init` in its own PID namespace (network shared with Pure).
5. Android starts the custom launcher, which opens Pardal.

Storage layout on userdata (`p53`): GSI at the start, the autostart package at 3.5 GiB
(block 917504) and a persistent Android `/data` (ext4, 16 GiB) from 4 GiB.

## Development

Set `DASHPURE` to the path of this folder; the scripts use it to find their files.

```sh
export DASHPURE="$PWD"
```

### Connecting over USB
Connect the DASH01 with USB-C and give the host side of the USB network `10.0.0.2/24`. A shell is
available **only over USB** (never over Wi-Fi or 4G):

```sh
nc 10.0.0.1 2323
```

### Changing scripts, the launcher or the Wi-Fi config
1. Edit the files in `container/` or `container/herstel/`.
2. Run `container/herstel/persist.sh`: it builds the autostart package, sends it to the device,
   writes it to userdata and verifies it.
3. Reboot the device. Re-flashing `boot_a` is only needed when `/init` itself changes.

Wi-Fi credentials go in `container/herstel/wifi.conf` (copy `wifi.conf.voorbeeld`, `chmod 600`).
This file is ignored by git.

### Building
| What | Command |
|---|---|
| C program from `src/` | `tools/mk.sh <name>` (aarch64, musl, static; set `CC` to your cross-compiler) |
| Push and run a binary | `tools/push.sh <name> [args]` |
| Replace `/init` in a boot image | `tools/repack_init.py <in.img> <new-init> <out.img>` |
| Boot logo / splash / boot animation | `tools/logo/mk_pardal_logo.py`, `tools/logo/mk_splash.py` |

## Safety rules
- Never write the modem and identity partitions (`nvram`, `nvdata`, `nvcfg`, `proinfo`, `protect1/2`,
  `seccfg`, `persist`, `md1img*`). They hold the IMEI and calibration of your specific device.
- Only the first 2 KB of `para` (the bootloader command block) may be cleared.
- Do not install or run an eSIM manager that can erase profiles unless you know what you are doing.
- Always keep the backup made by the installer. With it, the device can always be restored via BROM.

## Troubleshooting

| Symptom | Check |
|---|---|
| No `10.0.0.1` | Is the host side of the USB network set to `10.0.0.2`? Replug the cable. |
| No 4G | `cat /sys/kernel/ccci/lk_md` must say `Enabled`; the first bytes of `para` must be empty. |
| Wi-Fi does not turn on | `dmesg \| grep WMT`; check `wifi.conf`. |
| Not charging | `/tmp/laden.log` on the device. |
| Screen does not wake on touch | `ps \| grep wekker`, `/tmp/wekker.log`. |

## Licence
DASH-PURE is licensed under the [GNU GPLv3](../LICENSE).
