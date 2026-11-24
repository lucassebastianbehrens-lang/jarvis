# Simulations-Videos „Was ist besser?“ – Themen & Regeln

## Regeln gegen Sperren / „unoriginal“
- Jede Folge ist ein **eigenes Thema** mit eigenem Skript, eigenen Zahlen und eigener Grafik (per Code gezeichnet). Nie ein fremdes Video nachbauen, nie Clips anderer Kanäle verwenden.
- Ein Thema, das andere Kanäle auch haben, nur mit **eigenem Blickwinkel** (andere Strecke/Mengen, andere Pointe, eigener Text). Titel und Caption nie 1:1 übernehmen.
- Stimme, Sprechtempo, Farben und Hintergrund wechseln automatisch je Folge (sim.py). Keine Folge gleicht der anderen.
- Jede Zahl braucht eine Quelle (Feld `quelle` im Spec, wird in die Beschreibung geschrieben). Lieber runde, vorsichtige Werte als falsche.
- KI-Kennzeichnung bei TikTok immer an. Familienfreundlich, keine Marken/Logos, keine echten Personen.
- Erledigte Themen unten abhaken – nichts doppelt.

## Spec-Format (generisch)
`modell.typ = "generisch"`, je Seite `a`/`b`: `name`, `figur` (geher|laeufer|auto|rad), `dauer_s` (wie lange es in der Simulation dauert), `menge` (Endwert), `info` (kleine Zeile).
`modell.einheit`, `modell.zaehler` (z. B. „Liter“), `modell.besser` (weniger|mehr), optional `modell.wetter = "regen"`, `skala` (3 Beschriftungen), `ergebnis` ("{p} % weniger …").
`lines` mit `phase` intro → race → result (die Rennen-Phase bestimmt das Tempo der Animation).

## Themen-Pool
- [x] Rennen vs Gehen im Regen – wer wird weniger nass? (sim-01)
- [x] Treppe vs Aufzug – 5 Stockwerke, was ist schneller? (sim-02)
- [ ] Auto vs Fahrrad in der Stadt – 5 km im Berufsverkehr
- [ ] Wasserkocher vs Herd – 1 Liter Wasser, Zeit & Strom
- [ ] Fön vs Lufttrocknen – Haare, Zeit & Strom
- [ ] Spülmaschine vs Handspülen – Wasser pro Ladung
- [ ] Laden vs Tanken – 100 km E-Auto vs Benziner, Kosten
- [ ] Standby vs Aus – 10 Geräte ein Jahr, Stromkosten
- [ ] Laufen vs Radfahren – 30 Minuten, Kalorien
- [ ] Mikrowelle vs Backofen – Pizza aufwärmen, Strom
- [ ] Rolltreppe gehen vs stehen – wer ist zuerst oben?
- [ ] Kaffee vs Energydrink – Koffein pro Getränk
