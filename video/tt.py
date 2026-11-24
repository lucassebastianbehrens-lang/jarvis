"""TT KI-Miniserie: Drehbuch (Szenen mit Dialogzeilen) -> Hochkant-Video 1080x1920 mit mehreren KI-Stimmen,
realistischen 3D-Obst-Bildern (Pollinations), Untertiteln mit Sprechernamen und Endkarte.
Aufruf: python3 video/tt.py video/tt/<id>.json   Ausgabe: video/out/<id>.mp4 + <id>.txt"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from long import tts, dur, sh, ts, esc, OUT

W, H, FPS = 1080, 1920, 30
STYLE = ("3D animated movie still, cute fruit and vegetable plush toy figurines: the fruit or vegetable IS the whole body "
         "(no separate head, no hair), cartoon eyes and mouth on the fruit, tiny stubby arms and legs, "
         "not a person, not a girl, not a doll, no human faces, no human hair, no human skin, family friendly, "
         "cinematic soft lighting, detailed textures, vertical 9:16, no text")
COLS = ["&H0066CCFF", "&H00FF99CC", "&H0099FF99", "&H00FFCC66", "&H00CC99FF", "&H0066FFFF"]


def img(prompt, path, seed):
    if os.path.exists(path):
        return
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(f"{prompt}, {STYLE}")
           + f"?width=720&height=1280&nologo=true&seed={seed}")
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-tt"}), timeout=150) as r:
                data = r.read()
            if len(data) > 15000:
                open(path, "wb").write(data); time.sleep(16); return
        except urllib.error.HTTPError as e:
            time.sleep(int(e.headers.get("Retry-After") or 30) + 5); continue
        except Exception as e:
            print("  Bild:", e)
        time.sleep(20)
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0xff7a59:c1=0x2b1055:d=1", "-frames:v", "1", path)


def build(spec_path):
    sp = json.load(open(spec_path)); vid = sp["id"]
    tmp = os.path.join(OUT, vid + "_tmp"); os.makedirs(tmp, exist_ok=True)
    print("▶", vid)
    names = list(sp["voices"])
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.25", f"{tmp}/gap.mp3")
    t0, alist, caps, scenes = 0.0, [], [], []
    for i, sc in enumerate(sp["scenes"]):
        s0 = t0
        for j, ln in enumerate(sc["lines"]):
            mp3 = f"{tmp}/v{i}_{j}.mp3"
            ws = tts(ln["t"], sp["voices"][ln["s"]], ln.get("rate", "+6%"), mp3)
            cur = []
            for a, b, w in ws:
                cur.append((t0 + a, t0 + b, w))
                if len(cur) >= 3:
                    caps.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur), ln["s"])); cur = []
            if cur:
                caps.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur), ln["s"]))
            t0 += dur(mp3) + 0.25; alist += [mp3, f"{tmp}/gap.mp3"]
        scenes.append((s0, t0))
    # Endkarte (Stille 2,5 s)
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2.5", f"{tmp}/end.mp3")
    alist.append(f"{tmp}/end.mp3"); end0 = t0; t0 += 2.5
    with open(f"{tmp}/a.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in alist)
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/a.txt", "-ar", "44100", "-ac", "2", "-c:a", "aac",
       "-b:a", "160k", f"{tmp}/voice.m4a")
    print(f"  Länge {t0:.0f} s")
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,560,1
Style: Who,DejaVu Sans,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,5,0,2,60,60,660,1
Style: Top,DejaVu Sans,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,5,0,8,60,60,110,1
Style: Ki,DejaVu Sans,28,&H00DDDDDD,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,8,60,60,175,1
Style: End,DejaVu Sans,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,3,22,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,{ts(0)},{ts(t0)},Top,,0,0,0,,{esc(sp.get('series','KI-Serie')).upper()} · FOLGE {sp.get('episode','')}
Dialogue: 1,{ts(0)},{ts(t0)},Ki,,0,0,0,,KI-generiert
"""
    for k, (s, e, t, who) in enumerate(caps):
        e2 = caps[k + 1][0] if k + 1 < len(caps) and caps[k + 1][0] - e < 0.5 else e + 0.1
        col = COLS[names.index(who) % len(COLS)]
        ass += f"Dialogue: 2,{ts(s)},{ts(e2)},Who,,0,0,0,,{{\\c{col}}}{esc(who).upper()}\n"
        ass += f"Dialogue: 2,{ts(s)},{ts(e2)},Cap,,0,0,0,,{{\\fscx90\\fscy90\\t(0,80,\\fscx100\\fscy100)}}{esc(t).upper()}\n"
    ass += f"Dialogue: 3,{ts(end0)},{ts(t0)},End,,0,0,0,,{esc(sp.get('end','Folge mir für Teil 2!'))}\n"
    open(f"{tmp}/s.ass", "w").write(ass)
    clips = []
    for i, ((s, e), sc) in enumerate(zip(scenes, sp["scenes"])):
        p = f"{tmp}/i{i}.jpg"; img(sc["p"], p, seed=sum(map(ord, vid)) + i * 7)
        seg = (e - s) + (2.5 if i == len(scenes) - 1 else 0); fr = int(seg * FPS) + 2
        z = "min(zoom+0.0009,1.15)" if i % 2 == 0 else "if(eq(on,1),1.15,max(zoom-0.0009,1))"
        c = f"{tmp}/c{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", p, "-vf",
           f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
           f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps={FPS}",
           "-t", f"{seg:.3f}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", c)
        clips.append(c)
    with open(f"{tmp}/v.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
    out = os.path.join(OUT, vid + ".mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/v.txt", "-i", f"{tmp}/voice.m4a", "-vf",
       f"ass={tmp}/s.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "copy", "-shortest",
       "-movflags", "+faststart", out)
    open(os.path.join(OUT, vid + ".txt"), "w").write(
        f"TITEL: {sp.get('title','')}\nTEXT: {sp.get('caption','')} {' '.join(sp.get('hashtags', []))}\nKI-generiert: ja\n")
    print(f"  ✓ {out} ({t0:.0f} s, {os.path.getsize(out)/1e6:.1f} MB)")


if __name__ == "__main__":
    bad = []
    for f in sys.argv[1:]:
        try:
            build(f)
        except Exception as e:
            import traceback; traceback.print_exc(); bad.append(f)
    sys.exit(1 if bad else 0)
