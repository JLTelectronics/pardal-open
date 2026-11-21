# Routing – build-up, rules and order (Pardal Dash rev B: Radxa CM3 + EC200U)

## Layers (6, JLC, **1.0 mm**, outer 1 oz / inner 0.5 oz)
| Layer | Use |
|---|---|
| F.Cu (L1) | back of the device: CM3 connectors CN1–CN3, EC200U, sensors, **RF traces (CPWG) + antennas** |
| In1 (L2) | **GND plane** (continuous under RF, DSI, USB) |
| In2 (L3) | signals: I2C, GPIO, SIM, buttons, audio |
| In3 (L4) | **VBAT plane** (battery → CM3 VCC_BAT+, modem, boost, amplifier) |
| In4 (L5) | **GND plane** (reference for B.Cu) |
| B.Cu (L6) | screen side: USB-C, battery J1, DSI connector J3, 5V J4, SIM/eUICC, side buttons |

Antenna zones (GNSS top, LTE main top-right, Wi-Fi/BT bottom-right) are rule areas: no planes or vias.
**Place nothing under the CM3 (F side)** (1.5 mm stack); traces and vias are allowed.

## Net classes (`tools/regels.py`)
| Class | Nets | Trace / clearance | Note |
|---|---|---|---|
| Default | rest | 0.12 / 0.10 mm, via 0.45/0.25 | DF40 pitch 0.4 mm: fan out with 0.1 mm traces between the rows |
| VBAT | VBAT, **BAT_N**, **VBUS** | 0.80 mm | up to 3 A (charging, modem peaks). BAT_N ≠ GND: runs through the fuel gauge in the CM3 |
| VOEDING | QI_5V, DISP_5V, DISP_SW, +3V3_DISP, MOT_N | 0.40 mm | |
| RF50 | ANT_* | 0.18 / 0.20 mm (approx.) | 50 Ω CPWG on L1, GND vias every 1 mm |
| USB90 | USB_D± (OTG0 → USB-C), MDM_USB_DP/DM (HOST2 → EC200U) | pair 0.13 / 0.15 (approx.) | 90 Ω differential |
| MIPI100 | DSI_* (CN2 → J3) | pair 0.10 / 0.18 (approx.) | 100 Ω differential, length within a pair ±0.1 mm |

**Widths are approximate.** When ordering with impedance control, get the values for the 1.0 mm stack-up from the
[JLC calculator](https://jlcpcb.com/pcb-impedance-calculator) and put them in `regels.py`.

## Order
1. **Power:** J1 (battery, B) → CN3 VCC_BAT+/- (directly above, F): short wide traces + via fields.
   VBAT to the In3 plane; from there EC200U (VBAT pins top left, decoupling next to it), TPS61023, NS4150B.
   VBUS: J2 (USB-C, bottom) → CN3 USB_5V_IN (top) with 0.8 mm on In2/B.Cu; Qi diode D3 in between.
2. **RF:** ANT_MAIN (EC200U top) → pi network → meander (top-right); ANT_GNSS → pi → J10 (top);
   W3006 → J8 (bottom-right, I-PEX cable to the CM3). CPWG on L1, via fence, as short as possible.
3. **High speed:** DSI 2 lanes + clock CN2 (left) → J3 (B, bottom center); USB OTG0 CN2 → USBLC6 → J2;
   USB HOST2 CN3 → EC200U USB_DP/DM (left on the module).
4. **SIM:** EC200U USIM (bottom edge of module) → 22R/33pF → eUICC + nano-SIM J5 (B, directly behind it).
5. **Rest:** I2C2_M1 (screen), I2C4_M0 (sensors), GPIOs, button ADC (shielded, 3W rule), audio, UART.
6. GND vias all around, DRC, and keep the antenna zones clear.
