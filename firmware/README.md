# Firmware

*[Italiano](README.it.md)*

ESPHome configuration of both boards. Two separate devices, each with its own
ESP32-S3:

| File | Board | Role |
|---|---|---|
| `control/spb-control.yaml` | ESP32-S3-DevKitC-1 (N16R8) on the custom PCB | reads the sensors, drives pumps and valves, talks to the VFD, decides the interlocks |
| `display/spb-display.yaml` | Waveshare ESP32-S3-Touch-LCD-7B | draws the touch panel, sends command requests |

The two boards are linked only by a 3-wire UART (TX/RX/GND, 115200 8N1). The
message format is in [`../docs/uart-protocol.md`](../docs/uart-protocol.md).

## Structure

```
control/
  spb-control.yaml              <- the file to build; holds all the values to tune
  packages/
    control-base.yaml             framework, network, services, safe state at boot
    control-bus-sensors.yaml      I2C, ADS1115, INA3221 x2, MCP23017, 1-Wire, flow, levels
    control-outputs.yaml           dosing relays, filtration relay, solenoid valves, jog
    control-vfd-modbus.yaml       Toshiba VF-S15 over RS-485 Modbus RTU
    control-logic.yaml           calibrations, 13 dosing permissives, backwash, autonomy
    control-link-display.yaml     UART protocol, control-board side
display/
  spb-display.yaml              <- single file: panel, touch, UART link, LVGL (8 pages)
simulator/
  spb_simulator.py              simulates the control board over a USB-serial adapter
secrets.yaml.example            <- copy to secrets.yaml and fill in
```

## First build

```bash
cp secrets.yaml.example secrets.yaml     # then fill it in for real
cp secrets.yaml control/secrets.yaml
cp secrets.yaml display/secrets.yaml
cd control && esphome config spb-control.yaml && esphome run spb-control.yaml
cd ../display && esphome config spb-display.yaml && esphome run spb-display.yaml
```

Both files pass `esphome config` with ESPHome 2026.9.1. `secrets.yaml` is ignored
by git: never commit it. The display fonts are downloaded from Google Fonts at
compile time, so the build machine needs internet access.

## What to tune before using it

All values are at the top of `spb-control.yaml`, in the `substitutions` block:

- `shunt_4_20ma` — 5.6 ohm
- `cn12_ratio`, `cn12_full_scale_v`, `pressure_full_scale_bar` — the 0-10 V
  pressure input; if you close the jumpers for 4-20 mA, rewrite the
  `filter_pressure` lambda
- `k_factor_pulses_per_litre` — pulses per litre of your flow meter
- `tank_empty_m`, `tank_full_m`, `tank_litres` — drum geometry, measured by hand
- `dosing_pump_litres_per_s` — dosing pump flow, for the autonomy estimate
- `freq_*_hz` — limits and normal frequency of the filtration pump
- probe-disagreement and minimum-flow thresholds

Also: the DS18B20 addresses must be read from the first-boot log and written in
`control-bus-sensors.yaml`, and the pH/ORP calibration coefficients (`cal_ph_slope`,
`cal_ph_offset`, `cal_orp_slope`, `cal_orp_offset` in `control-logic.yaml`) must be derived
from a two-point calibration with buffer solutions. The full list of checks is
in the [bring-up checklist](../docs/bring-up.md).

## Simulator and demo

`simulator/spb_simulator.py` plays the control board over a USB-serial adapter
(wiring in the file header). For a demo or a video use the slow, realistic
curves:

```
python spb_simulator.py COM7 --demo --speed 90
```

and in `spb-display.yaml` set `trend_interval_s: "2"`. One real second is then 90
simulated seconds, so the Trends charts show about 12 simulated hours in 8
minutes: pH drifts up and is pulled back, ORP follows, the water warms and
cools. Without `--demo` the simulator sends fast test waves.

## Safety measures built in

- Outputs start **off**, and an explicit `go_to_safe_state` script exists. The
  gates also have hardware pull-downs, so the protection is double.
- Manual dosing is always a pulse with a maximum duration (`jog_max_ms`): there is
  no continuous ON that can be commanded from the touch panel.
- Commands from the panel are **checked by the control board**, which can refuse
  them and return the reason; the panel decides nothing by itself.
- If the UART drops, the panel declares the data stale and blocks the commands.
- None of this replaces the hardware emergency chain, which stays independent of
  the ESP32.

## Panel notes

- UART to the control board on GPIO43/44, header H3, with SW1 on H3. GPIO15/16 on
  the 7B are the SP3485 RS-485 pair and do not come out as TTL. The logger sits
  on `USB_SERIAL_JTAG` because UART0 is the link; read the console from the
  native USB-C.
- The panel is described pin by pin with `rpi_dpi_rgb`, with no predefined
  `model`. Verified timings: hsync 162/152/48, vsync 45/13/3. The pixel clock is
  30 MHz (inverted), the maximum allowed by the component: with a 1386 × 661 frame
  that is 32.7 Hz, while 21 MHz would give 22.9 Hz.
- **Smoothness is about where LVGL draws.** `buffer_size: 12%` (one eighth,
  150 KB) because ESPHome tries internal SRAM only when the fraction is at least
  1/4, and 300 KB of contiguous internal SRAM do not exist with Wi-Fi on.
  `CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP` moves the network buffers to PSRAM and
  frees internal RAM. See the comments in `spb-display.yaml` for what to do if the
  boot log reports a failed allocation.
- `rpi_dpi_rgb` fixes `num_fbs = 1`, so a share of refresh artefacts is
  unavoidable by construction.
- The CH32V003 expander uses an external component
  (`github.com/fuzzybear62/esphome-waveshare_io_ch32v003`), pinned to a commit:
  adjustable backlight and panel/touch reset.
- Eight LVGL pages: Home, Filtration, Chemistry, Valves, Alarms, Maintenance,
  Commands, Trends. The navigation column, the header and the status bar live in
  the `top_layer`, so they exist once instead of eight times. If the touch ever
  stops responding on the pages, that is the first place to look.
- **Trends page.** Two charts: pH and ORP, and pool temperature and main flow.
  ESPHome has no chart widget, so the charts are LVGL charts created from code
  (`-DLV_USE_CHART=1` in `spb-display.yaml`). One sample per `trend_interval_s`
  seconds (default 30), `trend_points` samples per chart (default 240, that is
  the last 2 hours); a lost link draws a gap. The history lives in RAM and is
  lost at reset.
- Only the visible page is updated, and every label is rewritten only if its text
  really changed.
