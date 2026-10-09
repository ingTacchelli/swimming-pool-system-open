# Use cases

*[Italiano](use-cases.it.md)*

The board was designed for one private pool, but nothing in it is specific to
one. These are the situations it fits, and what it would take. Only the first one has
been run in practice; the others are ideas that have not been tested.

## Private pool, fully automatic
The design case: pH and chlorine kept in range, filtration run at the right
speed through an inverter, waterfall and jets on a touch panel.
*Needs:* pH and ORP probes, two dosing pumps, a flow sensor, an inverter (optional).

## Pool you already have, with a dumb controller
Keep the pumps and add only the measuring and the safeguards: the board reads,
shows and warns, and you decide when to let it dose.
*Needs:* probes and flow sensor; dosing outputs can stay unconnected.

## Shared or small public pool
More water, more risk: two probes of each kind cross-check each other, and
dosing stops when they disagree. A log of readings is useful for the operator.
*Needs:* the secondary probes on the 4-20 mA inputs and a network connection.

## Hotel, camping or holiday home
Remote visibility (Wi-Fi, Home Assistant), alarms for low product or high
pressure, and a safe state if nobody is there.
*Needs:* network access and notification setup.

## Spa, hot tub or wellness pool
Same chemistry, smaller volume, tighter limits: tune the thresholds and the
dosing pulse length.

## Water features and ponds
The four valve outputs can drive a waterfall, jets or misters on their own;
useful for natural ponds with a filter and a pump.

## Aquaculture, tanks and water treatment
pH, ORP, temperature and level on one board, with relays for a dosing pump or an
aerator. The same firmware ideas apply.

## Learning and prototyping
A complete, documented, open example of an ESPHome plant controller: sensors,
actuators, interlocks and a touch interface.

---

Have another use in mind? Tell us in Discussions.
