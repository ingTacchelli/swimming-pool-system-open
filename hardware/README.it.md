# Hardware

*[English](README.md)*

Scheda di acquisizione e controllo, progettata in EasyEDA Pro.

| Percorso | Contenuto |
|---|---|
| `eda/swimming-pool-board.epro2` | progetto nativo EasyEDA Pro (schema + PCB), modificabile |
| `schematic/schematic.pdf` | schema elettrico, 2 fogli |
| `layout/pcb-front.png`, `layout/pcb-bottom.png` | immagini del layout del PCB, fronte e retro |
| `assembly/assembly-drawing.pdf` | disegno di montaggio, 10 pagine, con l'elenco dei componenti |
| `fabrication/gerber.zip` | file Gerber, file di foratura e dati del test flying-probe |
| `bom.csv` | distinta base, senza prezzi |
| `enclosure/` | render del contenitore: fronte (display, selettore, due pulsanti e fungo di emergenza) e interno (scheda montata sopra le morsettiere e il blocco contatti) |

## Ordinare il PCB

Carica `fabrication/gerber.zip` presso il tuo produttore di PCB. È una scheda a
due strati; l'archivio contiene un `How-to-order-PCB.txt` che rimanda alla guida
all'ordine di EasyEDA. I componenti in `bom.csv` riportano il codice LCSC nella
colonna `SupplierPart`.

## Note

- Le serigrafie sulla scheda (nomi di connettori e relè) sono in italiano.
- Il modulo è una ESP32-S3-DevKitC-1 N16R8 innestata sulla scheda.
- Il pannello (Waveshare ESP32-S3-Touch-LCD-7B) è una scheda commerciale
  separata e non fa parte di questo PCB.
- Prima di collegare le pompe, leggi le note sui connettori dei relè nella
  [checklist di prima accensione](../docs/bring-up.it.md).
