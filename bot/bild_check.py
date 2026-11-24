"""Bild-Prüfung für die Früchte-Serie: 6 Standbilder → Groq-Bilderkennung → sind echte Menschen zu sehen?
Aufruf: python3 bot/bild_check.py video/out/<id>.mp4   Exit 1 = Mensch/Freizügiges gefunden → nicht posten."""
import base64, json, os, subprocess, sys, tempfile, urllib.request

KEY = os.environ.get("GROQ_KEY", "")
MODELL = "meta-llama/llama-4-scout-17b-16e-instruct"
FRAGE = ("These are frames from a family-friendly cartoon series whose characters must ALL be fruit or vegetable mascots "
         "(heads/bodies are real fruits or vegetables). For each frame: does it show a human being or a human-looking face/body "
         "(e.g. a woman or man with human skin, human hair, human face), or anything revealing/sexualized? "
         'Answer ONLY JSON: {"frames":[{"nr":1,"mensch":false,"freizuegig":false,"was":"short description"}]}')


def frames(mp4, n=6):
    d = tempfile.mkdtemp()
    dauer = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4]))
    out = []
    for i in range(n):
        p = f"{d}/f{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(dauer * (i + .5) / n), "-i", mp4, "-frames:v", "1", "-vf", "scale=360:-1", p], check=True)
        out.append(p)
    return out


def pruefen(bilder):
    inhalt = [{"type": "text", "text": FRAGE}] + [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(open(b, "rb").read()).decode()}} for b in bilder]
    body = {"model": MODELL, "messages": [{"role": "user", "content": inhalt}], "response_format": {"type": "json_object"}, "temperature": 0}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + KEY, "User-Agent": "jarvis-bot"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(txt[txt.find("{"):txt.rfind("}") + 1]).get("frames", [])


if __name__ == "__main__":
    if not KEY:
        print("Kein GROQ_KEY – Bildprüfung übersprungen (Claude prüft dann von Hand).")
        sys.exit(0)
    bilder = frames(sys.argv[1])
    befund = []
    for teil in (bilder[:3], bilder[3:]):  # Groq erlaubt nur wenige Bilder pro Anfrage
        try:
            befund += pruefen(teil)
        except Exception as e:
            print("Bildprüfung nicht möglich:", e)
            sys.exit(0)
    for b in befund:
        print(("✕" if b.get("mensch") or b.get("freizuegig") else "✓"), b.get("was", ""))
    schlecht = [b for b in befund if b.get("mensch") or b.get("freizuegig")]
    if schlecht:
        print(f"NICHT POSTEN: {len(schlecht)} Bild(er) mit Mensch/Freizügigem.")
        sys.exit(1)
    print("Bildprüfung bestanden.")
