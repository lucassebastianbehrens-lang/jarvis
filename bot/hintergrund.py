"""Leibgarde – Lucas' persönliche Hintergrund-Bots (Ben, Lea, Kai).
Arbeiten NUR für Lucas' Aufträge, parallel zu allen anderen Bots (eigene Warteschlange, nie blockiert).
Ablauf: Plan → mehrere Websuchen (Groq Compound) → Antwort mit echten Quellen-Links.
Ergebnis → data/hintergrund/<id>.json (Jarvis-App zeigt es an) + Telegram-Nachricht."""
import json, os, re, sys, time
from jlib import ki, parse_json, store, path, tg

AUFGABE = os.environ.get("AUFGABE", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
ID = re.sub(r"[^\w-]", "", os.environ.get("AUFTRAG_ID", "")) or str(int(time.time()))
BOT = os.environ.get("BOT", "") or "Ben"
HEUTE = time.strftime("%d.%m.%Y")
URL = re.compile(r"https?://[^\s)\]>\"'`]+")

ICH = (f"Du bist {BOT}, ein persönlicher Hintergrund-Bot von Jarvis und arbeitest nur für Lucas "
       "(Schichtarbeiter in Oschersleben, baut nebenbei Online-Geschäfte). Deutsch, Beträge in Euro, "
       f"heute ist der {HEUTE}. Sei genau: nur belegbare Fakten, nichts erfinden; wenn etwas unklar ist, sag es.")


def websuche(frage):
    """Eine Websuche über Groq Compound → (Text, Quellen-Links)."""
    t = ki(ICH + " Recherchiere im Internet und antworte knapp mit den wichtigsten Fakten. "
           "Nenne zu jedem Fakt den Quellen-Link (volle URL).", frage, search=True)
    return t, [u.rstrip(".,;:") for u in URL.findall(t)]


def main():
    if not AUFGABE:
        print("Kein Auftrag.")
        return
    t0 = int(time.time())
    try:
        plan = parse_json(ki("Du planst Recherchen. Antworte nur mit gültigem JSON.",
                             f"Auftrag von Lucas: {AUFGABE}\n\nBraucht der Auftrag aktuelle Infos aus dem Internet? "
                             'Wenn ja: 2–4 präzise, unterschiedliche Suchfragen (Deutsch oder Englisch, je nachdem, wo die besten Quellen sind). '
                             'Wenn nein (z. B. Text schreiben, rechnen): leere Liste. JSON: {"suchen": ["..."]}', json_mode=True))
        suchen = [s for s in plan.get("suchen", []) if isinstance(s, str)][:4]
    except Exception as e:
        print("Plan", e)
        suchen = [AUFGABE]

    funde, quellen = [], []
    for s in suchen:
        text, links = websuche(s)
        if text:
            funde.append(f"### Suche: {s}\n{text[:4000]}")
            quellen += [u for u in links if u not in quellen]
        print("Suche:", s, "→", len(links), "Links")

    antwort = ki(ICH + " Liefere das fertige Ergebnis in Markdown: zuerst die Antwort in 1–2 Sätzen (fett), "
                 "dann die Details als kurze Liste. Nutze NUR Links, die in den Rechercheergebnissen stehen, "
                 "und setze sie direkt hinter den passenden Punkt. Am Ende: '**Nächster Schritt:**' mit 1 Satz.",
                 f"Auftrag: {AUFGABE}\n\n" + ("Rechercheergebnisse:\n" + "\n\n".join(funde) if funde else "(keine Websuche nötig)"))
    ok = bool(antwort)
    if not ok:
        antwort = "Ich konnte den Auftrag gerade nicht bearbeiten (KI nicht erreichbar). Bitte später nochmal starten."
    # nur Links behalten, die wirklich aus der Recherche stammen
    erfunden = [u for u in URL.findall(antwort) if quellen and u.rstrip(".,;:") not in quellen]
    for u in erfunden:
        antwort = antwort.replace(u, "")
    os.makedirs(path("data", "hintergrund"), exist_ok=True)
    store(f"hintergrund/{ID}.json", {"id": ID, "bot": BOT, "aufgabe": AUFGABE, "ok": ok, "antwort": antwort,
                                     "quellen": quellen[:15], "suchen": suchen, "start": t0, "ende": int(time.time())})
    tg(f"✅ {BOT} ist fertig: {AUFGABE[:80]}\n\n{re.sub(r'[*#]', '', antwort)[:3000]}")
    print(f"Fertig: {len(suchen)} Suchen, {len(quellen)} Quellen, {len(erfunden)} unbelegte Links entfernt")


if __name__ == "__main__":
    main()
