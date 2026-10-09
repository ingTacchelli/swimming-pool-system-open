# Hardware

*[Italiano](README.it.md)*

Acquisition and control board, designed in EasyEDA Pro.

| Path | Content |
|---|---|
| `eda/swimming-pool-board.epro2` | native EasyEDA Pro project (schematic + PCB), editable |
| `schematic/schematic.pdf` | schematic, 2 sheets |
| `layout/pcb-front.png`, `layout/pcb-bottom.png` | PCB layout images, front and bottom |
| `assembly/assembly-drawing.pdf` | assembly drawing, 10 pages, with the parts list |
| `fabrication/gerber.zip` | Gerber files, drill files and flying-probe test data |
| `bom.csv` | bill of materials, without prices |
| `enclosure/` | renders of the enclosure: front (display, selector, two buttons and emergency mushroom) and interior (board mounted above the terminal blocks and contact block) |

## Ordering the PCB

Upload `fabrication/gerber.zip` to your PCB manufacturer. It is a two-layer board;
the archive includes a `How-to-order-PCB.txt` that points to the EasyEDA ordering
guide. The parts in `bom.csv` carry the LCSC part number in the `SupplierPart`
column.

## Notes

- Silkscreen labels on the board (connector and relay names) are in Italian.
- The module is an ESP32-S3-DevKitC-1 N16R8 plugged into the board.
- The panel (Waveshare ESP32-S3-Touch-LCD-7B) is a separate off-the-shelf board
  and is not part of this PCB.
- Before wiring pumps, read the notes on the relay connectors in the
  [bring-up checklist](../docs/bring-up.md).
