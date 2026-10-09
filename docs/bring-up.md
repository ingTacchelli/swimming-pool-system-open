# Bring-up checklist

*[Italiano](bring-up.it.md)*

Do these checks on the bench, with **no pump, valve or inverter connected**, in
this order.

## Before power-up

1. **DevKitC-1 revision.** Look at the module silkscreen. On v1.0 modules GPIO48
   drives the RGB LED; here it carries the main flow input, so that LED is not
   usable. Make sure the module is an ESP32-S3-DevKitC-1 N16R8.
2. **R63 must be a pull-down to ground**, not a pull-up to VCC. With a pull-up the
   MAX3485 starts in transmit mode and Modbus never starts.
3. **Relay connectors.** The firmware maps the dosing relays by connector
   designator: CN8 = acid (GPIO18), CN18 = chlorine (GPIO7), CN7 = spare (GPIO17),
   CN9 = filtration (GPIO10). Check the text printed on your PCB next to each of
   those connectors, and wire the pumps accordingly. If you want a different
   mapping, change only the pins in `firmware/control/packages/control-outputs.yaml`.
4. **Shunts.** Confirm the 4-20 mA shunt resistors are 5.6 Ω; the value is
   `shunt_4_20ma` in `spb-control.yaml`.
5. **CN12 jumpers.** With no jumpers CN12 channels are 0-10 V inputs. If you close
   them, the input becomes 4-20 mA and the `filter_pressure` lambda must be
   rewritten.

## First power-up

6. **Outputs off at boot.** With the firmware flashed (and also during the flash)
   all four relays and four valve drivers must stay off.
7. **I²C scan.** The boot log must show 0x20, 0x2F, 0x40, 0x41 and 0x48. Erratic
   readings or NAKs point first at the ADS1115, which runs at 5 V on a 3.3 V bus.
8. **Emergency chain.** With the contact closed the monitor input (GPIO21) must
   read high; unplugging the cable must read as an open chain.
9. **Selector and floats.** Check AUTO / MANUAL / ZERO and the three drum floats
   in the web interface.
10. **Ultrasonic sensors.** Measure the distance with the drums empty and full and
    set `tank_empty_m` and `tank_full_m`.
11. **Temperature.** Read the DS18B20 addresses from the first-boot log and write
    them in `control-bus-sensors.yaml`.
12. **pH and ORP.** Run a two-point calibration with buffer solutions and write
    the coefficients (`cal_ph_slope`, `cal_ph_offset`, `cal_orp_slope`, `cal_orp_offset`) in
    `control-logic.yaml`.
13. **Flow.** Set `k_factor_pulses_per_litre` for your flow meter and check the pulse
    counts.

## With the inverter (Toshiba VF-S15)

14. Set the drive parameters: `f829 = 1` (Modbus RTU), `f800` / `f801` for
    19200 bps and even parity.
15. Check on the real drive the scale of the output-current register FD03
    (percentage of the rated current set in `f601`) and which bit of FA00
    commands forward run. Until confirmed, the displayed current is indicative
    and the run switch must be tested on the bench.

## Panel

16. Put **SW1** on H3. Check that the ROM line `ESP-ROM:esp32s3-...` appears at
    reset on a terminal at 115200 connected to H3.
17. Look for `Failed to allocate 153600 bytes for internal draw buffer` in the
    boot log: if it appears, the draw buffer is still in PSRAM and the
    suggestions in `spb-display.yaml` apply.
18. The `waveshare_io_ch32v003` external component is pinned to a commit in
    `spb-display.yaml`; update the pin on purpose, not by accident.
19. To test the protocol before the control board is ready, use
    `firmware/simulator/spb_simulator.py`.
20. Open the **Trends** page and leave it for a few minutes: the charts must start
    drawing, and the boot log must not report an allocation failure. With the
    simulator's `--demo --speed 90` and `trend_interval_s: "2"` they fill quickly.

## Before any dosing

21. Run the pumps in manual, as time-limited pulses, with water, and verify that
    each pump starts from the intended connector.
22. Verify that the hardware emergency chain stops everything on its own,
    independently of the firmware.
