"""Jarvis schreibt TikTok-Folgen selbst (ohne Claude) – mit der kostenlosen Groq-KI.
Ablauf (nach Lucas' Vorlage „Viral Studio“, 24.11.2026):
  1. Idee   – nächstes Thema aus THEMEN.md, eigene Idee über $IDEE, leerer Pool füllt sich selbst auf
  2. Fakten – erst Fakten mit Quelle sammeln, dann daraus das Skript schreiben (sim)
  3. Skript – 3 Hook-Varianten für Sekunde 1, Prüfer wählt die stärkste; Schluss mit Kommentar-Frage
  4. Prüfen – zweiter KI-Durchgang als strenger Prüfer; bei Fehlern wird einmal neu geschrieben
  python3 bot/video_auto.py sim   -> nächstes Thema aus video/sim/THEMEN.md als Spec (video/sim/sim-NN-*.json)
  python3 bot/video_auto.py tt    -> nächste Folge der Früchte-Serie nach der Serien-Bibel (video/tt/tt-s1-fNN.json)
  python3 bot/video_auto.py geld  -> nächste Folge „Kontostand“ (LED-Geldanzeige, video/geld/geld-s1-fNN.json)
  python3 bot/video_auto.py zt    -> nächste Zeichentrick-Folge „Stell dir vor“ (Finn per Code gezeichnet, video/zt/zt-NN-*.json)
Gibt den Pfad der neuen Spec aus (und schreibt ihn nach $GITHUB_OUTPUT als spec=...)."""
import glob, json, os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ki_router

KEY = os.environ.get("GROQ_KEY", "")
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
VERBOTEN = re.compile(r"\b(man|woman|women|men|girl|boy|human|person|people|sexy|bikini|bra|crop top|cleavage|naked)\b", re.I)


PRUEFRUNDEN = 3  # so oft wird jede Folge geprüft und verbessert, bevor sie gerendert wird


def ki(system, user, temp=0.8):
    last = None
    for runde in range(3):  # bei Groq-Limit (429) warten und es noch einmal versuchen – wichtig beim Wochen-Vorrat
        limit = 0
        for m in (MODELS if KEY else []):
            try:
                body = {"model": m, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                        "response_format": {"type": "json_object"}, "temperature": temp}
                req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(body).encode(),
                                             {"Content-Type": "application/json", "Authorization": "Bearer " + KEY, "User-Agent": "jarvis-bot"})  # ohne User-Agent: Groq antwortet 403
                with urllib.request.urlopen(req, timeout=120) as r:
                    txt = json.load(r)["choices"][0]["message"]["content"]
                return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
            except urllib.error.HTTPError as e:
                last = e
                print("Modell", m, "Fehler:", e)
                if e.code == 429:
                    limit = max(limit, min(90, float(e.headers.get("retry-after") or 30)))
            except Exception as e:
                last = e
                print("Modell", m, "Fehler:", e)
        # Groq weg -> KI-Weiche (Gemini, OpenRouter, Ollama) statt Abbruch
        txt = ki_router.weiter([{"role": "system", "content": system}, {"role": "user", "content": user}], json_mode=True, temp=temp)
        if txt and "{" in txt:
            return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        if not limit or runde == 2:
            break
        print(f"Groq-Limit – warte {limit + 30 * runde:.0f} s")
        time.sleep(limit + 30 * runde)
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
    f = []
    for x in r.get("fakten", []) if isinstance(r.get("fakten"), list) else []:
        if isinstance(x, str):  # manche Modelle liefern nur Sätze
            x = {"satz": x, "quelle": ""}
        if isinstance(x, dict) and str(x.get("satz", "")).strip():
            f.append({"satz": str(x["satz"]).strip(), "wert": str(x.get("wert", "")), "quelle": str(x.get("quelle", "")).strip() or "Richtwert"})
    assert len(f) >= 2, "Zu wenige Fakten"
    an = r.get("annahmen", [])
    return {"fakten": f, "annahmen": [str(a) for a in an] if isinstance(an, list) else [str(an)]}


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
            f"modell {{typ:'generisch', einheit, zaehler, besser:'weniger'|'mehr'}}, a und b je {{name, figur (geher|laeufer|auto|rad), dauer_s, menge, info (max. 25 Zeichen)}}, "
            f"skala [3 kurze Beschriftungen], ergebnis (mit {{p}}), lines (5–7, je {{phase: intro|race|result, t}}; 1. Zeile = Frage, "
            f"mind. 2 race-Zeilen, letzte = result mit Ergebnis; Zahlen und Einheiten ausgeschrieben sprechbar, keine Pfeile/Formeln), "
            f"hooks [3 verschiedene Einstiegssätze für Sekunde 1, je max. 10 Wörter: 1× Frage, 1× überraschende Zahl, 1× Behauptung/Mythos], "
            f"kommentar_frage (kurze Frage an die Zuschauer, die zum Kommentieren bringt, z. B. „Was hättest du getippt?“, max. 8 Wörter), "
            f"caption (≤150 Zeichen, mit Emoji), hashtags (5, erstes #simulation), quelle.\n"
            f"id muss sein: {sid}\nBeispiel für das Format:\n{vorlage}" +
            (f"\n\nDER PRÜFER HAT FOLGENDES BEMÄNGELT – unbedingt beheben:\n- " + "\n- ".join(feedback) if feedback else ""))
    sp["id"] = sid
    sp.setdefault("modell", {})["typ"] = "generisch"
    for k in ("a", "b"):
        p = sp[k]; p["dauer_s"] = float(p["dauer_s"]); p["menge"] = float(p["menge"])
        assert p["dauer_s"] > 0 and p["menge"] >= 0, "dauer_s muss > 0 und menge ≥ 0 sein"
        if p.get("figur") not in ("geher", "laeufer", "auto", "rad"):
            p["figur"] = "geher"
    mengen = sorted([sp["a"]["menge"], sp["b"]["menge"]])
    assert mengen[1] > 0, "mindestens eine menge muss > 0 sein"  # 0 ist erlaubt (z. B. Fahrrad: 0 € Sprit)
    if sp["modell"].get("besser") == "mehr":
        assert mengen[0] > 0, "bei besser=mehr muss auch die kleinere menge > 0 sein"
    sp["lines"] = [l if isinstance(l, dict) else {"phase": "race", "t": str(l)} for l in sp["lines"]]
    if sp["lines"] and sp["lines"][-1].get("phase") != "result":
        sp["lines"][-1]["phase"] = "result"
    if isinstance(sp.get("hashtags"), str):
        sp["hashtags"] = sp["hashtags"].split()
    ph = [l.get("phase") for l in sp["lines"]]
    assert 4 <= len(ph) <= 8 and "race" in ph and ph[-1] == "result", "Sprechzeilen ungültig"
    assert len(sp["caption"]) <= 220 and len(sp["hashtags"]) >= 3
    sp["hooks"] = [h.strip() for h in sp.get("hooks", []) if isinstance(h, str) and 2 <= len(h.split()) <= 14][:3]
    return sp


def sprechbar(t):
    """Symbole, die die KI-Stimme falsch oder gar nicht vorliest, in Wörter umwandeln."""
    t = str(t).replace("\u202f", " ").replace("\u00a0", " ")
    for a, b in ((" → ", ", "), ("→", ", "), (" + ", " plus "), (" = ", " gleich "), (" ≈ ", " etwa "), ("≈", "etwa "),
                 ("km/h", "Kilometer pro Stunde"), (" %", " Prozent"), ("%", " Prozent")):
        t = t.replace(a, b)
    t = re.sub(r"(\d)\s*min\b", r"\1 Minuten", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def kurz(t, n=26):
    t = str(t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;–-")


def sim_fertig(sp, hook):
    """Stärksten Hook nach vorn, Kommentar-Frage ans Ende (Engagement), Faktenliste in die Quelle."""
    if sp.get("hooks"):
        sp["lines"][0]["t"] = sp["hooks"][min(max(hook, 0), len(sp["hooks"]) - 1)]
    fr = str(sp.get("kommentar_frage", "")).strip()
    if fr and len(fr.split()) <= 12:
        sp["lines"].append({"phase": "result", "t": fr.rstrip("?") + "? Schreib es in die Kommentare."})
        if fr not in sp["caption"]:
            sp["caption"] = (sp["caption"] + " " + fr.rstrip("?") + "? 👇")[:220]
    for l in sp["lines"]:
        l["t"] = sprechbar(l["t"])
    for k in ("a", "b"):  # lange Info-Zeile überlappt sonst „IM ZIEL“
        sp[k]["info"] = kurz(sp[k].get("info", ""))
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
    try:
        fk = fakten(thema)
    except (AssertionError, AttributeError, TypeError):
        fk = fakten(thema)
    try:
        sp = sim_schreiben(thema, sid, fk, regeln, vorlage)
    except (AssertionError, KeyError, ValueError, TypeError, AttributeError) as e:  # Formfehler der KI → 1× mit Hinweis neu
        print("Format-Fehler, neuer Versuch:", repr(e))
        sp = sim_schreiben(thema, sid, fk, regeln, vorlage, [f"Formatfehler: {e!r} – alle Pflichtfelder korrekt füllen"])
    # 3 Prüfrunden: prüfen → verbessern → nochmal prüfen (Lucas will 3-fache Kontrolle vor dem Posten)
    for runde in range(1, PRUEFRUNDEN + 1):
        probleme, hook = pruefen("Simulations", sp, "FAKTEN:\n" + json.dumps(fk, ensure_ascii=False))
        print(f"Prüfrunde {runde}/{PRUEFRUNDEN}:", probleme or "ok")
        if not probleme:
            break
        try:
            sp = sim_schreiben(thema, sid, fk, regeln, vorlage, probleme)
        except (AssertionError, KeyError, ValueError, TypeError, AttributeError) as e:
            print("Verbesserung fehlgeschlagen:", repr(e)); break
    sp = sim_fertig(sp, hook)
    sp["fakten"] = fk["fakten"]
    path = f"video/sim/{sp['id']}.json"
    json.dump(sp, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if m:
        open("video/sim/THEMEN.md", "w", encoding="utf-8").write(themen.replace(m.group(0), f"- [x] {thema} ({sp['id']})", 1))
    return path


def serie(ordner, prefix, bibel_datei, name, max_folgen, extra=""):
    """Nächste Folge einer Serie nach ihrer Bibel schreiben, 3× prüfen, Format absichern."""
    bibel = open(bibel_datei, encoding="utf-8").read()
    files = sorted(glob.glob(f"{ordner}/{prefix}-f*.json"))
    letzte = json.load(open(files[-1], encoding="utf-8"))
    f01 = json.load(open(f"{ordner}/{prefix}-f01.json", encoding="utf-8"))
    nr = int(re.search(r"f(\d+)", files[-1]).group(1)) + 1
    if nr > max_folgen:
        raise SystemExit(f"Staffel ({name}) ist fertig – nächste Staffel muss geplant werden.")
    def schreiben(feedback=None):
        return ki(f"Du schreibst die deutsche KI-Miniserie „{name}“ für TikTok. Antworte NUR mit einem JSON-Objekt im exakt gleichen Format wie die letzte Folge. "
            "Halte dich strikt an die Serien-Bibel. Familienfreundlich, nichts Anzügliches. Bildprompts auf Englisch, Dialoge auf Deutsch.",
            f"SERIEN-BIBEL:\n{bibel}\n\nLETZTE FOLGE (Format-Vorlage):\n{json.dumps(letzte, ensure_ascii=False)}\n\n"
            f"Schreibe Folge {nr} genau nach dem Folgenplan-Eintrag F{nr:02d}. 5–7 scenes, 140–170 Wörter Dialog insgesamt, Sekunde 1 Konflikt, "
            f"Ende Cliffhanger, end wie in der Bibel mit Teil {nr + 1}. Jeder Bildprompt p beginnt mit der exakten Figurenbeschreibung aus "
            f"„figuren“ der Figuren in der Szene. Verbotene Wörter in p: man, woman, girl, boy, human, person, people, sexy.{extra}" +
            (f"\n\nDER PRÜFER HAT FOLGENDES BEMÄNGELT – unbedingt beheben:\n- " + "\n- ".join(feedback) if feedback else ""))

    ep = schreiben()
    for runde in range(1, PRUEFRUNDEN + 1):  # 3 Prüfrunden mit Verbesserung
        probleme = pruefen("Serien-Folge", ep, f"Muss zur Serien-Bibel passen (Folgenplan F{nr:02d}, Figuren, Ton), Sekunde 1 Konflikt, Ende Cliffhanger, "
                           f"Bildprompts zeigen nur Obst-/Gemüse-Figuren, Untertitel-Sätze kurz und fehlerfrei.\nBIBEL:\n{bibel[:6000]}")[0]
        print(f"Prüfrunde {runde}/{PRUEFRUNDEN}:", probleme or "ok")
        if not probleme:
            break
        ep = schreiben(probleme)
    ep["id"], ep["episode"], ep["voices"], ep["figuren"] = f"{prefix}-f{nr:02d}", nr, f01["voices"], f01["figuren"]
    ep.setdefault("series", f01.get("series"))
    if "konten" in f01:
        konten_sichern(ep, letzte)
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
    path = f"{ordner}/{ep['id']}.json"
    json.dump(ep, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def konten_sichern(ep, letzte):
    """Kontostand-Format: Startwerte = Endstand der letzten Folge; je Szene nur bekannte Figuren, ganze Euro ≥ 0, max. 3 Anzeigen."""
    stand = dict(letzte.get("konten", {}))
    for s in letzte.get("scenes", []):
        stand.update(s.get("konto") or {})
    ep["konten"] = dict(stand)
    for s in ep["scenes"]:
        k = s.get("konto") if isinstance(s.get("konto"), dict) else {}
        sauber = {}
        for wer, wert in k.items():
            if wer not in ep["figuren"]:
                continue
            try:
                wert = int(float(str(wert).replace("€", "").replace(".", "").replace(",", ".").strip()))
            except ValueError:
                wert = stand.get(wer, 0)
            sauber[wer] = max(0, wert)
        if not sauber:  # Szene ohne Angaben: Figuren, die sprechen, mit ihrem letzten Stand zeigen
            for l in s.get("lines", []):
                if l.get("s") in stand:
                    sauber[l["s"]] = stand[l["s"]]
        s["konto"] = dict(list(sauber.items())[:3])
        stand.update(s["konto"])


def tt():
    return serie("video/tt", "tt-s1", "video/tt/00-STAFFEL-1-BIBEL.md", "Früchte-Drama", 14)


def geld():
    return serie("video/geld", "geld-s1", "video/geld/00-BIBEL.md", "Kontostand", 10,
                 " Jede Szene braucht konto = {Figur: Betrag in ganzen Euro} für die Figuren im Bild (max. 3); "
                 "Beträge ändern sich nur, wenn die Handlung es zeigt. Keine Zahlen oder Schrift in den Bildprompts.")


ZT_BG = {"zimmer", "bett", "schreibtisch", "strasse", "schule", "kueche", "nacht"}
ZT_POSE = {"neutral", "staunen", "schock", "freude", "traurig", "denken", "zeigen", "schlafen"}
ZT_PROP = {"keins", "handy", "wecker", "geld", "brief", "laptop"}


def zt_schreiben(thema, nr, bibel, vorlage, feedback=None):
    return ki("Du schreibst die deutsche Zeichentrick-Reihe „Stell dir vor“ für TikTok. Antworte NUR mit einem JSON-Objekt im exakt gleichen Format wie die Vorlage. "
              "Halte dich strikt an die Serien-Bibel: ruhig, Du-Ansprache, ein einziger Moment, echt statt übertrieben. Familienfreundlich, keine Marken, keine echten Personen.",
              f"SERIEN-BIBEL:\n{bibel}\n\nVORLAGE (Format):\n{vorlage}\n\nTHEMA: {thema}\n\n"
              f"Schreibe Folge {nr}: 5–8 scenes, insgesamt 70–130 Wörter in text. Szene 1 sofort der Moment (Sekunde 0–3). "
              "Höchstens 3 Szenen mit zahl, die Zahlen steigen. Vor der größten Zahl pause 0.8–1.5. Letzte Szene: Frage an den Zuschauer, "
              "auf die jeder von sich selbst erzählt. bg/pose/prop NUR aus den erlaubten Werten der Bibel. "
              "Felder: id (leer lassen), series, episode, title, caption (mit Frage + 👇), hashtags (5), end (z. B. „TEIL 2? SCHREIB'S IN DIE KOMMENTARE“), thema, scenes."
              + (f"\n\nDER PRÜFER HAT FOLGENDES BEMÄNGELT – unbedingt beheben:\n- " + "\n- ".join(feedback) if feedback else ""))


def zt_sauber(sp):
    sc = [s for s in sp.get("scenes", []) if isinstance(s, dict) and str(s.get("text", "")).strip()]
    assert 4 <= len(sc) <= 9, "Szenenzahl ungültig"
    for s in sc:
        s["bg"] = s.get("bg") if s.get("bg") in ZT_BG else "zimmer"
        s["pose"] = s.get("pose") if s.get("pose") in ZT_POSE else "neutral"
        s["prop"] = s.get("prop") if s.get("prop") in ZT_PROP else "keins"
        s["text"] = sprechbar(s["text"])
        if s.get("zahl") is not None:
            try:
                s["zahl"] = max(0, int(float(str(s["zahl"]).replace(".", "").replace(",", ".").replace("€", ""))))
            except ValueError:
                s.pop("zahl")
        try:
            s["pause"] = min(2.0, max(0.0, float(s.get("pause", 0) or 0)))
        except (TypeError, ValueError):
            s["pause"] = 0
    woerter = sum(len(s["text"].split()) for s in sc)
    assert 55 <= woerter <= 170, f"Textlänge {woerter} Wörter"
    sp["scenes"] = sc
    return sp


def zt():
    """Zeichentrick „Stell dir vor“: Thema aus video/zt/THEMEN.md, schreiben, 3× prüfen, Format absichern."""
    bibel = open("video/zt/00-BIBEL.md", encoding="utf-8").read()
    themen = open("video/zt/THEMEN.md", encoding="utf-8").read()
    idee = os.environ.get("IDEE", "").strip()
    m = None
    if idee:
        thema = idee
    else:
        if not re.search(r"^- \[ \] .+$", themen, re.M):
            neu = ki("Du findest Themen für die TikTok-Reihe „Stell dir vor“. Antworte NUR mit JSON.",
                     f"{bibel}\n\nBisherige Themen:\n{themen}\n\nDenk dir 8 neue Themen aus, die BEIDE Fragen bestehen "
                     "(Kann mir das passieren? Wie sieht mein Leben dann aus?). Jedes ein einziger Moment in einem Satz, Du-Form, Alltag. "
                     '{"themen": ["..."]}', 0.9).get("themen", [])
            themen = themen.rstrip() + "\n" + "".join(f"- [ ] {str(t).strip()}\n" for t in neu if str(t).strip())
            open("video/zt/THEMEN.md", "w", encoding="utf-8").write(themen)
        m = re.search(r"^- \[ \] (.+)$", themen, re.M)
        thema = m.group(1).strip()
    files = sorted(glob.glob("video/zt/zt-*.json"))
    nr = 1 + max([int(re.search(r"zt-(\d+)", p).group(1)) for p in files] or [0])
    vorlage = open(files[0], encoding="utf-8").read() if files else ""
    try:
        sp = zt_sauber(zt_schreiben(thema, nr, bibel, vorlage))
    except (AssertionError, KeyError, ValueError, TypeError, AttributeError) as e:
        print("Format-Fehler, neuer Versuch:", repr(e))
        sp = zt_sauber(zt_schreiben(thema, nr, bibel, vorlage, [f"Formatfehler: {e!r}"]))
    for runde in range(1, PRUEFRUNDEN + 1):
        probleme = pruefen("Zeichentrick", sp, "Muss zur Bibel passen: EIN Moment, Du-Ansprache, ruhig und echt, Szene 1 sofort spannend, "
                           "Zahlen steigen glaubwürdig, Schluss-Frage lädt ein, von sich zu erzählen. Rechtschreibung.\nBIBEL:\n" + bibel)[0]
        print(f"Prüfrunde {runde}/{PRUEFRUNDEN}:", probleme or "ok")
        if not probleme:
            break
        try:
            sp = zt_sauber(zt_schreiben(thema, nr, bibel, vorlage, probleme))
        except (AssertionError, KeyError, ValueError, TypeError, AttributeError) as e:
            print("Verbesserung fehlgeschlagen:", repr(e)); break
    sp["id"], sp["episode"], sp["series"], sp["thema"] = f"zt-{nr:02d}-{slug(thema)[:24].strip('-')}", nr, "Stell dir vor", thema
    path = f"video/zt/{sp['id']}.json"
    json.dump(sp, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if m:
        open("video/zt/THEMEN.md", "w", encoding="utf-8").write(themen.replace(m.group(0), f"- [x] {thema} ({sp['id']})", 1))
    return path


if __name__ == "__main__":
    if not (KEY or ki_router.anbieter()):
        raise SystemExit("Kein KI-Schlüssel (GROQ_KEY, GEMINI_KEY oder OPENROUTER_KEY) – GitHub → Settings → Secrets → Actions")
    p = {"sim": sim, "tt": tt, "geld": geld, "zt": zt}[sys.argv[1]]()
    print(p)
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"spec={p}\n")
