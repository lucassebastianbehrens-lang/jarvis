# Simulations-Videos „Was ist besser?“ – Themen & Regeln

## Regeln gegen Sperren / „unoriginal“
- Jede Folge ist ein **eigenes Thema** mit eigenem Skript, eigenen Zahlen und eigener Grafik (per Code gezeichnet). Nie ein fremdes Video nachbauen, nie Clips anderer Kanäle verwenden.
- Ein Thema, das andere Kanäle auch haben, nur mit **eigenem Blickwinkel** (andere Strecke/Mengen, andere Pointe, eigener Text). Titel und Caption nie 1:1 übernehmen.
- Stimme, Sprechtempo, Farben und Hintergrund wechseln automatisch je Folge (sim.py). Keine Folge gleicht der anderen.
- Jede Zahl braucht eine Quelle (Feld `quelle` im Spec, wird in die Beschreibung geschrieben). Lieber runde, vorsichtige Werte als falsche.
- KI-Kennzeichnung bei TikTok immer an. Familienfreundlich, keine Marken/Logos, keine echten Personen.
- Erledigte Themen unten abhaken – nichts doppelt. Ist der Pool leer, denkt sich Jarvis selbst neue Themen aus (bot/video_auto.py).

## Ablauf je Folge (seit 24.11.2026)
1. Idee (Pool oder eigene Idee über den Workflow-Knopf „idee“) → 2. Fakten mit Quelle sammeln → 3. Skript nur aus diesen Fakten,
3 Hook-Varianten für Sekunde 1 → 4. Prüfer-KI checkt Zahlen/Hook/Familientauglichkeit, wählt den besten Hook, bei Fehlern 1× neu schreiben
→ Schluss-Frage an die Zuschauer („Was hättest du getippt?“) für mehr Kommentare → Rendern → video_check.py.

## Spec-Format (generisch)
`modell.typ = "generisch"`, je Seite `a`/`b`: `name`, `figur` (geher|laeufer|auto|rad), `dauer_s` (wie lange es in der Simulation dauert), `menge` (Endwert), `info` (kleine Zeile).
`modell.einheit`, `modell.zaehler` (z. B. „Liter“), `modell.besser` (weniger|mehr), optional `modell.wetter = "regen"`, `skala` (3 Beschriftungen), `ergebnis` ("{p} % weniger …").
`lines` mit `phase` intro → race → result (die Rennen-Phase bestimmt das Tempo der Animation).

## Themen-Pool
- [x] Rennen vs Gehen im Regen – wer wird weniger nass? (sim-01)
- [x] Treppe vs Aufzug – 5 Stockwerke, was ist schneller? (sim-02)
- [x] Auto vs Fahrrad in der Stadt – 5 km im Berufsverkehr (sim-03-auto-vs-fahrrad-in-der-stadt)
- [x] Wasserkocher vs Herd – 1 Liter Wasser, Zeit & Strom (sim-04-wasserkocher-vs-herd)
- [x] Fön vs Lufttrocknen – Haare, Zeit & Strom (sim-05-foen-vs-lufttrocknen)
- [x] Spülmaschine vs Handspülen – Wasser pro Ladung (sim-06-spuelmaschine-vs-handspuelen)
- [x] Laden vs Tanken – 100 km E-Auto vs Benziner, Kosten (sim-07-laden-vs-tanken)
- [x] Standby vs Aus – 10 Geräte ein Jahr, Stromkosten (sim-08-standby-vs-aus)
- [ ] Laufen vs Radfahren – 30 Minuten, Kalorien
- [ ] Mikrowelle vs Backofen – Pizza aufwärmen, Strom
- [ ] Rolltreppe gehen vs stehen – wer ist zuerst oben?
- [ ] Kaffee vs Energydrink – Koffein pro Getränk
