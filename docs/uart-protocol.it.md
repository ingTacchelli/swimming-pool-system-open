# Protocollo UART fra scheda di controllo e pannello

*[English](uart-protocol.md)*

## Collegamento fisico

UART diretta, 3 fili (TX, RX, GND), **incrociati**: il TX di una va sull'RX
dell'altra.

| | scheda di controllo | pannello (Waveshare 7B) |
|---|---|---|
| TX | GPIO15 | **GPIO43** — header H3 pin 4 (EX_TXD) |
| RX | GPIO16 | **GPIO44** — header H3 pin 3 (EX_RXD) |
| GND | massa comune | header H3 pin 2 |

Sullo schematico Waveshare, foglio 1, la tabella di allocazione assegna IO15 a
RS485_TX e IO16 a RS485_RX: quei due pin vanno all'SP3485 e non sono disponibili
come TTL sul pannello. L'unica UART TTL portata fuori è UART0 su GPIO43/44, che
attraversa U13 (FSUSB42UMX, commutatore 2:1) e finisce o sul ponticello
USB-seriale CH343P di bordo o sull'header H3, secondo la posizione di **SW1**,
che va tenuto su H3. Il pin 1 di H3 è un'uscita 3V3 e va lasciato libero.

Conseguenza per il firmware del pannello: il logger ESPHome deve stare su
`hardware_uart: USB_SERIAL_JTAG`, altrimenti occupa UART0 insieme al link. La
console si legge dall'altra USB-C, quella nativa.

Al reset il bootloader ROM del pannello stampa una riga su GPIO43 a 115200. È
innocua: non inizia per `S`, `A` o `C` e comunque non supera il controllo del
checksum.

Parametri: **115200 baud, 8N1**, nessun controllo di flusso. Il cavo è corto
(stesso contenitore), quindi non serve differenziale.

## Principio

Il pannello non decide mai: **chiede**. La scheda di controllo è l'unica che
conosce lo stato reale e che valuta gli interblocchi; il pannello disegna quello
che riceve e invia richieste. Nessuno stato "vero" vive nel pannello.

Tre tipi di messaggio, tutti in ASCII, una riga per messaggio terminata da `\n`,
campi separati da `|`, checksum XOR finale.

## Formato

```
<TIPO>|<chiave>=<valore>|<chiave>=<valore>|...|*<XX>\n
```

`*XX` è lo XOR di tutti i caratteri che precedono l'asterisco, in esadecimale
maiuscolo a due cifre. Un messaggio con checksum errato viene scartato senza
risposta.

### S — stato (controllo → pannello), ogni 500 ms

| chiave | significato | esempio |
|---|---|---|
| `mo` | modalità selettore: `A` auto, `M` manuale, `0` zero | `mo=A` |
| `tv` / `tc` | temperatura vasca / cella, °C | `tv=27.4` |
| `ph` / `ps` | pH primario / secondario | `ph=7.22` |
| `or` / `os` | ORP primario / secondario, mV | `or=712` |
| `hz` / `cu` | frequenza e corrente VFD | `hz=42.0` |
| `pu` | pompa filtrazione in marcia (0/1) | `pu=1` |
| `q1` / `q2` | portata principale / cella, m³/h | `q1=14.2` |
| `l1`..`l3` | livello fusti 1-3, % | `l1=72` |
| `f1`..`f3` | galleggianti minimo fusti 1-3 (1 = prodotto presente) | `f1=1` |
| `ev` | stato 4 elettrovalvole, 4 cifre | `ev=1100` |
| `do` | dosaggio abilitato (0/1) | `do=1` |
| `cs` | consensi soddisfatti su 13 | `cs=13` |
| `al` | allarmi attivi (numero) | `al=0` |

Il valore `-999` significa "non valido". Il firmware attuale riporta sempre `tc`
come -999: la temperatura della cella non è ancora letta.

Esempio completo:

```
S|mo=A|tv=27.4|tc=26.9|ph=7.22|ps=7.18|or=712|os=706|hz=42.0|cu=3.8|pu=1|q1=14.2|q2=2.1|l1=72|l2=58|l3=91|f1=1|f2=1|f3=1|ev=1100|do=1|cs=13|al=0|*64
```

Se il pannello non riceve un `S` valido per **3 secondi**, dichiara i dati non
aggiornati (tutti i valori in grigio, banda "collegamento perso") e blocca i
comandi.

### C — comando (pannello → controllo)

| chiave | significato |
|---|---|
| `n` | numero progressivo del comando, 1-999, serve per l'ack |
| `c` | comando |
| `v` | valore |

Comandi:

| `c` | `v` | effetto |
|---|---|---|
| `pump` | `0` / `1` | arresto / avvio pompa filtrazione |
| `hz` | `25.0`..`50.0` | frequenza richiesta al VFD |
| `ev1`..`ev4` | `0` / `1` | chiusura / apertura elettrovalvola |
| `dosa` `dosc` `dosr` | `1`..`60` | jog dosaggio acido / cloro / riserva, in secondi |
| `filt` | `0` / `1` | relè filtrazione |
| `scen` | `norm` `int` `sil` `heat` `play` `frost` | scenario di filtrazione |
| `back` | `1` / `0` | avvio / interruzione controlavaggio |
| `ackal` | `1` | tacita gli allarmi attivi |

Esempio: `C|n=17|c=pump|v=0|*2B`

### A — risposta (controllo → pannello)

`r=ok` se il comando è stato accettato ed eseguito, `r=err` altrimenti, con `w=`
che porta il motivo del rifiuto, da mostrare all'utente così com'è.

```
A|n=17|r=ok|*23
A|n=18|r=err|w=selector not in MANUAL|*26
```

Il pannello considera il comando fallito se non riceve l'ack entro **2 secondi**,
e lo segnala invece di far finta che sia andato a buon fine.

## Motivi di rifiuto

Le stringhe dei motivi sono in inglese, come appaiono sul pannello.

- `selector not in MANUAL` — comando manuale con selettore in AUTO o 0
- `selector in ZERO` — qualunque comando con il selettore a 0
- `dosing blocked` — manca almeno un consenso (riservato, non ancora emesso dal firmware attuale)
- `procedure in progress` — controlavaggio o lavaggio filtro attivi
- `blocking alarm` — allarme che impedisce quella manovra (riservato, non ancora emesso)
- `VFD unreachable` — timeout Modbus verso l'inverter (riservato, non ancora emesso)
- `frequency out of range`, `duration out of range` — valore fuori dai limiti
- `acid tank empty`, `chlorine tank empty`, `reserve tank empty` — galleggiante del fusto al minimo
- `unknown command`, `unknown valve` — comando o valvola non riconosciuti

## Nota di sicurezza

Questo canale non fa parte della catena di sicurezza. L'arresto di emergenza è
hardware e indipendente: se il pannello o questa UART smettono di funzionare,
l'impianto deve restare in uno stato sicuro senza il loro intervento.
