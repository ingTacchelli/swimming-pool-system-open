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
receives and sends requests. No "true" state lives in the panel.

Three message types, all ASCII, one line per message terminated by `\n`, fields
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
| `ev` | state of the 4 solenoid valves, 4 digits | `ev=1100` |
| `do` | dosing enabled (0/1) | `do=1` |
| `cs` | permissives satisfied out of 13 | `cs=13` |
| `al` | active alarms (number) | `al=0` |

A value of `-999` means "not valid". The current firmware always reports `tc` as
-999: the cell temperature is not read yet.

Complete example:

```
S|mo=A|tv=27.4|tc=26.9|ph=7.22|ps=7.18|or=712|os=706|hz=42.0|cu=3.8|pu=1|q1=14.2|q2=2.1|l1=72|l2=58|l3=91|f1=1|f2=1|f3=1|ev=1100|do=1|cs=13|al=0|*64
```

If the panel does not receive a valid `S` for **3 seconds**, it declares the data
stale (all values greyed out, "link lost" banner) and blocks the commands.

### C — command (panel → control)

| key | meaning |
|---|---|
| `n` | command sequence number, 1-999, used for the ack |
| `c` | command |
| `v` | value |

Commands:

| `c` | `v` | effect |
|---|---|---|
| `pump` | `0` / `1` | stop / start the filtration pump |
| `hz` | `25.0`..`50.0` | frequency requested from the VFD |
| `ev1`..`ev4` | `0` / `1` | close / open the solenoid valve |
| `dosa` `dosc` `dosr` | `1`..`60` | dosing jog acid / chlorine / spare, in seconds |
| `filt` | `0` / `1` | filtration relay |
| `scen` | `norm` `int` `sil` `heat` `play` `frost` | filtration scenario |
| `back` | `1` / `0` | start / stop backwash |
| `ackal` | `1` | acknowledge the active alarms |

Example: `C|n=17|c=pump|v=0|*2B`

### A — reply (control → panel)

`r=ok` if the command was accepted and executed, `r=err` otherwise, with `w=`
carrying the reason for the refusal, to be shown to the user as it is.

```
A|n=17|r=ok|*23
A|n=18|r=err|w=selector not in MANUAL|*26
```

The panel considers a command failed if it receives no ack within **2 seconds**,
and reports it instead of pretending it succeeded.

## Refusal reasons

The reason strings are in English, as shown on the panel.

- `selector not in MANUAL` — manual command with the selector in AUTO or 0
- `selector in ZERO` — any command with the selector at 0
- `dosing blocked` — at least one permissive is missing (reserved, not yet issued by the current firmware)
- `procedure in progress` — backwash or filter wash running
- `blocking alarm` — an alarm prevents that manoeuvre (reserved, not yet issued)
- `VFD unreachable` — Modbus timeout towards the inverter (reserved, not yet issued)
- `frequency out of range`, `duration out of range` — value outside the allowed range
- `acid tank empty`, `chlorine tank empty`, `reserve tank empty` — drum float at minimum
- `unknown command`, `unknown valve` — unknown command or valve

## Safety note

This channel is not part of the safety chain. The emergency stop is hardware and
independent: if the panel or this UART stops working, the plant must stay in a
safe state without their intervention.
