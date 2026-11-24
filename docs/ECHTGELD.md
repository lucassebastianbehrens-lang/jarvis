# Echtgeld-Start – Schritt für Schritt

Der Bot handelt erst mit echtem Geld, wenn **alle** Bedingungen erfüllt sind. Bis dahin passiert nichts – auch wenn Schlüssel schon eingetragen sind.

## Freigabe-Bedingungen (prüft der Bot automatisch)

| Bedingung | Ziel |
|---|---|
| Gewinntrades nach Gebühren | mindestens 80 % |
| Spielgeld-Konto | mindestens 3.500 € (Start 1.000 €) |
| Abgeschlossene Trades mit der aktuellen Strategie | mindestens 100 |

Wenn alles erreicht ist, kommt eine Telegram-Nachricht **„🏁 FREIGABE ERREICHT“**. Den aktuellen Stand siehst du in der Jarvis-App und in `data/paper.json` unter `gate`.

---

## Jetzt schon: Kraken-Konto vorbereiten

1. Auf **kraken.com** ein Konto anlegen (E-Mail, Passwort).
2. **Identität verifizieren** (Stufe „Intermediate“: Ausweis + Selfie + Adresse). Nötig für Euro-Einzahlungen per SEPA. Dauert meist 1–3 Tage.
3. **Zwei-Faktor-Anmeldung (2FA)** einschalten: Einstellungen → Sicherheit → 2FA mit einer Authenticator-App (nicht SMS).
4. Noch **kein Geld einzahlen** und noch **keinen API-Schlüssel** anlegen.

---

## Erst nach „FREIGABE ERREICHT“

### Schritt 1 – API-Schlüssel bei Kraken
1. Kraken → Profil → **Einstellungen → API** → „Neuen Schlüssel erstellen“.
2. Name: `jarvis-bot`.
3. Nur diese Rechte anhaken:
   - Funds: **Query** (Guthaben abfragen)
   - Orders & Trades: **Query open orders & trades**, **Query closed orders & trades**, **Create & modify orders**, **Cancel & close orders**
4. **NICHT** anhaken: *Withdraw Funds* (Abheben), *Deposit*, *Earn*, *Export*. So kann niemand mit dem Schlüssel Geld abziehen.
5. Speichern. Kraken zeigt **API Key** und **Private Key** – beide kopieren (der Private Key wird nur einmal angezeigt).

### Schritt 2 – Schlüssel bei GitHub hinterlegen
1. github.com → Repo **jarvis** → **Settings → Secrets and variables → Actions**.
2. Reiter **Secrets** → „New repository secret“:
   - Name `KRAKEN_KEY` → Wert: API Key
   - Name `KRAKEN_SECRET` → Wert: Private Key
3. Reiter **Variables** → „New repository variable“:
   - `LIVE_MODE` = `test`
   - `LIVE_MAX_EUR` = `100` (Höchstbetrag, den der Bot insgesamt einsetzt)
   - `LIVE_MAX_DAY_LOSS` = `15` (ab diesem Tagesverlust keine neuen Käufe)

Schlüssel niemals in den Chat, in Code oder in Dateien schreiben – nur in die GitHub-Secrets.

### Schritt 3 – Testlauf (1–2 Tage, kein echter Handel)
Im Modus `test` schickt der Bot jede Order an Kraken **nur zur Prüfung** (`validate`) – Kraken führt nichts aus.
- In Telegram kommen Nachrichten mit **„[nur Test]“**.
- Kommt „⚠️ Fehler“, sag mir Bescheid, dann behebe ich das vor dem Start.

### Schritt 4 – Geld einzahlen
Kraken → **Einzahlen → EUR → SEPA**. Betrag = `LIVE_MAX_EUR` (z. B. 100 €). Ankunft meist am nächsten Werktag.

### Schritt 5 – Scharf schalten
GitHub → Variables → `LIVE_MODE` auf **`an`** ändern. Ab dem nächsten Lauf (alle 15 Min) spiegelt der Bot jeden neuen Spielgeld-Kauf mit echtem Geld (Einsatz je Trade = `LIVE_MAX_EUR` ÷ 5) und legt bei Kraken sofort eine Stop-Loss-Order an.

### Schritt 6 – Beobachten
Mindestens 4 Wochen mit kleinem Betrag. Erst erhöhen (`LIVE_MAX_EUR`), wenn Echtgeld- und Spielgeld-Ergebnisse ähnlich sind.

---

## Not-Aus

| `LIVE_MODE` | Wirkung |
|---|---|
| `aus` | keine neuen Käufe, offene Positionen werden normal verkauft |
| `stop` | **alles sofort verkaufen**, danach nichts mehr |
| `test` | nur Prüf-Orders, kein echter Handel |
| `an` | echter Handel |

Zusätzlich pausiert der Bot von selbst, wenn der Tagesverlust `LIVE_MAX_DAY_LOSS` erreicht oder die letzten 30 Spielgeld-Trades unter 70 % Treffer fallen.

## Wichtig zu wissen
- **Steuern (Deutschland):** Krypto-Gewinne innerhalb eines Jahres sind steuerpflichtig (§ 23 EStG, Freigrenze 1.000 € Gesamtgewinn pro Jahr). Kraken bietet einen Export aller Trades. Keine Steuerberatung – im Zweifel Steuerberater fragen.
- GitHub startet die Läufe manchmal mit Verspätung. Der Stop-Loss liegt deshalb direkt bei Kraken; Gewinnmitnahmen können ein paar Minuten später als im Spielgeld passieren.
- Vergangene Ergebnisse (Backtest, Spielgeld) garantieren keine zukünftigen Gewinne. Nur Geld einsetzen, dessen Verlust du verkraften kannst.
