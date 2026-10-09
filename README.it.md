# Swimming Pool Board (SPB) — Rev A

*[English](README.md)*

Scheda di acquisizione e controllo per una piscina privata, con un pannello touch
come interfaccia utente. La scheda legge pH, ORP, pressione, temperatura,
portata, livello dei fusti e contatti puliti, comanda pompe dosatrici,
elettrovalvole e una pompa di filtrazione (direttamente o tramite inverter
Modbus), e applica una serie di consensi prima di permettere qualsiasi
dosaggio. Il pannello chiede soltanto; è la scheda a decidere.

![Contenitore, fronte](hardware/enclosure/render-front.png)

![Schema del sistema](docs/system-overview.svg)

## Stato

La Rev A è la prima emissione pubblica. La scheda è stata progettata, costruita
e fatta funzionare su una piscina vera. Funziona, con i limiti elencati in
[docs/limitations.it.md](docs/limitations.it.md).

È un progetto di livello amatoriale condiviso per studio, feedback e uso non
commerciale. **Non** è certificato secondo alcuna normativa. Vedi l'[avviso di
sicurezza](#avviso-di-sicurezza).

## Cosa fa

| | |
|---|---|
| **Ingressi analogici** | pH e ORP (fronte potenziometrico, OPA2338 → ADS1115), un ingresso 0-10 V (pressione filtro) più uno di riserva, sei loop 4-20 mA (2 × INA3221, shunt da 5,6 Ω) |
| **Ingressi digitali** | bus 1-Wire DS18B20, tre sensori a ultrasuoni per il livello dei fusti, 16 ingressi a contatto pulito (MCP23017), monitor della catena di emergenza con fotoaccoppiatore, due flussimetri a impulsi |
| **Uscite** | 4 relè (3 dosaggio, 1 filtrazione), 4 driver per elettrovalvole sul lato basso, master RS-485 Modbus RTU per inverter Toshiba VF-S15 |
| **Logica** | 13 consensi al dosaggio esposti uno per uno, dosaggio manuale a impulsi con limite di tempo, sequenza di controlavaggio, stato sicuro all'avvio |
| **Pannello** | Waveshare ESP32-S3-Touch-LCD-7B, sette pagine LVGL, dialoga con la scheda su UART a 3 fili |
| **Integrazione** | API nativa ESPHome (Home Assistant è opzionale: l'impianto funziona anche senza) |

## Struttura del repository

| Cartella | Contenuto |
|---|---|
| [`hardware/`](hardware/README.it.md) | progetto EasyEDA Pro, file Gerber, schema elettrico, disegno di montaggio, BOM, immagine del layout, render del contenitore |
| [`firmware/`](firmware/README.it.md) | configurazione ESPHome delle due schede e simulatore Python della scheda di controllo |
| [`docs/`](docs/) | schema dei pin, mappa degli I/O, protocollo UART, limitazioni, checklist di prima accensione |

Ogni documento esiste in inglese e in italiano (`*.it.md`).

## Per iniziare

1. **Hardware** — ordina il PCB dai file Gerber e procura i componenti dalla
   [`hardware/bom.csv`](hardware/bom.csv).
2. **Firmware** — segui [`firmware/README.it.md`](firmware/README.it.md): copia
   `secrets.yaml.example`, regola i valori in cima a `spb-control.yaml`, poi
   `esphome run` per entrambe le schede.
3. **Prima accensione** — percorri la [checklist](docs/bring-up.it.md) prima di
   collegare qualsiasi pompa o valvola.

## Avviso di sicurezza

Questa scheda comanda pompe dosatrici di acido e cloro, elettrovalvole e una
pompa di filtrazione. Un guasto, un errore di cablaggio o di configurazione può
rilasciare prodotti chimici o far girare le apparecchiature a secco.

- La **catena di emergenza è hardware** e indipendente dal firmware. I tredici
  consensi al dosaggio nel firmware sono una comodità, non il sistema di
  sicurezza. Realizza una vera catena di sicurezza hardware.
- Le uscite partono spente e il dosaggio manuale è sempre un impulso a tempo
  limitato. Queste protezioni non sostituiscono la catena di emergenza.
- Il cablaggio a tensione di rete deve essere eseguito da personale qualificato,
  in un contenitore adatto e con le protezioni appropriate.
- Il progetto è fornito senza garanzie di alcun tipo e lo usi a tuo rischio.

## Feedback e interesse commerciale

Il feedback è il motivo per cui il progetto è pubblico.

- Domande, idee e casi d'uso: apri una **Discussion**.
- Errori nello schema, nel layout, nella BOM, nel firmware o nei documenti: apri una **Issue**.
- Richieste commerciali (produzione, rivendita, integrazione, licenza): apri una
  Discussion nella categoria *Commercial*.

Vedi [CONTRIBUTING.md](CONTRIBUTING.md).

## Licenza

Rilasciato con licenza [Creative Commons Attribuzione - Non commerciale -
Condividi allo stesso modo 4.0 Internazionale (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.it).
Vedi [LICENSE](LICENSE). L'uso commerciale non è coperto da questa licenza:
contatta gli autori tramite una Discussion.
