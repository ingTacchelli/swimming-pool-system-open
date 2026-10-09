# Inputs, outputs and functions

*[Italiano](io-map.it.md)*

Inventory of the acquisition and control board. The panel board is separate and
carries only the display, its touch controller and the serial link.

### Analog inputs

| Function | Type | Channels | Interface | Address |
|---|---|---|---|---|
| Primary pH | Potentiometric | 1 | OPA2338 front end → ADS1115 | 0x48 A0 |
| Primary ORP | Potentiometric | 1 | OPA2338 front end → ADS1115 | 0x48 A1 |
| Filter pressure | 0-10 V | 1 | Divider → ADS1115 | 0x48 A3 |
| Spare | 0-10 V | 1 | Divider → ADS1115 | 0x48 A2 |
| Current loops | 4-20 mA | 6 | INA3221 × 2 on 5.6 Ω shunts | 0x40, 0x41 |

The potentiometric front end needs a negative rail for the amplifier, produced
locally by a charge pump. Two of the six loops are used for the secondary pH and
ORP transmitters; four are free.

### Digital and counting inputs

| Function | Type | Channels | Interface | Pin |
|---|---|---|---|---|
| Water temperature | 1-Wire | 1+ | DS18B20 | GPIO5 |
| Drum level | Time of flight | 3 | Shared TRIG, three ECHO | GPIO4 / 41, 40, 39 |
| Dry contacts | Digital | 16 | MCP23017 with 4.7 kΩ pull-ups | 0x20 |
| Emergency chain | Opto-coupled digital | 1 | PC817 | GPIO21 |
| Flow meters | Pulse counting | 2 | PC817 | GPIO48, GPIO47 |
| Expander interrupt | Digital | 1 | MCP23017 INTA, active low | GPIO6 |

The 1-Wire bus carries several sensors on the same pin; the firmware currently
reads one temperature (the pool basin). Five of the sixteen dry contacts are
used: three drum floats and two selector positions.

### Outputs

| Function | Type | Channels | Interface | Pin |
|---|---|---|---|---|
| Relays | Dry contact | 4 | Driver + relay | GPIO18, 7, 17, 10 |
| Solenoid valves | MOSFET, low side | 4 | UCC27517 gate driver + MOSFET | GPIO14, 13, 12, 11 |

Three relays are for dosing and one for filtration; one of the three dosing
relays is a spare, like the fourth solenoid valve. The valves stay on real GPIOs
and not on an expander so they can be modulated.

### Buses

| Function | Interface | Pin |
|---|---|---|
| RS-485 to the inverter | MAX3485, Modbus RTU master | GPIO1 / 2 / 42 |
| UART to the panel | Direct TTL, 115200 8N1 | GPIO15 / 16 |
| I²C | MCP23017, ADS1115, 2 × INA3221, MCP4018 | GPIO8 / 9 |

The inverter is a Toshiba VF-S15. The protocol of the panel link is documented
in [`uart-protocol.md`](uart-protocol.md).

### Known limits

See [limitations.md](limitations.md).
