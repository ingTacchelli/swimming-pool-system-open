# UART protocol between control board and panel

*[Italiano](uart-protocol.it.md)*

## Physical link

Direct UART, 3 wires (TX, RX, GND), **crossed**: the TX of one goes to the RX of
the other.

| | control board | panel (Waveshare 7B) |
|---|---|---|
| TX | GPIO15 | **GPIO43** — header H3 pin 4 (EX_TXD) |
| RX | GPIO16 | **GPIO44** — header H3 pin 3 (EX_RXD) |
| GND | common ground | header H3 pin 2 |

On the Waveshare schematic, sheet 1, the pin allocation table assigns IO15 to
RS485_TX and IO16 to RS485_RX: those two pins go to the SP3485 and are not
available as TTL on the panel. The only TTL UART brought out is UART0 on
GPIO43/44, which passes through U13 (FSUSB42UMX, 2:1 switch) and ends either on
the on-board CH343P USB-serial bridge or on header H3, depending on **SW1**,
which must be kept on H3. Pin 1 of H3 is a 3V3 output and must be left free.

Consequence for the panel firmware: the ESPHome logger must sit on
`hardware_uart: USB_SERIAL_JTAG`, otherwise it takes UART0 together with the
link. The console is read from the other, native, USB-C.

At reset the panel's ROM bootloader prints one line on GPIO43 at 115200. It is
harmless: it does not start with `S`, `A` or `C` and would not pass the checksum
anyway.

Parameters: **115200 baud, 8N1**, no flow control. The cable is short (same
enclosure), so no differential signalling is needed.

## Principle

The panel never decides: it **asks**. The control board is the only one that
knows the real state and evaluates the interlocks; the panel draws what it
receives and sends requests. No "true" state lives in the panel. Editable
parameters, calibration and the filtration schedule live on the control board
and are stored in its flash; the panel only shows them and requests changes.

Five message types, all ASCII, one line per message terminated by `\n`, fields
separated by `|`, XOR checksum at the end.

## Format

```
<TYPE>|<key>=<value>|<key>=<value>|...|*<XX>\n
```

`*XX` is the XOR of all the characters before the asterisk, as two uppercase hex
digits. A message with a wrong checksum is discarded without a reply.

### S — status (control → panel), every 500 ms

| key | meaning | example |
|---|---|---|
| `mo` | selector mode: `A` auto, `M` manual, `0` zero | `mo=A` |
| `tv` / `tc` | basin / cell temperature, °C | `tv=27.4` |
| `ph` / `ps` | primary / secondary pH | `ph=7.22` |
| `or` / `os` | primary / secondary ORP, mV | `or=712` |
| `hz` / `cu` | VFD frequency and current | `hz=42.0` |
| `pu` | filtration pump running (0/1) | `pu=1` |
| `q1` / `q2` | main / cell flow, m³/h | `q1=14.2` |
| `l1`..`l3` | drum level 1-3, % | `l1=72` |
| `f1`..`f3` | drum minimum floats 1-3 (1 = product present) | `f1=1` |
| `ev` | state of the 4 outputs (EV1-EV3 valves, EV4 pool lighting), 4 digits | `ev=1100` |
| `do` | dosing enabled (0/1) | `do=1` |
| `cs` | permissives satisfied out of 13 | `cs=13` |
| `al` | active alarms (number) | `al=0` |
| `cb` | the 13 permissives C01..C13, one character each (`1` = satisfied) | `cb=1111111111111` |
| `pa` / `pb` / `dd` | filter pressure upstream / downstream / differential, bar | `dd=0.23` |
| `lc` | backwash advised (0/1) | `lc=0` |
| `dt` | board local date and time `YYYYMMDDHHMM`, `0` if the clock is not synchronised | `dt=202610131715` |

A value of `-999` means "not valid". The current firmware always reports `tc` as
-999: the cell temperature is not read yet. The panel ignores a `cb` that is not
exactly 13 characters long.

`lc` is 1 when the pump is running, no backwash is in progress and the
differential has been above the threshold (`dl`, default 0.50 bar) for 5
minutes; it drops after 30 s below the threshold.

Complete example:

```
S|mo=A|tv=27.4|tc=-999.0|ph=7.22|ps=7.18|or=712|os=706|hz=42.0|cu=61.0|pu=1|q1=14.2|q2=2.1|l1=72|l2=58|l3=91|f1=1|f2=1|f3=1|ev=1100|do=1|cs=13|al=0|cb=1111111111111|pa=1.85|pb=1.62|dd=0.23|lc=0|dt=202610131715|*4C
```

If the panel does not receive a valid `S` for **3 seconds**, it declares the data
stale (all values greyed out, "link lost" banner) and blocks the commands.

### P — parameters and calibration (control → panel), every 2 s and after each settings command

| key | meaning |
|---|---|
| `fp` / `fc` | minimum flow, main circuit / measuring cell (m³/h) |
| `dp` / `do` | maximum mismatch between the two pH / ORP probes |
| `fn` | normal pump frequency (Hz) |
| `dl` | filter differential pressure above which a backwash is advised (bar) |
| `vp` / `vo` | average pH / ORP probe voltage (V), `-999` = not available |
| `cp` / `co` | pH / ORP calibration valid (0/1) |
| `np` / `no` | first calibration point pending (0/1) |
| `bp` / `bo` | buffer of the pending point |
| `mp` / `mr` | slope of the line in use (pH/V, mV/V) |

```
P|fp=5.00|fc=0.30|dp=0.30|do=40|fn=42.0|vp=1.2043|vo=0.7360|cp=1|co=1|np=0|bp=0.00|no=0|bo=0|mp=-3.412|mr=962.500|dl=0.50|*37
```

The panel does not use `P` to supervise the link (that stays `S` every 500 ms).
If no `P` arrives for 6 s the Parameters and Calibration pages show `--`.

### G — filtration schedule (control → panel), every 2 s and after each `set`

| key | meaning |
|---|---|
| `pr` | program: 0 off, 1 daily, 2 weekly, 3 winter |
| `mo` | mode: 0 high, 1 normal, 2 gentle |
| `fv` | photovoltaic (0/1): filtration only in the daylight window `vi`..`vf` |
| `sh` | shock filtration (0/1): continuous filtration, not stored in flash |
| `in` / `fi` | normal window (minutes from midnight, default 08:00-22:00) |
| `vi` / `vf` | daylight window for photovoltaic (default 08:00-19:00, fixed: the sun is not measured) |
| `h0`..`h6` | filtration minutes of each day (Monday = 0), computed by the board from program + mode |
| `ac` / `tg` | minutes run today / today's target |
| `st` | 0 off, 1 outside the window, 2 running, 3 target reached, 4 selector not in AUTO, 5 time not available, 6 target zero, 7 shock running |

Hours per day: daily high 8, normal 5, gentle 3; weekly Mon-Fri 7/5/3 and
Sat-Sun 10/8/5; winter 4/3/2. The program drives the pump only with the selector
in AUTO and outside a backwash; in MANUAL/ZERO it does nothing and never stops a
pump started by the operator. The accumulated time resets at midnight and at
every board restart.

```
G|pr=2|mo=1|fv=0|sh=0|in=480|fi=1320|vi=480|vf=1140|h0=300|h1=300|h2=300|h3=300|h4=300|h5=480|h6=480|ac=125|tg=300|st=2|*7D
```

### C — command (panel → control)

| key | meaning |
|---|---|
| `n` | command sequence number, 1-999, used for the ack |
| `c` | command |
| `v` | value |

Commands:

| `c` | `v` | effect |
|---|---|---|
| `pump` | `0` / `1` | stop / start the filtration pump (stop uses the run command, not a 0 Hz reference) |
| `hz` | `25.0`..`50.0` | frequency requested from the VFD |
| `ev1`..`ev4` | `0` / `1` | close / open the solenoid valve (`ev4` = pool lighting) |
| `dosa` `dosc` `dosr` | `1`..`60` | dosing jog acid / chlorine / reserve, in seconds |
| `filt` | `0` / `1` | filtration relay |
| `scen` | `norm` `int` `sil` `risc` `gioco` `gelo` | filtration scenario — **not implemented on the control board**: it answers `unknown command` |
| `back` | `1` / `0` | start / stop backwash |
| `ackal` | `1` | acknowledge the active alarms |
| `set` | `key:value` | change a parameter (see below) |
| `rst` | `par` | restore the parameters to the build-time values |
| `calp` | pH of the buffer | capture a pH calibration point (MANUAL only) |
| `calo` | mV of the buffer | capture an ORP calibration point (MANUAL only) |
| `calc` | `p` or `o` | cancel the pending first point |

Keys of `set`:

| key | parameter | range |
|---|---|---|
| `fp` / `fc` | minimum flow main / cell (m³/h) | 0..100 / 0..20 |
| `dp` / `do` | maximum pH / ORP mismatch | 0.05..2 / 5..300 |
| `fn` | normal pump frequency (Hz) | `freq_min_hz`..`freq_max_hz` |
| `dl` | backwash differential (bar) | 0.1..3.0 |
| `gpr` / `gmo` | schedule program / mode | 0..3 / 0..2 |
| `gfv` / `gsh` | photovoltaic / shock | 0/1 |
| `gin` `gfi` `gvi` `gvf` | window start/end (minutes from midnight) | 0..1439 |

The starting values of the parameters come from the substitutions in
`spb-control.yaml` **only on the very first boot**; afterwards the live value is
the one stored in flash (`rst|par` brings back the build-time ones).

Two-point calibration: the first point (`calp` / `calo`) does not change the
calibration in use and expires after 10 minutes; at the second point the line is
recomputed and declared valid, if the checks pass (probe stable, different buffer
and voltage, plausible slope).

Example: `C|n=21|c=set|v=fp:6.5|*65`

### A — reply (control → panel)

`r=ok` if the command was accepted and executed, `r=err` otherwise, with `w=`
carrying the reason for the refusal. The reason is in English; the panel
translates it when its language is Italian.

```
A|n=17|r=ok|*23
A|n=18|r=err|w=selector not in MANUAL|*26
```

The panel considers a command failed if it receives no ack within **2 seconds**,
and reports it instead of pretending it succeeded.

## Refusal reasons

- `selector not in MANUAL` — manual command with the selector in AUTO or 0
- `selector in ZERO` — any command with the selector at 0
- `procedure in progress` — backwash running
- `frequency out of range`, `duration out of range`, `value out of range` — value outside the allowed range
- `invalid value`, `unknown parameter`, `unknown reset` — malformed `set` / `rst`
- `acid drum empty`, `chlorine drum empty`, `reserve drum empty` — drum float at minimum
- `invalid buffer value`, `buffer out of range`, `probe has no reading`, `unstable reading`, `buffer same as first point`, `voltage same as first point`, `abnormal slope`, `unknown probe` — calibration refusals
- `unknown command`, `unknown valve` — unknown command or valve

## Safety note

This channel is not part of the safety chain. The emergency stop is hardware and
independent: if the panel or this UART stops working, the plant must stay in a
safe state without their intervention.
