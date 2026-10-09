# Swimming Pool Board (SPB) — Rev A

*[Italiano](README.it.md)*

An acquisition and control board for a private swimming pool, with a touch
panel as its user interface. The board reads pH, ORP, pressure, temperature,
flow, drum levels and dry contacts, drives dosing pumps, solenoid valves and a
filtration pump (directly or through a Modbus inverter), and enforces a set of
interlocks before it allows any dosing. The panel only asks; the board decides.

![Enclosure, front](hardware/enclosure/render-front.png)

![System overview](docs/system-overview.svg)

## Status

Rev A is the first public release. The board has been designed, built and run
on a real pool. It works, with the limitations listed in
[docs/limitations.md](docs/limitations.md).

This is a hobbyist-grade design shared for study, feedback and
non-commercial use. It is **not** certified for any regulatory scheme.
See the [safety notice](#safety-notice).

## What it does

| | |
|---|---|
| **Analog inputs** | pH and ORP (potentiometric front end, OPA2338 → ADS1115), one 0-10 V input (filter pressure) plus one spare, six 4-20 mA loops (2 × INA3221, 5.6 Ω shunts) |
| **Digital inputs** | DS18B20 1-Wire bus, three ultrasonic drum-level sensors, 16 dry-contact inputs (MCP23017), opto-coupled emergency-chain monitor, two pulse flow meters |
| **Outputs** | 4 relays (3 dosing, 1 filtration), 4 low-side solenoid-valve drivers, RS-485 Modbus RTU master for a Toshiba VF-S15 inverter |
| **Logic** | 13 dosing permissives exposed one by one, pulsed manual dosing with a hard time limit, backwash sequence, safe state at boot |
| **Panel** | Waveshare ESP32-S3-Touch-LCD-7B, seven LVGL pages, talks to the board over a 3-wire UART |
| **Integration** | ESPHome native API (Home Assistant optional — the plant runs without it) |

## Repository layout

| Folder | Content |
|---|---|
| [`hardware/`](hardware/README.md) | EasyEDA Pro project, Gerber files, schematic, assembly drawing, BOM, layout image, enclosure renders |
| [`firmware/`](firmware/README.md) | ESPHome configuration of both boards, and a Python simulator of the control board |
| [`docs/`](docs/) | pin map, I/O map, UART protocol, limitations, bring-up checklist |

Every document exists in English and Italian (`*.it.md`).

## Getting started

1. **Hardware** — order the PCB from the Gerber files and source the parts
   from [`hardware/bom.csv`](hardware/bom.csv).
2. **Firmware** — follow [`firmware/README.md`](firmware/README.md): copy
   `secrets.yaml.example`, tune the values at the top of `spb-control.yaml`,
   then `esphome run` both boards.
3. **First power-up** — go through the [bring-up checklist](docs/bring-up.md)
   before connecting any pump or valve.

## Safety notice

This board switches dosing pumps for acid and chlorine, solenoid valves and a
filtration pump. A fault or a wiring or configuration error can release
chemicals or run equipment dry.

- The **emergency chain is hardware** and independent of the firmware. The
  thirteen dosing permissives in the firmware are a convenience, not the safety
  system. Build a proper hardware safety chain.
- All outputs start off, and manual dosing is always a time-limited pulse. These
  protections do not replace the emergency chain.
- Mains-voltage wiring must be done by a qualified person, in a suitable
  enclosure, with proper protection.
- The design comes with no warranty of any kind, and you use it at your own risk.

## Feedback and commercial interest

Feedback is the reason this is public.

- Questions, ideas and use cases: open a **Discussion**.
- Bugs and errors in the schematic, layout, BOM, firmware or documents: open an **Issue**.
- Commercial enquiries (manufacturing, resale, integration, licensing): open a
  Discussion in the *Commercial* category.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/).
See [LICENSE](LICENSE). Commercial use is not covered by this license: contact
the authors through a Discussion.
