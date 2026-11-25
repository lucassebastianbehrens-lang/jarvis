"""Shop-Baukasten: „Bau mir einen Shop für …“ -> fertige, schöne Shop-Seite unter shops/<name>/.

Ablauf
 1. KI plant den Shop (Name, Slogan, Produkte mit Preisen, Vorteile, FAQ, Suchmaschinen-Texte, TikTok-Ideen) als JSON.
 2. Die Seite wird mit einer FESTEN, hochwertigen Vorlage gebaut (Design kommt nicht aus der KI -> sieht immer ordentlich aus).
 3. KI-Kundenpanel: 25 Kundentypen stehen zusammen für 100.000 virtuelle Kunden (jeder Typ = ein Anteil, siehe PANEL).
    Jeder Typ bewertet streng: „sehr gut?“ und „würde öfter kaufen?“. Bestanden = gewichteter Anteil mit
    beidem JA >= 75 %. Mit Handy-Screenshot (Bild-KI), sonst nur Text.
 4. Nicht bestanden -> Kritik der Kunden zusammenfassen, Shop überarbeiten, neu bauen, neu testen (max. MAX_RUNDEN).
 5. 3 Pflicht-Prüfungen vor der Veröffentlichung: Technik (alle Produkte/Preise da, keine Platzhalter, mobil-tauglich),
    Inhalt (Preise > 0, Texte ohne „Lorem“/„TODO“), Recht (Vorschau-Hinweis + noindex + Kaufknopf gesperrt, solange
    shops/STATUS.md nicht „Verkauf freigeschaltet: ja“ sagt – Lucas braucht erst Gewerbe, Impressum, AGB, Widerruf).
Wichtig: Das Panel sind KI-Kunden, keine echten Menschen. Es zeigt Schwächen auf, ersetzt aber keinen Test mit echten Kunden.
Aufruf: python3 bot/shop_bau.py "Shop für handgemachte Hundeleinen"
"""
import base64, html, json, os, re, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = 0.75
KUNDEN = 100_000
MAX_RUNDEN = int(os.environ.get("SHOP_RUNDEN", "8"))
VISION = "qwen/qwen3.8-27b"

# 25 Kundentypen, Anteile ergeben zusammen 100 % (= 100.000 virtuelle Kunden)
PANEL = [
    ("Schnäppchenjägerin, 34, vergleicht jeden Preis", 6), ("Student, 21, wenig Geld, kauft am Handy", 5),
    ("Familienvater, 41, will Qualität und schnelle Lieferung", 5), ("Rentnerin, 68, liest alles genau, misstraut Online-Shops", 4),
    ("Geschenkekäuferin, 29, sucht etwas Besonderes", 5), ("Handwerker, 47, kurz angebunden, will Fakten", 4),
    ("Nachhaltigkeits-Fan, 31, achtet auf Herkunft und Material", 4), ("Impulskäufer, 25, kommt über TikTok", 5),
    ("Skeptiker, 52, sucht Impressum, Rückgabe, Kontakt", 4), ("Mutter, 36, wenig Zeit, will es einfach", 5),
    ("Design-Liebhaberin, 27, achtet auf Optik", 4), ("Stammkunde-Typ, 45, kauft gern wieder, wenn Service stimmt", 4),
    ("Technik-Fan, 33, will Details und Maße", 3), ("Landwirt, 58, regional, vertraut Kleinbetrieben", 3),
    ("Azubi, 18, erster eigener Einkauf", 3), ("Selbstständige, 39, kauft für ihr Geschäft", 4),
    ("Großeltern-Paar, 71, kauft für Enkel", 3), ("Fitness-Typ, 28, achtet auf Nutzen", 3),
    ("Pendlerin, 44, kauft abends im Zug", 4), ("Sammler, 50, Liebhaber der Nische", 3),
    ("Preis-Leistungs-Rechner, 37, rechnet nach", 4), ("Erstbesucherin, 30, kennt die Marke nicht", 5),
    ("Tierfreundin, 26, emotional, liebt Geschichten", 3), ("Vielbestellerin, 42, vergleicht mit großen Shops", 4),
    ("Sparfuchs-Rentner, 66, nur wenn es sich lohnt", 3),
]
assert sum(a for _, a in PANEL) == 100

PALETTEN = {  # feste, geprüfte Farbwelten (Kontrast lesbar)
    "wald": ("#1f6f50", "#e9f5ee", "#f2b134"), "ozean": ("#1d4e89", "#e8f1fb", "#ff8c42"),
    "beere": ("#8e2c5a", "#fbeef4", "#f6c445"), "sand": ("#8a5a2b", "#f8f1e7", "#2f7d6d"),
    "nacht": ("#232a4d", "#eef0f8", "#ffcd3c"), "koralle": ("#c44536", "#fdf0ec", "#197278"),
    "salbei": ("#4f6f52", "#f1f5ee", "#d98e04"), "graphit": ("#2d2d2d", "#f4f4f4", "#e4572e"),
}

PLAN_REGELN = """Antworte NUR mit JSON in genau diesem Schema (Deutsch, Preise in Euro als Zahl):
{"name":"kurzer einprägsamer Shopname","slogan":"max 8 Wörter","palette":"wald|ozean|beere|sand|nacht|koralle|salbei|graphit",
 "hero_titel":"starke Überschrift, Nutzen für Kunden","hero_text":"2 Sätze, warum hier kaufen","cta":"Knopftext",
 "vorteile":[{"emoji":"🚚","titel":"","text":""}] (genau 4),
 "produkte":[{"emoji":"","name":"","preis":0.0,"alter_preis":null,"kurz":"1 Satz Nutzen","details":["3 Fakten: Material/Maße/Lieferumfang"],"badge":"Bestseller|Neu|Tipp|"}] (4 bis 8),
 "geschichte":"3-4 Sätze: wer dahinter steckt, warum, ehrlich (Gründer: Lucas aus Sachsen-Anhalt)",
 "angebot":"Erstkunden-Vorteil, z. B. Versandkostenfrei ab X €",
 "faq":[{"f":"","a":""}] (5: Lieferzeit, Versandkosten, Rückgabe 14 Tage, Bezahlung PayPal, Kontakt),
 "seo_titel":"max 60 Zeichen","seo_beschreibung":"max 155 Zeichen",
 "tiktok_ideen":["5 konkrete Video-Ideen, die Leute in den Shop bringen"]}
Regeln: realistische Marktpreise (vorher überlegen, was vergleichbare Shops nehmen), keine erfundenen Bewertungen,
Kundenstimmen, Siegel oder Auszeichnungen, keine Heilversprechen, keine Markennamen anderer, keine Superlative ohne Beleg."""


def slug(t):
    t = t.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "shop"


def plan(wunsch, alt=None, kritik=None):
    if alt is None:
        aufgabe = f"Plane einen Online-Shop: {wunsch}"
    else:
        aufgabe = (f"Hier ist der aktuelle Shop (JSON):\n{json.dumps(alt, ensure_ascii=False)}\n\nKundenpanel-Kritik (gewichtet, wichtigste zuerst):\n{kritik}\n\n"
                   "Überarbeite den Shop gezielt, sodass möglichst viele Kunden ihn SEHR GUT finden und ÖFTER kaufen würden: "
                   "Preise, Produktauswahl, Texte, Vertrauen (Rückgabe, Kontakt, Versand), Angebot, Klarheit. Gleiches JSON-Schema.")
    for _ in range(3):
        try:
            d = jlib.parse_json(jlib.ki("Du bist ein erfahrener E-Commerce-Berater und Texter. " + PLAN_REGELN, aufgabe, json_mode=True))
            if d.get("produkte") and d.get("name"):
                return d
        except Exception as e:
            print("Plan:", e)
    raise SystemExit("KI konnte keinen Shop planen")


def eur(x):
    return f"{float(x):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def baue_html(d, url, freigeschaltet=False):
    e = lambda s: html.escape(str(s or ""))
    p1, p2, akz = PALETTEN.get(d.get("palette"), PALETTEN["nacht"])
    vorteile = "".join(f'<div class="vt"><span>{e(v.get("emoji"))}</span><b>{e(v.get("titel"))}</b><p>{e(v.get("text"))}</p></div>'
                       for v in d.get("vorteile", [])[:4])
    prods = []
    for i, p in enumerate(d["produkte"][:8]):
        alt = f'<s>{eur(p["alter_preis"])}</s> ' if p.get("alter_preis") and float(p["alter_preis"]) > float(p["preis"]) else ""
        badge = f'<i class="bd">{e(p["badge"])}</i>' if p.get("badge") else ""
        det = "".join(f"<li>{e(x)}</li>" for x in (p.get("details") or [])[:3])
        prods.append(f'<article class="pr">{badge}<div class="bild" aria-hidden="true">{e(p.get("emoji") or "🛍")}</div>'
                     f'<h3>{e(p["name"])}</h3><p>{e(p.get("kurz"))}</p><ul>{det}</ul>'
                     f'<div class="preis">{alt}<b>{eur(p["preis"])}</b></div>'
                     f'<button onclick="rein({i})">In den Warenkorb</button></article>')
    faq = "".join(f'<details><summary>{e(q.get("f"))}</summary><p>{e(q.get("a"))}</p></details>' for q in d.get("faq", [])[:6])
    daten = json.dumps([{"n": p["name"], "p": float(p["preis"])} for p in d["produkte"][:8]], ensure_ascii=False)
    vorschau = "" if freigeschaltet else '<div class="vor">🔒 Vorschau – der Verkauf startet in Kürze. Bestellungen sind noch nicht möglich.</div>'
    robots = "index,follow" if freigeschaltet else "noindex,nofollow"
    kasse = ("location.href='#kontakt'" if freigeschaltet else "alert0()")
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d.get("seo_titel") or d["name"])}</title><meta name="description" content="{e(d.get("seo_beschreibung"))}">
<meta name="robots" content="{robots}"><link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(d["name"])} – {e(d.get("slogan"))}"><meta property="og:description" content="{e(d.get("seo_beschreibung"))}">
<style>
:root{{--p:{p1};--h:{p2};--a:{akz};--t:#1c1d21;--m:#5d6270}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--t);background:#fff}}
.vor{{background:#fff3cd;color:#664d03;text-align:center;font-size:14px;padding:8px 12px}}
nav{{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:12px 18px;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid #eee}}
nav b{{font-size:19px;color:var(--p)}}nav a{{color:var(--t);text-decoration:none;margin-left:14px;font-size:15px}}
.wk{{background:var(--p);color:#fff!important;padding:7px 12px;border-radius:999px}}
.hero{{background:linear-gradient(135deg,var(--p),color-mix(in srgb,var(--p) 65%,#000));color:#fff;padding:64px 20px 72px;text-align:center}}
.hero h1{{font-size:clamp(30px,6vw,52px);line-height:1.1;margin:0 auto 14px;max-width:820px}}.hero p{{max-width:620px;margin:0 auto 26px;font-size:18px;opacity:.93}}
.knopf{{display:inline-block;background:var(--a);color:#1c1d21;font-weight:700;padding:14px 28px;border-radius:999px;text-decoration:none;box-shadow:0 8px 24px rgba(0,0,0,.18)}}
.angebot{{background:var(--h);text-align:center;padding:14px;font-weight:600;color:var(--p)}}
.wrap{{max-width:1100px;margin:0 auto;padding:46px 18px}}h2{{font-size:30px;text-align:center;margin:0 0 26px}}
.vts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}
.vt{{background:var(--h);border-radius:18px;padding:20px}}.vt span{{font-size:30px}}.vt b{{display:block;margin:8px 0 4px}}.vt p{{margin:0;color:var(--m)}}
.prs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}}
.pr{{position:relative;border:1px solid #ececf1;border-radius:20px;padding:18px;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s}}
.pr:hover{{transform:translateY(-3px);box-shadow:0 14px 34px rgba(0,0,0,.08)}}
.bild{{height:150px;border-radius:14px;background:linear-gradient(135deg,var(--h),#fff);display:grid;place-items:center;font-size:72px;margin-bottom:12px}}
.pr h3{{margin:0 0 6px;font-size:19px}}.pr p{{margin:0 0 8px;color:var(--m)}}.pr ul{{margin:0 0 12px;padding-left:18px;color:var(--m);font-size:14px}}
.preis{{margin-top:auto;font-size:22px}}.preis s{{color:#999;font-size:16px}}.preis b{{color:var(--p)}}
.pr button{{margin-top:12px;background:var(--p);color:#fff;border:0;border-radius:12px;padding:12px;font-size:16px;font-weight:600;cursor:pointer}}
.bd{{position:absolute;top:14px;right:14px;background:var(--a);color:#1c1d21;font-style:normal;font-size:12px;font-weight:700;padding:4px 10px;border-radius:999px}}
.gesch{{background:var(--h)}}.gesch p{{max-width:720px;margin:0 auto;font-size:18px;text-align:center}}
details{{border-bottom:1px solid #eee;padding:14px 4px;max-width:760px;margin:0 auto}}summary{{font-weight:600;cursor:pointer}}details p{{color:var(--m)}}
footer{{background:#111;color:#bbb;padding:30px 18px;text-align:center;font-size:14px}}footer a{{color:#ddd}}
#korb{{position:fixed;right:16px;bottom:16px;background:#fff;border:1px solid #ddd;border-radius:16px;padding:14px;box-shadow:0 10px 30px rgba(0,0,0,.15);display:none;max-width:300px;z-index:9}}
#korb button{{width:100%;margin-top:8px;background:var(--a);border:0;border-radius:10px;padding:10px;font-weight:700;cursor:pointer}}
</style></head><body>
{vorschau}
<nav><b>{e(d["name"])}</b><div><a href="#produkte">Produkte</a><a href="#faq">Fragen</a><a class="wk" href="#produkte" id="wkz">🛒 0</a></div></nav>
<header class="hero"><h1>{e(d.get("hero_titel"))}</h1><p>{e(d.get("hero_text"))}</p><a class="knopf" href="#produkte">{e(d.get("cta") or "Jetzt entdecken")}</a></header>
<div class="angebot">🎁 {e(d.get("angebot"))}</div>
<section class="wrap"><div class="vts">{vorteile}</div></section>
<section class="wrap" id="produkte"><h2>Unsere Produkte</h2><div class="prs">{"".join(prods)}</div></section>
<section class="gesch"><div class="wrap"><h2>Wer steckt dahinter?</h2><p>{e(d.get("geschichte"))}</p></div></section>
<section class="wrap" id="faq"><h2>Häufige Fragen</h2>{faq}</section>
<footer id="kontakt"><b>{e(d["name"])}</b> · {e(d.get("slogan"))}<br><br>Impressum · Datenschutz · AGB · Widerruf – folgen vor Verkaufsstart</footer>
<div id="korb"><b>Warenkorb</b><div id="kl"></div><div id="ks"></div><button onclick="{kasse}">Zur Kasse</button></div>
<script>
const P={daten};let K=[];try{{K=JSON.parse(localStorage.getItem("korb_{slug(d["name"])}")||"[]")}}catch(e){{}}
function zeig(){{let s=0;document.getElementById("kl").innerHTML=K.map(i=>{{s+=P[i].p;return P[i].n}}).join("<br>");
document.getElementById("ks").innerHTML="<b>Summe: "+s.toFixed(2).replace(".",",")+" €</b>";document.getElementById("wkz").textContent="🛒 "+K.length;
document.getElementById("korb").style.display=K.length?"block":"none";try{{localStorage.setItem("korb_{slug(d["name"])}",JSON.stringify(K))}}catch(e){{}}}}
function rein(i){{K.push(i);zeig()}}
function alert0(){{document.getElementById("ks").innerHTML+="<p>🔒 Der Verkauf startet in Kürze – schau bald wieder vorbei!</p>"}}
zeig();
</script></body></html>"""


def screenshot(html_text):
    """Handy-Ansicht als PNG (Chrome headless). Ohne Chrome: None -> Panel bewertet nur Text."""
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if subprocess.run(["which", c], capture_output=True).returncode == 0), None)
    if not chrome:
        return None
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "s.html"); open(f, "w").write(html_text)
        png = os.path.join(d, "s.png")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--window-size=414,2600",
                        f"--screenshot={png}", "file://" + f], capture_output=True, timeout=90)
        return open(png, "rb").read() if os.path.exists(png) else None


def panel(d, html_text, bild=None):
    """Bewertung durch 25 Kundentypen (= 100.000 virtuelle Kunden). Rückgabe: (Anteil, Kritikliste, Details)."""
    inhalt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_text)
    inhalt = html.unescape(re.sub(r"<[^>]+>", " ", inhalt))
    inhalt = re.sub(r"\s+", " ", inhalt)[:7000]
    ergebnisse = []
    for i in range(0, len(PANEL), 5):
        gruppe = PANEL[i:i + 5]
        typen = "\n".join(f"{n + 1}. {t}" for n, (t, _) in enumerate(gruppe))
        frage = (f"Du spielst nacheinander diese 5 echten, KRITISCHEN Online-Kunden aus Deutschland:\n{typen}\n\n"
                 f"Sie besuchen diesen Shop (Inhalt der Seite):\n{inhalt}\n\n"
                 "Jeder urteilt ehrlich aus seiner Sicht: Preis, Vertrauen, Produktauswahl, Optik, Klarheit. "
                 "'sehr_gut' nur true, wenn der Shop wirklich überzeugt (nicht nur okay). 'oefter_kaufen' nur true, wenn er hier "
                 "kaufen UND wiederkommen würde. Antworte NUR mit JSON: {\"kunden\":[{\"nr\":1,\"note\":1-10,\"sehr_gut\":bool,"
                 "\"oefter_kaufen\":bool,\"kritik\":\"größte Schwäche\",\"wunsch\":\"konkrete Verbesserung\"}]} (genau 5).")
        antwort = None
        if bild and jlib.GROQ:
            try:
                j = jlib.http("https://api.groq.com/openai/v1/chat/completions",
                              {"model": VISION, "response_format": {"type": "json_object"},
                               "messages": [{"role": "user", "content": [{"type": "text", "text": frage + "\nDas Bild zeigt die Handy-Ansicht des Shops."},
                                                                         {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(bild).decode()}}]}]},
                              {"Authorization": "Bearer " + jlib.GROQ}, timeout=150)
                antwort = jlib.parse_json(j["choices"][0]["message"]["content"])
            except Exception as e:
                print("Panel mit Bild:", e)
        if antwort is None:
            antwort = jlib.parse_json(jlib.ki("Du simulierst ehrliche, kritische Kunden.", frage, json_mode=True))
        ks = antwort.get("kunden", [])
        for n, (typ, anteil) in enumerate(gruppe):
            k = ks[n] if n < len(ks) else {"note": 0, "sehr_gut": False, "oefter_kaufen": False, "kritik": "keine Antwort", "wunsch": ""}
            ergebnisse.append({"typ": typ, "anteil": anteil, **k})
        time.sleep(2)
    zustimmung = sum(r["anteil"] for r in ergebnisse if r.get("sehr_gut") is True and r.get("oefter_kaufen") is True) / 100
    kritik = sorted((r for r in ergebnisse if not (r.get("sehr_gut") is True and r.get("oefter_kaufen") is True)), key=lambda r: -r["anteil"])
    text = "\n".join(f"- ({r['anteil'] * KUNDEN // 100:,} Kunden, {r['typ']}): {r.get('kritik')} -> Wunsch: {r.get('wunsch')}".replace(",", ".") for r in kritik[:15])
    return zustimmung, text, ergebnisse


def pruefen(d, html_text, freigeschaltet):
    """3 Pflicht-Prüfungen. Rückgabe: Liste der Fehler (leer = alles ok)."""
    f = []
    # 1 Technik
    for p in d["produkte"][:8]:
        if html.escape(p["name"]) not in html_text:
            f.append(f"Produkt fehlt: {p['name']}")
    if 'name="viewport"' not in html_text:
        f.append("nicht handy-tauglich")
    # 2 Inhalt
    if any(float(p.get("preis") or 0) <= 0 for p in d["produkte"]):
        f.append("Preis 0 oder fehlt")
    if re.search(r"lorem|todo|xxx|platzhalter", html_text, re.I):
        f.append("Platzhaltertext")
    if re.search(r"(★|sterne|bewertung(en)?\s*von|testsieger|ausgezeichnet mit)", html_text, re.I):
        f.append("erfundene Bewertungen/Siegel")
    # 3 Recht
    if not freigeschaltet and ("noindex" not in html_text or "Vorschau" not in html_text):
        f.append("Vorschau-Schutz fehlt")
    return f


def main(wunsch):
    status = os.path.join(ROOT, "shops", "STATUS.md")
    frei = os.path.exists(status) and re.search(r"Verkauf freigeschaltet:\s*ja", open(status).read(), re.I) is not None
    d = plan(wunsch)
    name = slug(d["name"])
    url = f"https://lucassebastianbehrens-lang.github.io/jarvis/shops/{name}/"
    verlauf, bester = [], None
    for runde in range(1, MAX_RUNDEN + 1):
        h = baue_html(d, url, frei)
        fehler = pruefen(d, h, frei)
        if fehler:
            print("Prüfung:", fehler)
            d = plan(wunsch, d, "Technische/inhaltliche Fehler beheben: " + "; ".join(fehler)); continue
        quote, kritik, details = panel(d, h, screenshot(h))
        verlauf.append({"runde": runde, "zustimmung": round(quote * 100, 1), "kritik": kritik})
        print(f"Runde {runde}: {quote * 100:.1f} % der {KUNDEN:,} KI-Kunden: sehr gut + öfter kaufen".replace(",", "."))
        if bester is None or quote > bester[0]:
            bester = (quote, d, h, details)
        if quote >= ZIEL:
            break
        d = plan(wunsch, d, kritik)
    quote, d, h, details = bester
    ordner = os.path.join(ROOT, "shops", name); os.makedirs(ordner, exist_ok=True)
    open(os.path.join(ordner, "index.html"), "w").write(h)
    json.dump({"wunsch": wunsch, "shop": d, "panel": details, "verlauf": verlauf}, open(os.path.join(ordner, "panel.json"), "w"), ensure_ascii=False, indent=1)
    ok = quote >= ZIEL
    bericht = (f"# {d['name']}\n\nWunsch: {wunsch}\nAdresse: {url}\n\n"
               f"KI-Kundenpanel ({KUNDEN:,} virtuelle Kunden, 25 Typen): **{quote * 100:.1f} %** sagen „sehr gut“ und würden öfter kaufen "
               f"(Ziel {ZIEL * 100:.0f} %) – {'✅ bestanden' if ok else '❌ nach ' + str(len(verlauf)) + ' Runden nicht erreicht (bester Stand veröffentlicht)'}\n\n"
               "Runden: " + " → ".join(f"{v['zustimmung']} %" for v in verlauf) + "\n\n"
               "## TikTok-Ideen\n" + "\n".join(f"- {x}" for x in d.get("tiktok_ideen", [])) + "\n\n"
               "Hinweis: Das Panel sind KI-Kunden, keine echten Menschen.\n").replace(",", ".")
    open(os.path.join(ordner, "BERICHT.md"), "w").write(bericht)
    print(bericht)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as o:
        o.write(f"name={name}\nurl={url}\nquote={quote * 100:.1f}\nok={'1' if ok else '0'}\nshop={d['name']}\nrunden={len(verlauf)}\n")
    return ok


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or os.environ.get("WUNSCH", ""))
