"""Automatische Qualitätsprüfung eines fertigen Videos (ohne Claude):
Länge, Tonspur hörbar, Bilder nicht schwarz/eingefroren. Exit-Code 1 = durchgefallen."""
import subprocess, sys, json


def main(path, min_s, max_s):
    fehler = []
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip() or 0)
    if not (min_s <= d <= max_s):
        fehler.append(f"Länge {d:.1f} s (erlaubt {min_s}–{max_s})")
    vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mv = [float(l.split(":")[1].split()[0]) for l in vol.splitlines() if "mean_volume" in l]
    if not mv or mv[0] < -35:
        fehler.append(f"Ton zu leise/fehlt ({mv[0] if mv else 'kein Ton'} dB)")
    # 6 Bilder: Helligkeit + Unterschiede
    from PIL import Image, ImageStat, ImageChops
    import os, tempfile
    tmp = tempfile.mkdtemp()
    hell, bilder = [], []
    for i in range(6):
        t = d * (i + 0.5) / 6
        f = os.path.join(tmp, f"{i}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", "scale=90:160", f])
        im = Image.open(f).convert("L"); bilder.append(im); hell.append(ImageStat.Stat(im).mean[0])
    if min(hell) < 8:
        fehler.append("schwarzes Bild gefunden")
    diffs = [ImageStat.Stat(ImageChops.difference(bilder[i], bilder[i + 1])).mean[0] for i in range(5)]
    if max(diffs) < 1.5:
        fehler.append("Video wirkt eingefroren")
    print(json.dumps({"datei": path, "dauer": round(d, 1), "ton_db": mv[0] if mv else None, "fehler": fehler}, ensure_ascii=False))
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
