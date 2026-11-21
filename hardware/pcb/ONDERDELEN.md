# Bill of materials – Pardal Dash rev B

Board components can be assembled by JLCPCB (LCSC part numbers below). Look up current price and stock with
`python3 tools/jlc.py "<part>"`. The source of truth is `tools/design.py`.

## Separate parts (order yourself)
| Part | Notes |
|---|---|
| **Radxa CM3** 2 GB / 16 GB with Wi-Fi/BT (RK3566) | Compute module on CN1–CN3; includes the RK817 PMIC with charger and fuel gauge. |
| **Waveshare 3.4inch DSI LCD (C)** | Round 800×800 IPS with touch; connects to J3 (15-pin DSI) and J4 (5 V). |
| **Battery 603450H** LiPo 1100 mAh, −20…85 °C, 10 k NTC (B3435) | On J1 (PH 2.0, 3-pin). |
| **eUICC MFF2** (e.g. sysmoEUICC1) | U3; downloadable eSIM profiles. |
| Box speaker 1511, 8 Ω 1 W | On J6. |
| Vibration motor, coin type Ø8 mm, 3 V | Solder pads TP7/TP8. |
| GPS patch antenna 12×12×4 mm, passive, with U.FL cable | On J10. |
| Qi receiver (coil Ø40 + board, 5 V) | Optional; pads TP5/TP6. |
| Short I-PEX MHF1 ↔ U.FL cable | J8 → Wi-Fi connector on the CM3. |

## Board components
| Ref | Part | LCSC |
|---|---|---|
| CN1–CN3 | Hirose DF40C-100DS-0.4V(51), 1.5 mm stack (CM3 connectors) | C597931 |
| U2 | Quectel EC200U-EU (LTE Cat 1 + GNSS) | C2942341 |
| J5 | Nano-SIM holder | C7529386 |
| J1 | JST PH 2.0 3-pin (battery) | C52025061 |
| J2 | USB-C 16P (TYPE-C-31-M-12) | C165948 |
| U4 | USBLC6-2SC6 (USB ESD) | C2827654 |
| D1, D2 | SMAJ5.0A (TVS) | C908757 |
| D3 | SS34 (Qi input) | C8678 |
| J3 | 15-pin DSI connector, 1.0 mm | C7529394 |
| J4, J6 | JST SH 1.0 mm 2-pin | C19271996 |
| U5 | TPS61023 5 V boost (screen board) | C919459 |
| L1 | 1 µH shielded 2520 | C2849428 |
| U6 | ME6211C33 3.3 V LDO | C82942 |
| U7 | STK3311-X light + proximity | C966926 |
| U8 | LSM6DS3TR-C IMU | C967633 |
| U9 | MMC5603NJ compass | C404328 |
| U10 | NS4150B class-D amplifier | C189961 |
| MK1, MK2 | LMA2718T421 MEMS microphone | C7587901 |
| FB1, FB2 | Ferrite 600 Ω @ 100 MHz, 0402 | C181004 |
| SW1, SW2 | Alps SKRTLAE010 side switch (volume) | C110293 |
| SW3 | TS-1187A tactile switch (power) | C318884 |
| SW4 | TS-1088 tactile switch (recovery, pinhole) | C720477 |
| Q1, Q2 | 2N7002 | C8545 |
| Q3 | AO3400A (vibration motor) | C20917 |
| D4 | 1N4148WS | C2128 |
| AE1 | LTE meander PCB-trace antenna | – |
| AE2 | Pulse W3006 Wi-Fi/BT antenna (2.4 + 5 GHz) | C5123155 |
| J7, J8, J10 | U.FL connector | C5299419 |
| J9 | Debug UART pads (1.8 V) | – |

## Passives (0402 unless noted)
| Value | LCSC | | Value | LCSC |
|---|---|---|---|---|
| 10 pF | C32949 | | 0 Ω | C17168 |
| 33 pF | C1562 | | 22 Ω | C25092 |
| 1 nF | C1523 | | 2.2 kΩ | C25879 |
| 100 nF | C1525 | | 4.7 kΩ | C25900 |
| 1 µF | C52923 | | 5.1 kΩ | C25905 |
| 2.2 µF (0603) | C23630 | | 10 kΩ | C25744 |
| 10 µF (0603) | C19702 | | 15 kΩ | C25756 |
| 22 µF (0603) | C59461 | | 100 kΩ | C25741 |
| 100 µF (1206) | C15008 | | 732 kΩ | C5159692 |

C39–C43 are antenna tuning positions (not mounted by default; values after measurement).
