# Automaton – Jarvis finanziert sich selbst (PayPal)

Idee aus dem Video „KI, die sich selbst klont“ (Conway-Research/automaton), umgebaut auf **PayPal statt Krypto-Wallet**.
Bot: `bot/automaton.py` · Dienst: `automaton.yml` (alle 2 h) · Daten: `data/automaton.json` · App: Tab **Trading** ganz oben.

## So funktioniert's
**Jarvis-Topf** = Startguthaben (25 €) + PayPal-Eingänge seit Start − Server (9,50 €/Monat) − Budgets lebender Kinder.

| Stufe | Topf | Was passiert |
|---|---|---|
| 🟢 normal | ≥ 50 € | großes KI-Modell, alle Bots, darf Klone vorschlagen |
| 🟡 sparsam | ≥ 15 € | kleineres KI-Modell (für **alle** Bots über `jlib.ki`) |
| 🟠 kritisch | > 0 € | Recherche, Lage, Videos pausieren – nur noch Geld-Suche (Scout, Shop-Bau) |
| ⚫ ruhe | ≤ 0 € | nur Wächter, Leibgarde, Ideen, Scout, Shop-Bau, Automaton |

**Klonen:** ab 40 € im Topf (höchstens alle 3 Tage, max. 3 Kinder) schlägt Jarvis ein Kind vor – Bauer 🏗️ (Shops), Vermarkter 📣 (Videos) oder Sicherung 💾.
Ein Kind entsteht **nur nach deinem „Ja“** in der App (oder Telegram-Hinweis → App). Es bekommt bis zu 10 € Budget (rein rechnerisch),
macht alle 2 h einen Schritt und darf dafür höchstens einen Jarvis-Dienst starten. Kein Budget mehr und nichts verdient → 💀.
Zahlungen mit der Kennung `[K-XXXX]` im PayPal-Verwendungszweck werden dem Kind gutgeschrieben.

Werte ändern: einfach in `data/automaton.json` (`startguthaben`, `server_eur_monat`, `klon_ab`, `max_kinder`, `kind_budget_max`).

## Sicherheit
- Der Bot **liest** PayPal nur (Kontostand + Umsätze). Er kann kein Geld senden, abheben oder ausgeben.
- Ohne PayPal-Schlüssel bleibt Jarvis auf „normal“ – nichts wird abgeschaltet.

## PayPal verbinden (einmalig, ca. 5 Min)
1. https://developer.paypal.com/dashboard/applications/live öffnen und mit deinem PayPal anmelden.
2. **Create App** → Name `jarvis-automaton` → Typ *Merchant* → Erstellen.
3. In der App unter **Features** den Haken bei **Transaction Search** setzen → Speichern (PayPal schaltet das teils erst nach bis zu 3 h frei).
4. **Client ID** und **Secret** kopieren (Secret über „Show“).
5. https://github.com/lucassebastianbehrens-lang/jarvis/settings/secrets/actions/new öffnen:
   - Name `PAYPAL_CLIENT_ID` → Client ID → *Add secret*
   - nochmal: Name `PAYPAL_SECRET` → Secret → *Add secret*
6. Fertig – beim nächsten Lauf (oder Actions → „Automaton“ → *Run workflow*) steht „PayPal-Konto …“ in der App.
