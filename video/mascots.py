"""Erzeugt Maskottchen-Posen (Pollinations, kostenlos) für die Kanäle. Aufruf: python3 video/mascots.py"""
import os, time, urllib.parse, urllib.request, urllib.error
M = {
 "np": "a friendly anthropomorphic brown bear mascot wearing a dark green suit jacket, white shirt and green tie, gold watch",
 "ag": "a friendly anthropomorphic black bear mascot wearing orange work overalls over a grey t-shirt, small wrench in chest pocket",
}
P = {
 "zeigen": "pointing up to the right with index finger, confident smile",
 "denken": "hand on chin thinking, slight smirk",
 "finger": "raising one index finger explaining something, friendly",
 "arme": "arms crossed, confident relaxed smile",
 "winken": "waving hello with one hand, big smile",
 "daumen": "giving a thumbs up, happy",
}
STYLE = ("full body, standing, clean bold black outlines, flat cel shading, modern 2D cartoon character design, "
         "centered, isolated on pure white background, no text, no shadow")
out = os.path.join(os.path.dirname(__file__), "assets")
for ch, desc in M.items():
    os.makedirs(f"{out}/{ch}", exist_ok=True)
    for pose, pd in P.items():
        for seed in (11, 23, 47):
            path = f"{out}/{ch}/{pose}-{seed}.jpg"
            if os.path.exists(path):
                continue
            url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(f"{desc}, {pd}, {STYLE}")
                   + f"?width=768&height=1024&nologo=true&seed={seed}")
            for k in range(5):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis"}), timeout=150) as r:
                        data = r.read()
                    if len(data) > 15000:
                        open(path, "wb").write(data); print("✓", path); break
                except urllib.error.HTTPError as e:
                    time.sleep(int(e.headers.get("Retry-After") or 30) + 5)
                except Exception as e:
                    print(" ", e); time.sleep(20)
            time.sleep(16)
