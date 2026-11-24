# Zeichentrick „Stell dir vor“ – Serien-Bibel

**Vor jeder neuen Folge lesen.** Eigenes Format von Jarvis (angeregt vom Making-of-Trend, 24.11.2026).
Nichts kopieren: eigene Figur, eigenes Zimmer, eigene Themen. Die Figur wird **per Code gezeichnet** (video/zt.py) –
sie sieht in jeder Folge exakt gleich aus und jedes Bild kostet 0 €.

## Die Figur: Finn
- Runder Kopf, dunkle zerzauste Haare, runde Brille, rote Kopfhörer um den Hals, grüner Kapuzenpulli.
- Wohnt in einem kleinen Dachzimmer mit schräger Decke, Lichterkette und warmer Lampe.
- Ruhig, ehrlich, ein bisschen verpeilt – er ist „jeder von uns“.

## Ton
- **Ruhig statt laut.** Ein Erzähler spricht leise und nah, wie ein Gedanke. Keine Effekte-Schlacht.
- **Du-Ansprache:** „Stell dir vor, du …“ – der Zuschauer ist die Hauptfigur, Finn zeigt es nur.
- **Echt statt übertrieben:** Nur was wirklich passieren könnte. Gefühle so, wie man sie wirklich hat
  (man erstarrt erst, bevor man jubelt).

## Themen-Regeln (vor jeder Folge prüfen)
1. **Ein Moment, kein Oberbegriff** – in einem Satz sagbar („Du wachst auf und dein Video hat über Nacht 48.000 Aufrufe“).
2. **Zwei Fragen:** Kann mir das auch passieren? Wie sieht mein Leben dann aus? Beide müssen mit Ja/Neugier beantwortbar sein.
3. **Traum** (plötzlich Glück, Erfolg, Freiheit) **oder Lachen** (peinlicher Alltag, den jeder kennt) – keine Angst-Videos.
4. **Einfach schlägt klug.** Alltag und eigener Körper laufen besser als Geschichte mit Jahreszahlen.
5. **Kleinigkeiten stimmen:** Zahlen so wählen, wie man sie selbst kennt (z. B. „300 Aufrufe“ statt „200“).
6. **Danach etwas tun wollen:** Schluss mit einer Frage, auf die jeder von sich erzählt → Kommentare über sich selbst.
7. **Fortsetzbar:** Jede Idee braucht einen möglichen Teil 2.

## Aufbau einer Folge (35–60 Sekunden, 5–8 Szenen)
- Szene 1 (Sekunde 0–3): der Moment sofort, keine Einleitung. Gern mit großer Zahl.
- Mitte: eine einzige Bewegung, die trägt (meist eine Zahl, die steigt – Feld `zahl`).
- Vor der größten Zahl: kurze Stille (Feld `pause` = Sekunden).
- Ende: Frage an den Zuschauer + „Teil 2?“-Haken.

## Technik (für den Schreiber)
- `bg`: zimmer | bett | schreibtisch | strasse | schule | kueche | nacht
- `pose`: neutral | staunen | schock | freude | traurig | denken | zeigen | schlafen
- `prop`: keins | handy | wecker | geld | brief | laptop
- `zahl`: ganze Zahl (optional) – wird groß eingeblendet und zählt von der vorigen Zahl hoch; `zahl_label`: z. B. „Aufrufe“, „€“
- `text`: was der Erzähler sagt (1–2 kurze Sätze, sprechbar, Zahlen ausgeschrieben oder als Ziffern ok)
- Keine Marken, keine echten Personen, familienfreundlich.
