# Known limitations

*[Italiano](limitations.it.md)*

Rev A works. These are its known limits; they are the main candidates for the
next revision.

## Hardware

- **No battery-backed clock.** Time comes only from SNTP and is lost without a
  network, so weekly timers cannot be relied on offline.
- **No analog outputs.**
- **A single RS-485 port.**
- **Limited surge protection.** There is a TVS diode on the 24 V input (SMBJ30A)
  and on the RS-485 pair (SMAJ12CA); the other lines leaving the cabinet — sensor
  inputs, relay and valve outputs — carry no surge protection.
- **The field front end is referenced to the board ground.** There is no galvanic
  isolation: the optocouplers on the emergency-chain and flow inputs share the
  board ground on both sides. The reference electrode of the pH probe sits in the
  same water as the electrolysis cell.

## Firmware

- **Cell temperature is not read.** The 1-Wire bus supports several sensors, but
  the firmware reads one (the basin); `tc` in the panel protocol is always -999.
- **The panel shows only the number of active alarms**, not the list.
- **The valve state on the panel** is the `ev` field received from the control
  board, not the position of the last button pressed.
- **The MCP4018 digital potentiometer** (VFD speed reference, CN6) is fitted but
  not used: the inverter is controlled over Modbus.
- **Inverter registers.** The scale of the output-current register (FD03) and the
  FA00 run bit have to be checked on your drive (see
  [bring-up.md](bring-up.md)).
- **Calibration is not done at the factory.** Until a two-point calibration is made
  from the panel, the coefficients are placeholders and dosing stays blocked.
- **Pressure full scale** (4 bar at 20 mA) is an assumption: confirm it on the
  transmitter datasheet.
- **Scenarios.** The `scen` command exists on the panel but the board does not
  implement it yet; use the scheduler.
- **Scheduler and clock.** Programs depend on SNTP time (see the clock limit
  above); the shock mode is deliberately not saved to flash.
- **Default settings PIN is 1234**: change `settings_pin` before use.
- **Display refresh.** The panel component uses a single frame buffer, so some
  tearing artefacts in the refresh are unavoidable by construction. Removing
  them needs a local copy of the display component with a double frame buffer.
- **Trends history is volatile.** The charts on the Trends page keep their samples
  in RAM: a reset empties them, and nothing is stored or exported. They are
  drawn by code, outside the ESPHome LVGL schema; check the boot log for
  allocation errors after opening the page (see [bring-up.md](bring-up.md)).
- **Languages.** Entity names and the control-board messages are in English; the
  panel offers English and Italian (Settings), with English as the default at first boot.
