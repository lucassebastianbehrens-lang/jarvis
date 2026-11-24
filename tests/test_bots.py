"""Schnelltests für die Bots – ohne Internet. Start: python3 tests/test_bots.py"""
import json, os, sys, tempfile, time, pathlib
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
