# Wiring (draft)

*[Italiano](wiring.it.md)*

**Draft.** This page lists what is certain today and marks what must still be
confirmed on the real board. Do not wire pumps from it until the *To confirm*
items are closed.

![Wiring overview](wiring.svg)

## Principles

- **Mains stays outside the board.** The relays are dry contacts: the pump or
  valve supply is wired through them by the installer, in a suitable enclosure,
  with its own protection.
- **The hardware emergency chain** (selector, push buttons, mushroom) interrupts
  the loads independently of the firmware. The board only *monitors* it.
- **One cable, one purpose:** probes with shielded cable away from relay and
  pump wiring; BNC for pH and ORP.

## Connectors

| Connector | Silkscreen | Function | Status |
|---|---|---|---|
| CN2 | ALIMENTAZIONE | 24 V DC power input | confirmed |
| CN18 | DOSATRICE | relay, chlorine dosing pump | confirmed |
| CN9 | FILTRAGGIO | relay, filtration pump | confirmed |
| CN7 | ACIDO | relay, **see the warning below** | **to confirm** |
| CN8 | PH | relay, **see the warning below** | **to confirm** |
| CN10 | ELETTROVALVOLE | solenoid valves EV1-EV4 (5 pins: four outputs and the common) | confirmed, pinout to document |
| CN11 | RS485A | RS-485 to the inverter | confirmed, pinout to document |
| CN6 | vfd pot | speed reference (digital potentiometer, unused by the firmware) | confirmed |
| CN12 | | analog input 0-10 V, pressure | confirmed |
| CN19-CN22 | PH-5A | 16 dry-contact inputs | confirmed; function per connector to document |
| RF1, RF2 | | BNC: pH and ORP probes | confirmed |
| U29 | | emergency-chain monitor (pin 1), flow B (pin 2), flow A (pin 3) | confirmed |
| CN1, CN5, CN13, CN14, CN3, CN4, U30, U38, U46, U47 | | ultrasonic sensors, 1-Wire, flow, LED out, panel link and others | **to document** |

## Warning: relay connectors CN7 and CN8

The firmware drives the acid pump from CN8 and the spare dosing output from CN7.
The silkscreen text next to the connectors reads the other way round (CN7
"ACIDO", CN8 "PH"). Until this is checked on the real board, **do not connect an
acid or chlorine pump**. Verify with a meter that GPIO18 drives the relay that
you intend to use for acid, then either change the pins in
`firmware/control/packages/control-outputs.yaml` or note the correction here.

## To do for the final version

- Per-connector pinout tables with wire colours and recommended cable.
- A wiring diagram of a complete cabinet, with the emergency chain.
- Recommended wire gauge and fuses for each load.
