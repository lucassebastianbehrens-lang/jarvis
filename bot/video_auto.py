"""Jarvis schreibt TikTok-Folgen selbst (ohne Claude) – mit der kostenlosen Groq-KI.
  python3 bot/video_auto.py sim   -> nächstes Thema aus video/sim/THEMEN.md als Spec (video/sim/sim-NN-*.json)
  python3 bot/video_auto.py tt    -> nächste Folge der Früchte-Serie nach der Serien-Bibel (video/tt/tt-s1-fNN.json)
Gibt den Pfad der neuen Spec aus (und schreibt ihn nach $GITHUB_OUTPUT als spec=...)."""
import glob, json, os, re, sys, urllib.request

KEY = os.environ.get("GROQ_KEY", "")
MODELS = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
VERBOTEN = re.compile(r"\b(man|woman|women|men|girl|boy|human|person|people|sexy|bikini|bra|crop top|cleavage|naked)\b", re.I)


def ki(system, user):
    last = None
    for m in MODELS:
        try:
            body = {"model": m, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "response_format": {"type": "json_object"}, "temperature": 0.8}
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = json.load(r)["choices"][0]["message"]["content"]
            return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        except Exception as e:
            last = e
            print("Modell", m, "Fehler:", e)
    raise SystemExit(f"KI nicht erreichbar: {last}")


def slug(t):
    t = t.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:30]


def sim():
    themen = open("video/sim/THEMEN.md", encoding="utf-8").read()
    m = re.search(r"^- \[ \] (.+)$", themen, re.M)
    if not m:
        raise SystemExit("Kein offenes Thema in THEMEN.md")
    thema = m.group(1).strip()
    nr = 1 + max([int(re.search(r"sim-(\d+)", p).group(1)) for p in glob.glob("video/sim/sim-*.json")] or [0])
    vorlage = open("video/sim/sim-02-treppe-aufzug.json", encoding="utf-8").read() if os.path.exists("video/sim/sim-02-treppe-aufzug.json") else ""
    regeln = themen.split("## Themen-Pool")[0]
    sp = ki("Du schreibst deutsche TikTok-Simulationsvideos „Was ist besser?“. Antworte NUR mit einem JSON-Objekt. "
            "Zahlen realistisch und vorsichtig (bekannte Richtwerte von Verbraucherzentrale, Umweltbundesamt, Herstellern); "
            "nenne die Quellen im Feld quelle. Keine Marken, keine echten Personen, familienfreundlich.",
            f"Thema: {thema}\n\nRegeln und Format:\n{regeln}\n\nPflichtfelder: id, titel [2 kurze GROSSE Wörter], frage [Zeile1, Zeile2 GROSS], "
            f"modell {{typ:'generisch', einheit, zaehler, besser:'weniger'|'mehr'}}, a und b je {{name, figur (geher|laeufer|auto|rad), dauer_s, menge, info}}, "
            f"skala [3 kurze Beschriftungen], ergebnis (mit {{p}}), lines (5–7, je {{phase: intro|race|result, t}}; 1. Zeile = Frage, "
            f"mind. 2 race-Zeilen, letzte = result mit Ergebnis), caption (≤150 Zeichen, mit Emoji), hashtags (5, erstes #simulation), quelle.\n"
            f"id muss sein: sim-{nr:02d}-{slug(thema.split('–')[0])}\nBeispiel für das Format:\n{vorlage}")
    sp["id"] = f"sim-{nr:02d}-{slug(thema.split('–')[0])}"
    sp.setdefault("modell", {})["typ"] = "generisch"
    for k in ("a", "b"):
        p = sp[k]; p["dauer_s"] = float(p["dauer_s"]); p["menge"] = float(p["menge"])
        assert p["dauer_s"] > 0 and p["menge"] > 0, "Werte ungültig"
        if p.get("figur") not in ("geher", "laeufer", "auto", "rad"):
            p["figur"] = "geher"
    ph = [l.get("phase") for l in sp["lines"]]
    assert 4 <= len(ph) <= 9 and "race" in ph and ph[-1] == "result", "Sprechzeilen ungültig"
    assert len(sp["caption"]) <= 220 and len(sp["hashtags"]) >= 3
    path = f"video/sim/{sp['id']}.json"
    json.dump(sp, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
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
    ep = ki("Du schreibst die deutsche KI-Miniserie „Früchte-Drama“ für TikTok. Antworte NUR mit einem JSON-Objekt im exakt gleichen Format wie die letzte Folge. "
            "Halte dich strikt an die Serien-Bibel. Familienfreundlich, nichts Anzügliches. Bildprompts auf Englisch, Dialoge auf Deutsch.",
            f"SERIEN-BIBEL:\n{bibel}\n\nLETZTE FOLGE (Format-Vorlage):\n{json.dumps(letzte, ensure_ascii=False)}\n\n"
            f"Schreibe Folge {nr} genau nach dem Folgenplan-Eintrag F{nr:02d}. 5–7 scenes, 140–170 Wörter Dialog insgesamt, Sekunde 1 Konflikt, "
            f"Ende Cliffhanger, end = „Folge mir für Teil {nr + 1}“. Jeder Bildprompt p beginnt mit der exakten Figurenbeschreibung aus "
            f"„figuren“ der Figuren in der Szene. Verbotene Wörter in p: man, woman, girl, boy, human, person, people, sexy.")
    ep["id"], ep["episode"], ep["voices"], ep["figuren"] = f"tt-s1-f{nr:02d}", nr, f01["voices"], f01["figuren"]
    ep.setdefault("series", f01.get("series"))
    sc = ep["scenes"]
    assert 4 <= len(sc) <= 8, "Szenenzahl ungültig"
    for s in sc:
        if VERBOTEN.search(s["p"]):
            s["p"] = VERBOTEN.sub("", s["p"])
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
