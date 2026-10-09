# Ingressi, uscite e funzioni

*[English](io-map.md)*

Inventario della scheda di acquisizione e controllo. La scheda del pannello è
separata e porta solo il display, il suo controller touch e il link seriale.

### Ingressi analogici

| Funzione | Tipo | Canali | Interfaccia | Indirizzo |
|---|---|---|---|---|
| pH primario | Potenziometrico | 1 | Fronte OPA2338 → ADS1115 | 0x48 A0 |
| ORP primario | Potenziometrico | 1 | Fronte OPA2338 → ADS1115 | 0x48 A1 |
| Pressione filtro | 0-10 V | 1 | Partitore → ADS1115 | 0x48 A3 |
| Riserva | 0-10 V | 1 | Partitore → ADS1115 | 0x48 A2 |
| Loop di corrente | 4-20 mA | 6 | INA3221 × 2 su shunt da 5,6 Ω | 0x40, 0x41 |

Il fronte potenziometrico ha bisogno di una rail negativa per l'amplificatore,
prodotta in locale da una pompa di carica. Due dei sei loop sono usati per i
trasmettitori secondari di pH e ORP; quattro sono liberi.

### Ingressi digitali e di conteggio

| Funzione | Tipo | Canali | Interfaccia | Pin |
|---|---|---|---|---|
| Temperatura acqua | 1-Wire | 1+ | DS18B20 | GPIO5 |
| Livello fusti | Tempo di volo | 3 | TRIG comune, tre ECHO | GPIO4 / 41, 40, 39 |
| Contatti puliti | Digitale | 16 | MCP23017 con pull-up da 4,7 kΩ | 0x20 |
| Catena di emergenza | Digitale con fotoaccoppiatore | 1 | PC817 | GPIO21 |
| Flussimetri | Conteggio impulsi | 2 | PC817 | GPIO48, GPIO47 |
| Interrupt espansore | Digitale | 1 | MCP23017 INTA, attivo basso | GPIO6 |

Il bus 1-Wire regge più sensori sullo stesso pin; il firmware legge oggi una sola
temperatura (la vasca). Cinque dei sedici contatti puliti sono usati: tre
galleggianti dei fusti e due posizioni del selettore.

### Uscite

| Funzione | Tipo | Canali | Interfaccia | Pin |
|---|---|---|---|---|
| Relè | Contatto pulito | 4 | Driver + relè | GPIO18, 7, 17, 10 |
| Elettrovalvole | MOSFET, lato basso | 4 | Gate driver UCC27517 + MOSFET | GPIO14, 13, 12, 11 |

Tre relè sono per il dosaggio e uno per la filtrazione; uno dei tre relè di
dosaggio è di riserva, come la quarta elettrovalvola. Le valvole restano su GPIO
veri e non su un espansore per poterle modulare.

### Bus

| Funzione | Interfaccia | Pin |
|---|---|---|
| RS-485 verso l'inverter | MAX3485, master Modbus RTU | GPIO1 / 2 / 42 |
| UART verso il pannello | TTL diretta, 115200 8N1 | GPIO15 / 16 |
| I²C | MCP23017, ADS1115, 2× INA3221, MCP4018 | GPIO8 / 9 |

L'inverter è un Toshiba VF-S15. Il protocollo del link verso il pannello è
documentato in [`uart-protocol.it.md`](uart-protocol.it.md).

### Limiti noti

Vedi [limitations.it.md](limitations.it.md).
