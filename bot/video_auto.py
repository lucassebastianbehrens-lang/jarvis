"""Jarvis schreibt TikTok-Folgen selbst (ohne Claude) – mit der kostenlosen Groq-KI.
Ablauf (nach Lucas' Vorlage „Viral Studio“, 24.11.2026):
  1. Idee   – nächstes Thema aus THEMEN.md, eigene Idee über $IDEE, leerer Pool füllt sich selbst auf
  2. Fakten – erst Fakten mit Quelle sammeln, dann daraus das Skript schreiben (sim)
  3. Skript – 3 Hook-Varianten für Sekunde 1, Prüfer wählt die stärkste; Schluss mit Kommentar-Frage
  4. Prüfen – zweiter KI-Durchgang als strenger Prüfer; bei Fehlern wird einmal neu geschrieben
  python3 bot/video_auto.py sim   -> nächstes Thema aus video/sim/THEMEN.md als Spec (video/sim/sim-NN-*.json)
  python3 bot/video_auto.py tt    -> nächste Folge der Früchte-Serie nach der Serien-Bibel (video/tt/tt-s1-fNN.json)
Gibt den Pfad der neuen Spec aus (und schreibt ihn nach $GITHUB_OUTPUT als spec=...)."""
import glob, json, os, re, sys, urllib.request

KEY = os.environ.get("GROQ_KEY", "")
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
VERBOTEN = re.compile(r"\b(man|woman|women|men|girl|boy|human|person|people|sexy|bikini|bra|crop top|cleavage|naked)\b", re.I)


def ki(system, user, temp=0.8):
    last = None
    for m in MODELS:
        try:
            body = {"model": m, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "response_format": {"type": "json_object"}, "temperature": temp}
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "Authorization": "Bearer " + KEY, "User-Agent": "jarvis-bot"})  # ohne User-Agent: Groq antwortet 403
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = json.load(r)["choices"][0]["message"]["content"]
            return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        except Exception as e:
            last = e
            print("Modell", m, "Fehler:", e)
    raise SystemExit(f"KI nicht erreichbar: {last}")


def saeubern(p):
    """Verbotene Wörter raus, ohne Verneinungen zu zerstören ("no human face" darf nicht zu "no face" werden)."""
    p = re.sub(r"\bno\s+(?:human|person|people|man|woman|women|men)\b[^,]*,?\s*", "", p, flags=re.I)  # STYLE verbietet Menschen schon
    p = VERBOTEN.sub("", p)
    p = re.sub(r"\b(apron|dress|skirt|blouse|lipstick|high heels)\b", "tiny accessory", p, flags=re.I)  # Kleidung lockt Menschen-Bilder
    return re.sub(r"\s{2,}", " ", re.sub(r"\bno\s+,", "", p)).strip(" ,")


def slug(t):
    t = t.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:30]


def neue_themen(themen, anzahl=8):
    """Pool leer? Jarvis denkt sich selbst neue „Was ist besser?“-Themen aus (keine Dopplungen)."""
    alt = [re.sub(r"\s*\(sim-\d+[^)]*\)\s*$", "", t).strip() for t in re.findall(r"^- \[[ x]\] (.+)$", themen, re.M)]
    bekannt = {t.lower() for t in alt}
    r = ki("Du planst deutsche TikTok-Simulationsvideos „Was ist besser?“. Antworte NUR mit JSON.",
           f"Erfinde {anzahl} neue Alltags-Vergleiche (A vs B, mit messbarem Ergebnis wie Zeit, Kosten, Strom, Wasser, Kalorien). "
           f"Format pro Thema: „A vs B – kurze Frage“. Nichts davon darf schon vorkommen:\n" + "\n".join(alt) +
           '\nAntwort: {"themen": ["...", "..."]}', 0.9)
    neu = []
    for t in r.get("themen", []):
        t = str(t).strip()
        if " vs " in t and t.lower() not in bekannt:
            neu.append(t); bekannt.add(t.lower())
    neu = neu[:anzahl]
    if not neu:
        raise SystemExit("Keine neuen Themen gefunden")
    return themen.rstrip("\n") + "\n" + "".join(f"- [ ] {t}\n" for t in neu)


def fakten(thema):
    """Schritt 2: erst Fakten mit Quelle, dann Skript – damit keine Zahl erfunden ist."""
    r = ki("Du bist ein vorsichtiger Faktenprüfer. Antworte NUR mit JSON. Nur Werte, die du sicher kennst "
           "(Verbraucherzentrale, Umweltbundesamt, Hersteller-Richtwerte, Physik). Lieber runde, vorsichtige Werte.",
           f"Thema: {thema}\nSammle 3–6 Kernfakten, die man für einen fairen Vergleich braucht. "
           '{"fakten": [{"satz": "...", "wert": "...", "quelle": "..."}], "annahmen": ["gleiche Bedingungen für A und B ..."]}', 0.2)
    f = [x for x in r.get("fakten", []) if x.get("satz") and x.get("quelle")]
    assert len(f) >= 2, "Zu wenige belegbare Fakten"
    return {"fakten": f, "annahmen": r.get("annahmen", [])}


def pruefen(art, spec, extra):
    """Schritt 4: strenger zweiter Blick (Reality Checker). Gibt (probleme, bester_hook) zurück."""
    try:
        r = ki("Du bist der strenge Reality Checker für TikTok-Videos. Antworte NUR mit JSON. Sei kritisch, aber nenne nur echte Fehler.",
               f"Prüfe dieses {art}-Video vor dem Rendern.\n{extra}\n\nVIDEO:\n{json.dumps(spec, ensure_ascii=False)}\n\n"
               "Prüfe: Stimmen alle Zahlen zu den Fakten und zueinander (Ergebnis-Prozent passt zu menge a/b)? Ist Sekunde 1 sofort spannend? "
               "Familienfreundlich, keine Marken/echten Personen? Rechtschreibung? "
               'Wähle außerdem aus "hooks" den stärksten Einstieg (Index ab 0, sonst 0). '
               '{"ok": true|false, "probleme": ["..."], "bester_hook": 0}', 0.1)
    except SystemExit as e:  # Prüfer nicht erreichbar → nicht blockieren, video_check.py prüft danach trotzdem
        print("Prüfer übersprungen:", e)
        return [], 0
    probleme = [] if r.get("ok", True) else [str(p) for p in r.get("probleme", []) if p]
    try:
        hook = int(r.get("bester_hook", 0))
    except (TypeError, ValueError):
        hook = 0
    return probleme, hook


def sim_schreiben(thema, sid, fk, regeln, vorlage, feedback=""):
    sp = ki("Du schreibst deutsche TikTok-Simulationsvideos „Was ist besser?“. Antworte NUR mit einem JSON-Objekt. "
            "Benutze NUR die gelieferten Fakten für Zahlen und nenne ihre Quellen im Feld quelle. Keine Marken, keine echten Personen, familienfreundlich.",
            f"Thema: {thema}\n\nFAKTEN (nur diese Zahlen verwenden):\n{json.dumps(fk, ensure_ascii=False)}\n\nRegeln und Format:\n{regeln}\n\n"
            f"Pflichtfelder: id, titel [2 kurze GROSSE Wörter], frage [Zeile1, Zeile2 GROSS], "
            f"modell {{typ:'generisch', einheit, zaehler, besser:'weniger'|'mehr'}}, a und b je {{name, figur (geher|laeufer|auto|rad), dauer_s, menge, info}}, "
            f"skala [3 kurze Beschriftungen], ergebnis (mit {{p}}), lines (5–7, je {{phase: intro|race|result, t}}; 1. Zeile = Frage, "
            f"mind. 2 race-Zeilen, letzte = result mit Ergebnis), "
            f"hooks [3 verschiedene Einstiegssätze für Sekunde 1, je max. 10 Wörter: 1× Frage, 1× überraschende Zahl, 1× Behauptung/Mythos], "
            f"kommentar_frage (kurze Frage an die Zuschauer, die zum Kommentieren bringt, z. B. „Was hättest du getippt?“, max. 8 Wörter), "
            f"caption (≤150 Zeichen, mit Emoji), hashtags (5, erstes #simulation), quelle.\n"
            f"id muss sein: {sid}\nBeispiel für das Format:\n{vorlage}" +
            (f"\n\nDER PRÜFER HAT FOLGENDES BEMÄNGELT – unbedingt beheben:\n- " + "\n- ".join(feedback) if feedback else ""))
    sp["id"] = sid
    sp.setdefault("modell", {})["typ"] = "generisch"
    for k in ("a", "b"):
        p = sp[k]; p["dauer_s"] = float(p["dauer_s"]); p["menge"] = float(p["menge"])
        assert p["dauer_s"] > 0 and p["menge"] > 0, "Werte ungültig"
        if p.get("figur") not in ("geher", "laeufer", "auto", "rad"):
            p["figur"] = "geher"
    ph = [l.get("phase") for l in sp["lines"]]
    assert 4 <= len(ph) <= 8 and "race" in ph and ph[-1] == "result", "Sprechzeilen ungültig"
    assert len(sp["caption"]) <= 220 and len(sp["hashtags"]) >= 3
    sp["hooks"] = [h.strip() for h in sp.get("hooks", []) if isinstance(h, str) and 2 <= len(h.split()) <= 14][:3]
    return sp


def sim_fertig(sp, hook):
    """Stärksten Hook nach vorn, Kommentar-Frage ans Ende (Engagement), Faktenliste in die Quelle."""
    if sp.get("hooks"):
        sp["lines"][0]["t"] = sp["hooks"][min(max(hook, 0), len(sp["hooks"]) - 1)]
    fr = str(sp.get("kommentar_frage", "")).strip()
    if fr and len(fr.split()) <= 12:
        sp["lines"].append({"phase": "result", "t": fr.rstrip("?") + "? Schreib es in die Kommentare."})
        if fr not in sp["caption"]:
            sp["caption"] = (sp["caption"] + " " + fr.rstrip("?") + "? 👇")[:220]
    return sp


def sim():
    themen = open("video/sim/THEMEN.md", encoding="utf-8").read()
    idee = os.environ.get("IDEE", "").strip()
    m = None
    if idee:
        thema = idee
    else:
        if not re.search(r"^- \[ \] .+$", themen, re.M):
            themen = neue_themen(themen)
            open("video/sim/THEMEN.md", "w", encoding="utf-8").write(themen)
        m = re.search(r"^- \[ \] (.+)$", themen, re.M)
        thema = m.group(1).strip()
    nr = 1 + max([int(re.search(r"sim-(\d+)", p).group(1)) for p in glob.glob("video/sim/sim-*.json")] or [0])
    sid = f"sim-{nr:02d}-{slug(thema.split('–')[0])}"
    vorlage = open("video/sim/sim-02-treppe-aufzug.json", encoding="utf-8").read() if os.path.exists("video/sim/sim-02-treppe-aufzug.json") else ""
    regeln = themen.split("## Themen-Pool")[0]
    fk = fakten(thema)
    sp = sim_schreiben(thema, sid, fk, regeln, vorlage)
    probleme, hook = pruefen("Simulations", sp, "FAKTEN:\n" + json.dumps(fk, ensure_ascii=False))
    if probleme:
        print("Prüfer:", probleme)
        sp = sim_schreiben(thema, sid, fk, regeln, vorlage, probleme)
        hook = pruefen("Simulations", sp, "FAKTEN:\n" + json.dumps(fk, ensure_ascii=False))[1]
    sp = sim_fertig(sp, hook)
    sp["fakten"] = fk["fakten"]
    path = f"video/sim/{sp['id']}.json"
    json.dump(sp, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if m:
        open("video/sim/THEMEN.md", "w", encoding="utf-8").write(themen.replace(m.group(0), f"- [x] {thema} ({sp['id']})", 1))
    return path


def tt():
    bibel = open("video/tt/00-STAFFEL-1-BIBEL.md", encoding="utf-8").read()
    files = sorted(glob.glob("video/tt/tt-s1-f*.json"))
    letzte = json.load(open(files[-1], encoding="utf-8"))
    f01 = json.load(open("video/tt/tt-s1-f01.json", encoding="utf-8"))
    nr = int(re.search(r"f(\d+)", files[-1]).group(1)) + 1
    if nr > 14:
        raise SystemExit("Staffel 1 ist fertig – Staffel 2 muss geplant werden.")
    def schreiben(feedback=None):
        return ki("Du schreibst die deutsche KI-Miniserie „Früchte-Drama“ für TikTok. Antworte NUR mit einem JSON-Objekt im exakt gleichen Format wie die letzte Folge. "
            "Halte dich strikt an die Serien-Bibel. Familienfreundlich, nichts Anzügliches. Bildprompts auf Englisch, Dialoge auf Deutsch.",
            f"SERIEN-BIBEL:\n{bibel}\n\nLETZTE FOLGE (Format-Vorlage):\n{json.dumps(letzte, ensure_ascii=False)}\n\n"
            f"Schreibe Folge {nr} genau nach dem Folgenplan-Eintrag F{nr:02d}. 5–7 scenes, 140–170 Wörter Dialog insgesamt, Sekunde 1 Konflikt, "
            f"Ende Cliffhanger, end = „Folge mir für Teil {nr + 1}“. Jeder Bildprompt p beginnt mit der exakten Figurenbeschreibung aus "
            f"„figuren“ der Figuren in der Szene. Verbotene Wörter in p: man, woman, girl, boy, human, person, people, sexy." +
            (f"\n\nDER PRÜFER HAT FOLGENDES BEMÄNGELT – unbedingt beheben:\n- " + "\n- ".join(feedback) if feedback else ""))

    ep = schreiben()
    probleme = pruefen("Serien-Folge", ep, f"Muss zur Serien-Bibel passen (Folgenplan F{nr:02d}, Figuren, Ton), Sekunde 1 Konflikt, Ende Cliffhanger.\nBIBEL:\n{bibel[:6000]}")[0]
    if probleme:
        print("Prüfer:", probleme)
        ep = schreiben(probleme)
    ep["id"], ep["episode"], ep["voices"], ep["figuren"] = f"tt-s1-f{nr:02d}", nr, f01["voices"], f01["figuren"]
    ep.setdefault("series", f01.get("series"))
    sc = ep["scenes"]
    assert 4 <= len(sc) <= 8, "Szenenzahl ungültig"
    for s in sc:
        s["p"] = saeubern(s["p"])
        assert s.get("lines"), "Szene ohne Text"
        for l in s["lines"]:
            if l["s"] not in ep["voices"]:
                l["s"] = "Erzähler"
    woerter = sum(len(l["t"].split()) for s in sc for l in s["lines"])
    assert 90 <= woerter <= 260, f"Dialoglänge {woerter} Wörter"
    path = f"video/tt/{ep['id']}.json"
    json.dump(ep, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


if __name__ == "__main__":
    if not KEY:
        raise SystemExit("GROQ_KEY fehlt (GitHub → Settings → Secrets → Actions)")
    p = {"sim": sim, "tt": tt}[sys.argv[1]]()
    print(p)
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"spec={p}\n")
