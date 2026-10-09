# Scheda tecnica — Swimming Pool System Open, Rev A

*[English](datasheet.md)*

Scheda di acquisizione e controllo per il trattamento e la filtrazione dell'acqua
di piscina. Preliminare: i valori marcati **TBC** sono da confermare alla prima
accensione.

![Scheda](../hardware/layout/pcb-front.png)

## In sintesi

| | |
|---|---|
| Controllore | modulo ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM), doppio core, Wi-Fi |
| Scheda | due strati, circa 165 × 94 mm, quattro fori di fissaggio M4 |
| Alimentazione | 24 V DC, protetta da TVS (SMBJ30A) |
| Software | ESPHome (ESP-IDF); API nativa; Home Assistant facoltativo |
| Interfaccia utente | Waveshare ESP32-S3-Touch-LCD-7B, 7", 1024 × 600, touch, collegamento seriale a 3 fili |
| Revisione | Rev A (stampata sulla scheda come "Rev 0.A") |

## Ingressi

| Funzione | Q.tà | Dettagli |
|---|---|---|
| Sonde pH, ORP | 1 + 1 | BNC, stadio potenziometrico (OPA2338), ADS1115 a 16 bit; calibrazione nel firmware |
| Pressione / analogico | 2 | 0-10 V, partitore verso ADS1115 (uno per la pressione del filtro, uno di riserva) |
| Anelli di corrente | 6 | 4-20 mA, INA3221 × 2, shunt da 5,6 Ω; due usati per pH e ORP secondari |
| Temperatura | 1+ | DS18B20 su 1-Wire (il firmware ne legge uno) |
| Livello fusti | 3 | sensori a ultrasuoni tipo JSN-SR04T, trigger comune |
| Minimo fusti | 3 | galleggianti, contatti puliti |
| Contatti puliti | 16 | MCP23017, pull-up da 4,7 kΩ, 5 usati (3 galleggianti, 2 posizioni del selettore) |
| Portata | 2 | ingressi a impulsi, optoisolati (PC817) |
| Catena di emergenza | 1 | ingresso di monitor optoisolato; la catena stessa è hardware |

## Uscite

| Funzione | Q.tà | Dettagli |
|---|---|---|
| Relè | 4 | serie SRD, un contatto in scambio ciascuno (3 dosaggio, 1 filtrazione); portate **TBC** secondo il datasheet del relè e le distanze della scheda |
| Elettrovalvole | 4 | MOSFET low-side con driver di gate (UCC27517), connettore a 5 poli |
| Collegamento inverter | 1 | RS-485 (MAX3485), master Modbus RTU, 19200 bps parità pari, terminazione 120 Ω, protetto da TVS (SMAJ12CA); inverter di riferimento Toshiba VF-S15 |
| Riferimento di velocità | 1 | potenziometro digitale MCP4018 su CN6 (montato, non usato dal firmware) |
| Uscita di stato | 1 | LED OUT (CN4) |

## Comportamento

- 13 consensi al dosaggio, ciascuno visibile; senza tutti soddisfatti non si dosa.
- Il dosaggio manuale è sempre un impulso con durata massima.
- Tutte le uscite partono spente; una catena di emergenza hardware è indipendente dal firmware.
- Il pannello chiede soltanto; la scheda di controllo decide e restituisce il motivo del rifiuto.

## Dati elettrici e ambientali

| | |
|---|---|
| Corrente assorbita | TBC |
| Portata dei contatti dei relè | TBC |
| Corrente delle uscite valvole | TBC |
| Temperatura di funzionamento | TBC (pensata per un quadro asciutto e ventilato) |
| Isolamento | nessuno tra ingressi di campo e massa della scheda (vedi [limiti](limitations.it.md)) |
| Protezioni | TVS su ingresso 24 V e su RS-485; nessuna protezione dalle sovratensioni sulle altre linee di campo |
| Certificazioni | nessuna: progetto amatoriale, vedi l'[avviso di sicurezza](../README.it.md#avviso-di-sicurezza) |

## Documenti

[Mappa dei pin](pin-map.it.md) · [Ingressi e uscite](io-map.it.md) · [Protocollo del pannello](uart-protocol.it.md) ·
[Cablaggio (bozza)](wiring.it.md) · [Checklist di prima accensione](bring-up.it.md) · [Limiti](limitations.it.md)
