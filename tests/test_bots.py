"""Schnelltests für die Bots – ohne Internet. Start: python3 tests/test_bots.py"""
<<<<<<< HEAD
import glob, json, os, sys, tempfile, time, pathlib
=======
import json, os, sys, tempfile, time, pathlib
>>>>>>> 3d29b45 (Früchte-Serie: Folge 2 Avo als echte Avocado (Bild war zu menschenähnlich))
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
<<<<<<< HEAD
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
=======
>>>>>>> 3d29b45 (Früchte-Serie: Folge 2 Avo als echte Avocado (Bild war zu menschenähnlich))
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
