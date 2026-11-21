"""Vektor-Bär für den Erklär-Stil: immer gleiche Figur, Posen, Mund auf/zu, Blinzeln.
render_set(kind, outdir) erzeugt PNG-Sprites: <pose>_<m0|m1>_<e0|e1>.png (Höhe 1000 px)."""
import os

INK = "#1d1d1f"
KINDS = {
    "np": dict(fur="#9a6236", furd="#7a4a26", muz="#e8c9a3", outfit="suit", c1="#1f5a3a", c2="#164530", acc="#3fbf6e", shirt="#ffffff"),
    "ag": dict(fur="#2b2b2e", furd="#1a1a1c", muz="#c9a17c", outfit="overall", c1="#ff8a1f", c2="#e06e00", acc="#3a3a40", shirt="#5d6470"),
}


def arm(x, y, ang, length, col, paw, finger=False, side=1):
    """Arm als abgerundeter Balken, gedreht um die Schulter (x,y)."""
    f = (f'<rect x="-9" y="{length+12}" width="18" height="40" rx="9" fill="{paw}" stroke="{INK}" stroke-width="5"/>'
         if finger else "")
    return (f'<g transform="translate({x},{y}) rotate({ang})">'
            f'<rect x="-30" y="-10" width="60" height="{length}" rx="30" fill="{col}" stroke="{INK}" stroke-width="6"/>'
            f'{f}<circle cx="0" cy="{length}" r="30" fill="{paw}" stroke="{INK}" stroke-width="6"/></g>')


def svg(kind, pose="neutral", mouth=0, eyes=1):
    k = KINDS[kind]
    W, H = 720, 1000
    fur, muz = k["fur"], k["muz"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    # Beine + Schuhe
    leg = k["c2"] if k["outfit"] == "suit" else k["c1"]
    for lx in (225, 375):
        p.append(f'<rect x="{lx-45}" y="660" width="90" height="270" rx="30" fill="{leg}" stroke="{INK}" stroke-width="6"/>')
        p.append(f'<ellipse cx="{lx+8}" cy="935" rx="62" ry="30" fill="{INK}"/>')
    # Arme (hinter dem Körper: linker Arm)
    p.append(arm(178, 430, 12, 230, k["c1"] if k["outfit"] == "suit" else fur, fur))
    # Körper
    p.append(f'<rect x="150" y="390" width="300" height="320" rx="80" fill="{k["c1"]}" stroke="{INK}" stroke-width="6"/>')
    if k["outfit"] == "suit":
        p.append(f'<path d="M300 400 L250 400 L300 560 L350 400 Z" fill="{k["shirt"]}" stroke="{INK}" stroke-width="5"/>')
        p.append(f'<path d="M300 420 L285 445 L300 545 L315 445 Z" fill="{k["acc"]}" stroke="{INK}" stroke-width="4"/>')
        p.append(f'<path d="M250 400 L300 560 L230 470 Z" fill="{k["c2"]}" stroke="{INK}" stroke-width="5"/>'
                 f'<path d="M350 400 L300 560 L370 470 Z" fill="{k["c2"]}" stroke="{INK}" stroke-width="5"/>')
        p.append(f'<circle cx="300" cy="600" r="7" fill="{INK}"/><circle cx="300" cy="640" r="7" fill="{INK}"/>')
        p.append(f'<rect x="375" y="470" width="40" height="10" rx="4" fill="#ffffff"/>')
    else:
        p.append(f'<rect x="185" y="390" width="230" height="140" rx="40" fill="{k["shirt"]}" stroke="{INK}" stroke-width="5"/>')
        p.append(f'<rect x="200" y="470" width="200" height="230" rx="30" fill="{k["c1"]}" stroke="{INK}" stroke-width="6"/>')
        p.append(f'<rect x="250" y="520" width="100" height="70" rx="12" fill="{k["c2"]}" stroke="{INK}" stroke-width="5"/>')
        for sx in (215, 385):
            p.append(f'<line x1="{sx}" y1="400" x2="{sx}" y2="480" stroke="{k["c2"]}" stroke-width="18"/><circle cx="{sx}" cy="480" r="10" fill="#d9d9d9" stroke="{INK}" stroke-width="4"/>')
        p.append(f'<rect x="322" y="505" width="14" height="50" rx="5" fill="#9aa0a8" stroke="{INK}" stroke-width="4"/>')
    # rechter Arm je nach Pose (zeigt zu den Karten auf der rechten Seite)
    sleeve = k["c1"] if k["outfit"] == "suit" else fur
    if pose == "zeigen":
        p.append(arm(420, 440, -128, 220, sleeve, fur, finger=True))
    elif pose == "finger":
        p.append(arm(420, 440, -165, 170, sleeve, fur, finger=True))
    elif pose == "winken":
        p.append(arm(420, 440, -150, 210, sleeve, fur))
    elif pose == "denken":
        pass  # Arm wird nach dem Kopf gezeichnet (Pfote am Kinn)
    else:
        p.append(arm(422, 430, -12, 230, sleeve, fur))
    # Kopf
    p.append(f'<circle cx="185" cy="130" r="55" fill="{fur}" stroke="{INK}" stroke-width="6"/><circle cx="185" cy="130" r="28" fill="{muz}"/>')
    p.append(f'<circle cx="415" cy="130" r="55" fill="{fur}" stroke="{INK}" stroke-width="6"/><circle cx="415" cy="130" r="28" fill="{muz}"/>')
    p.append(f'<ellipse cx="300" cy="250" rx="165" ry="155" fill="{fur}" stroke="{INK}" stroke-width="6"/>')
    p.append(f'<ellipse cx="300" cy="315" rx="88" ry="68" fill="{muz}" stroke="{INK}" stroke-width="5"/>')
    p.append(f'<ellipse cx="300" cy="282" rx="30" ry="21" fill="{INK}"/><ellipse cx="292" cy="275" rx="9" ry="5" fill="#ffffff" opacity=".7"/>')
    # Augen
    for ex in (235, 365):
        if eyes:
            p.append(f'<ellipse cx="{ex}" cy="215" rx="19" ry="23" fill="{INK}"/><circle cx="{ex+6}" cy="207" r="7" fill="#ffffff"/>')
        else:
            p.append(f'<path d="M{ex-20} 218 Q{ex} 230 {ex+20} 218" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
        by = 175 if pose != "denken" else 168
        p.append(f'<path d="M{ex-24} {by+4} Q{ex} {by-8} {ex+24} {by+4}" fill="none" stroke="{k["furd"]}" stroke-width="9" stroke-linecap="round"/>')
    # Mund
    if mouth:
        p.append(f'<path d="M262 318 Q300 378 338 318 Z" fill="#7a2a2a" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                 f'<path d="M280 345 Q300 365 320 345" fill="#e46b6b"/>')
    else:
        p.append(f'<path d="M268 320 Q300 348 332 320" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
    if pose == "denken":
        p.append(arm(420, 450, 152, 150, sleeve, fur))
    p.append("</svg>")
    return "".join(p)


POSES = ["neutral", "zeigen", "finger", "winken", "denken"]


def render_set(kind, outdir, height=1000):
    import cairosvg
    os.makedirs(outdir, exist_ok=True)
    for pose in POSES:
        for m in (0, 1):
            for e in (0, 1):
                cairosvg.svg2png(bytestring=svg(kind, pose, m, e).encode(), write_to=f"{outdir}/{pose}_m{m}_e{e}.png",
                                 output_height=height)


if __name__ == "__main__":
    import sys
    for k in KINDS:
        render_set(k, sys.argv[1] if len(sys.argv) > 1 else f"/tmp/baer/{k}")
