# Auftrags-Scout – so richtest du ihn ein

Der Auftrags-Scout (`bot/auftraege.py`, läuft täglich ca. 6–7 Uhr und nachmittags per GitHub Actions) sucht bezahlte
Aufgaben, die die KIs komplett erledigen können, und bereitet Angebot, Preis und fertigen Entwurf vor.
Du findest alles in **Jarvis → KI-Stadt → Auftragsbüro** und bekommst eine Telegram-Nachricht.

## Einmal einrichten (ca. 15 Minuten)

1. **PayPal.me** – dein Link `paypal.me/LucasBehrenski` ist schon eingetragen. Prüfe einmal im Browser, ob er
   funktioniert. Anderer Name? GitHub → Settings → Secrets and variables → Actions → *Variables* → `PAYPAL_ME`.
2. **Reddit-Konto** (kostenlos) – für Aufträge aus r/forhire, r/slavelabour, r/HireaWriter. Dort antwortest du
   dem Auftraggeber per Kommentar/Chat mit dem fertigen Angebot. Bezahlt wird über deinen PayPal-Link im Angebot.
3. **Freelancer.com-Konto** (kostenlos) – Profil ausfüllen, unter *Auszahlungen* **PayPal** hinterlegen.
   Wichtig: Bei Freelancer läuft die Zahlung **immer über die Plattform** (Jarvis setzt dort keinen PayPal-Link
   ins Angebot, sonst droht eine Sperre). Gratis-Konto = begrenzte Gebote pro Monat.
4. **Optional, bessere Texte:** kostenlosen API-Schlüssel bei groq.com holen und als GitHub-*Secrets* eintragen:
   `AI_URL` = `https://api.groq.com/openai/v1`, `AI_KEY` = dein Schlüssel, `AI_MODEL` = `openai/gpt-oss-120b`.
   Ohne Schlüssel nutzt der Scout die kostenlose KI (langsamer).
5. **Erster Test:** Actions → *Auftrags-Scout* → *Run workflow*. Nach 2–5 Minuten steht das Ergebnis im Auftragsbüro.

## Täglich (ca. 5–10 Minuten pro Auftrag)

1. Telegram-Meldung antippen bzw. Auftragsbüro öffnen.
2. **Auftrag öffnen**, kurz prüfen, ob er seriös ist (keine Vorkasse von dir, keine Hausaufgaben, keine Fake-Bewertungen).
3. **Angebot kopieren** und beim Auftraggeber senden → **✉ Gesendet** tippen.
4. Zusage? **Entwurf kopieren**, durchlesen, ggf. anpassen, liefern.
5. Geld auf PayPal angekommen → **✓ Bezahlt** – Jarvis bucht es automatisch unter Finanzen.

## Was der Scout zeigt (seit 23.11.2026)

- **Nur schnelle Einmal-Aufträge** bis 250 €: Formulare, Vorlagen (Word/Excel/PowerPoint), kurze Texte,
  Produktbeschreibungen, Lebenslauf/Anschreiben, Korrekturlesen, Zusammenfassungen. Prüfen dauert ca. 15 Minuten.
- **Automatisch aussortiert** (Haftungsrisiko oder viel Eigenarbeit): Recht/Verträge/Datenschutz/AGB, Steuern und
  Buchhaltung, Gesundheit/Ernährung, Finanz- und Anlageberatung, Werbekampagnen und Massen-/Kalt-Mails (UWG),
  personenbezogene Daten und Lead-Listen, Zugriff auf Kundenkonten, Websites/Live-Code, Erfolgsgarantien,
  Dauerbetreuung, Schul- und Uni-Aufgaben.
- Im Angebot steht immer, dass der Kunde das Ergebnis vor dem Einsatz prüft.

## Gut zu wissen

- Jarvis verschickt nichts selbst – Plattformen verbieten Bots, und du haftest für das, was rausgeht.
- Es kommt jeden Tag mindestens ein Auftrag: Findet der Scout nichts, gibt es ein **eigenes Tagesangebot** zum
  Posten (Kleinanzeigen, Facebook-Gruppen, Instagram) mit PayPal-Link.
- Ob und wie viele Aufträge tatsächlich bezahlt werden, hängt davon ab, wer zusagt – eine Garantie gibt es nicht.
- Regelmäßige Einnahmen sind steuerpflichtig: über deine bestehenden Nebengeschäfte abrechnen (Gewerbe) und für die
  Steuer zurücklegen.
- PayPal: Für Dienstleistungen „Waren und Dienstleistungen“ nutzen (Käuferschutz, kleine Gebühr), nicht „Freunde“.
