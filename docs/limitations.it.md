# Limitazioni note

*[English](limitations.md)*

La Rev A funziona. Questi sono i suoi limiti noti; sono i principali candidati
per la revisione successiva.

## Hardware

- **Nessun orologio tamponato.** L'ora arriva solo da SNTP e si perde senza rete,
  quindi i timer settimanali non reggono fuori linea.
- **Nessuna uscita analogica.**
- **Una sola porta RS-485.**
- **Protezione dalle sovratensioni limitata.** C'è un diodo TVS sull'ingresso a
  24 V (SMBJ30A) e sulla coppia RS-485 (SMAJ12CA); le altre linee che escono dal
  quadro — ingressi dei sensori, uscite dei relè e delle valvole — non hanno
  protezione dalle sovratensioni.
- **Il fronte di campo è riferito alla massa di scheda.** Non c'è isolamento
  galvanico: i fotoaccoppiatori degli ingressi catena di emergenza e portata
  condividono la massa di scheda da entrambi i lati. L'elettrodo di riferimento
  del pH è immerso nella stessa acqua della cella di elettrolisi.

## Firmware

- **La temperatura della cella non è letta.** Il bus 1-Wire regge più sensori, ma
  il firmware ne legge uno (la vasca); `tc` nel protocollo del pannello è sempre
  -999.
- **Il pannello mostra solo il numero di allarmi attivi**, non l'elenco.
- **Lo stato delle valvole sul pannello** è il campo `ev` ricevuto dalla scheda di
  controllo, non la posizione dell'ultimo pulsante premuto.
- **Il potenziometro digitale MCP4018** (riferimento velocità VFD, CN6) è montato
  ma non usato: l'inverter si comanda via Modbus.
- **Registri dell'inverter.** La scala del registro della corrente di uscita
  (FD03) e il bit di marcia di FA00 vanno verificati sul proprio drive (vedi
  [bring-up.it.md](bring-up.it.md)).
- **La calibrazione non è fatta in fabbrica.** Finché non si esegue la calibrazione a due
  punti dal pannello, i coefficienti sono segnaposto e il dosaggio resta bloccato.
- **Fondo scala pressione** (4 bar a 20 mA) è un'ipotesi: va confermato sul
  datasheet del trasmettitore.
- **Scenari.** Il comando `scen` esiste sul pannello ma la scheda non lo implementa
  ancora; usa il programmatore.
- **Programmatore e orologio.** I programmi dipendono dall'ora SNTP (vedi il limite
  dell'orologio sopra); la modalità shock non viene salvata in flash di proposito.
- **PIN impostazioni di default 1234**: cambia `settings_pin` prima dell'uso.
- **Refresh del display.** Il componente del pannello usa un solo framebuffer,
  quindi una parte degli artefatti nel refresh è inevitabile per costruzione.
  Per eliminarli serve una copia locale del componente con doppio framebuffer.
- **Lo storico di Trends è volatile.** I grafici della pagina Trends tengono i
  campioni in RAM: un riavvio li svuota e nulla viene salvato o esportato. Sono
  disegnati da codice, fuori dallo schema LVGL di ESPHome; dopo aver aperto la
  pagina controlla il log di avvio per errori di allocazione (vedi
  [bring-up.it.md](bring-up.it.md)).
- **Lingue.** Nomi delle entità e messaggi della scheda sono in inglese; il pannello
  offre inglese e italiano (Impostazioni), con l'inglese come predefinito al primo avvio.
