# Archiv Jarvis v1 (abgeschaltet am 23.11.2026)

Die Jarvis-App (Web-Seite) ist abgeschaltet. Nichts wurde gelöscht:

- **Branch `archiv/jarvis-v1`** – kompletter Code-Stand inkl. **KI-Stadt** (Agentur, Trading-Viertel, KI-Team-Haus, Agenten-Daten in `data/agents.json`), Chat, Finanzen, Trading-Tab, App-Werkstatt.
- **Branch `archiv/jarvis-v1-live`** – die zuletzt veröffentlichte Live-Seite (gh-pages).

Weiter aktiv im Hintergrund (unverändert): alle GitHub-Workflows (Spielgeld-Bot, Backtest, Aufträge, Ideen, Videos, Telegram), `bot/`, `video/`, `data/`, `sparen/`, Server-Skripte `setup.sh` / `brain.sh`.

Wiederherstellen: `git checkout archiv/jarvis-v1 -- index.html sw.js` und pushen.

Nachfolger: OpenJarvis – Installation siehe `openjarvis.sh`.

## Jarvis v2 (seit 23.11.2026 live)
Neue eigene App unter https://lucassebastianbehrens-lang.github.io/jarvis/ – Chat mit Gedächtnis und Stimme,
KI-Stadt (jeder Bot ein Haus), Tages-Briefing, Trading, „Neu entdeckt“.
Neue Bots: `bot/waechter.py` (stündlich, repariert selbst), `bot/recherche.py` (nachts), `bot/briefing.py` (6 Uhr).
Bewohner der Stadt: `data/bots.json`. Gedächtnis wird nur verschlüsselt gesichert (`data/gehirn.enc`).
