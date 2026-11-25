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

XF = 0.4  # Sekunden Überblendung zwischen Szenen


def satz(t):
    """Untertitel in normaler Schreibweise statt GROSSBUCHSTABEN (ruhiger zu lesen), erster Buchstabe groß."""
    t = t.strip()
    return t[:1].upper() + t[1:] if t else t


def verlauf(path):
    """Halbtransparente Verläufe oben/unten, damit Schrift auf jedem Bild gut lesbar ist."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y in range(320):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, int(120 * (1 - y / 320) ** 1.6)))
    for y in range(H - 900, H):
        a = (y - (H - 900)) / 900
        d.line([(0, y), (W, y)], fill=(0, 0, 0, int(170 * a ** 1.4)))
    im.save(path)


FONT_LED = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_NAME = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def euro(n):
    """12 -> €12, 4800000 -> €4.800.000 (deutsche Tausenderpunkte)."""
    return "€" + f"{int(n):,}".replace(",", ".")


def konto_bild(path, konto, vorher):
    """„Kontostand“-Format: leuchtende LED-Anzeigen (Name + Betrag) oben im Bild, eine pro Figur der Szene.
    Hat sich ein Betrag seit der letzten Szene geändert, erscheint darunter ▲ +€… (grün) bzw. ▼ −€… (rot)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    led, nf, df = ImageFont.truetype(FONT_LED, 62), ImageFont.truetype(FONT_NAME, 30), ImageFont.truetype(FONT_NAME, 32)
    teile = []
    for name, wert in list(konto.items())[:3]:
        txt = euro(wert)
        tw = int(led.getlength(txt)); bw, bh = tw + 56, 104
        tafel = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(tafel)
        d.rounded_rectangle([20, 20, 20 + bw, 20 + bh], 26, fill=(14, 16, 18, 235), outline=(70, 74, 80, 255), width=5)
        d.rounded_rectangle([34, 32, 6 + bw, 8 + bh], 16, fill=(8, 34, 32, 255))
        glow = Image.new("RGBA", tafel.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((48, 34), txt, font=led, fill=(80, 255, 210, 255))
        tafel.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)))
        d.text((48, 34), txt, font=led, fill=(150, 255, 225, 255))
        for y in range(34, 8 + bh, 5):   # LED-Raster wie eine Punktmatrix
            d.line([(36, y), (4 + bw, y)], fill=(8, 34, 32, 110), width=1)
        diff = int(wert) - int(vorher.get(name, wert))
        teile.append((name, tafel, diff))
    gap = 26
    breite = sum(t.width for _, t, _ in teile) + gap * (len(teile) - 1)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x, y = (W - breite) // 2, 250
    for name, tafel, diff in teile:
        cx = x + tafel.width // 2
        d.text((cx, y), name.upper(), font=nf, fill=(255, 255, 255, 255), anchor="mb", stroke_width=4, stroke_fill=(0, 0, 0, 200))
        im.alpha_composite(tafel, (x, y + 2))
        if diff:
            col = (90, 240, 120, 255) if diff > 0 else (255, 90, 90, 255)
            d.text((cx, y + tafel.height + 4), ("▲ +" if diff > 0 else "▼ −") + euro(abs(diff)), font=df, fill=col,
                   anchor="mt", stroke_width=4, stroke_fill=(0, 0, 0, 220))
        x += tafel.width + gap
    im.save(path)


def _hole(prompt, seed, versuche):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
           + f"?width=720&height=1280&nologo=true&seed={seed}")
    for k in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-tt"}), timeout=150) as r:
                data = r.read()
            if len(data) > 15000:
                return data
            print(f"  Bild zu klein ({len(data)} B), Versuch {k + 1}")
        except urllib.error.HTTPError as e:
            print(f"  Bild HTTP {e.code}, Versuch {k + 1}")
            time.sleep(int(e.headers.get("Retry-After") or 30) + 5); continue
        except Exception as e:
            print("  Bild:", e)
        time.sleep(20)
    return None


def img(prompt, path, seed):
    if os.path.exists(path):
        return
    # 1. volle Beschreibung, 2. kurze Beschreibung mit neuem Startwert (lange Texte lehnt der Bilddienst manchmal ab)
    kurz = prompt.split(", the character is literally")[0][:260]
    for p, sd, n in ((f"{prompt}, {STYLE}", seed, 4), (f"{kurz}, cute vegetable plush toy figurine, not a person, 3D movie still", seed + 777, 4)):
        data = _hole(p, sd, n)
        if data:
            open(path, "wb").write(data); time.sleep(16); return
    print("  ⚠️ Bild fehlt – Farbverlauf als Platzhalter:", path)
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
            orig = [w for w in ln["t"].split() if any(ch.isalnum() for ch in w)]  # Originalwörter mit Satzzeichen
            if len(orig) == len(ws):
                ws = [(a, b, o) for (a, b, _), o in zip(ws, orig)]
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
    # Untertitel: ruhiger Satz-Stil im unteren Drittel (über der TikTok-Leiste), Sprechername als farbiges Etikett
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00202020,&H96000000,-1,0,0,0,100,100,0.5,0,1,5,3,2,90,90,470,1
Style: Who,DejaVu Sans,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,3,12,0,2,90,90,600,1
Style: Top,DejaVu Sans,40,&H00FFFFFF,&H00FFFFFF,&H00202020,&H64000000,-1,0,0,0,100,100,3,0,1,3,2,8,60,60,120,1
Style: Ki,DejaVu Sans,26,&H00E6E6E6,&H00FFFFFF,&H00202020,&H64000000,0,0,0,0,100,100,1,0,1,2,1,8,60,60,180,1
Style: End,DejaVu Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,5,4,5,90,90,0,1
Style: End2,DejaVu Sans,44,&H0066D9FF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,3,2,5,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,{ts(0)},{ts(end0)},Top,,0,0,0,,{{\\fad(400,300)}}{esc(sp.get('series','KI-Serie')).upper()} · FOLGE {sp.get('episode','')}
Dialogue: 1,{ts(0)},{ts(end0)},Ki,,0,0,0,,{{\\fad(400,300)}}KI-generiert
"""
    for k, (s, e, t, who) in enumerate(caps):
        e2 = caps[k + 1][0] if k + 1 < len(caps) and caps[k + 1][0] - e < 0.5 else e + 0.1
        col = COLS[names.index(who) % len(COLS)]
        neu = k == 0 or caps[k - 1][3] != who            # Etikett nur beim Sprecherwechsel einblenden
        fad = "\\fad(120,0)" if neu else ""
        ass += f"Dialogue: 2,{ts(s)},{ts(e2)},Who,,0,0,0,,{{\\3c{col}&\\4c{col}&{fad}\\1c&H00FFFFFF&\\bord10}} {esc(who).upper()} \n"
        ass += f"Dialogue: 2,{ts(s)},{ts(e2)},Cap,,0,0,0,,{{\\blur0.6\\fscx96\\fscy96\\t(0,90,\\fscx100\\fscy100)}}{esc(satz(t))}\n"
    endtxt = esc(sp.get('end', 'Folge mir für Teil 2!'))
    ass += f"Dialogue: 3,{ts(end0)},{ts(t0)},End,,0,0,0,,{{\\fad(350,0)\\pos({W//2},{H//2 - 110})}}{endtxt}\n"
    ass += f"Dialogue: 3,{ts(end0 + 0.3)},{ts(t0)},End2,,0,0,0,,{{\\fad(350,0)\\pos({W//2},{H//2 + 190})}}{esc(sp.get('series','Früchte-Drama')).upper()} · JEDEN TAG NEU\n"
    open(f"{tmp}/s.ass", "w").write(ass)
    verlauf(f"{tmp}/ov.png")
    clips, segs = [], []
    for i, ((s, e), sc) in enumerate(zip(scenes, sp["scenes"])):
        p = f"{tmp}/i{i}.jpg"
        seed = sc.get("seed", sum(map(ord, vid)) + i * 7 + int(os.environ.get("SEED_SHIFT", "0") or 0))  # "seed" = festes, geprüftes Bild
        img(sc["p"], p, seed=seed)
        seg = (e - s) + (2.5 if i == len(scenes) - 1 else 0); segs.append(seg)
        lang = seg + (XF if i < len(scenes) - 1 else 0)    # Überlappung für weiche Überblendung
        fr = int(lang * FPS) + 2
        z = "min(zoom+0.0007,1.12)" if i % 2 == 0 else "if(eq(on,1),1.12,max(zoom-0.0007,1))"
        c = f"{tmp}/c{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", p, "-vf",
           f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase:flags=lanczos,crop={W*2}:{H*2},"
           f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps={FPS},"
           f"eq=saturation=1.06:contrast=1.03,unsharp=5:5:0.5",
           "-t", f"{lang:.3f}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", c)
        clips.append(c)
    # Szenen weich überblenden statt hart schneiden
    args, fl, last, off = [], [], "0:v", 0.0
    for c in clips:
        args += ["-i", c]
    for k in range(1, len(clips)):
        off += segs[k - 1]
        fl.append(f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]"); last = f"x{k}"
    ende = end0 - 0.0
    fl.append(f"[{last}]fps={FPS},format=yuv420p[base]")
    fl.append(f"[base][{len(clips)}:v]overlay=0:0[ov]")
    # „Kontostand“-Format: LED-Anzeigen je Szene (nur wenn die Szene ein Feld „konto“ hat)
    kargs, stand, cur = [], dict(sp.get("konten", {})), "ov"
    for i, ((s, e), sc) in enumerate(zip(scenes, sp["scenes"])):
        if not sc.get("konto"):
            continue
        kp = f"{tmp}/k{i}.png"; konto_bild(kp, sc["konto"], stand); stand.update(sc["konto"])
        n = len(clips) + 2 + len(kargs) // 4
        kargs += ["-loop", "1", "-i", kp]
        fl.append(f"[{n}:v]format=rgba,fade=in:st={s + 0.15:.2f}:d=0.35:alpha=1[k{i}]")
        fl.append(f"[{cur}][k{i}]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[o{i}]"); cur = f"o{i}"
    fl.append(f"[{cur}]drawbox=0:0:{W}:{H}:color=black@0.45:t=fill:enable='gte(t,{ende:.2f})',ass={tmp}/s.ass[v]")
    out = os.path.join(OUT, vid + ".mp4")
    sh("ffmpeg", "-y", *args, "-loop", "1", "-i", f"{tmp}/ov.png", "-i", f"{tmp}/voice.m4a", *kargs,
       "-filter_complex", ";".join(fl), "-map", "[v]", "-map", f"{len(clips) + 1}:a",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "copy", "-t", f"{t0:.3f}",
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
