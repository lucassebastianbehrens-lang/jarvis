"""Schnelltests für die Bots – ohne Internet. Start: python3 tests/test_bots.py"""
import glob, json, os, sys, tempfile, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bot"))
fehler = []


def check(name, bed, info=""):
    print(("✓ " if bed else "✕ ") + name + (f" – {info}" if info and not bed else ""))
    bed or fehler.append(name)


# jlib
import jlib
check("jlib: JSON aus KI-Text lesen", jlib.parse_json('Hier:\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]})
os.environ.pop("GROQ_KEY", None)
check("jlib: ohne Schlüssel leere Antwort statt Absturz", jlib.ki("s", "u") == "" or not jlib.GROQ)

# KI-Weiche: ohne Schlüssel leer, mit (nachgestellter) Ollama-KI kommt die Antwort von dort
import ki_router, threading, http.server
for k in ("GEMINI_KEY", "OPENROUTER_KEY", "OLLAMA_URL"):
    os.environ.pop(k, None)
check("KI-Weiche: ohne Schlüssel leer statt Absturz", ki_router.weiter([{"role": "user", "content": "hi"}]) == "")
class _Fake(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        b = json.dumps({"choices": [{"message": {"content": "Hallo Lucas"}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a):
        pass
_srv = http.server.HTTPServer(("127.0.0.1", 0), _Fake)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
os.environ["OLLAMA_URL"] = f"http://127.0.0.1:{_srv.server_port}"
check("KI-Weiche: Groq weg → Ollama antwortet", jlib.ki("s", "u") == "Hallo Lucas")
os.environ.pop("OLLAMA_URL"); _srv.shutdown()

# Lage-Bot
import lage
L = lambda t: lage.laender_von({"titel": t, "text": ""})
check("Lage: USA + Russland erkannt", L("Die USA und Russland verhandeln") == ["USA", "Russland"])
check("Lage: Neu-Delhi ist nicht EU", L("Neu-Delhi meldet Hitze") == ["Indien"])
check("Lage: Romantik ist nicht Rom", "Italien" not in L("Romantik in Paris"))
with tempfile.TemporaryDirectory() as d:
    feed = pathlib.Path(d) / "f.xml"
    feed.write_text('<?xml version="1.0"?><rss><channel><item><title>Russland greift Kiew an</title><link>https://x.de/1</link>'
                    '<description>Tote in der Ukraine</description></item><item><title>Wetter</title><link>https://x.de/2</link></item></channel></rss>')
    alt_store, gespeichert = lage.store, {}
    lage.store = lambda n, o: gespeichert.update(o)
    lage.FEEDS, lage.maerkte, lage.ki = [("t", feed.as_uri())], (lambda: ([], {})), (lambda *a, **k: "")
    lage.main()
    lage.store = alt_store
    check("Lage: Feed → Länder + Hotspot", gespeichert["orte"][0]["heiss"] >= 1 and len(gespeichert["orte"]) == 2, str(gespeichert.get("orte"))[:200])
    check("Lage: Lagebild auch ohne KI", "Wichtigste Meldung" in gespeichert["lagebild"])

# Videofabrik: Bildprompts säubern, ohne Verneinungen zu zerstören
import video_auto
sp = video_auto.saeubern("a walking red onion, wearing a floral apron, no human face, no human skin, sexy")
check("Video: 'no human face' wird nicht zu 'no face'", "no face" not in sp and "no skin" not in sp, sp)

# Videofabrik: Fakten → Skript → Prüfer → bester Hook + Kommentar-Frage (KI gemockt, ohne Internet)
_ki_alt, _antworten = video_auto.ki, []
def _fake_ki(system, user, temp=0.8):
    _antworten.append(user)
    if "Kernfakten" in user:
        return {"fakten": [{"satz": "Wasserkocher braucht ca. 0,11 kWh pro Liter", "wert": "0,11", "quelle": "Verbraucherzentrale"},
                           {"satz": "Elektroherd braucht ca. 0,19 kWh pro Liter", "wert": "0,19", "quelle": "Verbraucherzentrale"}]}
    if "Reality Checker" in system:
        return {"ok": len(_antworten) > 3, "probleme": ["Prozentwert passt nicht"], "bester_hook": 1}
    return {"titel": ["KOCHER", "HERD"], "frage": ["Was ist", "SPARSAMER?"], "modell": {"einheit": "kWh", "zaehler": "Strom", "besser": "weniger"},
            "a": {"name": "KOCHER", "figur": "xyz", "dauer_s": "3", "menge": 0.11}, "b": {"name": "HERD", "figur": "auto", "dauer_s": 6, "menge": 0.19},
            "lines": [{"phase": "intro", "t": "Frage"}, {"phase": "race", "t": "a"}, {"phase": "race", "t": "b"}, {"phase": "result", "t": "Ergebnis"}],
            "hooks": ["Kocht dein Herd heimlich Geld weg?", "Fast doppelt so viel Strom fürs gleiche Wasser!", "Herd ist sparsamer – stimmt nicht."],
            "kommentar_frage": "Was hättest du getippt?", "caption": "Kocher oder Herd? ⚡", "hashtags": ["#simulation", "#strom", "#sparen"], "quelle": "VZ"}
video_auto.ki = _fake_ki
fk = video_auto.fakten("Wasserkocher vs Herd")
sp = video_auto.sim_schreiben("Wasserkocher vs Herd", "sim-99-test", fk, "", "")
probleme, hook = video_auto.pruefen("Simulations", sp, "")
check("Video: Prüfer meldet Fehler → Neuschreiben", probleme == ["Prozentwert passt nicht"])
sp2 = video_auto.sim_schreiben("Wasserkocher vs Herd", "sim-99-test", fk, "", "", probleme)
check("Video: Prüfer-Kritik landet im neuen Auftrag", "Prozentwert passt nicht" in _antworten[-1])
check("Video: Prüfer zufrieden beim 2. Mal", video_auto.pruefen("Simulations", sp2, "")[0] == [])
sp2 = video_auto.sim_fertig(sp2, hook)
check("Video: stärkster Hook steht vorn", sp2["lines"][0]["t"].startswith("Fast doppelt"), sp2["lines"][0]["t"])
check("Video: Kommentar-Frage am Ende + in Caption", sp2["lines"][-1]["phase"] == "result" and "Kommentare" in sp2["lines"][-1]["t"] and "👇" in sp2["caption"])
_alt_fake = video_auto.ki
def _null_ki(system, user, temp=0.8):
    r = _fake_ki(system, user, temp); r["a"]["menge"] = 0; return r
video_auto.ki = _null_ki
check("Video: menge 0 erlaubt (z. B. Fahrrad 0 € Sprit)", video_auto.sim_schreiben("x", "sim-98-x", fk, "", "")["a"]["menge"] == 0.0)
video_auto.ki = lambda s_, u, t=0.8: {"fakten": ["Rad kostet 0 € Sprit", {"satz": "Auto ca. 7 l/100 km", "quelle": "ADAC-Richtwert"}], "annahmen": "gleiche Strecke"}
fk2 = video_auto.fakten("Auto vs Fahrrad")
check("Video: Fakten als reine Sätze werden akzeptiert", len(fk2["fakten"]) == 2 and fk2["fakten"][0]["quelle"] == "Richtwert", str(fk2))
def _str_lines(system, user, temp=0.8):
    r = _fake_ki(system, user, temp); r["lines"] = ["Frage?", "a", "b", "Ergebnis"]; r["hashtags"] = "#simulation #a #b"; return r
video_auto.ki = _str_lines
sp3 = video_auto.sim_schreiben("x", "sim-97-x", fk, "", "")
check("Video: Zeilen als Text + Hashtags als Text werden repariert", sp3["lines"][-1]["phase"] == "result" and len(sp3["hashtags"]) == 3)
video_auto.ki = _alt_fake
check("Video: Sprechtext ohne Pfeile/Formeln", video_auto.sprechbar("Auto 15 km/h → 20 min + 10 min = 30 min") == "Auto 15 Kilometer pro Stunde, 20 Minuten plus 10 Minuten gleich 30 Minuten")
check("Video: Info-Zeile gekürzt ohne Wortbruch", video_auto.kurz("30 min inkl. 10 min Parkplatzsuche") == "30 min inkl. 10 min")
check("Video: unbekannte Figur → geher, Zahlen als float", sp2["a"]["figur"] == "geher" and sp2["a"]["dauer_s"] == 3.0)
def _ki_weg(*a, **k): raise SystemExit("offline")
video_auto.ki = _ki_weg
check("Video: Prüfer offline blockiert nicht", video_auto.pruefen("x", {}, "") == ([], 0))
video_auto.ki = lambda s, u, t=0.8: {"themen": ["Duschen vs Baden – wer spart Wasser?", "Rennen vs Gehen im Regen – wer wird weniger nass?", "kein Vergleich"]}
neu = video_auto.neue_themen("## Themen-Pool\n- [x] Rennen vs Gehen im Regen – wer wird weniger nass? (sim-01)\n")
check("Video: leerer Pool füllt sich ohne Dopplungen", "- [ ] Duschen vs Baden" in neu and neu.count("Rennen vs Gehen") == 1, neu)
video_auto.ki = _ki_alt
# Kontostand-Serie: LED-Beträge werden abgesichert, Grafik entsteht
ep = {"figuren": {"Kalle": "x", "Anton": "y"}, "scenes": [
    {"konto": {"Kalle": "€27", "Fremder": 5, "Anton": -3}, "lines": [{"s": "Kalle", "t": "a"}]},
    {"lines": [{"s": "Anton", "t": "b"}]}]}
video_auto.konten_sichern(ep, {"konten": {"Kalle": 12, "Anton": 4800000}, "scenes": [{"konto": {"Kalle": 20}}]})
check("Kontostand: Startwerte aus letzter Folge", ep["konten"]["Kalle"] == 20, ep["konten"])
check("Kontostand: Beträge sauber, Fremde raus", ep["scenes"][0]["konto"] == {"Kalle": 27, "Anton": 0}, ep["scenes"][0])
check("Kontostand: leere Szene zeigt Sprecher", ep["scenes"][1]["konto"] == {"Anton": 0}, ep["scenes"][1])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "video"))
import tt as _tt
check("Kontostand: Euro-Format", _tt.euro(4800000) == "€4.800.000" and _tt.euro(12) == "€12")
with tempfile.TemporaryDirectory() as d:
    _tt.konto_bild(d + "/k.png", {"Kalle": 27, "Anton": 4800000}, {"Kalle": 12})
    check("Kontostand: LED-Grafik erzeugt", os.path.getsize(d + "/k.png") > 5000)
for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "video", "geld", "geld-*.json"))):
    g = json.load(open(f, encoding="utf-8"))
    check(f"Kontostand: {os.path.basename(f)} hat konto + Stimmen", all(s.get("konto") for s in g["scenes"]) and
          all(l["s"] in g["voices"] for s in g["scenes"] for l in s["lines"]))
check("Video: Schürze/Verbotenes entfernt", "apron" not in sp and "sexy" not in sp, sp)

# Telegram-Jarvis: Leibgarde parallel, Chat frei
import jarvis_live as J
with tempfile.TemporaryDirectory() as d:
    J.F_Q, said = d + "/q.json", []
    J.say = lambda t: said.append(t)
    J.ki = lambda msgs: (time.sleep(0.5), "Ergebnis")[1]
    J.gedaechtnis_text = J.lern_text = lambda: ""
    t0 = time.time()
    for i in range(4):
        J.aufgabe_neu(f"Aufgabe {i}")
    check("Telegram: Chat sofort wieder frei", time.time() - t0 < 0.3)
    time.sleep(1.6)
    q = json.load(open(J.F_Q))
    check("Telegram: 4 Aufträge mit 3 Helfern erledigt", all(a["status"] == "fertig" for a in q) and len(q) == 4, str(q))
    check("Telegram: Helfer haben Namen", any("Ben ist fertig" in s for s in said))

# Claude-Fähigkeiten im Telegram-Jarvis (Fotos, Dokumente, Links, Dateien, Rechnen, /neu)
import io, zipfile, threading as _th, http.server as _hs
with tempfile.TemporaryDirectory() as d:
    J.F_HIST, J.F_DOK, said, calls = d + "/h.json", d + "/dok.json", [], []
    J.say = lambda t: said.append(t)
    J.tg = lambda method, **p: calls.append((method, p)) or {"result": {"file_path": "x"}}
    J.im_hintergrund = lambda titel, fn: fn("Ben")
    check("Rechnen: 19 % von 249,90", J.rechnen("19 % von 249,90") == "47,481", J.rechnen("19 % von 249,90"))
    check("Rechnen: Punkt vor Strich + Tausender", J.rechnen("1.250 + 3 * 2,5") == "1.257,5", J.rechnen("1.250 + 3 * 2,5"))
    try:
        J.rechnen("__import__('os')"); check("Rechnen: kein Code ausführbar", False)
    except Exception:
        check("Rechnen: kein Code ausführbar", True)
    said.clear(); J.handle({"text": "rechne 12*(3+4)", "message_id": 1})
    check("Rechnen über Chat", said and said[-1].endswith("= 84"), str(said))
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, "w")
    z.writestr("word/document.xml", "<w:document><w:p><w:t>Mietvertrag</w:t></w:p><w:p><w:t>Miete 650 Euro</w:t></w:p></w:document>"); z.close()
    t = J.text_aus_datei("vertrag.docx", buf.getvalue())
    check("Word-Datei lesen", "Mietvertrag" in t and "650" in t, t)
    check("HTML lesen ohne Skripte", J.html_zu_text("<p>Hallo</p><script>böse()</script><p>Welt</p>").split() == ["Hallo", "Welt"])
    seen = {}
    J.tg_datei = lambda fid: buf.getvalue()
    J.ki = lambda msgs: (seen.update(m=msgs), "Kurzfassung: Miete 650 €")[1]
    said.clear(); J.handle({"document": {"file_id": "f1", "file_name": "vertrag.docx", "file_size": 999}, "caption": "Wie hoch ist die Miete?", "message_id": 2})
    check("Dokument: Frage beantwortet", any("650" in x for x in said) and "Wie hoch ist die Miete" in seen["m"][-1]["content"], str(said))
    seen.clear(); said.clear(); J.load = J.load; J.handle({"text": "Was steht im Dokument zur Kaution?", "message_id": 3})
    check("Dokument: Folgefrage kennt den Text", "Mietvertrag" in seen["m"][0]["content"])
    J.foto_frage = lambda m, f: said.append("FOTO:" + f)
    said.clear(); J.handle({"photo": [{"file_id": "p"}], "caption": "Welche Pflanze ist das?", "message_id": 4})
    check("Foto + Frage geht an die Bild-KI", said == ["FOTO:Welche Pflanze ist das?"], str(said))
    class _S(_hs.BaseHTTPRequestHandler):
        def do_GET(self):
            b = "<html><title>x</title><body><h1>Angebot</h1><p>Preis 19,99 Euro</p><script>x()</script></body></html>".encode()
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(b)
        def log_message(self, *a):
            pass
    srv = _hs.HTTPServer(("127.0.0.1", 0), _S); _th.Thread(target=srv.serve_forever, daemon=True).start()
    seen.clear(); said.clear(); J.handle({"text": f"http://127.0.0.1:{srv.server_port}/angebot was kostet das?", "message_id": 5})
    check("Link lesen + Frage", "Preis 19,99" in seen["m"][-1]["content"] and "was kostet das" in seen["m"][-1]["content"], str(seen))
    srv.shutdown()
    gesendet = []
    J.datei_senden = lambda name, inhalt, text="": gesendet.append((name, inhalt))
    J.ki = lambda msgs: "Datum;Betrag\n01.12.;12,50"
    J.handle({"text": "Erstelle eine Tabelle für mein Haushaltsbudget", "message_id": 6})
    check("Datei erstellen: Tabelle als CSV", gesendet and gesendet[-1][0].endswith(".csv") and b"Betrag" in gesendet[-1][1], str(gesendet))
    J.ki = lambda msgs: "<!doctype html><html><body>Hi</body></html>"
    J.handle({"text": "Erstelle eine Webseite für meinen Grillstand", "message_id": 7})
    check("Datei erstellen: Webseite als HTML", gesendet[-1][0].endswith(".html"), str(gesendet[-1][0]))
    os.environ.pop("GH_TOKEN", None); said.clear()
    J.handle({"text": "Jarvis bau mir einen Shop für Hundeleinen", "message_id": 10})
    check("Shop-Befehl erkannt (ohne Schlüssel: Anleitung mit Link)", said and "shop-bau.yml" in said[-1], str(said))
    json.dump([{"role": "user", "content": "alt"}], open(J.F_HIST, "w"))
    said.clear(); J.handle({"text": "/neu", "message_id": 8})
    check("/neu leert den Verlauf", json.load(open(J.F_HIST)) == [], open(J.F_HIST).read())
    J.ki = lambda msgs: "A" * 5000
    calls.clear(); said.clear(); J.handle({"text": "erzähl ausführlich", "message_id": 9})
    check("Lange Antwort wird geteilt", said and len(said[0]) == 1100 and len(calls[-1][1]["text"]) == 3900, f"{[len(x) for x in said]}")

# Shop-Baukasten: Panel unter 75 % -> überarbeiten -> erneut testen, bis bestanden
import shop_bau as SB
with tempfile.TemporaryDirectory() as d:
    SB.ROOT = d; SB.screenshot = lambda h: None; SB.time.sleep = lambda s: None
    runden = {"plan": 0, "panel": 0}
    PLAN = {"name": "Pfotenglück", "slogan": "Leinen mit Liebe", "palette": "wald", "hero_titel": "Handgemachte Hundeleinen",
            "hero_text": "Robust. Schön.", "cta": "Ansehen", "vorteile": [{"emoji": "🚚", "titel": "Schnell", "text": "2 Tage"}] * 4,
            "produkte": [{"emoji": "🐕", "name": f"Leine {i}", "preis": 19.9 + i, "alter_preis": None, "kurz": "Stark",
                          "details": ["Tau", "2 m", "Karabiner"], "badge": "Neu" if i == 0 else ""} for i in range(4)],
            "geschichte": "Lucas näht.", "angebot": "Versandkostenfrei ab 30 €", "faq": [{"f": "Lieferzeit?", "a": "2–3 Tage"}] * 5,
            "seo_titel": "Hundeleinen", "seo_beschreibung": "Handgemacht", "tiktok_ideen": ["Leine im Test"]}
    def fake_ki(system, user, search=False, json_mode=False):
        if "simulierst" in system:
            runden["panel"] += 1
            gut = runden["panel"] > 10  # Ausgangsstand (2 × 5 Gruppen) schlecht, danach gut
            return json.dumps({"kunden": [{"nr": i + 1, "note": 9 if gut else 5, "sehr_gut": gut, "oefter_kaufen": gut,
                                           "kritik": "Preise zu hoch" if not gut else "-", "wunsch": "günstiger"} for i in range(5)]})
        runden["plan"] += 1
        if runden["plan"] > 1:
            check("Shop: Überarbeitung bekommt die Kundenkritik", "Preise zu hoch" in user and "Kunden" in user)
        return json.dumps(PLAN)
    SB.jlib.ki = fake_ki
    ok = SB.main("Shop für handgemachte Hundeleinen")
    info = json.load(open(d + "/shops/pfotenglueck/panel.json"))
    check("Shop: erst durchgefallen, dann überarbeitet und bestanden", ok and [v["zustimmung"] for v in info["verlauf"]] == [0.0, 100.0], str(info["verlauf"]))
    h = open(d + "/shops/pfotenglueck/index.html").read()
    check("Shop: alle Produkte + Preise auf der Seite", all(f"Leine {i}" in h for i in range(4)) and "19,90 €" in h)
    check("Shop: Vorschau-Schutz (noindex, Banner, Kasse gesperrt)", "noindex" in h and "Vorschau" in h and "alert0()" in h)
    check("Shop: 100.000 KI-Kunden im Bericht", "100.000" in open(d + "/shops/pfotenglueck/BERICHT.md").read())
    check("Shop: Panel deckt 100 % ab (25 Typen)", len(SB.PANEL) == 25 and sum(a for _, a in SB.PANEL) == 100)
    # Weitermachen: schlechtere Überarbeitung wird verworfen, bester Stand bleibt
    runden["panel"] = 0
    def fake_schlecht(system, user, search=False, json_mode=False):
        if "simulierst" in system:
            runden["panel"] += 1
            gut = runden["panel"] <= 10  # Ausgangsstand gut, Überarbeitung schlecht
            return json.dumps({"kunden": [{"nr": i + 1, "note": 5, "sehr_gut": gut, "oefter_kaufen": gut, "kritik": "x", "wunsch": "y"} for i in range(5)]})
        return json.dumps(dict(PLAN, slogan="schlechter"))
    SB.jlib.ki = fake_schlecht; SB.ZIEL = 1.01; SB.MAX_RUNDEN = 1
    SB.main("", "pfotenglueck")
    info2 = json.load(open(d + "/shops/pfotenglueck/panel.json"))
    check("Shop: schlechtere Überarbeitung verworfen, bester Stand bleibt", info2["shop"]["slogan"] == "Leinen mit Liebe" and info2["verlauf"][-1]["behalten"] is False, str(info2["verlauf"][-2:]))
    SB.ZIEL, SB.MAX_RUNDEN = 0.75, 8
    check("Shop: keine erfundenen Bewertungen erlaubt", SB.pruefen(PLAN, h.replace("</footer>", "★★★★★ Testsieger</footer>"), False) != [])

# Alle Bots lassen sich übersetzen, alle Daten sind gültiges JSON
for f in sorted([*(ROOT / "bot").glob("*.py"), *(ROOT / "video").glob("*.py")]):
    try:
        compile(f.read_text(encoding="utf-8"), str(f), "exec")
    except Exception as e:
        check(f"Python: {f.name}", False, str(e))
for f in sorted((ROOT / "data").rglob("*.json")):
    try:
        json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        check(f"Daten: {f.name}", False, str(e))
check("Alle Bots + Daten gültig", not [x for x in fehler if x.startswith(("Python", "Daten"))])

print(f"\n{len(fehler)} Fehler")
sys.exit(1 if fehler else 0)
