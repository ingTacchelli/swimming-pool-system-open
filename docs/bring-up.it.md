# Checklist di prima accensione

*[English](bring-up.md)*

Esegui questi controlli sul banco, **senza pompe, valvole o inverter
collegati**, in quest'ordine.

## Prima di alimentare

1. **Revisione della DevKitC-1.** Guarda la serigrafia del modulo. Sui moduli
   v1.0 GPIO48 pilota il LED RGB; qui porta l'ingresso della portata principale,
   quindi quel LED non è utilizzabile. Verifica che il modulo sia una
   ESP32-S3-DevKitC-1 N16R8.
2. **R63 deve essere un pull-down verso massa**, non un pull-up verso VCC. Con il
   pull-up il MAX3485 parte in trasmissione e il Modbus non parte mai.
3. **Connettori dei relè.** Il firmware associa i relè di dosaggio per sigla del
   connettore: CN8 = acido (GPIO18), CN18 = cloro (GPIO7), CN7 = riserva
   (GPIO17), CN9 = filtrazione (GPIO10). Controlla il testo stampato sul tuo PCB
   accanto a ciascuno di quei connettori e collega le pompe di conseguenza. Se
   vuoi un'associazione diversa, cambia solo i pin in
   `firmware/control/packages/control-outputs.yaml`.
4. **Shunt.** Conferma che gli shunt dei 4-20 mA siano da 5,6 Ω; il valore è
   `shunt_4_20ma` in `spb-control.yaml`.
5. **Ponticelli di CN12.** Senza ponticelli i canali di CN12 sono ingressi 0-10 V.
   Se li chiudi, l'ingresso diventa 4-20 mA e va riscritta la lambda di
   `filter_pressure`.

## Prima accensione

6. **Uscite spente all'avvio.** Con il firmware caricato (e anche durante il
   flash) i quattro relè e i quattro driver delle valvole devono restare spenti.
7. **Scansione I²C.** Il log di avvio deve mostrare 0x20, 0x2F, 0x40, 0x41 e 0x48.
   Letture erratiche o NAK puntano prima di tutto all'ADS1115, che lavora a 5 V su
   un bus a 3,3 V.
8. **Catena di emergenza.** A contatto chiuso l'ingresso di monitor (GPIO21) deve
   leggere alto; staccando il cavo deve leggere catena aperta.
9. **Selettore e galleggianti.** Verifica AUTO / MANUALE / ZERO e i tre
   galleggianti dei fusti dall'interfaccia web.
10. **Sensori a ultrasuoni.** Misura la distanza a fusti vuoti e pieni e imposta
    `tank_empty_m` e `tank_full_m`.
11. **Temperatura.** Leggi gli indirizzi dei DS18B20 dal log del primo avvio e
    scrivili in `control-bus-sensors.yaml`.
12. **pH e ORP.** Esegui una calibrazione a due punti con le soluzioni tampone e
    scrivi i coefficienti (`cal_ph_slope`, `cal_ph_offset`, `cal_orp_slope`, `cal_orp_offset`) in
    `control-logic.yaml`.
13. **Portata.** Imposta `k_factor_pulses_per_litre` per il tuo flussometro e controlla il
    conteggio degli impulsi.

## Con l'inverter (Toshiba VF-S15)

14. Imposta i parametri del drive: `f829 = 1` (Modbus RTU), `f800` / `f801` per
    19200 bps e parità pari.
15. Verifica sul drive reale la scala del registro della corrente di uscita FD03
    (percentuale della corrente nominale impostata in `f601`) e quale bit di FA00
    comanda la marcia avanti. Finché non è confermato, la corrente mostrata è
    indicativa e lo switch di marcia va provato a banco.

## Pannello

16. Metti **SW1** su H3. Verifica che la riga ROM `ESP-ROM:esp32s3-...` compaia al
    reset su un terminale a 115200 collegato a H3.
17. Cerca `Failed to allocate 153600 bytes for internal draw buffer` nel log di
    avvio: se compare, il buffer di disegno è ancora in PSRAM e valgono i
    suggerimenti in `spb-display.yaml`.
18. Il componente esterno `waveshare_io_ch32v003` è bloccato su un commit in
    `spb-display.yaml`; aggiorna il riferimento di proposito, non per caso.
19. Per provare il protocollo prima che la scheda di controllo sia pronta, usa
    `firmware/simulator/spb_simulator.py`.
20. Apri la pagina **Trends** e lasciala qualche minuto: i grafici devono
    iniziare a disegnarsi e il log di avvio non deve segnalare errori di
    allocazione. Con `--demo --speed 90` del simulatore e `trend_interval_s: "2"`
    si riempiono in fretta.

## Prima di qualsiasi dosaggio

21. Fai girare le pompe in manuale, a impulsi a tempo limitato, con acqua, e
    verifica che ogni pompa parta dal connettore previsto.
22. Verifica che la catena di emergenza hardware fermi tutto da sola,
    indipendentemente dal firmware.
