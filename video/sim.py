"""Simulations-Videos (Stil „Was passiert, wenn …?“): zwei Bahnen im Duell, live mitgerechnet,
Erzählerstimme, Untertitel, Ergebnis-Karte. Alles per Code gezeichnet – keine KI-Bilder, keine Kosten.
Aufruf: python3 video/sim.py video/sim/<id>.json   Ausgabe: video/out/<id>.mp4 + <id>.txt + <id>.jpg
Lokaler Test ohne Netz: FAKE_TTS=1"""
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
try:
    import numpy  # noqa: F401  (nur für den Lichtschein; ohne numpy einfacher Ersatz)
    _NP = True
except ImportError:
    _NP = False
sys.path.insert(0, os.path.dirname(__file__))
from long import tts, dur, sh, OUT

W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG, GRID, WHITE, YEL = (12, 20, 38), (32, 46, 74), (240, 244, 250), (255, 205, 60)
RAIN = (120, 160, 210)
F = {s: ImageFont.truetype(BOLD, s) for s in (24, 30, 36, 40, 44, 48, 52, 56, 64, 72, 80, 96)}


def passend(d, text, max_w, start):
    """Größte Schrift (<= start), mit der text in max_w Pixel passt – nichts läuft mehr aus dem Bild."""
    for g in sorted((g for g in F if g <= start), reverse=True):
        if d.textlength(text, font=F[g]) <= max_w:
            return F[g]
    return F[24]
# Jede Folge klingt und sieht etwas anders aus (keine 1:1-Kopien -> kein „unoriginal“-Filter)
VOICES = ["de-DE-ConradNeural", "de-DE-KillianNeural", "de-DE-FlorianMultilingualNeural",
          "de-DE-SeraphinaMultilingualNeural", "de-DE-AmalaNeural", "de-DE-KatjaNeural"]
THEMES = [((12, 20, 38), (32, 46, 74)), ((24, 14, 36), (54, 36, 78)), ((10, 28, 30), (28, 62, 66)),
          ((30, 22, 14), (70, 52, 34)), ((16, 16, 20), (44, 44, 56))]
PAIRS = [((240, 70, 70), (70, 215, 130)), ((255, 140, 40), (70, 160, 255)), ((230, 80, 200), (90, 220, 220)),
         ((255, 200, 50), (150, 110, 255))]


def car(d, x, y, col, phase):
    d.rounded_rectangle([x - 60, y - 52, x + 60, y - 18], 10, fill=col)
    d.rounded_rectangle([x - 34, y - 80, x + 30, y - 50], 10, fill=col)
    d.rectangle([x - 26, y - 74, x + 22, y - 54], fill=(30, 40, 60))
    for wx in (x - 34, x + 34):
        d.ellipse([wx - 16, y - 34, wx + 16, y - 2], fill=(20, 20, 24))
        a = phase * 2 * math.pi
        d.line([(wx, y - 18), (wx + math.cos(a) * 12, y - 18 + math.sin(a) * 12)], fill=(160, 160, 170), width=4)


def bike(d, x, y, col, phase):
    for wx in (x - 34, x + 34):
        d.ellipse([wx - 24, y - 48, wx + 24, y], outline=WHITE, width=6)
    d.line([(x - 34, y - 24), (x, y - 24), (x + 34, y - 24), (x + 10, y - 56), (x - 10, y - 24)], fill=col, width=7)
    figure(d, x - 4, y - 36, phase, col, False)


def ease_out_back(a):
    """Animation mit kleinem Überschwinger (wirkt „lebendig“)."""
    a = max(0.0, min(1.0, a)); c = 1.70158
    return 1 + (c + 1) * (a - 1) ** 3 + c * (a - 1) ** 2


def hintergrund(bg, grid, glow):
    """Einmal pro Video: Verlauf + Lichtschein + feines Raster + Vignette (pro Bild nur noch kopiert -> schnell)."""
    from PIL import ImageFilter
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
    top = tuple(min(255, int(c * 1.6) + 8) for c in bg); bot = tuple(int(c * 0.45) for c in bg)
    for y in range(0, H, 4):
        f = y / H
        d.rectangle([0, y, W, y + 4], fill=tuple(int(top[i] * (1 - f) + bot[i] * f) for i in range(3)))
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=tuple(int(c * 0.55 + g * 0.45) for c, g in zip(bg, grid)), width=1)
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=tuple(int(c * 0.55 + g * 0.45) for c, g in zip(bg, grid)), width=1)
    licht = Image.new("RGB", (W, H), (0, 0, 0)); ld = ImageDraw.Draw(licht)
    for (cx, cy), col in zip(((W * 0.2, 560), (W * 0.8, 1300)), glow):
        ld.ellipse([cx - 420, cy - 420, cx + 420, cy + 420], fill=tuple(int(c * 0.35) for c in col))
    licht = licht.filter(ImageFilter.GaussianBlur(160))
    if _NP:  # Licht dazuaddieren (heller Schein in den Spielerfarben)
        import numpy as np
        im = Image.fromarray(np.clip(np.asarray(im, dtype=np.int16) + np.asarray(licht, dtype=np.int16), 0, 255).astype(np.uint8))
    else:
        im = Image.blend(im, licht, 0.25)
    vig = Image.new("L", (W, H), 0); ImageDraw.Draw(vig).ellipse([-260, -200, W + 260, H + 200], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(220))
    return Image.composite(im, Image.new("RGB", (W, H), tuple(int(c * 0.3) for c in bg)), vig)


def schatten_text(d, xy, t, font, fill, mitte=True):
    """Text mit weichem Schlagschatten + Kontur (gut lesbar auf jedem Hintergrund)."""
    x = xy[0] - (d.textlength(t, font=font) / 2 if mitte else 0)
    d.text((x + 5, xy[1] + 7), t, font=font, fill=(0, 0, 0))
    d.text((x, xy[1]), t, font=font, fill=fill, stroke_width=4, stroke_fill=(8, 10, 18))


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
    h_ = sum(map(ord, vid))
    voice = sp.get("voice") or VOICES[h_ % len(VOICES)]
    global BG, GRID
    BG, GRID = THEMES[h_ % len(THEMES)]
    cols = PAIRS[(h_ // 7) % len(PAIRS)]
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.2", f"{tmp}/gap.mp3")
    t0, alist, caps, ph = 0.4, [], [], {}
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.4", f"{tmp}/pre.mp3"); alist.append(f"{tmp}/pre.mp3")
    for i, ln in enumerate(sp["lines"]):
        mp3 = f"{tmp}/l{i}.mp3"
        ws = tts(ln["t"], voice, ln.get("rate", f"+{4 + h_ % 9}%"), mp3)
        for k in range(0, len(ws), 3):
            c = ws[k:k + 3]
            caps.append((t0 + c[0][0], t0 + c[-1][1] + 0.05, " ".join(x[2] for x in c), [(t0 + x[0], x[2]) for x in c]))
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
    L = []
    if m.get("typ", "regen") == "regen":  # Nässe = Regen von oben (Zeit) + Regen von vorne (Strecke)
        D, rho, vr, At, Af = m["distanz_m"], m["tropfen_pro_m3"], m["fallgeschw_ms"], m["flaeche_oben_m2"], m["flaeche_vorne_m2"]
        for key, col in zip(("a", "b"), cols):
            p = sp[key]; v = p["kmh"] / 3.6
            L.append({"name": p["name"], "col": col, "T": D / v, "rate": rho * (At * vr + Af * v), "run": p.get("rennt", False),
                      "fig": "laeufer" if p.get("rennt") else "geher", "info": f"{p['kmh']} km/h"})
        einheit, label, regen, weniger_gut = "", m.get("zaehler", "Tropfen abbekommen"), True, True
        for l in L:
            l["total"] = l["rate"] * l["T"]
    else:  # generisch: jede Seite braucht dauer_s (Simulationszeit) und kommt am Ende auf „menge“
        D = 100
        for key, col in zip(("a", "b"), cols):
            p = sp[key]
            L.append({"name": p["name"], "col": col, "T": float(p["dauer_s"]), "total": float(p["menge"]),
                      "rate": float(p["menge"]) / float(p["dauer_s"]), "run": p.get("figur") == "laeufer",
                      "fig": p.get("figur", "geher"), "info": p.get("info", "")})
        einheit, label = m.get("einheit", ""), m.get("zaehler", "")
        regen, weniger_gut = m.get("wetter") == "regen", m.get("besser", "weniger") == "weniger"
    rs, re_ = ph.get("race", (2, total - 6))
    tmax = max(l["T"] for l in L)
    k = tmax / max(1.0, re_ - rs)  # Simulationssekunden pro Videosekunde
    win, lose = sorted(L, key=lambda l: l["total"], reverse=not weniger_gut)
    big = max(l["total"] for l in L)
    pct = round(abs(1 - win["total"] / lose["total"]) * 100)
    fmt = (lambda x: (f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") if big < 100 else num(x)) + (" " + einheit if einheit else ""))
    print(f"   {L[0]['name']}: {num(L[0]['total'])} · {L[1]['name']}: {num(L[1]['total'])} · Gewinner {win['name']} −{pct} %")

    rnd = random.Random(7)
    drops = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(18, 34)] for _ in range(230)]
    X0, X1 = 120, 860          # rechts bleibt Platz für TikToks Knöpfe
    lanes = [720, 1170]        # alles Wichtige oberhalb von ~1550 px (unten liegt TikToks Beschreibung)
    bgimg = hintergrund(BG, GRID, cols)
    conf = [(rnd.uniform(90, W - 90), rnd.uniform(-300, 0), rnd.uniform(-4, 4), rnd.uniform(6, 13), rnd.choice([YEL, WHITE, cols[0], cols[1]]))
            for _ in range(90)]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", f"{tmp}/voice.m4a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", os.path.join(OUT, vid + ".mp4")], stdin=subprocess.PIPE)
    n = int(total * FPS)
    thumb = None
    for fi in range(n):
        t = fi / FPS
        im = bgimg.copy(); d = ImageDraw.Draw(im)
        # Titel: fliegt in der ersten halben Sekunde von oben herein
        dy = (1 - ease_out_back(t / 0.5)) * -160
        tw = [sp["titel"][0], " vs ", sp["titel"][1]]
        gross = passend(d, tw[0] + tw[2], W - 140 - d.textlength(" vs ", font=F[52]), 96)
        widths = [d.textlength(x, font=gross if i != 1 else F[52]) for i, x in enumerate(tw)]
        x = (W - sum(widths)) / 2
        for i, (s_, wdt) in enumerate(zip(tw, widths)):
            schatten_text(d, (x, 150 + dy + (26 if i == 1 else 0)), s_, gross if i != 1 else F[52], [L[0]["col"], WHITE, L[1]["col"]][i], False); x += wdt
        fy = (1 - ease_out_back((t - 0.25) / 0.5)) * 60
        schatten_text(d, (W / 2, 290 + fy), sp["frage"][0], passend(d, sp["frage"][0], W - 120, 52), WHITE)
        schatten_text(d, (W / 2, 356 + fy), sp["frage"][1], passend(d, sp["frage"][1], W - 120, 64), YEL)
        # Regen
        for dr in (drops if regen else []):
            dr[1] = (dr[1] + dr[2]) % H
            d.line([(dr[0], dr[1]), (dr[0] - 3, dr[1] + 26)], fill=RAIN, width=3)
        st = max(0.0, (t - rs) * k)  # Simulationszeit
        for l, ly in zip(L, lanes):
            tt_ = min(st, l["T"])
            got = l["rate"] * tt_
            d.rounded_rectangle([X0 - 30, ly - 4, X1 + 70, ly + 14], 9, fill=tuple(int(c * 0.35) for c in l["col"]))
            d.rounded_rectangle([X0 - 30, ly - 4, X0 - 30 + (X1 + 100 - X0) * min(1, tt_ / l["T"]), ly + 14], 9, fill=l["col"])
            for i_, mm in enumerate(sp.get("skala", [f"0 m", f"{int(D/2)} m", f"{int(D)} m"])):
                xx = X0 + (X1 - X0) * i_ / 2
                d.line([(xx, ly + 8), (xx, ly + 28)], fill=GRID, width=4)
                text_c(d, (xx, ly + 34), mm, F[30], (130, 150, 180))
            # Dach / Ziel
            d.rectangle([X1 + 10, ly - 210, X1 + 90, ly - 196], fill=(170, 180, 200))
            d.line([(X1 + 20, ly - 196), (X1 + 20, ly + 4)], fill=(170, 180, 200), width=6)
            d.line([(X1 + 80, ly - 196), (X1 + 80, ly + 4)], fill=(170, 180, 200), width=6)
            lab = f"{l['name']}  {l['info']}"
            lf = next((F[g] for g in (44, 36, 30) if d.textlength(lab, font=F[g]) <= X1 - 60 - X0), F[30])
            schatten_text(d, (X0 - 20, ly - 215), lab, lf, l["col"], False)
            d.ellipse([xx_s := X0 + (X1 - X0) * (tt_ / l["T"]) + 50 - 70, ly - 6, xx_s + 140, ly + 18], fill=tuple(int(c * 0.25) for c in BG))  # Bodenschatten
            xx = X0 + (X1 - X0) * (tt_ / l["T"]) + 50
            phs = (t * (2.2 if l["run"] else 1.1)) % 1 if tt_ < l["T"] else 0
            if l["fig"] == "auto":
                car(d, xx, ly, l["col"], phs)
            elif l["fig"] == "rad":
                bike(d, xx, ly, l["col"], phs)
            else:
                figure(d, xx, ly, phs, l["col"], l["run"])
            # Zähler + Nässe-Balken
            box = [X0 - 20, ly + 80, X1 + 90, ly + 160]
            d.rounded_rectangle([box[0] + 6, box[1] + 10, box[2] + 6, box[3] + 10], 22, fill=(0, 0, 0))
            d.rounded_rectangle(box, 22, fill=tuple(int(c * 0.6) + 10 for c in BG), outline=l["col"], width=4)
            frac = got / big
            if frac > 0.02:
                bx1 = box[0] + (box[2] - box[0]) * frac
                d.rounded_rectangle([box[0], box[1], bx1, box[3]], 22, fill=tuple(int(c * 0.75) for c in l["col"]))
                d.rounded_rectangle([box[0] + 8, box[1] + 8, bx1 - 8, box[1] + 26], 9, fill=tuple(min(255, int(c * 1.15) + 20) for c in l["col"]))  # Glanzkante
            schatten_text(d, (box[0] + 24, box[1] + 16), f"{label}: {fmt(got)}" if label else fmt(got), F[44], WHITE, False)
            if tt_ >= l["T"]:
                d.rounded_rectangle([X1 - 40, ly - 268, X1 + 130, ly - 218], 16, fill=YEL)  # Abzeichen über dem Ziel
                text_c(d, (X1 + 45, ly - 262), "IM ZIEL", F[36], (20, 20, 30))
        # Ergebnis
        r0 = ph.get("result", (end0, end0))[0]
        if t >= r0:
            a = min(1, (t - r0) / 0.4)
            y = 1340 + (1 - ease_out_back((t - r0) / 0.55)) * 260
            for cx, cy, vx, sz, cc in conf:  # Konfetti
                ct = t - r0; px, py = cx + vx * ct * 40, cy + ct * 520
                if py < H:
                    d.rectangle([px, py, px + sz, py + sz * 1.6], fill=cc)
            d.rounded_rectangle([96, y + 12, W - 84, y + 262], 30, fill=(0, 0, 0))
            d.rounded_rectangle([90, y, W - 90, y + 250], 30, fill=(255, 205, 60), outline=WHITE, width=5)
            gw = f"{win['name']} GEWINNT"; eg = sp.get("ergebnis", "{p} % weniger").replace("{p}", str(pct))
            text_c(d, (W / 2, y + 34), gw, passend(d, gw, W - 240, 80), (20, 20, 30))
            text_c(d, (W / 2, y + 150), eg, passend(d, eg, W - 240, 64), (20, 20, 30))
            if thumb is None and a >= 1:
                thumb = im.copy()
        # Untertitel
        # Untertitel im TikTok-Stil: das gerade gesprochene Wort leuchtet gelb, Zeile springt kurz an
        cur = next((c for c in caps if c[0] <= t <= c[1]), None)
        if cur and t < r0:
            fnt = passend(d, cur[2], W - 160, 64); sp_w = d.textlength(" ", font=fnt)
            ws_ = [w for _, w in cur[3]]; ww = [d.textlength(w, font=fnt) for w in ws_]
            tot = sum(ww) + sp_w * (len(ws_) - 1)
            cy = 1420 - (1 - ease_out_back((t - cur[0]) / 0.18)) * 18
            d.rounded_rectangle([W / 2 - tot / 2 - 34, cy - 14, W / 2 + tot / 2 + 34, cy + 92], 26, fill=(10, 12, 20))
            x = W / 2 - tot / 2
            jetzt = max([i for i, (st_, _) in enumerate(cur[3]) if st_ <= t] or [0])
            for i, (w, wd) in enumerate(zip(ws_, ww)):
                d.text((x, cy), w, font=fnt, fill=YEL if i == jetzt else WHITE, stroke_width=3, stroke_fill=(0, 0, 0)); x += wd + sp_w
        if t >= end0:
            d.rounded_rectangle([60, 1620, W - 60, 1710], 26, fill=(0, 0, 0))
            text_c(d, (W / 2, 1638), sp.get("ende", "FOLGEN FÜR MEHR SIMULATIONEN"), F[52], YEL)
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
