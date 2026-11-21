"""Jarvis Video-Generator: Skript -> Hochkant-Video (1080x1920) mit deutscher Stimme,
eingebrannten Untertiteln und KI-Bildern. Kein Gesicht nötig.

Aufruf: python3 video/make.py video/specs/<id>.json [...]   (oder: all)
Ausgabe: video/out/<id>.mp4 + <id>.txt (Titel/Beschreibung zum Hochladen)
Benötigt: ffmpeg, pip install edge-tts (Netzwerk für Stimme + Bilder)."""
import json, os, subprocess, sys, time, urllib.parse, urllib.request
from glob import glob

W, H, FPS = 1080, 1920, 30
OUT = os.path.join(os.path.dirname(__file__), "out")
FONT = "DejaVu Sans"


def sh(*a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def ts(sec):
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def voice(spec, mp3):
    """Stimme + Wort-Zeitmarken (edge-tts). Rückgabe: Liste (start, ende, wort) in Sekunden."""
    import edge_tts
    com = edge_tts.Communicate(spec["text"], spec.get("voice", "de-DE-ConradNeural"),
                               rate=spec.get("rate", "+8%"), boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        for ch in com.stream_sync():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7
                words.append((st, st + ch["duration"] / 1e7, ch["text"]))
    return words


def captions(words, max_words=3):
    """Gruppiert Wörter zu kurzen Untertitel-Häppchen (TikTok-Stil)."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[2].endswith((".", "?", "!", ":", ",")):
            out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur))); cur = []
    if cur:
        out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    # Lücken schließen, damit der Text nicht flackert
    return [(s, (out[i + 1][0] if i + 1 < len(out) else e), t) for i, (s, e, t) in enumerate(out)]


def ass(caps, spec, path):
    col = spec.get("color", "#2ecc71").lstrip("#")
    bgr = col[4:6] + col[2:4] + col[0:2]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,620,1
Style: Brand,{FONT},46,&H00{bgr},&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,4,0,8,60,60,110,1
Style: Ki,{FONT},30,&H00DDDDDD,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,8,60,60,175,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    end = caps[-1][1] + 1.5
    ev = [f"Dialogue: 1,{ts(0)},{ts(end)},Brand,,0,0,0,,{spec['channel'].upper()}",
          f"Dialogue: 1,{ts(0)},{ts(end)},Ki,,0,0,0,,Bilder & Stimme mit KI erstellt"]
    for s, e, t in caps:
        t = t.upper().replace("{", "(").replace("}", ")")
        ev.append(f"Dialogue: 2,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}{t}")
    open(path, "w").write(head + "\n".join(ev) + "\n")
    return end


def image(prompt, path, seed):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
           + f"?width={W}&height={H}&nologo=true&seed={seed}")
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "jarvis-video"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
            if os.path.getsize(path) > 10000:
                return
        except Exception as e:
            print("  Bild-Versuch", k + 1, "fehlgeschlagen:", e)
        time.sleep(20)
    raise RuntimeError("Bild konnte nicht geladen werden: " + prompt)


def build(spec_path):
    spec = json.load(open(spec_path))
    vid, tmp = spec["id"], os.path.join(OUT, spec["id"] + "_tmp")
    os.makedirs(tmp, exist_ok=True)
    print("▶", vid)
    words = voice(spec, f"{tmp}/voice.mp3")
    caps = captions(words)
    total = ass(caps, spec, f"{tmp}/subs.ass")
    imgs = []
    for i, p in enumerate(spec["prompts"]):
        path = f"{tmp}/img{i}.jpg"
        if not os.path.exists(path):
            image(p, path, seed=abs(hash(vid)) % 100000 + i)
            time.sleep(16)                     # Pollinations: 1 Bild / 15 s ohne Konto
        imgs.append(path)
    seg = total / len(imgs)
    frames = int(seg * FPS) + 1
    clips = []
    for i, p in enumerate(imgs):           # langsamer Zoom (Ken Burns), abwechselnd rein/raus
        z = "min(zoom+0.0006,1.12)" if i % 2 == 0 else "if(eq(on,1),1.12,max(zoom-0.0006,1))"
        c = f"{tmp}/clip{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", p, "-vf",
           f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
           f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
           f"eq=brightness=-0.06:saturation=1.08",
           "-t", f"{seg:.3f}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", c)
        clips.append(c)
    with open(f"{tmp}/list.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
    out = os.path.join(OUT, vid + ".mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-i", f"{tmp}/voice.mp3",
       "-vf", f"ass={tmp}/subs.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
       "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out)
    open(os.path.join(OUT, vid + ".txt"), "w").write(
        f"KANAL: {spec['channel']}\nTITEL: {spec['title']}\n\nBESCHREIBUNG:\n{spec.get('description','')}\n\n"
        "Beim Hochladen: Sichtbarkeit PRIVAT · 'Veränderte oder synthetische Inhalte' = JA (KI-Stimme/Bilder)\n")
    print("  ✓", out, f"{total:.1f} s")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:] or ["all"]
    files = sorted(glob(os.path.join(os.path.dirname(__file__), "specs", "*.json"))) if args == ["all"] else args
    for f in files:
        build(f)
