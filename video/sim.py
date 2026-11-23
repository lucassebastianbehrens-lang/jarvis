"""Simulations-Videos (Stil „Was passiert, wenn …?“): zwei Bahnen im Duell, live mitgerechnet,
Erzählerstimme, Untertitel, Ergebnis-Karte. Alles per Code gezeichnet – keine KI-Bilder, keine Kosten.
Aufruf: python3 video/sim.py video/sim/<id>.json   Ausgabe: video/out/<id>.mp4 + <id>.txt + <id>.jpg
Lokaler Test ohne Netz: FAKE_TTS=1"""
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from long import tts, dur, sh, OUT

W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG, GRID, WHITE, YEL = (12, 20, 38), (32, 46, 74), (240, 244, 250), (255, 205, 60)
RAIN = (120, 160, 210)
F = {s: ImageFont.truetype(BOLD, s) for s in (30, 36, 44, 52, 64, 80, 96)}


def num(x):
    return f"{int(round(x)):,}".replace(",", ".")


def text_c(d, xy, t, font, fill, stroke=0):
    w = d.textlength(t, font=font)
    d.text((xy[0] - w / 2, xy[1]), t, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def figure(d, x, y, phase, col, run):
    """Strichmännchen: x = Mitte, y = Fußlinie; phase 0..1 Schrittzyklus."""
    s = 1.0
    hip = (x, y - 70 * s)
    head = (x + (8 if run else 0), y - 128 * s)
    a = math.sin(phase * 2 * math.pi) * (0.9 if run else 0.5)
    lean = 14 if run else 0
    d.line([hip, (head[0] - 4, head[1] + 26)], fill=col, width=12)
    for sgn in (1, -1):  # Beine
        ang = a * sgn
        knee = (hip[0] + math.sin(ang) * 36, hip[1] + math.cos(ang) * 36)
        foot = (knee[0] + math.sin(ang - (0.5 if run else 0.2)) * 36, knee[1] + math.cos(ang) * 34)
        d.line([hip, knee, foot], fill=col, width=11, joint="curve")
    sh_ = (hip[0] + lean * 0.6, hip[1] - 42)
    for sgn in (1, -1):  # Arme
        ang = -a * sgn * 0.9
        d.line([sh_, (sh_[0] + math.sin(ang) * 40, sh_[1] + math.cos(ang) * 40)], fill=col, width=9)
    d.ellipse([head[0] - 22, head[1] - 22, head[0] + 22, head[1] + 22], fill=WHITE)


def build(spec_path):
    sp = json.load(open(spec_path)); vid = sp["id"]
    tmp = os.path.join(OUT, vid + "_tmp"); os.makedirs(tmp, exist_ok=True)
    print("▶", vid)
    voice = sp.get("voice", "de-DE-ConradNeural")
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.2", f"{tmp}/gap.mp3")
    t0, alist, caps, ph = 0.4, [], [], {}
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.4", f"{tmp}/pre.mp3"); alist.append(f"{tmp}/pre.mp3")
    for i, ln in enumerate(sp["lines"]):
        mp3 = f"{tmp}/l{i}.mp3"
        ws = tts(ln["t"], voice, ln.get("rate", "+8%"), mp3)
        for k in range(0, len(ws), 3):
            c = ws[k:k + 3]
            caps.append((t0 + c[0][0], t0 + c[-1][1] + 0.05, " ".join(x[2] for x in c)))
        d = dur(mp3)
        p = ln.get("phase", "intro")
        a, b = ph.get(p, (t0, t0))
        ph[p] = (min(a, t0), t0 + d)
        t0 += d + 0.2; alist += [mp3, f"{tmp}/gap.mp3"]
    end0 = t0; t0 += 2.2
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2.2", f"{tmp}/end.mp3"); alist.append(f"{tmp}/end.mp3")
    with open(f"{tmp}/a.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in alist)
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/a.txt", "-ar", "44100", "-ac", "2", "-c:a", "aac", f"{tmp}/voice.m4a")
    total = t0

    # ---- Physik (Modell): Nässe = Regen von oben (Zeit) + Regen von vorne (Strecke) ----
    m = sp["modell"]
    D, rho, vr, At, Af = m["distanz_m"], m["tropfen_pro_m3"], m["fallgeschw_ms"], m["flaeche_oben_m2"], m["flaeche_vorne_m2"]
    L = []
    for key, col in (("a", (240, 70, 70)), ("b", (70, 215, 130))):
        p = sp[key]; v = p["kmh"] / 3.6
        L.append({"name": p["name"], "col": col, "v": v, "T": D / v, "rate": rho * (At * vr + Af * v), "run": p.get("rennt", False)})
    for l in L:
        l["total"] = l["rate"] * l["T"]
    rs, re_ = ph.get("race", (2, total - 6))
    tmax = max(l["T"] for l in L)
    k = tmax / max(1.0, re_ - rs)  # Simulationssekunden pro Videosekunde
    win, lose = sorted(L, key=lambda l: l["total"])
    pct = round((1 - win["total"] / lose["total"]) * 100)
    print(f"   {L[0]['name']}: {num(L[0]['total'])} · {L[1]['name']}: {num(L[1]['total'])} · Gewinner {win['name']} −{pct} %")

    rnd = random.Random(7)
    drops = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(18, 34)] for _ in range(230)]
    X0, X1 = 120, 960
    lanes = [830, 1300]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", f"{tmp}/voice.m4a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", os.path.join(OUT, vid + ".mp4")], stdin=subprocess.PIPE)
    n = int(total * FPS)
    thumb = None
    for fi in range(n):
        t = fi / FPS
        im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
        # Titel
        tw = [sp["titel"][0], " vs ", sp["titel"][1]]
        widths = [d.textlength(x, font=F[96] if i != 1 else F[52]) for i, x in enumerate(tw)]
        x = (W - sum(widths)) / 2
        for i, (s_, wdt) in enumerate(zip(tw, widths)):
            d.text((x, 150 + (26 if i == 1 else 0)), s_, font=F[96] if i != 1 else F[52], fill=[L[0]["col"], WHITE, L[1]["col"]][i]); x += wdt
        text_c(d, (W / 2, 290), sp["frage"][0], F[52], WHITE)
        text_c(d, (W / 2, 356), sp["frage"][1], F[64], YEL)
        # Regen
        for dr in drops:
            dr[1] = (dr[1] + dr[2]) % H
            d.line([(dr[0], dr[1]), (dr[0] - 3, dr[1] + 26)], fill=RAIN, width=3)
        st = max(0.0, (t - rs) * k)  # Simulationszeit
        for l, ly in zip(L, lanes):
            tt_ = min(st, l["T"]); pos = l["v"] * tt_
            got = l["rate"] * tt_
            d.rectangle([X0 - 20, ly + 2, X1 + 60, ly + 8], fill=GRID)
            for mm in (0, D / 2, D):
                xx = X0 + (X1 - X0) * mm / D
                d.line([(xx, ly + 8), (xx, ly + 28)], fill=GRID, width=4)
                text_c(d, (xx, ly + 34), f"{int(mm)} m", F[30], (130, 150, 180))
            # Dach / Ziel
            d.rectangle([X1 + 10, ly - 210, X1 + 90, ly - 196], fill=(170, 180, 200))
            d.line([(X1 + 20, ly - 196), (X1 + 20, ly + 4)], fill=(170, 180, 200), width=6)
            d.line([(X1 + 80, ly - 196), (X1 + 80, ly + 4)], fill=(170, 180, 200), width=6)
            d.text((X0 - 20, ly - 250), f"{l['name']}  {sp['a' if l is L[0] else 'b']['kmh']} km/h", font=F[36], fill=l["col"])
            xx = X0 + (X1 - X0) * pos / D + 50
            figure(d, xx, ly, (t * (2.2 if l["run"] else 1.1)) % 1 if tt_ < l["T"] else 0, l["col"], l["run"])
            # Zähler + Nässe-Balken
            box = [X0 - 20, ly + 80, X1 + 90, ly + 160]
            d.rounded_rectangle(box, 18, fill=(22, 34, 60))
            frac = got / lose["total"]
            d.rounded_rectangle([box[0], box[1], box[0] + (box[2] - box[0]) * frac, box[3]], 18, fill=(40, 110, 200))
            d.text((box[0] + 24, box[1] + 18), f"Tropfen abbekommen: {num(got)}", font=F[36], fill=WHITE)
            if tt_ >= l["T"]:
                d.text((box[2] - 190, ly - 300 + 52), "IM ZIEL", font=F[36], fill=YEL)
        # Ergebnis
        r0 = ph.get("result", (end0, end0))[0]
        if t >= r0:
            a = min(1, (t - r0) / 0.4)
            y = 1480 + (1 - a) * 80
            d.rounded_rectangle([90, y, W - 90, y + 250], 30, fill=(255, 205, 60))
            text_c(d, (W / 2, y + 34), f"{win['name']} GEWINNT", F[80], (20, 20, 30))
            text_c(d, (W / 2, y + 150), f"{pct} % weniger nass", F[64], (20, 20, 30))
            if thumb is None and a >= 1:
                thumb = im.copy()
        # Untertitel
        cur = next((c for c in caps if c[0] <= t <= c[1]), None)
        if cur and t < r0:
            tw_ = d.textlength(cur[2], font=F[64])
            d.rounded_rectangle([W / 2 - tw_ / 2 - 30, 1560, W / 2 + tw_ / 2 + 30, 1660], 24, fill=WHITE)
            text_c(d, (W / 2, 1572), cur[2], F[64], (15, 15, 25))
        if t >= end0:
            d.rectangle([0, 1760, W, 1880], fill=(0, 0, 0))
            text_c(d, (W / 2, 1785), sp.get("ende", "FOLGEN FÜR MEHR SIMULATIONEN"), F[52], YEL)
        ff.stdin.write(im.tobytes())
    ff.stdin.close(); ff.wait()
    (thumb or im).convert("RGB").save(os.path.join(OUT, vid + ".jpg"), quality=90)
    with open(os.path.join(OUT, vid + ".txt"), "w") as f:
        f.write(f"{sp['caption']}\n\n{' '.join(sp['hashtags'])}\n\nModell: {sp.get('quelle', '')}\n")
    print("   ✓", vid + ".mp4", f"{total:.1f} s")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for p in sys.argv[1:]:
        build(p)
