# Pardal on a Flitsmeister DASH01

Give your DASH01 a second life: a custom boot system with Android 13 and Pardal.
Ignition on → Pardal logo → Pardal.

> **Important, read this first.** This is for advanced users and you do it at your own risk.
> Modifying the software may void your warranty, and the original Flitsmeister software and
> services will no longer run while Pardal is installed. It can always be restored to the factory state, provided you
> make the backup that the installer enforces. **No** factory firmware is distributed — the
> installer uses only what is already on **your own** device.

## How does it work?
The installer does not unlock the bootloader. It uses the standard USB service mode of the MediaTek
chip (BROM) through the open-source tool [mtkclient](https://github.com/bkerler/mtkclient), first to
back up your device and then to install the Pardal boot system. Because the backup can always be
written back the same way, you can always return to the factory state. See [BOOTLOADER.md](BOOTLOADER.md).

## What works after installation
4G (with your own data eSIM; the eSIM chip itself is never touched), Wi-Fi hotspot or Bluetooth tethering, GPS, Wi-Fi, Bluetooth, sound, charging and battery %,
waking on ignition, automatic Pardal, screen off after 5 min without power and
fully off after 2 hours. Custom boot logo and recovery screen. Open item: VoLTE (calling).

## What you need
- A Mac or Linux PC with Python 3 and ~70 GB free space.
- [mtkclient](https://github.com/bkerler/mtkclient) in `~/mtkclient`.
- A USB-C cable.
- The **LineageOS 20 GSI** (`arm64_bgN`, vndklite variant), to download yourself from the
  official LineageOS GSI builds (~2.6 GB). We do not distribute it.

## Steps
Everything runs through the **DASH-PURE installer** in [`dash-pure/installer/`](../dash-pure/installer).
It first enforces a complete, verified backup
and refuses to install until it is correct.

```sh
cd installer
python3 dash_installer.py check                      # is everything present?
python3 dash_installer.py backup ~/dash-backup       # FIRST: full backup + verification
python3 dash_installer.py install ~/dash-backup --gsi ~/lineage-20-...-vndklite.img
```

Entering BROM: the command waits for the device; then cut power to the DASH
(USB-C out, 2-3 s, back in), **without pressing any buttons**.

## Back to original
```sh
python3 dash_installer.py restore ~/dash-backup           # bootchain terug → fabrieks-Android
python3 dash_installer.py restore ~/dash-backup --alles   # alle partities terug
```

## What stays untouched
The installer writes only `boot_a`, `para` (only the first 2 KB) and the userdata area.
The modem and identity partitions (`nvram`, `nvdata`, `nvcfg`, `proinfo`, `protect1/2`,
`seccfg`, `persist`, `md1img*`, `md_udc`) and the **eSIM** (which lives in the modem's eUICC)
are never touched. That keeps your carrier working.
