# Casi d'uso

*[English](use-cases.md)*

La scheda è nata per una piscina privata, ma nulla in essa è specifico di una
sola. Queste sono le situazioni in cui si adatta e cosa serve. Solo la prima è
stata provata nella pratica; le altre sono idee non ancora verificate.

## Piscina privata, tutto automatico
Il caso di progetto: pH e cloro mantenuti nel range, filtrazione alla velocità
giusta tramite inverter, cascata e getti dal touch panel.
*Serve:* sonde pH e ORP, due pompe dosatrici, un sensore di portata, un inverter
(facoltativo).

## Piscina già esistente, con un regolatore semplice
Si tengono le pompe e si aggiungono solo misura e protezioni: la scheda legge,
mostra e avvisa, e sei tu a decidere quando lasciarla dosare.
*Serve:* sonde e sensore di portata; le uscite di dosaggio possono restare
scollegate.

## Piscina condominiale o piccola pubblica
Più acqua, più rischio: due sonde per ogni grandezza si controllano a vicenda e il
dosaggio si ferma se non concordano. Un registro delle letture è utile al gestore.
*Serve:* le sonde secondarie sugli ingressi 4-20 mA e una connessione di rete.

## Hotel, camping o casa vacanze
Visibilità da remoto (Wi-Fi, Home Assistant), allarmi per prodotto in esaurimento
o pressione alta e uno stato sicuro se non c'è nessuno.
*Serve:* accesso di rete e configurazione delle notifiche.

## Spa, idromassaggio o piscina wellness
Stessa chimica, volume minore, limiti più stretti: si regolano le soglie e la
durata dell'impulso di dosaggio.

## Giochi d'acqua e laghetti
Le quattro uscite per valvole possono comandare da sole una cascata, dei getti o
dei nebulizzatori; utile per laghetti naturali con filtro e pompa.

## Acquacoltura, vasche e trattamento acqua
pH, ORP, temperatura e livello su una sola scheda, con relè per una dosatrice o un
aeratore. Valgono le stesse idee di firmware.

## Studio e prototipazione
Un esempio completo, documentato e aperto di controllore d'impianto in ESPHome:
sensori, attuatori, interblocchi e interfaccia touch.

---

Hai in mente un altro uso? Scrivilo nelle Discussions.
