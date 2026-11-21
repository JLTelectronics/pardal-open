import json, os
from collections import OrderedDict, defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
CM3 = {con: {int(k): v['naam'].replace('\u2011', '-') for k, v in pins.items()}
       for con, pins in json.load(open(os.path.join(HIER, '..', 'datasheets', 'rockchip', 'cm3_pinnen.json'))).items()}

SHEETS = OrderedDict()
_cur = None
_count = defaultdict(int)
_used = {"CN1", "CN2", "CN3", "U1", "U2", "J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "MK1", "MK2", "J9", "J10", "SW1", "SW2", "SW3", "SW4"}

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
SMA = "Diode_SMD:D_SMA"
SOD323 = "Diode_SMD:D_SOD-323"
L0805 = "Inductor_SMD:L_0805_2012Metric"
TP15 = "TestPoint:TestPoint_Pad_D1.5mm"
TP10 = "TestPoint:TestPoint_Pad_D1.0mm"
PAD2 = "TestPoint:TestPoint_Pad_2.0x2.0mm"

def sheet(name, title):
    global _cur
    _cur = SHEETS.setdefault(name, {"title": title, "comps": [], "notes": []})
    _cur["groep"] = title

def groep(titel):
    _cur["groep"] = titel

def note(*lines):
    _cur["notes"].extend(lines)

def comp(prefix, lib, value, fp, pins, ref=None, **extra):
    if ref is None:
        while True:
            _count[prefix] += 1
            ref = f"{prefix}{_count[prefix]}"
            if ref not in _used:
                break
    _used.add(ref)
    _cur["comps"].append({"ref": ref, "lib": lib, "value": value, "fp": fp, "groep": _cur["groep"],
                          "pins": {str(k): v for k, v in pins.items()}, **extra})
    return ref

LCSC_R = {("0R", R0402): "C17168", ("10k", R0402): "C25744", ("100k", R0402): "C25741", ("22R", R0402): "C25092",
          ("4.7k", R0402): "C25900", ("2.2k", R0402): "C25879", ("15k", R0402): "C25756", ("5.1k", R0402): "C25905", ("200k", R0402): "C25764",
          ("732k", R0402): "C5159692"}
LCSC_C = {("100nF", C0402): "C1525", ("1uF", C0402): "C52923", ("10pF", C0402): "C32949", ("33pF", C0402): "C1562", ("1nF", C0402): "C1523",
          ("10uF", C0603): "C19702", ("22uF", C0603): "C59461", ("2.2uF", C0603): "C23630", ("100uF", C1206): "C15008"}

def R(value, a, b, fp=R0402, **kw):
    kw.setdefault("lcsc", LCSC_R.get((value, fp)))
    return comp("R", "Device:R", value, fp, {1: a, 2: b}, **kw)

def C(value, a, b, fp=C0402, **kw):
    kw.setdefault("lcsc", LCSC_C.get((value, fp)))
    return comp("C", "Device:C", value, fp, {1: a, 2: b}, **kw)

def TP(net, fp=TP10, **kw):
    return comp("TP", "Connector:TestPoint", net, fp, {1: net}, **kw)

def flag(net):
    comp("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {1: net})

def antenne_pi(poort, net_ant, tag):
    C("NM", poort, "GND", dnp=True)
    R("0R", poort, net_ant)
    C("NM", net_ant, "GND", dnp=True)

NM = 'GND'

def cm3_pinnen(con, kaart):
    uit = {}
    for nr, naam in CM3[con].items():
        if naam == 'GND':
            uit[nr] = 'GND'
        elif naam in kaart:
            uit[nr] = kaart[naam]
    return uit

sheet("cm3", "RADXA CM3 (RK3566) – ANDROID")
groep("Radxa CM3 (3x DF40C-100DS)")
comp("CN", "pardal_cm3:Radxa_CM3_J69", "Radxa CM3 J69", "Pardal:Radxa_CM3_J69", cm3_pinnen('J69', {
    '+3V3': '+3V3', 'GPIO_VREF': '+3V3', '+1V8': '+1V8',
    'I2C2_SCL_M1': 'DSI_SCL', 'I2C2_SDA_M1': 'DSI_SDA',
    'UART2_RX': 'DBG_RX', 'UART2_TX': 'DBG_TX',
    'SPI3_CLK_M0': 'SENS_SCL', 'SPI3_MOSI_M0': 'SENS_SDA',
    'PI_NLED_ACTIVITY': 'SPK_EN', 'I2S1_SDO2_M1': 'ALS_INT', 'SPI3_MISO_M0': 'IMU_INT1', 'SPI3_CSO_M0': 'IMU_INT2',
    'PWM11': 'DISP_5V_EN', 'I2S1_LRCK_RX_M1': 'MOT_EN',
    'PWRON_KEY': 'PWRON_KEY', 'PMIC_RESET_KEY': 'PMIC_RESET'}), ref="CN1", lcsc="C597931")
comp("CN", "pardal_cm3:Radxa_CM3_J68", "Radxa CM3 J68", "Pardal:Radxa_CM3_J68", cm3_pinnen('J68', {
    'USB_OTG0_DM': 'USB_D-', 'USB_OTG0_DP': 'USB_D+',
    'MIPI_DSI_TX0_D0N': 'DSI_D0_N', 'MIPI_DSI_TX0_D0P': 'DSI_D0_P', 'MIPI_DSI_TX0_D1N': 'DSI_D1_N',
    'MIPI_DSI_TX0_D1P': 'DSI_D1_P', 'MIPI_DSI_TX0_CLKN': 'DSI_CLK_N', 'MIPI_DSI_TX0_CLKP': 'DSI_CLK_P'}), ref="CN2", lcsc="C597931")
comp("CN", "pardal_cm3:Radxa_CM3_J1", "Radxa CM3 J1", "Pardal:Radxa_CM3_J1", cm3_pinnen('J1', {
    'SARADC_VIN0_KEY/RECOVERY': 'KEY_ADC', 'HPL_OUT': 'AUD_L', 'HP_SNS': 'GND', 'MIC1_IN': 'MIC_CM3',
    'USB2_HOST2_DP': 'MDM_USB_DP', 'USB2_HOST2_DM': 'MDM_USB_DM',
    'VCC_BAT-': 'BAT_N', 'VCC_BAT+': 'VBAT', 'TS': 'BAT_NTC', 'USB_5V_IN': 'VBUS', 'USB_OTG0_VBUSDET': 'VBUS_DET',
    'PDM_CLK1_M1': 'MDM_PWRKEY', 'PDM_SDI1_M1': 'MDM_RESET'}), ref="CN3", lcsc="C597931")
groep("Toetsen + herstelmodus (SARADC_VIN0)")
C("1nF", "KEY_ADC", "GND")
R("2.2k", "KEY_ADC", "KEY_UP_R")
R("10k", "KEY_ADC", "KEY_DN_R")
TP("PMIC_RESET")
groep("Debug-UART (1,8 V, 1 500 000 baud)")
comp("J", "Connector_Generic:Conn_01x04", "UART 1V8 (debug)", "Pardal:UART_4pads_P2.54",
     {1: "+1V8", 2: "DBG_TX", 3: "DBG_RX", 4: "GND"}, ref="J9")
groep("Netvlaggen CM3")
flag("+3V3")
flag("+1V8")

sheet("modem", "LTE + GNSS: QUECTEL EC200U-EU")
groep("Quectel EC200U-EU")
ec = {}
for nr, naam in ((57, 'VBAT'), (58, 'VBAT'), (59, 'VBAT'), (60, 'VBAT'), (7, 'MDM_1V8'), (20, 'MDM_RESET_N'),
                 (21, 'MDM_PWRKEY_N'), (69, 'MDM_USB_DP'), (70, 'MDM_USB_DM'), (71, 'MDM_VBUS'),
                 (14, 'SIM_VDD'), (15, 'SIM_IO_M'), (16, 'SIM_CLK_M'), (17, 'SIM_RST_M'), (10, 'GND'),
                 (47, 'ANT_GNSS_M'), (49, 'ANT_MAIN_M'), (73, 'MDM_SPK_P'), (74, 'MDM_SPK_N'),
                 (75, 'MDM_MIC_P'), (77, 'MDM_MIC_N'), (11, 'MDM_DBG_RX'), (12, 'MDM_DBG_TX'), (115, 'MDM_USB_BOOT')):
    ec[nr] = naam
for nr in (8, 9, 19, 22, 36, 46, 48, 50, 51, 52, 53, 54, 56, 72, 76) + tuple(range(85, 113)):
    ec[nr] = 'GND'
comp("U", "lcsc:EC200UEUAA-N05-SGNSA", "EC200U-EU", "lcsc:LCC-LGA-144_L31.0-W28.0-P1.30_L610-CN-02", ec, ref="U2", lcsc="C2942341")
groep("Ontkoppeling VBAT modem")
for tag in ("BB", "RF"):
    C("100uF", "VBAT", "GND", fp=C1206)
    C("100nF", "VBAT", "GND")
    C("33pF", "VBAT", "GND")
    C("10pF", "VBAT", "GND")
C("2.2uF", "MDM_1V8", "GND", fp=C0603)
R("0R", "VBAT", "MDM_VBUS")
TP("MDM_USB_BOOT")
TP("MDM_DBG_TX")
TP("MDM_DBG_RX")
groep("Aan/uit + reset modem")
for gate, drain in (("MDM_PWRKEY", "MDM_PWRKEY_N"), ("MDM_RESET", "MDM_RESET_N")):
    comp("Q", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", {1: gate, 2: "GND", 3: drain}, lcsc="C8545")
    R("100k", gate, "GND")
groep("SIM: eUICC (MFF2) + nano-SIM")
comp("U", "pardal:eUICC_MFF2", "eUICC (sysmoEUICC1)", "Package_DFN_QFN:DFN-8-1EP_6x5mm_P1.27mm_EP2x2mm",
     {8: "ESIM_VDD", 7: "SIM_RST", 6: "SIM_CLK", 3: "SIM_IO", 1: "GND", 9: "GND"}, note="los bestellen (sysmocom)")
R("0R", "SIM_VDD", "ESIM_VDD")
C("1uF", "ESIM_VDD", "GND")
flag("ESIM_VDD")
comp("J", "lcsc:NANOSIMXG6PH1.35", "nano-SIM (terugval)", "lcsc:SIM-SMD_NANO-SIM-XG6P-H1.35",
     {1: "NSIM_VDD", 2: "SIM_RST", 3: "SIM_CLK", 7: "SIM_IO", 5: "GND", 8: "GND", 9: "GND", 10: "GND", 11: "GND"},
     ref="J5", lcsc="C7529386")
R("0R", "SIM_VDD", "NSIM_VDD", dnp=True)
C("1uF", "NSIM_VDD", "GND")
for m, s_ in (("SIM_RST_M", "SIM_RST"), ("SIM_CLK_M", "SIM_CLK"), ("SIM_IO_M", "SIM_IO")):
    R("22R", m, s_)
    C("33pF", s_, "GND")
R("10k", "SIM_IO", "SIM_VDD")

sheet("voeding", "ACCU, USB-C, QI")
groep("Accu")
comp("J", "Connector_Generic_MountingPin:Conn_01x03_MountingPin", "Accu (PH 2.0, 2 A/pin)",
     "Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
     {1: "VBAT", 2: "BAT_NTC", 3: "BAT_N", "MP": "BAT_N"}, ref="J1", lcsc="C52025061")
comp("D", "Device:D_TVS", "SMAJ5.0A", SMA, {1: "VBAT", 2: "GND"}, lcsc="C908757")
groep("USB-C (laden + data, ESD)")
comp("J", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
      "SH": "GND", "A6": "USB_D+", "B6": "USB_D+", "A7": "USB_D-", "B7": "USB_D-", "A5": "CC1", "B5": "CC2"},
     ref="J2", lcsc="C165948")
R("5.1k", "CC1", "GND")
R("5.1k", "CC2", "GND")
comp("D", "Device:D_TVS", "SMAJ5.0A", SMA, {1: "VBUS", 2: "GND"}, lcsc="C908757")
comp("U", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
     {1: "USB_D+", 6: "USB_D+", 3: "USB_D-", 4: "USB_D-", 2: "GND", 5: "VBUS"}, lcsc="C2827654")
C("10uF", "VBUS", "GND", fp=C0603)
R("10k", "VBUS", "VBUS_DET")
R("15k", "VBUS_DET", "GND")
groep("Qi-ontvanger (los bordje, 5 V)")
comp("D", "Device:D_Schottky", "SS34", SMA, {1: "VBUS", 2: "QI_5V"}, lcsc="C8678")
TP("QI_5V", fp=PAD2)
TP("GND", fp=PAD2)
groep("Netvlaggen voeding")
flag("VBAT")
flag("VBUS")
flag("GND")
flag("QI_5V")
flag("BAT_N")

sheet("scherm", "SCHERM: WAVESHARE 3.4INCH DSI LCD (C) MET BORDJE")
groep("Aansluiting Waveshare-bordje")
comp("J", "lcsc:1.0MM-15PLT", "DSI 15P (RPi-pinout)", "lcsc:CONN-SMD_15P-P1.00_SHOU-HAN_1.0MM-15P-LT",
     {1: "GND", 2: "DSI_D1_N", 3: "DSI_D1_P", 4: "GND", 5: "DSI_CLK_N", 6: "DSI_CLK_P", 7: "GND", 8: "DSI_D0_N",
      9: "DSI_D0_P", 10: "GND", 11: "DSI_SCL", 12: "DSI_SDA", 13: "GND", 14: "+3V3_DISP", 15: "+3V3_DISP",
      16: "GND", 17: "GND"}, ref="J3", lcsc="C7529394")
comp("J", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "5V naar Waveshare-bordje",
     "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", {1: "DISP_5V", 2: "GND", "MP": "GND"},
     ref="J4", lcsc="C19271996")
R("4.7k", "DSI_SCL", "+3V3")
R("4.7k", "DSI_SDA", "+3V3")
groep("5 V-boost voor het bordje (TPS61023)")
comp("U", "lcsc:TPS61023DRLR", "TPS61023", "lcsc:SOT-563_L1.6-W1.2-P0.50-LS1.6-BR",
     {3: "VBAT", 2: "DISP_5V_EN", 5: "DISP_SW", 6: "DISP_5V", 4: "GND", 1: "DISP_FB"}, lcsc="C919459")
C("10uF", "VBAT", "GND", fp=C0603)
comp("L", "Device:L", "1uH 2,4A afgeschermd", "Inductor_SMD:L_1008_2520Metric", {1: "VBAT", 2: "DISP_SW"}, lcsc="C2849428")
C("22uF", "DISP_5V", "GND", fp=C0603)
C("22uF", "DISP_5V", "GND", fp=C0603)
R("732k", "DISP_5V", "DISP_FB")
R("100k", "DISP_FB", "GND")
R("100k", "DISP_5V_EN", "GND")
groep("3,3 V voor de DSI-connector (ME6211)")
comp("U", "lcsc:ME6211C33M5G-N", "ME6211C33", "lcsc:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BL",
     {1: "DISP_5V", 3: "DISP_5V", 2: "GND", 5: "+3V3_DISP"}, lcsc="C82942")
C("1uF", "DISP_5V", "GND")
C("1uF", "+3V3_DISP", "GND")
flag("DISP_5V")
flag("+3V3_DISP")

sheet("sensoren", "SENSOREN")
groep("Sensor-I2C pull-ups")
R("2.2k", "SENS_SCL", "+3V3")
R("2.2k", "SENS_SDA", "+3V3")
groep("Licht + nabijheid (STK3311-X, 0x48)")
comp("U", "lcsc:STK3311-X_C966926", "STK3311-X", "lcsc:LGA-8_L4.0-W2.4-P0.97-BR",
     {1: "SENS_SDA", 2: "ALS_INT", 5: "+3V3", 6: "GND", 7: "SENS_SCL", 8: "+3V3"}, lcsc="C966926")
C("100nF", "+3V3", "GND")
R("10k", "ALS_INT", "+3V3")
groep("IMU 6-assig (LSM6DS3TR-C, 0x6A)")
comp("U", "lcsc:LSM6DS3TR-C", "LSM6DS3TR-C", "lcsc:LGA-14_L3.0-W2.5-P0.50-TL",
     {1: "GND", 4: "IMU_INT1", 5: "+3V3", 6: "GND", 7: "GND", 8: "+3V3", 9: "IMU_INT2", 12: "+3V3",
      13: "SENS_SCL", 14: "SENS_SDA"}, lcsc="C967633")
C("100nF", "+3V3", "GND")
C("100nF", "+3V3", "GND")
groep("Kompas (MMC5603NJ, 0x30)")
comp("U", "lcsc:MMC5603NJ", "MMC5603NJ", "lcsc:FLIPCHIP-4_L0.8-W0.8-R2-C2-P0.40-TL",
     {"A1": "GND", "A2": "SENS_SCL", "B1": "+3V3", "B2": "SENS_SDA"}, lcsc="C404328")
C("1uF", "+3V3", "GND")

sheet("bediening", "KNOPPEN, AUDIO (LUIDSPREKER + 2 MICROFOONS), TRILMOTOR")
groep("Knoppen (volume +/-, aan/uit, herstel)")
for ref, a, lc, fp, w in (("SW1", "KEY_UP_R", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", "Volume +"),
                          ("SW2", "KEY_DN_R", "C110293", "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010", "Volume -"),
                          ("SW3", "PWRON_KEY", "C318884", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "Aan/uit"),
                          ("SW4", "KEY_ADC", "C720477", "Button_Switch_SMD:SW_SPST_TS-1088-xR020", "Herstel (pin-gaatje)")):
    comp("SW", "Switch:SW_Push", w, fp, {1: a, 2: "GND"}, ref=ref, lcsc=lc)
groep("Luidsprekerversterker (NS4150B)")
comp("U", "lcsc:NS4150", "NS4150B", "lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",
     {1: "SPK_EN", 2: "AMP_BYP", 3: "AMP_INP", 4: "AMP_INN", 5: "SPK_N", 6: "VBAT", 7: "GND", 8: "SPK_P"}, lcsc="C189961")
C("10uF", "VBAT", "GND", fp=C0603)
C("100nF", "VBAT", "GND")
C("1uF", "AMP_BYP", "GND")
R("100k", "SPK_EN", "GND")
C("100nF", "AUD_L", "AUD_L_C")
R("100k", "AUD_L_C", "AMP_INP")
C("100nF", "MDM_SPK_P", "MDM_SPK_PC")
R("100k", "MDM_SPK_PC", "AMP_INP")
C("100nF", "MDM_SPK_N", "MDM_SPK_NC")
R("100k", "MDM_SPK_NC", "AMP_INN")
comp("J", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "Speaker", "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal",
     {1: "SPK_P", 2: "SPK_N", "MP": "GND"}, ref="J6", lcsc="C19271996")
groep("Microfoons")
for mk, uit, vdd in (("MK1", "MIC1", "MIC_VDD1"), ("MK2", "MIC2", "MIC_VDD2")):
    comp("MK", "lcsc:LMA2718T421-OA5-2", "LMA2718T421", "lcsc:MIC-SMD_4P-L2.8-W1.9-P1.84-TL",
         {1: uit, 2: "GND", 3: "GND", 4: vdd}, ref=mk, lcsc="C7587901")
    comp("FB", "Device:FerriteBead", "600R@100MHz", "Inductor_SMD:L_0402_1005Metric", {1: "+3V3", 2: vdd}, lcsc="C181004")
    C("100nF", vdd, "GND")
C("100nF", "MIC1", "MDM_MIC_P")
C("33pF", "MDM_MIC_P", "GND")
C("100nF", "MDM_MIC_N", "GND")
C("33pF", "MDM_MIC_N", "GND")
C("1uF", "MIC2", "MIC_CM3")
groep("Trilmotor (soldeerpads)")
TP("VBAT", fp=PAD2)
TP("MOT_N", fp=PAD2)
comp("Q", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", {1: "MOT_EN", 2: "GND", 3: "MOT_N"}, lcsc="C20917")
R("100k", "MOT_EN", "GND")
comp("D", "Device:D", "1N4148WS", "Diode_SMD:D_SOD-323", {1: "VBAT", 2: "MOT_N"}, lcsc="C2128")

sheet("antennes", "ANTENNES")
groep("LTE hoofd")
antenne_pi("ANT_MAIN_M", "ANT_MAIN", "MAIN")
R("0R", "ANT_MAIN", "ANT_MAIN_PCB")
comp("AE", "Device:Antenna", "LTE hoofd (printspoor)", "Pardal:LTE_meander_hoofd", {1: "ANT_MAIN_PCB"})
R("0R", "ANT_MAIN", "ANT_MAIN_UFL", dnp=True)
comp("J", "Connector:Conn_Coaxial", "U.FL (terugval)", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
     {1: "ANT_MAIN_UFL", 2: "GND"}, ref="J7", dnp=True, lcsc="C5299419")
groep("GNSS (externe patch)")
antenne_pi("ANT_GNSS_M", "ANT_GNSS", "GNSS")
comp("J", "Connector:Conn_Coaxial", "U.FL GPS-patch", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
     {1: "ANT_GNSS", 2: "GND"}, ref="J10", lcsc="C5299419")
groep("Wi-Fi / BT (naar CM3)")
comp("AE", "lcsc:W3006", "W3006 (2,4 + 5 GHz)", "lcsc:ANT-SMD_L10.0-W3.2", {1: "ANT_WIFI", 2: "GND"}, lcsc="C5123155")
C("NM", "ANT_WIFI", "GND", dnp=True)
comp("J", "Connector:Conn_Coaxial", "U.FL naar CM3 (wifi)", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
     {1: "ANT_WIFI", 2: "GND"}, ref="J8", lcsc="C5299419")
