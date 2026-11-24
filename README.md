# Jarvis – Lucas' persönlicher KI-Assistent

**Live-App:** https://lucassebastianbehrens-lang.github.io/jarvis/ · **Bauplan:** [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md)

```
jarvis/
├── index.html          Frontend: nur das Gerüst der App (Tabs, Dialoge)
├── css/app.css         Frontend: komplettes Design (dunkles Rot, „Command Center“)
├── js/                 Frontend: Logik, ein Baustein pro Aufgabe (lädt in Nummern-Reihenfolge)
├── sw.js, manifest.json, icon*   App aufs Handy (PWA, offline)
├── bot/                Backend: alle Bots (Python, laufen als GitHub Actions bzw. auf dem Server)
├── video/              Backend: Video-Fabrik (TikTok/YouTube)
├── data/               Datenbank: JSON-Dateien, die Bots schreiben und die App liest
├── brain/JARVIS.md     Jarvis' Selbstbild, Regeln und Fähigkeiten
├── server/             Einrichtung des netcup-Servers (Telegram-Jarvis, Trading, Agenten)
├── sparen/             Webseite „Was ist günstiger?“
├── tests/              Tests für App (Browser) und Bots
├── docs/               Doku: Architektur, Echtgeld-Regeln, Auftrags-Scout, Archiv v1
└── .github/workflows/  Dienste: Zeitpläne der Bots, Prüfung, Veröffentlichung
```

## Ablauf einer Änderung
1. Code landet auf `main`.
2. **Qualitätsprüfung** (`pruefung.yml`) testet Bots und klickt die App im Browser komplett durch.
3. Nur wenn alles grün ist, bringt **App veröffentlichen** genau diesen geprüften Stand live und kontrolliert die Live-Seite.
4. **Wächter Willi** prüft danach stündlich, ob alles läuft, startet Kaputtes neu und meldet sich per Telegram.

## Selbst testen
```bash
python3 tests/test_bots.py                      # Bots, ohne Internet, ~3 s
pip install playwright && python3 -m playwright install chromium
python3 tests/test_app.py                       # App im Browser, ~30 s
```
