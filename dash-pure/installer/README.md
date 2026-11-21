# DASH01 installer

Installs DASH-PURE (custom boot system + Android 13 + Pardal) on a DASH01. The first step is always a
**complete, verified backup** of your own device. The installer talks to the device through the
MediaTek BROM using [mtkclient](https://github.com/bkerler/mtkclient), so you can always get back to the
factory state.

> The installer contains **no** factory firmware and no Flitsmeister software. Backup and restore use only
> what is already on your own device.

## Requirements
- Linux or macOS with Python 3 and ~70 GB of free disk space.
- [mtkclient](https://github.com/bkerler/mtkclient) in `~/mtkclient` (or set `MTKCLIENT`).
- A USB-C cable.
- The **LineageOS 20 GSI** (`arm64_bgN`, vndklite), downloaded yourself from the official LineageOS GSI builds.

## Entering BROM
When a command waits for the device: unplug the USB-C cable from the DASH01, wait 2–3 seconds and plug it
back in. **Do not press any buttons.** mtkclient picks up the connection automatically.

## Usage
```sh
python3 dash_installer.py check                                  # is everything present?
python3 dash_installer.py backup ~/dash-backup                   # 1. full backup
python3 dash_installer.py verify ~/dash-backup                   # 2. verify the backup
python3 dash_installer.py install ~/dash-backup --gsi <gsi.img>  # 3. dry run: shows the plan, writes nothing
python3 dash_installer.py install ~/dash-backup --gsi <gsi.img> --doe-het-echt   # 4. install for real
```

Back to the original software:
```sh
python3 dash_installer.py restore ~/dash-backup                      # boot chain back → factory Android
python3 dash_installer.py restore ~/dash-backup --alles              # all partitions (without userdata)
python3 dash_installer.py restore ~/dash-backup --alles --userdata   # including your old data
```

Every step asks for confirmation (type `JA`) unless you pass `--ja`.

## What the installer changes
| Partition | Change |
|---|---|
| `boot_a` | DASH-PURE kernel + init |
| `para` | only the first 2 KB (bootloader command block) cleared, so the modem loads normally |
| `userdata` | GSI + autostart package |

Everything else stays as it is. The modem and identity partitions (`nvram`, `nvdata`, `nvcfg`, `proinfo`,
`protect1/2`, `seccfg`, `persist`, `md1img*`, `md_udc`) are additionally copied to a separate `uniek/`
folder in your backup and are never written. The eSIM profile lives in the modem's eUICC and is not touched.

## Files
| File | Purpose |
|---|---|
| `dash_installer.py` | Command-line installer (entry point). |
| `install_plan.py` | Builds and checks the installation plan. |
| `partitions.py` | Partition table of the DASH01 (data only). |
| `volledige-install.sh` | Runs both install phases (BROM + USB shell) in one go; called by `install --doe-het-echt`. |
