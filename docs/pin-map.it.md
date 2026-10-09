# Schema dei pin

*[English](pin-map.md)*

![Schema dei pin](pin-map.svg)

La regola dietro questa allocazione: un segnale resta su un pin del
microcontrollore solo se ha un vincolo di tempo che il processore deve
rispettare di persona. Tutto il resto — contatti, letture analogiche, loop di
corrente — passa dietro il bus I²C, dove aggiungere un canale costa un
connettore e non un pin.

Restano così 24 segnali sull'ESP32-S3, e tutta la UART0 libera come console di
servizio.

## Microcontrollore

| Pin | Direzione | Funzione | Note |
|---|---|---|---|
| GPIO1 | out | RS-485 TX | verso l'inverter |
| GPIO2 | out | RS-485 DE / RE | abilitazione trasmissione |
| GPIO4 | out | TRIG ultrasuoni | in comune ai tre sensori |
| GPIO5 | bidir | 1-Wire | bus temperature DS18B20 |
| GPIO6 | in | Interrupt MCP23017 | attivo basso, INTA e INTB in OR |
| GPIO7 | out | Relè — dosaggio cloro | connettore CN18 |
| GPIO8 | bidir | I²C SDA | |
| GPIO9 | out | I²C SCL | |
| GPIO10 | out | Relè — filtrazione | connettore CN9 |
| GPIO11 | out | Elettrovalvola EV4 | di riserva |
| GPIO12 | out | Elettrovalvola EV3 | |
| GPIO13 | out | Elettrovalvola EV2 | |
| GPIO14 | out | Elettrovalvola EV1 | |
| GPIO15 | out | UART TX | verso il pannello |
| GPIO16 | in | UART RX | dal pannello |
| GPIO17 | out | Relè — dosaggio riserva | connettore CN7 |
| GPIO18 | out | Relè — dosaggio acido | connettore CN8 |
| GPIO21 | in | Ingresso optoisolato | catena di emergenza; contatto chiuso = ingresso alto |
| GPIO39 | in | ECHO ultrasuoni 3 | fusto di riserva |
| GPIO40 | in | ECHO ultrasuoni 2 | fusto cloro |
| GPIO41 | in | ECHO ultrasuoni 1 | fusto acido |
| GPIO42 | in | RS-485 RX | dall'inverter |
| GPIO47 | in | Conteggio impulsi | portata cella di misura |
| GPIO48 | in | Conteggio impulsi | portata circuito principale |
| GPIO43 / GPIO44 | — | UART0 | lasciata libera, console di servizio |

Pin liberi: GPIO3, 35, 36, 37, 38, 46.

Quattro dettagli da sapere prima di copiare questo schema.

**Connettori dei relè.** Il firmware associa i relè di dosaggio per sigla del
connettore: CN8 = acido, CN18 = cloro, CN7 = riserva, CN9 = filtrazione.
Verifica che il testo stampato accanto a ogni connettore sul tuo PCB sia
coerente con questa tabella prima di collegare una pompa (vedi la
[checklist](bring-up.it.md)).

**Pin ECHO.** Gli ECHO degli ultrasuoni sono siglati IN1, IN2 e IN3 sullo schema,
da un piano precedente in cui erano ingressi digitali generici. Il firmware li
usa come ritorni di eco. I sensori sono a 5 V, quindi ogni linea di eco sta
dietro un partitore 4,7 kΩ / 10 kΩ che porta il livello a 3,40 V.

**GPIO48** pilota il LED RGB di stato sulle DevKitC-1 di revisione 1.0. Qui
conta impulsi di portata, cosa che come ingresso va benissimo, ma quel LED non è
utilizzabile.

**GPIO2** tiene l'abilitazione di trasmissione del transceiver RS-485. Fra
l'accensione e il momento in cui il firmware prende il pin, il MAX3485 sta dove
lo mette la sua resistenza di polarizzazione: verifica sulla tua scheda che sia
lo stato di ricezione (R63 deve essere un pull-down verso massa) prima di
fidarti del bus all'avvio.

## Bus I²C

Cinque dispositivi (MCP23017, ADS1115, due INA3221 e un potenziometro digitale
MCP4018), 100 kHz, su GPIO8 e GPIO9.

| Indirizzo | Dispositivo | Uso |
|---|---|---|
| 0x20 | MCP23017 | 16 ingressi a contatto pulito, 5 usati |
| 0x2F | MCP4018 | potenziometro digitale, riferimento velocità VFD (CN6) |
| 0x48 | ADS1115 | 4 canali analogici, 16 bit, fondo scala 4,096 V |
| 0x40 | INA3221 #1 | loop di corrente da 1 a 3 |
| 0x41 | INA3221 #2 | loop di corrente da 4 a 6 |

L'MCP4018 è montato sulla scheda ma il firmware non lo usa.

### MCP23017 — 0x20

| Pin | Segnale |
|---|---|
| GP0 | Galleggiante di minimo, fusto acido |
| GP1 | Galleggiante di minimo, fusto cloro |
| GP2 | Galleggiante di minimo, fusto di riserva |
| GP3 | Selettore in AUTO |
| GP4 | Selettore in MANUALE |

Gli ingressi sono tirati in alto sulla scheda e letti invertiti, quindi un
contatto chiuso verso massa significa "prodotto presente" o "selettore in questa
posizione". Nessuna posizione asserita vuol dire selettore a ZERO: il firmware
deriva quel terzo stato invece di cablare un terzo contatto. I galleggianti sono
filtrati a 500 ms, il selettore a 100 ms.

Gli altri undici pin escono sui connettori da CN19 a CN22 e sono liberi. I
pull-up da 4,7 kΩ in scheda sono sugli otto ingressi GPA: controlla lo schema
prima di usare gli ingressi GPB.

### ADS1115 — 0x48

| Canale | Segnale |
|---|---|
| A0 | pH, tensione grezza dal fronte OPA2338 |
| A1 | ORP, tensione grezza |
| A2 | CN12 canale 2 — riserva, esposto come tensione grezza |
| A3 | CN12 canale 1 — pressione filtro, 0-10 V |

I due canali di CN12 passano per un partitore 0,4005, e ciascuno ha i ponticelli
che lo convertono in un ingresso 4-20 mA su un carico da 205 Ω, se lì preferisci
un loop di corrente.

L'ADS1115 è alimentato a 5 V mentre il bus è a 3,3 V, un po' sotto il livello
alto di ingresso richiesto (0,7 × VDD). Se compaiono letture erratiche o NAK sul
bus, è il primo posto dove guardare.

### INA3221 — 0x40 e 0x41

Sei ingressi 4-20 mA su shunt da 5,6 Ω. Due sono usati, per i trasmettitori
secondari di pH e ORP; gli altri quattro sono liberi.

## Pannello touch

Il pannello è un Waveshare ESP32-S3-Touch-LCD-7B di serie. Per questo progetto
conta un solo connettore: l'header **H3**, che porta fuori UART0.

| Pin H3 | Segnale | GPIO del pannello |
|---|---|---|
| 1 | 3V3 in uscita | — lasciare libero |
| 2 | GND | — |
| 3 | EX_RXD | GPIO44 |
| 4 | EX_TXD | GPIO43 |

GPIO15 e GPIO16 sul pannello *non* sono disponibili: lo schematico Waveshare li
assegna al transceiver RS-485 SP3485 e non escono mai come TTL. La UART0 arriva a
H3 solo se lo switch **SW1** è su H3 e non sul ponticello USB-seriale CH343P di
bordo.

L'header I²C del pannello su GPIO8 e GPIO9 e il socket micro-SD (MOSI GPIO11, SCK
GPIO12, MISO GPIO13, chip select sull'espansore CH32V003) non sono usati da
questo firmware e restano disponibili.
