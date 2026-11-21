"""Jarvis Erklär-Stil (YouTube 16:9): weißer Hintergrund, Maskottchen links, 1–3 Vergleichskarten rechts
(Überschrift + Bild oder Text), große Einzelwort-Untertitel. Stimme: edge-tts. Bilder: Pollinations (kostenlos).

Aufruf: python3 video/erklaer.py video/erklaer/<id>.json [...]
Ausgabe wie long.py: <id>.mp4, -thumbnail.jpg, .srt, .txt"""
import json, os, sys, textwrap, urllib.parse, urllib.request, urllib.error, time
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from long import tts, punctuate, dur, sh, ts, chap, esc, openverse, OUT, GAP

W, H, FPS = 1920, 1080, 30
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def font(n):
    return ImageFont.truetype(BOLD, n)


def icon(prompt, path, seed):
    """Isometrische Pastell-Illustration (Pollinations), Ersatz: Openverse-Foto, sonst leer."""
    if os.path.exists(path):
        return True
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(
        prompt + ", isometric 3D illustration, soft pastel colors, clean, centered, plain light background, no text")
        + f"?width=768&height=768&nologo=true&seed={seed}")
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-video"}), timeout=150) as r:
                data = r.read()
            if len(data) > 15000:
                open(path, "wb").write(data); time.sleep(16); return True
        except urllib.error.HTTPError as e:
            time.sleep(int(e.headers.get("Retry-After") or 30) + 5); continue
        except Exception as e:
            print("  Bild:", e)
        time.sleep(20)
    return openverse(prompt, path)


def cutout(path, h):
    """Maskottchen freistellen (weißer Hintergrund -> transparent) und auf Höhe h skalieren."""
    im = Image.open(path)
    if im.mode == "RGBA":  # bereits freigestellt
        return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    im = im.convert("RGB")
    im = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    g = im.convert("L").point(lambda v: 0 if v > 238 else 255).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA"); rgba.putalpha(g)
    return rgba


def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width, im.height], r, fill=255)
    im = im.convert("RGBA"); im.putalpha(m); return im


def card(content, w, h, bg, tmp):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base = Image.new("RGB", (w, h), bg)
    if content.startswith("txt:"):
        d = ImageDraw.Draw(base); txt = content[4:]
        for size in (64, 56, 48, 42, 36):
            f = font(size); lines = textwrap.wrap(txt, width=max(6, int(w / (size * 0.62))))
            hh = len(lines) * size * 1.2
            if hh < h * 0.8 and max(d.textlength(l, font=f) for l in lines) < w * 0.88:
                break
        y = (h - hh) / 2
        for l in lines:
            d.text(((w - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(25, 25, 30)); y += size * 1.2
    else:
        p = os.path.join(tmp, content)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB"); k = max(w / im.width, h / im.height)
            im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
            base.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    c.alpha_composite(rounded(base, 26))
    return c


def frame(beat, spec, tmp, mascots, out):
    im = Image.new("RGBA", (W, H), (252, 252, 250, 255))
    d = ImageDraw.Draw(im)
    m = mascots[beat.get("pose", "finger")]
    im.alpha_composite(m, (110 if spec.get("side", "left") == "left" else W - m.width - 110, H - m.height))
    cards = beat["c"]; n = len(cards)
    area_x, area_w = 820, 1020
    cw = {1: 640, 2: 470, 3: 320}[n]; ch = {1: 470, 2: 470, 3: 360}[n]; gap = (area_w - n * cw) // (n + 1)
    for i, cd in enumerate(cards):
        x = area_x + gap + i * (cw + gap); y = 190
        lab = cd.get("l", "")
        if lab:
            f = font(60 if n < 3 else 48); tw = d.textlength(lab, font=f)
            d.text((x + (cw - tw) / 2, y - 105), lab, font=f, fill=(20, 20, 24))
        bg = tuple(int(cd.get("bg", spec["bgs"][i % len(spec["bgs"])]).lstrip("#")[j:j + 2], 16) for j in (0, 2, 4))
        m_ = Image.new("L", (cw + 40, ch + 40), 0); ImageDraw.Draw(m_).rounded_rectangle([20, 20, cw + 20, ch + 20], 26, fill=55)
        sh_ = Image.new("RGBA", m_.size, (0, 0, 0, 0)); sh_.putalpha(m_.filter(ImageFilter.GaussianBlur(12)))
        im.alpha_composite(sh_, (x - 14, y - 8))
        im.alpha_composite(card(cd["v"], cw, ch, bg, tmp), (x, y))
    # Kanal-Logo
    col = spec.get("color", "#2ecc71").lstrip("#")
    d.text((60, 36), spec["channel"].upper(), font=font(30), fill=tuple(int(col[j:j + 2], 16) for j in (0, 2, 4)))
    d.text((60, 76), "Stimme & Bilder mit KI erstellt", font=font(18), fill=(150, 150, 150))
    im.convert("RGB").save(out, quality=92)


def build(spec_path):
    spec = json.load(open(spec_path)); vid = spec["id"]
    tmp = os.path.join(OUT, vid + "_tmp"); os.makedirs(tmp, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    print("▶", vid)
    # Maskottchen
    mascots = {k: cutout(os.path.join(ASSETS, v), 900) for k, v in spec["mascot"].items()}
    # Icons
    ok = 0
    for i, (k, p) in enumerate(spec["icons"].items()):
        ok += icon(p, os.path.join(tmp, k + ".jpg"), seed=sum(map(ord, vid)) + i * 13)
    print(f"  Icons: {ok}/{len(spec['icons'])}")
    # Stimme
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), f"{tmp}/gap.mp3")
    t0, words, alist, beats = 0.0, [], [], []
    for i, sc in enumerate(spec["scenes"]):
        mp3 = f"{tmp}/v{i}.mp3"; ws = punctuate(tts(sc["t"], spec["voice"], spec.get("rate", "+0%"), mp3), sc["t"])
        d = dur(mp3) + GAP
        words += [(t0 + a, t0 + b, w) for a, b, w in ws]
        # Beats: an Wortpositionen verteilen (b[i].at = Anteil 0..1, sonst gleichmäßig)
        bl = sc["b"]
        for j, b in enumerate(bl):
            st = t0 + d * b.get("at", j / len(bl)); en = t0 + d * (bl[j + 1].get("at", (j + 1) / len(bl)) if j + 1 < len(bl) else 1)
            beats.append((st, en, b))
        sc["_s"] = t0; alist += [mp3, f"{tmp}/gap.mp3"]; t0 += d
    total = t0
    with open(f"{tmp}/alist.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in alist)
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/alist.txt", "-ar", "44100", "-ac", "2", "-c:a", "aac",
       "-b:a", "160k", f"{tmp}/voice.m4a")
    print(f"  Stimme: {total/60:.1f} min, {len(beats)} Bilder-Wechsel")
    # Untertitel: 1–2 Wörter, groß, weiß mit dunkler Kontur (unter den Karten)
    caps, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 2 or w[2].endswith((".", ",", "?", "!", ":")) or len(w[2]) > 11:
            caps.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur))); cur = []
    if cur:
        caps.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    caps = [(s, (caps[i + 1][0] if i + 1 < len(caps) and caps[i + 1][0] - e < 0.6 else e + 0.1), t) for i, (s, e, t) in enumerate(caps)]
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,84,&H00FFFFFF,&H00FFFFFF,&H00303030,&H00000000,-1,0,0,0,100,100,2,0,1,7,0,2,820,80,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    srt = []
    for n, (s, e, t) in enumerate(caps, 1):
        ass += f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\fscx88\\fscy88\\t(0,80,\\fscx100\\fscy100)}}{esc(t.upper())}\n"
        srt.append(f"{n}\n{ts(s, True)} --> {ts(e, True)}\n{t}\n")
    open(f"{tmp}/subs.ass", "w").write(ass); open(os.path.join(OUT, vid + ".srt"), "w").write("\n".join(srt))
    # Bilder je Beat -> Clips mit leichtem Zoom
    clips = []
    for i, (s, e, b) in enumerate(beats):
        fp = f"{tmp}/f{i}.jpg"; frame(b, spec, tmp, mascots, fp)
        seg = e - s; frames = int(seg * FPS) + 2; c = f"{tmp}/c{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", fp, "-vf",
           f"scale={int(W*1.06)}:{int(H*1.06)},zoompan=z='min(zoom+0.0004,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
           f":d={frames}:s={W}x{H}:fps={FPS}", "-t", f"{seg:.3f}", "-pix_fmt", "yuv420p", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "20", c)
        clips.append(c)
    with open(f"{tmp}/vlist.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
    out = os.path.join(OUT, vid + ".mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/vlist.txt", "-i", f"{tmp}/voice.m4a",
       "-vf", f"ass={tmp}/subs.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "copy",
       "-shortest", "-movflags", "+faststart", out)
    # Thumbnail: Maskottchen + 2 Karten + große Schrift
    th = Image.new("RGBA", (1280, 720), (252, 252, 250, 255)); dd = ImageDraw.Draw(th)
    mm = mascots.get(spec.get("thumb_pose", "zeigen"), list(mascots.values())[0]).copy()
    mm = mm.resize((int(mm.width * 690 / mm.height), 690)); th.alpha_composite(mm, (20, 30))
    y = 70
    for k, line in enumerate(spec["thumb"]):
        f = font(96); col = spec.get("color", "#2ecc71").lstrip("#")
        fill = tuple(int(col[j:j + 2], 16) for j in (0, 2, 4)) if k == len(spec["thumb"]) - 1 else (20, 20, 24)
        dd.text((540, y), line, font=f, fill=fill, stroke_width=4, stroke_fill=(255, 255, 255)); y += 118
    th.convert("RGB").save(os.path.join(OUT, vid + "-thumbnail.jpg"), quality=92)
    # Text
    kap = "Kapitel:\n" + "\n".join(f"{chap(0 if i == 0 else sc['_s'])} {sc['ch']}" for i, sc in enumerate(spec["scenes"]) if "ch" in sc)
    open(os.path.join(OUT, vid + ".txt"), "w").write(
        f"KANAL: {spec['channel']}\nLÄNGE: {chap(total)} min\n\nTITEL:\n{spec['title']}\n\nBESCHREIBUNG:\n"
        f"{spec['description'].replace('{KAPITEL}', kap)}\n\nTAGS:\n{spec.get('tags','')}\n\nBEIM HOCHLADEN:\n"
        "- Sichtbarkeit: PRIVAT (erst nach deiner Prüfung öffentlich)\n- 'Veränderte oder synthetische Inhalte': JA\n"
        f"- 'Nicht speziell für Kinder'\n- Thumbnail: {vid}-thumbnail.jpg\n- Untertitel: {vid}.srt (Deutsch)\n")
    print(f"  ✓ {out} ({chap(total)} min, {os.path.getsize(out)/1e6:.0f} MB)")


if __name__ == "__main__":
    bad = []
    for f in sys.argv[1:]:
        try:
            build(f)
        except Exception as e:
            import traceback; traceback.print_exc(); bad.append(f)
    sys.exit(1 if bad and len(bad) == len(sys.argv[1:]) else 0)
