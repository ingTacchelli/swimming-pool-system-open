# Firmware

*[English](README.md)*

Configurazione ESPHome di entrambe le schede. Due dispositivi distinti, ognuno
con il suo ESP32-S3:

| File | Scheda | Ruolo |
|---|---|---|
| `control/spb-control.yaml` | ESP32-S3-DevKitC-1 (N16R8) sulla PCB custom | legge i sensori, comanda pompe e valvole, parla col VFD, decide gli interblocchi |
| `display/spb-display.yaml` | Waveshare ESP32-S3-Touch-LCD-7B | disegna il pannello touch, invia richieste di comando |

Le due schede sono collegate solo da una UART a 3 fili (TX/RX/GND, 115200 8N1). Il
formato dei messaggi è in [`../docs/uart-protocol.it.md`](../docs/uart-protocol.it.md).

## Struttura

```
control/
  spb-control.yaml              <- da compilare; contiene tutti i valori da tarare
  packages/
    control-base.yaml             framework, rete, servizi, stato sicuro all'avvio
    control-bus-sensors.yaml      I2C, ADS1115, INA3221 x2, MCP23017, 1-Wire, flussi, livelli
    control-outputs.yaml           relè dosaggio, relè filtrazione, elettrovalvole, jog
    control-vfd-modbus.yaml       Toshiba VF-S15 su RS-485 Modbus RTU
    control-logic.yaml           calibrazioni, 13 consensi al dosaggio, controlavaggio, autonomia
    control-link-display.yaml     protocollo UART, lato scheda di controllo
display/
  spb-display.yaml              <- file unico: pannello, touch, link UART, LVGL (7 pagine)
simulator/
  spb_simulator.py              simula la scheda di controllo con un adattatore USB-seriale
secrets.yaml.example            <- copiare in secrets.yaml e compilarlo
```

## Prima compilazione

```bash
cp secrets.yaml.example secrets.yaml     # poi compilarlo per davvero
cp secrets.yaml control/secrets.yaml
cp secrets.yaml display/secrets.yaml
cd control && esphome config spb-control.yaml && esphome run spb-control.yaml
cd ../display && esphome config spb-display.yaml && esphome run spb-display.yaml
```

Entrambi i file passano `esphome config` con ESPHome 2026.9.1. `secrets.yaml` è
ignorato da git: non va mai committato. I font del display vengono scaricati da
Google Fonts in compilazione, quindi la macchina di build deve avere accesso a
internet.

## Cosa va tarato prima di usarlo

Tutti i valori stanno in cima a `spb-control.yaml`, nel blocco `substitutions`:

- `shunt_4_20ma` — 5.6 ohm
- `cn12_ratio`, `cn12_full_scale_v`, `pressure_full_scale_bar` — ingresso
  0-10 V della pressione; se chiudi i ponticelli per il 4-20 mA va riscritta la
  lambda di `filter_pressure`
- `k_factor_pulses_per_litre` — impulsi/litro del tuo flussometro
- `tank_empty_m`, `tank_full_m`, `tank_litres` — geometria dei fusti misurata a mano
- `dosing_pump_litres_per_s` — portata della pompa dosatrice, per l'autonomia
- `freq_*_hz` — limiti e frequenza normale della pompa di filtrazione
- soglie di discordanza delle sonde e di flusso minimo

Inoltre: gli indirizzi dei DS18B20 vanno letti dal log del primo avvio e scritti in
`control-bus-sensors.yaml`, e i coefficienti di calibrazione pH/ORP (`cal_ph_slope`,
`cal_ph_offset`, `cal_orp_slope`, `cal_orp_offset` in `control-logic.yaml`) vanno ricavati da
una calibrazione a due punti con le soluzioni tampone. L'elenco completo dei
controlli è nella [checklist di prima accensione](../docs/bring-up.it.md).

## Misure di sicurezza presenti

- Le uscite partono **spente** e c'è uno script `go_to_safe_state` esplicito.
  I gate hanno anche pull-down hardware, quindi la protezione è doppia.
- Il dosaggio manuale è sempre a impulso con durata massima (`jog_max_ms`): non
  esiste un ON continuo comandabile dal touch.
- I comandi dal pannello vengono **verificati dalla scheda di controllo**, che può
  rifiutarli restituendo il motivo; il pannello non decide nulla da solo.
- Se la UART cade, il pannello dichiara i dati non aggiornati e blocca i comandi.
- Nessuna di queste protezioni sostituisce la catena di emergenza hardware, che
  resta indipendente dall'ESP32.

## Note sul pannello

- UART verso la scheda di controllo su GPIO43/44, header H3, con SW1 su H3.
  GPIO15/16 sul 7B sono la coppia RS-485 dell'SP3485 e non escono come TTL. Il
  logger sta su `USB_SERIAL_JTAG` perché UART0 è il link; la console si legge
  dall'USB-C nativa.
- Il pannello è descritto pin per pin con `rpi_dpi_rgb`, senza `model`
  predefinito. Timing verificati: hsync 162/152/48, vsync 45/13/3. Il pixel clock
  è 30 MHz (invertito), il massimo ammesso dal componente: con un quadro da
  1386 × 661 fa 32,7 Hz, mentre 21 MHz darebbero 22,9 Hz.
- **La fluidità dipende da dove disegna LVGL.** `buffer_size: 12%` (un ottavo,
  150 KB) perché ESPHome tenta la SRAM interna solo se la frazione è almeno 1/4, e
  300 KB contigui di SRAM interna non esistono con il Wi-Fi acceso.
  `CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP` sposta i buffer di rete in PSRAM e libera
  RAM interna. Vedi i commenti in `spb-display.yaml` per cosa fare se il log di
  avvio segnala un'allocazione fallita.
- `rpi_dpi_rgb` fissa `num_fbs = 1`, quindi una parte degli artefatti nel refresh
  è inevitabile per costruzione.
- L'espansore CH32V003 usa un componente esterno
  (`github.com/fuzzybear62/esphome-waveshare_io_ch32v003`), bloccato su un
  commit: retroilluminazione regolabile e reset del pannello e del touch.
- Sette pagine LVGL: Home, Filtration, Chemistry, Valves, Alarms, Maintenance,
  Commands. La colonna di navigazione, l'intestazione e la barra di stato
  stanno nel `top_layer`, quindi esistono una volta sola invece di sette. Se un
  giorno il touch smettesse di rispondere sulle pagine, è il primo posto dove
  guardare.
- Si aggiorna solo la pagina visibile, e ogni etichetta viene riscritta solo se il
  testo è cambiato davvero.
