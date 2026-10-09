# Datasheet — Swimming Pool System Open, Rev A

*[Italiano](datasheet.it.md)*

Acquisition and control board for swimming-pool water treatment and filtration.
Preliminary: values marked **TBC** are to be confirmed at bring-up.

![Board](../hardware/layout/pcb-front.png)

## At a glance

| | |
|---|---|
| Controller | ESP32-S3-DevKitC-1 N16R8 module (16 MB flash, 8 MB PSRAM), dual core, Wi-Fi |
| Board | two layers, about 165 × 94 mm, four M4 mounting holes |
| Supply | 24 V DC, TVS-protected (SMBJ30A) |
| Software | ESPHome (ESP-IDF); native API; Home Assistant optional |
| User interface | Waveshare ESP32-S3-Touch-LCD-7B, 7", 1024 × 600, touch, 3-wire serial link |
| Revision | Rev A (printed on the board as "Rev 0.A") |

## Inputs

| Function | Qty | Details |
|---|---|---|
| pH, ORP probes | 1 + 1 | BNC, potentiometric front end (OPA2338), 16-bit ADS1115; calibration in firmware |
| Pressure / analog | 2 | 0-10 V, divider to ADS1115 (one used for filter pressure, one spare) |
| Current loops | 6 | 4-20 mA, INA3221 × 2, 5.6 Ω shunts; two used for secondary pH and ORP |
| Temperature | 1+ | DS18B20 on 1-Wire (firmware reads one) |
| Tank level | 3 | JSN-SR04T-type ultrasonic sensors, shared trigger |
| Tank minimum | 3 | float switches, dry contacts |
| Dry contacts | 16 | MCP23017, 4.7 kΩ pull-ups, 5 used (3 floats, 2 selector positions) |
| Flow | 2 | pulse inputs, opto-coupled (PC817) |
| Emergency chain | 1 | opto-coupled monitor input; the chain itself is hardware |

## Outputs

| Function | Qty | Details |
|---|---|---|
| Relays | 4 | SRD-series, one changeover contact each (3 dosing, 1 filtration); load ratings **TBC** per the relay datasheet and the board's contact spacing |
| Solenoid valves | 4 | low-side MOSFET with gate driver (UCC27517), 5-pin connector |
| Inverter link | 1 | RS-485 (MAX3485), Modbus RTU master, 19200 bps even parity, 120 Ω termination, TVS-protected (SMAJ12CA); tested design target Toshiba VF-S15 |
| Speed reference | 1 | MCP4018 digital potentiometer on CN6 (fitted, not used by the firmware) |
| Status output | 1 | LED OUT (CN4) |

## Behaviour

- 13 dosing permissives, each visible on its own; dosing is refused unless all are met.
- Manual dosing is always a pulse with a maximum duration.
- All outputs start off; a hardware emergency chain is independent of the firmware.
- The panel only requests; the control board decides and returns the reason when it refuses.

## Electrical and environmental

| | |
|---|---|
| Supply current | TBC |
| Relay contact rating | TBC |
| Valve output current | TBC |
| Operating temperature | TBC (designed for a dry, ventilated cabinet) |
| Isolation | none between field inputs and board ground (see [limitations](limitations.md)) |
| Protection | TVS on 24 V input and on RS-485; no surge protection on the other field lines |
| Certification | none: hobbyist-grade design, see the [safety notice](../README.md#safety-notice) |

## Documents

[Pin map](pin-map.md) · [Inputs and outputs](io-map.md) · [Panel protocol](uart-protocol.md) ·
[Wiring (draft)](wiring.md) · [Bring-up checklist](bring-up.md) · [Limitations](limitations.md)
