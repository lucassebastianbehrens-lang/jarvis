"""Jarvis Lang-Video-Generator (YouTube, 16:9, 10+ Minuten) – komplett kostenlos.
Skript in Szenen -> deutsche KI-Stimme (edge-tts) + KI-Bilder (Pollinations) + Überschriften,
Untertitel, Kapitelmarken, Thumbnail und .srt.

Aufruf: python3 video/long.py video/long/<id>.json [...]
Ausgabe: video/out/<id>.mp4, <id>-thumbnail.jpg, <id>.srt, <id>.txt"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request, urllib.error

W, H, FPS = 1920, 1080, 30
OUT = os.path.join(os.path.dirname(__file__), "out")
FONT = "DejaVu Sans"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GAP = 0.6  # Pause zwischen Szenen (s)


def sh(*a):
    r = subprocess.run(a, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode:
        raise RuntimeError(r.stderr.decode()[-1500:])


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def ts(sec, srt=False):
    h, r = divmod(max(sec, 0), 3600); m, s = divmod(r, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def chap(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def tts(text, voice, rate, mp3):
    """Eine Szene sprechen. Rückgabe: Wörter [(start, ende, wort)] relativ zur Szene."""
    if os.environ.get("FAKE_TTS"):  # lokaler Test ohne Netz
        n = len(text.split()); d = n * 0.4
        sh("ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={d}", "-ar", "24000", mp3)
        return [(i * 0.4, i * 0.4 + 0.35, w) for i, w in enumerate(text.split())]
    import edge_tts
    for k in range(4):
        try:
            com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
            words = []
            with open(mp3, "wb") as f:
                for ch in com.stream_sync():
                    if ch["type"] == "audio":
                        f.write(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        st = ch["offset"] / 1e7
                        words.append((st, st + ch["duration"] / 1e7, ch["text"]))
            if words:
                return words
        except Exception as e:
            print("  Stimme Versuch", k + 1, e)
        time.sleep(10)
    raise RuntimeError("Stimme fehlgeschlagen")


def punctuate(words, text):
    toks, j, res = text.split(), 0, []
    norm = lambda x: re.sub(r"[^\wäöüß]", "", x.lower())
    for st, en, w in words:
        k = j
        while k < len(toks) and not norm(toks[k]).startswith(norm(w)[:4] or "#"):
            k += 1
        if k < len(toks):
            j = k + 1
            tail = re.search(r"[.,!?:;]+$", toks[k])
            res.append((st, en, w + (tail.group(0) if tail and norm(w) == norm(toks[k]) else "")))
        else:
            res.append((st, en, w))
    return res


def captions(words, max_words=7):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[2].endswith((".", "?", "!", ":")) or (len(cur) >= 4 and w[2].endswith(",")):
            out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur))); cur = []
    if cur:
        out.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    return out


STOP = {"photorealistic", "close-up", "cinematic", "minimal", "clean", "illustration", "with", "and", "on", "in",
        "of", "the", "a", "at", "for", "to", "next", "light", "soft", "warm", "bright", "design", "flat", "macro"}


def openverse(prompt, path):
    """Ersatz: gemeinfreie Fotos (CC0/Public Domain) von Openverse, ohne Konto und ohne Namensnennung."""
    q = " ".join([w for w in re.sub(r"[^a-z ]", " ", prompt.lower()).split() if w not in STOP][:3])
    try:
        api = ("https://api.openverse.org/v1/images/?license=cc0,pdm&aspect_ratio=wide&page_size=5&q="
               + urllib.parse.quote(q))
        req = urllib.request.Request(api, headers={"User-Agent": "jarvis-video"})
        res = json.load(urllib.request.urlopen(req, timeout=60)).get("results", [])
        for r in res:
            try:
                req = urllib.request.Request(r["url"], headers={"User-Agent": "jarvis-video"})
                with urllib.request.urlopen(req, timeout=60) as x, open(path, "wb") as f:
                    f.write(x.read())
                if os.path.getsize(path) > 30000:
                    print("  ↳ Openverse:", q); return True
            except Exception:
                pass
    except Exception as e:
        print("  Openverse:", e)
    return False


def image(prompt, path, seed, color):
    if not os.environ.get("NO_IMG"):
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + ", 16:9, high detail")
               + f"?width=1280&height=720&nologo=true&seed={seed}")
        for k in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "jarvis-video"})
                with urllib.request.urlopen(req, timeout=150) as r, open(path, "wb") as f:
                    f.write(r.read())
                if os.path.getsize(path) > 15000:
                    return True
            except urllib.error.HTTPError as e:
                wait = int(e.headers.get("Retry-After") or 0) or 30
                print(f"  Bild-Versuch {k+1}: HTTP {e.code}, warte {wait + 5} s"); time.sleep(wait + 5); continue
            except Exception as e:
                print(f"  Bild-Versuch {k+1}: {e}")
            time.sleep(20)
        if openverse(prompt, path):
            return True
        print("  ⚠ Ersatz-Hintergrund:", prompt[:60])
    c = color.lstrip("#")
    sh("ffmpeg", "-y", "-f", "lavfi", "-i",
       f"gradients=s={W}x{H}:c0=0x{c}:c1=0x0b0b10:x0=0:y0=0:x1={W}:y1={H}:d=1", "-frames:v", "1", path)
    return False


def esc(t):
    return t.replace("{", "(").replace("}", ")").replace("\n", " ")


def build(spec_path):
    spec = json.load(open(spec_path))
    vid = spec["id"]; tmp = os.path.join(OUT, vid + "_tmp"); os.makedirs(tmp, exist_ok=True)
    color = spec.get("color", "#2ecc71")
    voice, rate = spec.get("voice", "de-DE-ConradNeural"), spec.get("rate", "+0%")
    print("▶", vid, len(spec["scenes"]), "Szenen")

    # 1) Stimme pro Szene + Pausen -> eine Tonspur, exakte Szenen-Zeiten
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), f"{tmp}/gap.mp3")
    t0, scenes, words_all, alist = 0.0, [], [], []
    for i, sc in enumerate(spec["scenes"]):
        mp3 = f"{tmp}/v{i}.mp3"
        ws = punctuate(tts(sc["t"], voice, rate, mp3), sc["t"])
        d = dur(mp3)
        scenes.append((t0, t0 + d + GAP))
        words_all += [(t0 + a, t0 + b, w) for a, b, w in ws]
        alist += [mp3, f"{tmp}/gap.mp3"]
        t0 += d + GAP
    total = t0
    with open(f"{tmp}/alist.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in alist)
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/alist.txt", "-ar", "44100", "-ac", "2",
       "-c:a", "aac", "-b:a", "160k", f"{tmp}/voice.m4a")
    print(f"  Stimme: {total/60:.1f} min")

    # 2) Untertitel + Überschriften (ASS) und .srt
    caps = captions(words_all)
    col = color.lstrip("#"); bgr = col[4:6] + col[2:4] + col[0:2]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,3,14,0,2,160,160,60,1
Style: Head,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00{bgr},&H00{bgr},-1,0,0,0,100,100,0,0,3,18,0,7,70,70,70,1
Style: Brand,{FONT},34,&H00{bgr},&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,3,0,9,60,60,60,1
Style: Ki,{FONT},22,&H00DDDDDD,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,9,60,60,108,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 1,{ts(0)},{ts(total)},Brand,,0,0,0,,{spec['channel'].upper()}",
          f"Dialogue: 1,{ts(0)},{ts(total)},Ki,,0,0,0,,Stimme & Bilder mit KI erstellt"]
    for (s, e), sc in zip(scenes, spec["scenes"]):
        ev.append(f"Dialogue: 2,{ts(s + 0.2)},{ts(min(s + 7, e))},Head,,0,0,0,,"
                  f"{{\\fad(250,300)}}{esc(sc['h'])}")
    srt = []
    for n, (s, e, t) in enumerate(caps, 1):
        ev.append(f"Dialogue: 3,{ts(s)},{ts(e + 0.05)},Cap,,0,0,0,,{esc(t)}")
        srt.append(f"{n}\n{ts(s, True)} --> {ts(e, True)}\n{t}\n")
    open(f"{tmp}/subs.ass", "w").write(head + "\n".join(ev) + "\n")
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, vid + ".srt"), "w").write("\n".join(srt))

    # 3) Bilder + Ken-Burns-Clips je Szene
    clips, real = [], 0
    for i, ((s, e), sc) in enumerate(zip(scenes, spec["scenes"])):
        p = f"{tmp}/img{i}.jpg"
        if not os.path.exists(p):
            real += image(sc["p"], p, seed=sum(map(ord, vid)) * 11 + i, color=color)
            if not os.environ.get("NO_IMG"):
                time.sleep(16)
        seg = e - s; frames = int(seg * FPS) + 2
        z = "min(zoom+0.00025,1.10)" if i % 2 == 0 else "if(eq(on,1),1.10,max(zoom-0.00025,1))"
        c = f"{tmp}/clip{i}.mp4"
        sh("ffmpeg", "-y", "-loop", "1", "-i", p, "-vf",
           f"scale={int(W*1.25)}:{int(H*1.25)}:force_original_aspect_ratio=increase,crop={int(W*1.25)}:{int(H*1.25)},"
           f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
           f"eq=brightness=-0.08:saturation=1.05",
           "-t", f"{seg:.3f}", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", c)
        clips.append(c)
    print(f"  Bilder: {real}/{len(clips)} KI-Bilder")
    with open(f"{tmp}/vlist.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
    out = os.path.join(OUT, vid + ".mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/vlist.txt", "-i", f"{tmp}/voice.m4a",
       "-vf", f"ass={tmp}/subs.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
       "-c:a", "copy", "-shortest", "-movflags", "+faststart", out)

    # 4) Thumbnail 1280x720
    lines = spec.get("thumb", [spec["title"][:22]])
    vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=brightness=-0.18"
    y0 = 720 - 70 - 120 * len(lines)
    for k, ln in enumerate(lines):
        t = ln.replace(":", "\\:").replace("'", "’").replace("%", "\\%")
        vf += (f",drawtext=fontfile={BOLD}:text='{t}':fontsize=104:fontcolor=white:borderw=8:bordercolor=black"
               f":x=60:y={y0 + k * 120}" + (f":box=1:boxcolor=0x{col}@1:boxborderw=14" if k == 0 else ""))
    sh("ffmpeg", "-y", "-i", f"{tmp}/img{spec.get('thumb_img', 0)}.jpg", "-vf", vf, "-frames:v", "1", "-q:v", "3",
       os.path.join(OUT, vid + "-thumbnail.jpg"))

    # 5) Titel, Beschreibung mit Kapiteln, Tags
    kap = "Kapitel:\n" + "\n".join(f"{chap(0 if i == 0 else s)} {sc['ch']}"
                                    for i, ((s, e), sc) in enumerate(zip(scenes, spec["scenes"])) if "ch" in sc)
    desc = spec["description"].replace("{KAPITEL}", kap)
    open(os.path.join(OUT, vid + ".txt"), "w").write(
        f"KANAL: {spec['channel']}\nLÄNGE: {chap(total)} min\n\nTITEL:\n{spec['title']}\n\nBESCHREIBUNG:\n{desc}\n\n"
        f"TAGS:\n{spec.get('tags','')}\n\nBEIM HOCHLADEN:\n- Sichtbarkeit: PRIVAT (erst nach deiner Prüfung öffentlich)\n"
        "- 'Veränderte oder synthetische Inhalte': JA (KI-Stimme und KI-Bilder)\n"
        "- 'Nicht speziell für Kinder': auswählen\n"
        f"- Thumbnail: {vid}-thumbnail.jpg hochladen\n- Untertitel: {vid}.srt unter 'Untertitel' hochladen (Deutsch)\n")
    print(f"  ✓ {out} ({chap(total)} min, {os.path.getsize(out)/1e6:.0f} MB)")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for f in sys.argv[1:]:
        try:
            build(f)
        except Exception as e:
            print("  ✗", f, e); bad.append(f)
    sys.exit(1 if bad and len(bad) == len(sys.argv[1:]) else 0)
