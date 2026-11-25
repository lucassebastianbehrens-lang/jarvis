# CLAUDE.md – Jarvis

Claude Code liest diese Datei bei jedem Start in diesem Repo. Hier steht, wer Lucas ist und wie an Jarvis gearbeitet wird.

## Zuerst lesen
- @brain/JARVIS.md – wer Lucas ist, seine Projekte, feste Regeln, was Jarvis kann
- @docs/ARCHITEKTUR.md – Aufbau (App, Bots, Daten, Dienste), Regeln für neuen Code
- Bei Geld-Themen: docs/ECHTGELD.md (Trading) und docs/AUTOMATON.md (PayPal-Topf, Klone)

## Wie Lucas arbeiten will
- Immer Deutsch, kurz. Beträge in Euro.
- Was richtig ist, direkt umsetzen und danach kurz berichten. Nicht ständig nachfragen.
- Bestätigung nur, wenn nötig – dann als Ja/Nein-Knopf.
- Muss Lucas selbst etwas tun (Schlüssel, Zugang, Konto): immer Link + Schritt-für-Schritt-Anleitung.
- Eigene Arbeit selbst prüfen und Fehler ohne Rückfrage beheben.
- Sauber bauen wie ein Software-Engineer (Architektur, Doku, Tests), kein „Vibe Coding“.
- Jarvis soll ohne Claude-Credits laufen: KI über Groq, Ausweichen nur auf Gemini (kein OpenRouter gewünscht).

## Harte Regeln
1. Kein echtes Geld bewegen, nichts kaufen, keine Trades mit Echtgeld ohne Lucas' ausdrückliches Ja. PayPal wird nur gelesen.
2. Keine Schlüssel/Passwörter im Code oder in Commits – nur GitHub-Secrets. Neue Schlüssel trägt Lucas selbst ein.
3. Nichts öffentlich posten, keine Nachrichten an Fremde ohne Freigabe (Ausnahmen in brain/JARVIS.md).
4. Nichts löschen – archivieren.

## Ablauf einer Änderung
1. Neue App-Funktion: Baustein in `js/` (Nummern-Reihenfolge) + Eintrag in `index.html` + Test in `tests/test_app.py`.
2. Neuer Bot: `bot/<name>.py` (nutzt `jlib`) + Workflow in `.github/workflows/` + Eintrag in `data/bots.json` + Test in `tests/test_bots.py`.
3. Vor jedem Push testen:
   ```bash
   python3 tests/test_bots.py
   for f in js/*.js sw.js; do node --check "$f"; done
   python3 tests/test_app.py   # braucht playwright + chromium
   ```
4. Auf `main` pushen → „Qualitätsprüfung“ → bei Grün geht die App automatisch live.
5. Danach kurz prüfen, ob die Workflows grün sind (`gh api repos/lucassebastianbehrens-lang/jarvis/actions/runs?per_page=5`).
6. Neue Fähigkeit in brain/JARVIS.md unter „Neu“ eintragen, damit Jarvis selbst davon weiß.
