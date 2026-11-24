"""Zeichentrick „Stell dir vor“ – Finn wird komplett per Code gezeichnet (SVG → Bilder → Video).
Dadurch sieht er in jeder Folge exakt gleich aus, und kein Bild kostet etwas.
Aufruf: python3 video/zt.py video/zt/<id>.json   Ausgabe: video/out/<id>.mp4 + <id>.txt (Beschreibung) + <id>.jpg (Vorschau)"""
import asyncio, json, math, os, re, subprocess, sys, wave
import numpy as np
import cairosvg

W, H, FPS, SR = 1080, 1920, 24, 24000
VOICE = "de-DE-FlorianMultilingualNeural"
ROT = "#ff4d5a"


def sh(*a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def zahl_de(n):
    return f"{int(n):,}".replace(",", ".")


# ---------- Ton ----------
async def _tts(text, out):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-6%", pitch="-2Hz").save(out)


def sprache(text, tmp, i):
    """Erzähler-Stimme als Zahlenreihe (24 kHz mono). Ohne Internet: Stille in Sprechlänge (nur zum Testen)."""
    mp3, wav = f"{tmp}/v{i}.mp3", f"{tmp}/v{i}.wav"
    try:
        asyncio.run(_tts(text, mp3))
        sh("ffmpeg", "-y", "-i", mp3, "-ar", str(SR), "-ac", "1", wav)
        with wave.open(wav) as w:
            return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    except Exception as e:
        if os.environ.get("ZT_OHNE_STIMME") != "1":
            raise RuntimeError(f"Stimme fehlgeschlagen: {e}")
        return np.zeros(int(SR * max(1.2, len(text.split()) * 0.36)), np.float32)


def ding(sek=0.5):
    t = np.arange(int(SR * sek)) / SR
    return (0.18 * np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 7) + 0.1 * np.sin(2 * np.pi * 1975.5 * t) * np.exp(-t * 9)).astype(np.float32)


# ---------- Bühne ----------
def lichterkette(y0, t):
    s = ""
    for i in range(12):
        x = 40 + i * 92
        y = y0 + 26 * math.sin(i * 0.9)
        an = 0.55 + 0.45 * math.sin(t * 2.2 + i * 1.7)
        s += f'<circle cx="{x}" cy="{y:.0f}" r="11" fill="#ffd58a" opacity="{an:.2f}"/><circle cx="{x}" cy="{y:.0f}" r="26" fill="#ffd58a" opacity="{an * 0.18:.2f}"/>'
    return f'<path d="M0 {y0} Q540 {y0 + 70} 1080 {y0}" stroke="#2a1a22" stroke-width="3" fill="none"/>' + s


def hintergrund(art, t):
    zimmer = ('<rect width="1080" height="1920" fill="url(#wand)"/>'
              '<polygon points="0,0 1080,0 1080,180 0,520" fill="#3a2433"/>'
              '<polygon points="0,520 1080,180 1080,215 0,560" fill="#2a1a24"/>'
              '<rect x="700" y="420" width="250" height="300" rx="10" fill="#1d2440"/>'
              '<circle cx="860" cy="500" r="38" fill="#fff2c4"/><rect x="700" y="420" width="250" height="300" rx="10" fill="none" stroke="#2a1a24" stroke-width="16"/>'
              '<line x1="825" y1="420" x2="825" y2="720" stroke="#2a1a24" stroke-width="10"/>'
              '<rect x="80" y="760" width="300" height="16" fill="#6b4434"/>'
              + "".join(f'<rect x="{95 + i * 34}" y="{690 + (i % 3) * 10}" width="26" height="{70 - (i % 3) * 10}" fill="{c}"/>'
                        for i, c in enumerate(["#e0794c", "#6aa6a0", "#f1c55f", "#8f6bb3", "#e05a64", "#5c8fd6", "#d9a05b", "#7fb069"]))
              + lichterkette(600, t))
    boden = '<rect y="1560" width="1080" height="360" fill="#4a3027"/><rect y="1560" width="1080" height="14" fill="#3a241d"/>'
    if art == "strasse":
        return ('<rect width="1080" height="1920" fill="url(#himmel)"/>'
                + "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{1600 - y}" fill="{c}"/>'
                          for x, y, w, c in [(-20, 700, 300, "#7a5a8c"), (260, 820, 260, "#a0718f"), (500, 640, 320, "#6c4f7d"), (800, 760, 300, "#8d6a95")])
                + "".join(f'<rect x="{x}" y="{y}" width="40" height="56" fill="#ffd58a" opacity=".8"/>' for x, y in
                          [(40, 780), (140, 900), (330, 900), (560, 720), (680, 860), (880, 840), (960, 960)])
                + '<rect y="1600" width="1080" height="320" fill="#5b5662"/><rect y="1740" width="1080" height="12" fill="#e7e3d8" stroke-dasharray="80 60"/>')
    if art == "nacht":
        sterne = "".join(f'<circle cx="{(i * 397) % 1080}" cy="{(i * 211) % 1100}" r="{2 + i % 3}" fill="#fff" opacity="{0.4 + 0.5 * abs(math.sin(t + i)):.2f}"/>'
                         for i in range(40))
        return ('<rect width="1080" height="1920" fill="#141634"/>' + sterne + '<circle cx="820" cy="360" r="90" fill="#fff2c4"/>'
                '<polygon points="0,1500 300,1380 640,1460 1080,1340 1080,1920 0,1920" fill="#25203f"/>')
    if art == "schule":
        return ('<rect width="1080" height="1920" fill="#e9dcc2"/><rect x="120" y="380" width="840" height="420" rx="14" fill="#2f5d4a" stroke="#7a5236" stroke-width="22"/>'
                '<path d="M200 520 q60 -40 120 0 t120 0" stroke="#e9f2ea" stroke-width="6" fill="none" opacity=".7"/>' + boden)
    if art == "kueche":
        return ('<rect width="1080" height="1920" fill="#f4e6cf"/>'
                + "".join(f'<rect x="{x}" y="{y}" width="118" height="118" fill="none" stroke="#e2cfae" stroke-width="4"/>' for x in range(0, 1080, 120) for y in range(300, 1560, 120))
                + '<rect x="800" y="560" width="220" height="1000" rx="20" fill="#dfe7ea" stroke="#b9c5ca" stroke-width="6"/>' + boden)
    extra = ""
    if art == "bett":
        extra = '<rect x="60" y="1340" width="960" height="260" rx="40" fill="#e8e2f0"/><rect x="120" y="1240" width="260" height="140" rx="50" fill="#fff"/>'
    if art == "schreibtisch":
        extra = '<rect x="560" y="900" width="420" height="20" fill="#2a1a24"/><path d="M880 900 l-40 -120 l90 -30" stroke="#2a1a24" stroke-width="10" fill="none"/><ellipse cx="930" cy="740" rx="60" ry="34" fill="#f1a34a"/>'
    return zimmer + boden + extra


DEFS = ('<defs><linearGradient id="wand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7c4f63"/><stop offset="1" stop-color="#4b2f45"/></linearGradient>'
        '<linearGradient id="himmel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9e7a"/><stop offset="1" stop-color="#ffd3a1"/></linearGradient>'
        '<radialGradient id="schein"><stop offset="0" stop-color="#bfe6ff" stop-opacity=".55"/><stop offset="1" stop-color="#bfe6ff" stop-opacity="0"/></radialGradient></defs>')


DECKE = ('<path d="M40 1500 C200 1440 400 1470 540 1450 C700 1430 880 1470 1040 1440 L1040 1920 L40 1920 Z" fill="#8f6bb3"/>'
         '<path d="M40 1500 C200 1440 400 1470 540 1450 C700 1430 880 1470 1040 1440" stroke="#7a59a0" stroke-width="16" fill="none"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="10" fill="#b89bd6"/>' for x, y in [(160, 1600), (380, 1700), (620, 1620), (860, 1720), (500, 1820)]))


# ---------- Finn ----------
def finn(pose, prop, t, spricht, blinzeln):
    bob = 6 * math.sin(t * 2.1)
    if pose == "schock":
        bob += 3 * math.sin(t * 40)  # leichtes Zittern
    g = f'<g transform="translate(0 {bob:.1f})">'
    # Pulli + Kapuze + Kopfhörer
    g += ('<path d="M300 1900 C300 1420 360 1250 540 1240 C720 1250 780 1420 780 1900 Z" fill="#3f9b6e"/>'
          '<path d="M420 1250 C440 1330 640 1330 660 1250" stroke="#2f7a55" stroke-width="18" fill="none"/>'
          '<line x1="500" y1="1310" x2="490" y2="1430" stroke="#e8e2d0" stroke-width="7"/><line x1="580" y1="1310" x2="590" y2="1430" stroke="#e8e2d0" stroke-width="7"/>'
          '<path d="M400 1215 C420 1310 660 1310 680 1215" stroke="#e0353f" stroke-width="26" fill="none" stroke-linecap="round"/>'
          '<rect x="370" y="1185" width="56" height="78" rx="22" fill="#e0353f"/><rect x="654" y="1185" width="56" height="78" rx="22" fill="#e0353f"/>')
    # Arme
    haut = "#f2c7a5"
    arm = lambda d: f'<path d="{d}" stroke="#3f9b6e" stroke-width="64" fill="none" stroke-linecap="round"/>'
    hand = lambda x, y: f'<circle cx="{x}" cy="{y}" r="34" fill="{haut}"/>'
    if prop in ("handy", "laptop", "brief", "geld") and pose not in ("schock", "zeigen", "schlafen"):
        g += arm("M360 1360 Q380 1520 470 1470") + arm("M720 1360 Q700 1520 610 1470")
        if prop == "handy":
            g += ('<ellipse cx="540" cy="1300" rx="190" ry="160" fill="url(#schein)"/>'
                  '<rect x="470" y="1320" width="140" height="230" rx="22" fill="#1b1d2b" stroke="#444" stroke-width="6"/>'
                  '<rect x="482" y="1334" width="116" height="200" rx="12" fill="#bfe6ff"/>')
        elif prop == "brief":
            g += '<rect x="430" y="1360" width="220" height="150" rx="6" fill="#fffaf0" stroke="#d8c9a8" stroke-width="5"/><path d="M430 1362 L540 1440 L650 1362" stroke="#d8c9a8" stroke-width="5" fill="none"/>'
        elif prop == "geld":
            g += "".join(f'<rect x="{440 + i * 14}" y="{1380 - i * 16}" width="200" height="100" rx="8" fill="#7fbf7a" stroke="#4f8f4c" stroke-width="4"/>' for i in range(3))
        elif prop == "laptop":
            g += '<rect x="400" y="1360" width="280" height="180" rx="12" fill="#c9ced6"/><rect x="380" y="1530" width="320" height="22" rx="8" fill="#a9afb8"/>'
        g += hand(470, 1470) + hand(610, 1470)
    elif pose == "schock":
        g += arm("M360 1360 Q330 1200 420 1050") + arm("M720 1360 Q750 1200 660 1050") + hand(420, 1050) + hand(660, 1050)
    elif pose == "zeigen":
        g += arm("M360 1360 Q360 1520 420 1600") + arm("M720 1360 Q860 1300 900 1180") + hand(420, 1600) + hand(905, 1170)
    elif pose == "denken":
        g += arm("M360 1360 Q360 1520 420 1600") + arm("M720 1360 Q700 1260 600 1180") + hand(420, 1600) + hand(600, 1175)
    elif pose == "freude":
        g += arm("M360 1360 Q260 1200 300 1020") + arm("M720 1360 Q820 1200 780 1020") + hand(300, 1010) + hand(780, 1010)
    else:
        g += arm("M360 1360 Q340 1520 400 1610") + arm("M720 1360 Q740 1520 680 1610") + hand(400, 1610) + hand(680, 1610)
    if prop == "wecker":
        klingeln = 6 * math.sin(t * 50)
        g += f'<g transform="rotate({klingeln:.1f} 860 1560)"><circle cx="860" cy="1560" r="70" fill="#f1c55f" stroke="#2a1a24" stroke-width="8"/><line x1="860" y1="1560" x2="860" y2="1515" stroke="#2a1a24" stroke-width="7"/><line x1="860" y1="1560" x2="890" y2="1575" stroke="#2a1a24" stroke-width="7"/></g>'
    # Kopf
    g += (f'<circle cx="540" cy="980" r="190" fill="{haut}"/><ellipse cx="352" cy="1000" rx="26" ry="40" fill="{haut}"/><ellipse cx="728" cy="1000" rx="26" ry="40" fill="{haut}"/>'
          '<path d="M350 960 C330 780 460 740 540 760 C640 730 770 790 735 960 C720 880 690 860 650 850 C640 890 600 880 590 850 C560 880 520 880 500 850 C470 885 420 880 410 860 C380 880 365 910 350 960 Z" fill="#2b2220"/>'
          '<circle cx="415" cy="1050" r="26" fill="#f29c8f" opacity=".45"/><circle cx="665" cy="1050" r="26" fill="#f29c8f" opacity=".45"/>')
    # Augen (hinter Brille)
    gross = {"staunen": 1.35, "schock": 1.55}.get(pose, 1.0)
    blick = {"denken": (12, -14), "zeigen": (6, 4)}.get(pose, (0, 0))
    for x in (478, 602):
        if pose == "schlafen" or blinzeln:
            g += f'<path d="M{x - 22} 990 Q{x} 1004 {x + 22} 990" stroke="#2b2220" stroke-width="7" fill="none" stroke-linecap="round"/>'
        elif pose == "freude":
            g += f'<path d="M{x - 22} 996 Q{x} 970 {x + 22} 996" stroke="#2b2220" stroke-width="8" fill="none" stroke-linecap="round"/>'
        else:
            r = 15 * gross if pose != "schock" else 9
            g += f'<circle cx="{x}" cy="988" r="{24 * gross:.0f}" fill="#fff"/><circle cx="{x + blick[0]}" cy="{990 + blick[1]}" r="{r:.0f}" fill="#2b2220"/><circle cx="{x + blick[0] + 5}" cy="{984 + blick[1]}" r="4" fill="#fff"/>'
    g += ('<circle cx="478" cy="990" r="50" fill="none" stroke="#2b2220" stroke-width="9"/><circle cx="602" cy="990" r="50" fill="none" stroke="#2b2220" stroke-width="9"/>'
          '<path d="M528 985 Q540 975 552 985" stroke="#2b2220" stroke-width="8" fill="none"/>')
    braue = {"staunen": -26, "schock": -34, "traurig": 0, "denken": -8}.get(pose, -14)
    if pose == "traurig":
        g += '<path d="M440 925 L505 912" stroke="#2b2220" stroke-width="9" stroke-linecap="round"/><path d="M575 912 L640 925" stroke="#2b2220" stroke-width="9" stroke-linecap="round"/>'
    else:
        g += f'<path d="M440 {930 + braue} Q478 {915 + braue} 515 {930 + braue}" stroke="#2b2220" stroke-width="9" fill="none" stroke-linecap="round"/>'
        g += f'<path d="M565 {930 + braue} Q602 {915 + braue} 640 {930 + braue}" stroke="#2b2220" stroke-width="9" fill="none" stroke-linecap="round"/>'
    # Mund
    if pose in ("staunen", "schock"):
        h = 34 if pose == "schock" else 22
        g += f'<ellipse cx="540" cy="1085" rx="{h * 0.7 + (6 if spricht else 0):.0f}" ry="{h + (8 if spricht else 0)}" fill="#5a2a2a"/>'
    elif spricht:
        g += '<path d="M500 1075 Q540 1125 580 1075 Z" fill="#5a2a2a"/>'
    elif pose == "freude":
        g += '<path d="M490 1065 Q540 1130 590 1065 Z" fill="#5a2a2a"/><path d="M505 1070 Q540 1085 575 1070" fill="#fff"/>'
    elif pose == "traurig":
        g += '<path d="M505 1095 Q540 1070 575 1095" stroke="#5a2a2a" stroke-width="8" fill="none" stroke-linecap="round"/>'
    elif pose == "schlafen":
        g += '<ellipse cx="540" cy="1085" rx="10" ry="8" fill="#5a2a2a"/>'
        z = (t * 0.8) % 1
        g += f'<text x="{700 + z * 60:.0f}" y="{820 - z * 120:.0f}" font-size="{50 + z * 30:.0f}" font-family="DejaVu Sans" font-weight="bold" fill="#fff" opacity="{1 - z:.2f}">Z</text>'
    else:
        g += '<path d="M505 1078 Q540 1102 575 1078" stroke="#5a2a2a" stroke-width="8" fill="none" stroke-linecap="round"/>'
    return g + "</g>"


# ---------- Schrift ----------
def textzeile(txt, y, groesse, farbe="#fff", rand=14):
    s = esc(txt)
    return (f'<text x="540" y="{y}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="{groesse}" '
            f'fill="none" stroke="#1a0f16" stroke-width="{rand}" stroke-linejoin="round">{s}</text>'
            f'<text x="540" y="{y}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="{groesse}" fill="{farbe}">{s}</text>')


def zaehler(wert, label, pop):
    sk = 1 + 0.12 * pop
    breite = len(zahl_de(wert)) * 128 * 0.62
    auge = (f'<g transform="translate({540 - breite / 2 - 80:.0f} 318)"><ellipse rx="54" ry="34" fill="#fff" stroke="#1a0f16" stroke-width="10"/>'
            f'<circle r="20" fill="{ROT}"/><circle r="8" fill="#1a0f16"/></g>') if label.lower().startswith("aufruf") else ""
    return (f'<g transform="translate(540 330) scale({sk:.3f}) translate(-540 -330)">{auge}'
            + textzeile(zahl_de(wert) + ("" if not label or auge else f" {label}"), 362, 128, ROT, 22) + "</g>")


def chunks(text, n=4):
    w = text.split()
    return [" ".join(w[i:i + n]) for i in range(0, len(w), n)]


# ---------- Bau ----------
def build(spec_path):
    sp = json.load(open(spec_path, encoding="utf-8"))
    sid = sp["id"]
    tmp = f"video/out/{sid}_tmp"
    os.makedirs(tmp, exist_ok=True)
    szenen, ton, t0, vorher = [], [], 0.0, 0
    for i, s in enumerate(sp["scenes"]):
        pause = float(s.get("pause", 0) or 0)
        st = sprache(s["text"], tmp, i)
        dauer = pause + len(st) / SR + 0.35
        z = s.get("zahl")
        szenen.append({**s, "t0": t0, "pause": pause, "sprech": len(st) / SR, "dauer": dauer, "von": vorher if z is not None else None})
        ton += [np.zeros(int(SR * pause), np.float32), st, np.zeros(int(SR * 0.35), np.float32)]
        if z is not None:
            vorher = int(z)
        t0 += dauer
    ende = 2.4
    gesamt = t0 + ende
    audio = np.concatenate(ton + [np.zeros(int(SR * ende), np.float32)])
    for s in szenen:  # „Ding“, wenn die Zahl fertig hochgezählt hat
        if s.get("zahl") is not None:
            a = int(SR * (s["t0"] + s["pause"] + 1.6))
            d = ding()[: max(0, len(audio) - a)]
            audio[a:a + len(d)] += d
    audio = np.clip(audio, -1, 1)
    with wave.open(f"{tmp}/ton.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    out = f"video/out/{sid}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-", "-i", f"{tmp}/ton.wav",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                           "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    vorschau = None
    for f in range(int(gesamt * FPS)):
        t = f / FPS
        s = next((x for x in szenen if x["t0"] <= t < x["t0"] + x["dauer"]), None)
        if s is None:  # Abspann
            k = min(1, (t - t0) / 0.4)
            letzte = szenen[-1]
            svg = (hintergrund(letzte.get("bg", "zimmer"), t) + finn("zeigen", "keins", t, False, False)
                   + f'<rect width="1080" height="1920" fill="#1a0f16" opacity="{0.72 * k:.2f}"/>'
                   + "".join(textzeile(z, 820 + i * 110, 86, "#fff", 18) for i, z in enumerate(chunks(sp.get("end", "TEIL 2?"), 2))))
        else:
            lt = t - s["t0"]
            sprech_t = lt - s["pause"]
            spricht = 0 <= sprech_t < s["sprech"] and int(t * 9) % 2 == 0
            blinz = (t % 3.4) < 0.12
            zoom = 1 + 0.035 * lt / max(s["dauer"], 1)
            svg = (f'<g transform="translate(540 1100) scale({zoom:.4f}) translate(-540 -1100)">'
                   + hintergrund(s.get("bg", "zimmer"), t) + finn(s.get("pose", "neutral"), s.get("prop", "keins"), t, spricht, blinz)
                   + (DECKE if s.get("bg") == "bett" else "") + "</g>")
            if s.get("zahl") is not None:
                p = min(1, max(0, sprech_t / 1.6))
                e = 1 - (1 - p) ** 3
                wert = s["von"] + (int(s["zahl"]) - s["von"]) * e
                pop = max(0, 1 - abs(sprech_t - 1.6) / 0.25) if sprech_t > 1.3 else 0
                svg += zaehler(wert, s.get("zahl_label", ""), pop)
            if 0 <= sprech_t < s["sprech"]:
                teile = chunks(s["text"], 3)
                gewicht = [len(x) + 3 for x in teile]
                pos, acc = sprech_t / s["sprech"] * sum(gewicht), 0
                for x, gw in zip(teile, gewicht):
                    acc += gw
                    if pos < acc:
                        zeilen = [x] if len(x) <= 18 else [" ".join(x.split()[:-1]), x.split()[-1]] if len(x.split()) > 1 else [x]
                        for j, z in enumerate(zeilen):
                            svg += textzeile(z.upper(), 640 + j * 84 - (len(zeilen) - 1) * 42, 72)
                        break
        doc = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{DEFS}{svg}</svg>'
        png = cairosvg.svg2png(bytestring=doc.encode(), output_width=W, output_height=H)
        ff.stdin.write(png)
        if vorschau is None and t > 1.2:
            vorschau = png
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg fehlgeschlagen")
    if vorschau:
        open(f"{tmp}/v.png", "wb").write(vorschau)
        sh("ffmpeg", "-y", "-i", f"{tmp}/v.png", f"video/out/{sid}.jpg")
    tags = " ".join(sp.get("hashtags", []))
    open(f"video/out/{sid}.txt", "w", encoding="utf-8").write(f"{sp.get('caption', sp.get('title', ''))}\n\n{tags}\n")
    print(f"✅ {out} ({gesamt:.1f} s)")


if __name__ == "__main__":
    bad = []
    for f in sys.argv[1:]:
        try:
            build(f)
        except Exception:
            import traceback; traceback.print_exc(); bad.append(f)
    sys.exit(1 if bad else 0)
