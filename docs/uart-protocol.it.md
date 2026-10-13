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
che riceve e invia richieste. Nessuno stato "vero" vive nel pannello. Parametri
modificabili, calibrazione e programma di filtrazione vivono sulla scheda di
controllo e sono salvati nella sua flash; il pannello li mostra e chiede di
cambiarli.

Cinque tipi di messaggio, tutti in ASCII, una riga per messaggio terminata da `\n`,
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
| `ev` | stato delle 4 uscite (EV1-EV3 valvole, EV4 illuminazione piscina), 4 cifre | `ev=1100` |
| `do` | dosaggio abilitato (0/1) | `do=1` |
| `cs` | consensi soddisfatti su 13 | `cs=13` |
| `al` | allarmi attivi (numero) | `al=0` |
| `cb` | i 13 consensi C01..C13, un carattere ciascuno (`1` = soddisfatto) | `cb=1111111111111` |
| `pa` / `pb` / `dd` | pressione filtro a monte / a valle / differenziale, bar | `dd=0.23` |
| `lc` | lavaggio consigliato (0/1) | `lc=0` |
| `dt` | data e ora locali della scheda `YYYYMMDDHHMM`, `0` se l'ora non è sincronizzata | `dt=202610131715` |

Il valore `-999` significa "non valido". Il firmware attuale riporta sempre `tc`
come -999: la temperatura della cella non è ancora letta. Il pannello ignora un
`cb` che non sia lungo esattamente 13 caratteri.

`lc` vale 1 con la pompa in marcia, nessun controlavaggio in corso e il
differenziale sopra la soglia (`dl`, default 0,50 bar) per 5 minuti; cade dopo
30 s sotto soglia.

Esempio completo:

```
S|mo=A|tv=27.4|tc=-999.0|ph=7.22|ps=7.18|or=712|os=706|hz=42.0|cu=61.0|pu=1|q1=14.2|q2=2.1|l1=72|l2=58|l3=91|f1=1|f2=1|f3=1|ev=1100|do=1|cs=13|al=0|cb=1111111111111|pa=1.85|pb=1.62|dd=0.23|lc=0|dt=202610131715|*4C
```

Se il pannello non riceve un `S` valido per **3 secondi**, dichiara i dati non
aggiornati (tutti i valori in grigio, banda "collegamento perso") e blocca i
comandi.

### P — parametri e calibrazione (controllo → pannello), ogni 2 s e dopo ogni comando di impostazione

| chiave | significato |
|---|---|
| `fp` / `fc` | flusso minimo, circuito principale / cella di misura (m³/h) |
| `dp` / `do` | discordanza massima fra le due sonde pH / ORP |
| `fn` | frequenza normale della pompa (Hz) |
| `dl` | differenziale del filtro oltre cui si consiglia il lavaggio (bar) |
| `vp` / `vo` | tensione media della sonda pH / ORP (V), `-999` = non disponibile |
| `cp` / `co` | calibrazione pH / ORP valida (0/1) |
| `np` / `no` | primo punto di calibrazione in sospeso (0/1) |
| `bp` / `bo` | buffer del punto in sospeso |
| `mp` / `mr` | pendenza della retta in uso (pH/V, mV/V) |

```
P|fp=5.00|fc=0.30|dp=0.30|do=40|fn=42.0|vp=1.2043|vo=0.7360|cp=1|co=1|np=0|bp=0.00|no=0|bo=0|mp=-3.412|mr=962.500|dl=0.50|*37
```

Il pannello non usa `P` per sorvegliare il collegamento (resta l'`S` ogni 500
ms). Se non arriva un `P` da 6 s le pagine Parametri e Calibrazione mostrano `--`.

### G — programma di filtrazione (controllo → pannello), ogni 2 s e dopo ogni `set`

| chiave | significato |
|---|---|
| `pr` | programma: 0 spento, 1 giornaliero, 2 settimanale, 3 invernale |
| `mo` | modo: 0 elevata, 1 normale, 2 blanda |
| `fv` | fotovoltaico (0/1): filtrazione solo nella fascia diurna `vi`..`vf` |
| `sh` | filtrazione shock (0/1): filtrazione continua, non salvata in flash |
| `in` / `fi` | fascia normale (minuti dalla mezzanotte, default 08:00-22:00) |
| `vi` / `vf` | fascia diurna per il fotovoltaico (default 08:00-19:00, fissa: il sole non è misurato) |
| `h0`..`h6` | minuti di filtrazione di ogni giorno (lunedì = 0), calcolati dalla scheda da programma + modo |
| `ac` / `tg` | minuti di marcia oggi / target di oggi |
| `st` | 0 spento, 1 fuori fascia, 2 in corso, 3 target raggiunto, 4 selettore non in AUTO, 5 ora non disponibile, 6 target zero, 7 shock in corso |

Ore al giorno: giornaliero elevata 8, normale 5, blanda 3; settimanale lun-ven
7/5/3 e sab-dom 10/8/5; invernale 4/3/2. Il programma comanda la pompa solo con
selettore in AUTO e fuori dal controlavaggio; in MANUALE/ZERO non fa nulla e non
spegne mai una pompa avviata dall'operatore. Il tempo accumulato si azzera a
mezzanotte e a ogni riavvio della scheda.

```
G|pr=2|mo=1|fv=0|sh=0|in=480|fi=1320|vi=480|vf=1140|h0=300|h1=300|h2=300|h3=300|h4=300|h5=480|h6=480|ac=125|tg=300|st=2|*7D
```

### C — comando (pannello → controllo)

| chiave | significato |
|---|---|
| `n` | numero progressivo del comando, 1-999, serve per l'ack |
| `c` | comando |
| `v` | valore |

Comandi:

| `c` | `v` | effetto |
|---|---|---|
| `pump` | `0` / `1` | arresto / avvio pompa filtrazione (l'arresto usa il comando di marcia, non un riferimento a 0 Hz) |
| `hz` | `25.0`..`50.0` | frequenza richiesta al VFD |
| `ev1`..`ev4` | `0` / `1` | chiusura / apertura elettrovalvola (`ev4` = illuminazione piscina) |
| `dosa` `dosc` `dosr` | `1`..`60` | jog dosaggio acido / cloro / riserva, in secondi |
| `filt` | `0` / `1` | relè filtrazione |
| `scen` | `norm` `int` `sil` `risc` `gioco` `gelo` | scenario di filtrazione — **non implementato sulla scheda di controllo**: risponde `unknown command` |
| `back` | `1` / `0` | avvio / interruzione controlavaggio |
| `ackal` | `1` | tacita gli allarmi attivi |
| `set` | `chiave:valore` | cambia un parametro (vedi sotto) |
| `rst` | `par` | riporta i parametri ai valori di compilazione |
| `calp` | pH del buffer | acquisisce un punto di calibrazione pH (solo MANUALE) |
| `calo` | mV del buffer | acquisisce un punto di calibrazione ORP (solo MANUALE) |
| `calc` | `p` oppure `o` | annulla il primo punto in sospeso |

Chiavi di `set`:

| chiave | parametro | intervallo |
|---|---|---|
| `fp` / `fc` | flusso minimo principale / cella (m³/h) | 0..100 / 0..20 |
| `dp` / `do` | discordanza massima pH / ORP | 0,05..2 / 5..300 |
| `fn` | frequenza normale pompa (Hz) | `freq_min_hz`..`freq_max_hz` |
| `dl` | differenziale di lavaggio (bar) | 0,1..3,0 |
| `gpr` / `gmo` | programma / modo dello scheduler | 0..3 / 0..2 |
| `gfv` / `gsh` | fotovoltaico / shock | 0/1 |
| `gin` `gfi` `gvi` `gvf` | inizio/fine fascia (minuti dalla mezzanotte) | 0..1439 |

I valori di partenza dei parametri vengono dalle substitutions di
`spb-control.yaml` **solo alla primissima accensione**; dopo, il valore vivo è
quello salvato in flash (`rst|par` riporta quelli di compilazione).

Calibrazione a due punti: il primo punto (`calp` / `calo`) non cambia la
calibrazione in uso e scade dopo 10 minuti; al secondo punto la retta viene
ricalcolata e dichiarata valida, se i controlli passano (sonda stabile, buffer e
tensione diversi dal primo punto, pendenza plausibile).

Esempio: `C|n=21|c=set|v=fp:6.5|*65`

### A — risposta (controllo → pannello)

`r=ok` se il comando è stato accettato ed eseguito, `r=err` altrimenti, con `w=`
che porta il motivo del rifiuto. Il motivo è in inglese; il pannello lo traduce
quando la sua lingua è l'italiano.

```
A|n=17|r=ok|*23
A|n=18|r=err|w=selector not in MANUAL|*26
```

Il pannello considera il comando fallito se non riceve l'ack entro **2 secondi**,
e lo segnala invece di far finta che sia andato a buon fine.

## Motivi di rifiuto

- `selector not in MANUAL` — comando manuale con selettore in AUTO o 0
- `selector in ZERO` — qualunque comando con il selettore a 0
- `procedure in progress` — controlavaggio in corso
- `frequency out of range`, `duration out of range`, `value out of range` — valore fuori dai limiti
- `invalid value`, `unknown parameter`, `unknown reset` — `set` / `rst` malformati
- `acid drum empty`, `chlorine drum empty`, `reserve drum empty` — galleggiante del fusto al minimo
- `invalid buffer value`, `buffer out of range`, `probe has no reading`, `unstable reading`, `buffer same as first point`, `voltage same as first point`, `abnormal slope`, `unknown probe` — rifiuti della calibrazione
- `unknown command`, `unknown valve` — comando o valvola non riconosciuti

## Nota di sicurezza

Questo canale non fa parte della catena di sicurezza. L'arresto di emergenza è
hardware e indipendente: se il pannello o questa UART smettono di funzionare,
l'impianto deve restare in uno stato sicuro senza il loro intervento.
