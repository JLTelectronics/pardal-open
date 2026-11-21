# Pardal hardware

Open hardware for a round, standalone car display: a "phone without a camera" for the dashboard, with a
bootloader you can **always unlock and recover**. Status: in development (rev B), not yet produced.

## Overview
- **Compute:** Radxa CM3 (Rockchip RK3566), Android 11/12 (Treble, GSIs run), open U-Boot.
- **Mobile:** Quectel EC200U-EU (LTE Cat 1 + GNSS), nano-SIM and a soldered eUICC (eSIM).
- **Screen:** round DSI display with touch.
- **Other:** speaker amplifier, vibration motor, side buttons, USB-C (power + data), optional Qi charging.

## Folder layout
| Folder | Contents |
|---|---|
| `pcb/` | KiCad project (`pardal.kicad_pro`), PCB renders and the generator scripts in `pcb/tools/`. |
| `pcb/libs/` | Symbols, footprints and 3D models used by the project. The `lcsc.*` libraries were generated from the LCSC/EasyEDA part library with [easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py). |
| `pcb/datasheets/` | Pin tables (JSON) used by the generator scripts. |
| `pcb/tools/maten.py` | Board size and component positions (mm) used by `gen_pcb.py`. |

## PCB
Open `pcb/pardal.kicad_pro` in KiCad.

- Bill of materials with order numbers: [`pcb/ONDERDELEN.md`](pcb/ONDERDELEN.md).
- Layer stack-up, net classes and routing order: [`pcb/ROUTEREN.md`](pcb/ROUTEREN.md).

The schematic and board outline are generated from code. Run the scripts that use `pcbnew` with KiCad's Python:

```sh
cd pcb
python3 tools/gen_sch.py     # schematic sheets from tools/design.py
python3 tools/gen_pcb.py     # board outline, mounting holes, antenna zones, placement
python3 tools/regels.py      # net classes and design rules
python3 tools/route.py       # optional: autorouting with Freerouting
python3 tools/jlc.py "<part>"   # look up price/stock at JLCPCB/LCSC
```

Datasheets of the modules (Radxa, Quectel, …) are not included: download them from the manufacturers.

## Unlockable and unbrickable by design
- The secure-boot fuses are **never** blown: the chip always accepts your own bootloader.
- **Recovery button** behind a pinhole: hold it at power-on for Rockusb/Loader mode. Empty or broken storage
  falls back to Maskrom automatically. Flash with `rkdeveloptool` over USB-C.
- Debug UART and reset on test points.

See also [docs/BOOTLOADER.md](../docs/BOOTLOADER.md).
