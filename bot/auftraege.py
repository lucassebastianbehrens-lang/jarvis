"""Jarvis Auftrags-Scout – findet täglich bezahlte Aufgaben, die die KIs erledigen können.

Ablauf (läuft per GitHub Actions, siehe .github/workflows/auftraege.yml):
  1. Scout     – liest öffentliche Auftragsbörsen (Freelancer.com-API, Reddit r/forhire, r/slavelabour …)
  2. Filter    – wirft alles raus, was eine KI nicht allein liefern kann oder unseriös ist
                 (Telefon, vor Ort, Vorkasse, Krypto, Hausaufgaben/Prüfungen, Fake-Bewertungen …)
  3. Bewertung – die KI gibt jedem Auftrag 0–100 Punkte und einen fairen Preis in Euro
  4. Vorarbeit – für die besten Aufträge schreibt die KI Angebot + fertigen Entwurf des Ergebnisses
  5. Zahlung   – Direktkunden bekommen einen PayPal-Link (paypal.me/<Name>/<Betrag>EUR);
                 bei Plattformen (Freelancer) läuft die Zahlung über die Plattform → Auszahlung auf PayPal
  6. Meldung   – Ergebnis in data/auftraege.json (für Jarvis → KI-Stadt → Auftragsbüro) + Telegram

Mindestens 1 Auftrag pro Tag: Findet der Scout nichts Passendes, erstellt Jarvis ein eigenes
Tagesangebot (KI-Dienstleistung mit PayPal-Link), das du posten kannst.

Jarvis sendet NICHTS selbst – Angebote verschickst du mit einem Tipp (Plattform-Regeln, dein Konto).

Optionale Umgebungsvariablen: PAYPAL_ME, AI_URL, AI_KEY, AI_MODEL, TG_TOKEN, TG_CHAT, AUFTRAEGE_OUT
Test ohne Internet:  FAKE=1 python3 bot/auftraege.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

OUT = os.environ.get("AUFTRAEGE_OUT", "data/auftraege.json")
PAYPAL_ME = (os.environ.get("PAYPAL_ME") or "LucasBehrenski").strip().strip("/").split("/")[-1]
FAKE = os.environ.get("FAKE") == "1"
TZ = ZoneInfo("Europe/Berlin")
UA = "Mozilla/5.0 (compatible; jarvis-auftrags-scout/1.0; +https://github.com/lucassebastianbehrens-lang/jarvis)"
PER_DAY = 3            # so viele Aufträge werden täglich fertig vorbereitet (mind. 1)
MIN_EUR, MAX_AGE_H = 10, 72
KEEP = 60              # so viele Aufträge bleiben in der Datei

# Was eine KI gut allein liefern kann (Texte, Übersetzung, Recherche, Tabellen, Code-Kleinkram)
FL_QUERIES = ["article writing", "blog post", "product description", "translation german", "german",
              "proofreading", "copywriting", "excel formula", "data entry", "web research",
              "seo content", "email template", "resume", "python script", "summary"]
REDDIT = [("forhire", r"\[hiring\]"), ("slavelabour", r"\[task\]"), ("HireaWriter", r"\[hiring\]|\[task\]"),
          ("freelance_forhire", r"\[hiring\]")]
GOOD = re.compile(r"writ|text|blog|article|artikel|copy|translat|übersetz|proofread|korrektur|lektor|description|beschreib|"
                  r"research|recherch|excel|spreadsheet|sheet|data entry|daten|summar|zusammenfass|seo|email|newsletter|"
                  r"resume|cv|lebenslauf|bewerbung|script|python|formula|caption|social media post|product listing|etsy|"
                  r"prompt|chatgpt|ai |ki ", re.I)
BAD = re.compile(r"\b(phone calls?|cold call\w*|calls? (customers|clients|leads)|video calls?|anruf\w*|telefon\w*|"
                 r"on.?site|vor ort|in person|driver|delivery driver|babysit\w*|cleaning service|house ?clean\w*|"
                 r"upfront|vorkasse|deposit|crypto|bitcoin|usdt|nft|forex|whatsapp group|telegram group|"
                 r"homework|hausaufgabe\w*|assignments?|exams?|prüfung\w*|thesis|dissertation|essay for (my|a) class|"
                 r"fake reviews?|bewertungen schreiben|5.?star reviews?|upvotes?|captchas?|account creation|create accounts|verify accounts?|"
                 r"onlyfans|nsfw|adult|dating|gambling|casino|voice ?over|face ?time|show (your )?face)\b", re.I)


def now():
    return datetime.now(TZ)


def http(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def usd_eur():
    try:
        return float(http("https://api.frankfurter.app/latest?from=USD&to=EUR")["rates"]["EUR"])
    except Exception:
        return 0.92


# ---------- KI ----------
_last_ai = 0.0


def ai(system, user, want_json=False):
    """OpenAI-kompatible KI. Mit AI_URL/AI_KEY (z. B. Groq) schneller, sonst kostenlos über Pollinations."""
    global _last_ai
    if FAKE:
        return fake_ai(system, user, want_json)
    url = (os.environ.get("AI_URL") or "https://text.pollinations.ai/openai").rstrip("/")
    if os.environ.get("AI_URL"):
        url += "/chat/completions"
    key, model = os.environ.get("AI_KEY", ""), os.environ.get("AI_MODEL") or "openai"
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for attempt in range(4):
        wait = (16 if not key else 1) - (time.time() - _last_ai)   # kostenlose KI: max. 1 Anfrage / 15 s
        if wait > 0:
            time.sleep(wait)
        _last_ai = time.time()
        try:
            r = http(url, {"model": model, "messages": msgs}, {"Authorization": "Bearer " + key} if key else {}, timeout=120)
            txt = r["choices"][0]["message"]["content"].strip()
            if not want_json:
                return txt
            m = re.search(r"[\[{].*[\]}]", txt, re.S)
            return json.loads(m.group(0))
        except Exception as e:
            print(f"KI-Versuch {attempt + 1} fehlgeschlagen: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("KI nicht erreichbar")


def fake_ai(system, user, want_json):
    if want_json and "Punkte" in system:
        ids = re.findall(r"^#(\S+)", user, re.M)
        return [{"id": i, "punkte": 80 - n * 5, "preis_eur": 40, "warum": "Reiner Text, KI kann das komplett."} for n, i in enumerate(ids)]
    if want_json:
        return {"titel": "Test", "angebot": "Hallo, ich erledige das gern bis morgen.", "ergebnis": "Fertiger Entwurf …",
                "preis_eur": 40, "lieferzeit": "24 Stunden", "sprache": "de", "schritte": ["Angebot senden"]}
    return "ok"


# ---------- Scout ----------
def scout_freelancer(eur):
    out, seen = [], set()
    for q in FL_QUERIES:
        try:
            url = ("https://www.freelancer.com/api/projects/0.1/projects/active/?" + urllib.parse.urlencode(
                {"query": q, "limit": 20, "full_description": "true", "job_details": "true", "sort_field": "time_updated"}))
            res = http(url).get("result", {})
        except Exception as e:
            print(f"Freelancer '{q}': {e}", file=sys.stderr)
            continue
        for p in res.get("projects", []):
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            b, cur = p.get("budget") or {}, p.get("currency") or {}
            rate = float(cur.get("exchange_rate") or 1) * eur          # → USD → EUR
            lo, hi = float(b.get("minimum") or 0) * rate, float(b.get("maximum") or b.get("minimum") or 0) * rate
            out.append({"id": "fl-%s" % p["id"], "quelle": "Freelancer.com", "plattform": True,
                        "titel": p.get("title", ""), "text": (p.get("description") or p.get("preview_description") or "")[:2500],
                        "url": "https://www.freelancer.com/projects/" + (p.get("seo_url") or str(p["id"])),
                        "budget_eur": [round(lo), round(hi)], "stunden": p.get("type") == "hourly",
                        "gebote": (p.get("bid_stats") or {}).get("bid_count", 0),
                        "zeit": int(p.get("time_submitted") or p.get("time_updated") or time.time())})
    return out


def scout_reddit():
    out = []
    for sub, flag in REDDIT:
        data = None
        for host in ("https://www.reddit.com", "https://old.reddit.com", "https://api.reddit.com"):
            try:
                data = http(f"{host}/r/{sub}/new.json?limit=50&raw_json=1")
                break
            except Exception as e:
                print(f"Reddit r/{sub} über {host}: {e}", file=sys.stderr)
        for c in (data or {}).get("data", {}).get("children", []):
            d = c.get("data", {})
            if not re.search(flag, d.get("title", ""), re.I) or d.get("over_18"):
                continue
            money = re.findall(r"[$€£]\s?(\d{1,4})|(\d{1,4})\s?(?:usd|eur|€|\$|dollars?)", d.get("title", "") + " " + d.get("selftext", ""), re.I)
            vals = [int(a or b) for a, b in money if (a or b)]
            out.append({"id": "rd-" + d.get("id", ""), "quelle": "Reddit r/" + sub, "plattform": False,
                        "titel": d.get("title", ""), "text": d.get("selftext", "")[:2500],
                        "url": "https://www.reddit.com" + d.get("permalink", ""), "autor": d.get("author", ""),
                        "budget_eur": [min(vals), max(vals)] if vals else [0, 0], "stunden": False, "gebote": d.get("num_comments", 0),
                        "zeit": int(d.get("created_utc") or time.time())})
    return out


def prefilter(items, known):
    keep = []
    for it in items:
        txt = it["titel"] + " " + it["text"]
        if it["id"] in known or BAD.search(txt) or not GOOD.search(txt):
            continue
        if time.time() - it["zeit"] > MAX_AGE_H * 3600:
            continue
        if it["budget_eur"][1] and it["budget_eur"][1] < MIN_EUR:
            continue
        if it["plattform"] and it["gebote"] > 60:          # hoffnungslos überlaufen
            continue
        # Vorsortierung: frisch, wenig Konkurrenz, Budget vorhanden
        age_h = (time.time() - it["zeit"]) / 3600
        it["_vor"] = (it["budget_eur"][1] or 20) / (1 + it["gebote"] / 10) / (1 + age_h / 24)
        keep.append(it)
    return sorted(keep, key=lambda x: -x["_vor"])[:12]


# ---------- KI-Bewertung + Vorarbeit ----------
RATE_SYS = ("Du bewertest Aufträge für einen Ein-Personen-Dienstleister, der die Arbeit mit KI (Text-KI, Bild-KI, "
            "Tabellen, kleine Skripte) erledigt. Gib jedem Auftrag 0–100 Punkte: hoch nur, wenn eine KI das Ergebnis "
            "komplett digital liefern kann, der Auftrag seriös und legal ist, keine Täuschung verlangt (keine "
            "Hausaufgaben/Prüfungen, keine Fake-Bewertungen, keine Accounts) und in unter 2 Stunden prüfbar ist. "
            "Schätze einen fairen Festpreis in Euro (mind. 15). Antworte NUR mit JSON-Liste: "
            '[{"id":"…","punkte":0-100,"preis_eur":Zahl,"warum":"1 Satz Deutsch"}]')

WORK_SYS = ("Du bist Lucas' KI-Team und bereitest einen bezahlten Auftrag vollständig vor. Schreibe in der Sprache "
            "des Auftrags. Liefere: 1) ein kurzes, ehrliches Angebot (max. 120 Wörter, freundlich, konkret, nennt "
            "Lieferzeit und Preis, verspricht nichts Unmögliches, kein Hinweis auf ‚KI-Agentur‘ nötig, aber auch "
            "keine Lüge, falls gefragt), 2) das fertige Ergebnis bzw. einen vollständigen ersten Entwurf, so gut "
            "wie möglich direkt lieferbar (bei fehlenden Infos: sinnvolle Annahmen in [eckigen Klammern]), "
            "3) 2–4 kurze Schritte für Lucas auf Deutsch. Antworte NUR mit JSON: "
            '{"titel":"kurzer deutscher Titel","angebot":"…","ergebnis":"…","preis_eur":Zahl,"lieferzeit":"…",'
            '"sprache":"de|en|…","schritte":["…"]}')


def paypal(eur):
    return f"https://paypal.me/{PAYPAL_ME}/{int(round(eur))}EUR"


def prepare(it, rating):
    j = ai(WORK_SYS, f"Quelle: {it['quelle']}\nTitel: {it['titel']}\nBudget: {it['budget_eur']} EUR "
                     f"{'(Stundensatz)' if it['stunden'] else ''}\nVorgeschlagener Preis: {rating.get('preis_eur')} EUR\n\n{it['text']}",
           want_json=True)
    preis = float(j.get("preis_eur") or rating.get("preis_eur") or 30)
    lo, hi = it["budget_eur"]
    if hi:
        preis = min(max(preis, lo or preis), hi)            # im Budget des Kunden bleiben
    preis = max(15, round(preis))
    angebot = j.get("angebot", "").strip()
    if not it["plattform"]:
        angebot += ("\n\nZahlung: 50 % vorab, Rest nach Lieferung, per PayPal: " + paypal(preis / 2)
                    if preis >= 60 else "\n\nZahlung nach Lieferung per PayPal: " + paypal(preis))
    zahlung = ("Über " + it["quelle"] + " (Plattform zahlt aus – in den Kontoeinstellungen PayPal als Auszahlung wählen). "
               "Keine Zahlung außerhalb der Plattform anbieten!") if it["plattform"] else "Direkt per PayPal-Link (im Angebot enthalten)."
    return {"id": it["id"], "t": int(time.time()), "datum": now().strftime("%d.%m.%Y"), "quelle": it["quelle"],
            "plattform": it["plattform"], "url": it["url"], "titel": j.get("titel") or it["titel"][:80],
            "original": it["titel"], "auftrag": it["text"][:1500], "punkte": rating.get("punkte", 0),
            "warum": rating.get("warum", ""), "preis_eur": preis, "lieferzeit": j.get("lieferzeit", ""),
            "angebot": angebot, "ergebnis": j.get("ergebnis", ""), "schritte": j.get("schritte", []),
            "paypal": paypal(preis) if not it["plattform"] else "", "zahlung": zahlung, "status": "neu"}


EIGEN = [("Google-Profil-Check für Handwerksbetriebe", 49), ("10 Social-Media-Posts für einen lokalen Betrieb", 39),
         ("Etsy-Listing-Optimierung (Titel, 13 Tags, Beschreibung)", 19), ("Bewerbung + Lebenslauf überarbeiten", 29),
         ("Produktbeschreibungen für 10 Shop-Artikel", 35), ("Excel-/Google-Sheets-Haushaltsbuch nach Wunsch", 25),
         ("Übersetzung Deutsch ↔ Englisch bis 1.000 Wörter", 25)]


def eigenes_angebot():
    """Fallback: eigenes Tagesangebot, damit es jeden Tag mindestens einen Auftrag gibt."""
    name, preis = EIGEN[now().timetuple().tm_yday % len(EIGEN)]
    j = ai("Du schreibst für Lucas (Region Börde/Harz) ein kurzes, ehrliches Verkaufsangebot für eine digitale "
           "Dienstleistung, die sein KI-Team liefert. Antworte NUR mit JSON: "
           '{"titel":"…","angebot":"Text für Kleinanzeigen/Facebook/Instagram, max. 90 Wörter, mit klarem Nutzen, '
           'Lieferzeit und Preis","ergebnis":"Muster-Ergebnis als Arbeitsprobe (kurz)","preis_eur":Zahl,'
           '"lieferzeit":"…","sprache":"de","schritte":["…"]}',
           f"Dienstleistung: {name}\nPreis: {preis} €", want_json=True)
    return {"id": "eigen-" + now().strftime("%Y%m%d"), "t": int(time.time()), "datum": now().strftime("%d.%m.%Y"),
            "quelle": "Eigenes Tagesangebot", "plattform": False, "url": "", "titel": j.get("titel") or name,
            "original": name, "auftrag": "Kein passender fremder Auftrag gefunden – eigenes Angebot zum Posten "
            "(Kleinanzeigen, Facebook-Gruppen, Instagram, WhatsApp-Status).", "punkte": 0, "warum": "",
            "preis_eur": preis, "lieferzeit": j.get("lieferzeit", "48 Stunden"),
            "angebot": j.get("angebot", "").strip() + "\n\nBezahlen per PayPal: " + paypal(preis),
            "ergebnis": j.get("ergebnis", ""), "schritte": j.get("schritte") or ["Angebot posten", "Bei Anfrage Auftrag in Jarvis erledigen lassen"],
            "paypal": paypal(preis), "zahlung": "Direkt per PayPal-Link.", "status": "neu"}


# ---------- Telegram ----------
def notify(text):
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not (tok and chat) or FAKE:
        return
    try:
        http(f"https://api.telegram.org/bot{tok}/sendMessage", {"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True})
    except Exception as e:
        print("Telegram:", e, file=sys.stderr)


def fake_items():
    t = int(time.time())
    return [{"id": "fl-1", "quelle": "Freelancer.com", "plattform": True, "titel": "Write 5 blog articles about dogs",
             "text": "Need 5 SEO blog articles, 800 words each.", "url": "https://example.com/1", "budget_eur": [30, 120],
             "stunden": False, "gebote": 12, "zeit": t - 3600},
            {"id": "rd-2", "quelle": "Reddit r/slavelabour", "plattform": False, "titel": "[TASK] Translate 600 words EN to German $25",
             "text": "Translate my product page to German.", "url": "https://example.com/2", "budget_eur": [25, 25],
             "stunden": False, "gebote": 2, "zeit": t - 7200},
            {"id": "rd-3", "quelle": "Reddit r/forhire", "plattform": False, "titel": "[Hiring] Cold caller needed",
             "text": "phone calls", "url": "https://example.com/3", "budget_eur": [100, 100], "stunden": False, "gebote": 1, "zeit": t}]


def main():
    try:
        state = json.load(open(OUT))
    except Exception:
        state = {"auftraege": []}
    known = {a["id"] for a in state.get("auftraege", [])}
    heute = now().strftime("%d.%m.%Y")
    schon = [a for a in state["auftraege"] if a.get("datum") == heute]

    items = fake_items() if FAKE else scout_freelancer(usd_eur()) + scout_reddit()
    roh = len(items)
    cand = prefilter(items, known)
    print(f"Gefunden: {roh} Aufträge, nach Filter: {len(cand)}")

    neu = []
    if cand:
        try:
            ratings = ai(RATE_SYS, "\n\n".join(f"#{c['id']} | {c['quelle']} | Budget {c['budget_eur']} EUR\n{c['titel']}\n{c['text'][:700]}" for c in cand), want_json=True)
            rmap = {str(r.get("id")).lstrip("#"): r for r in ratings if isinstance(r, dict)}
        except Exception as e:
            print("Bewertung fehlgeschlagen:", e, file=sys.stderr)
            rmap = {c["id"]: {"punkte": 50, "preis_eur": max(MIN_EUR, c["budget_eur"][1] or 30)} for c in cand}
        best = sorted(cand, key=lambda c: -(rmap.get(c["id"], {}).get("punkte") or 0))
        for c in best:
            if len(neu) + len(schon) >= PER_DAY:
                break
            r = rmap.get(c["id"], {})
            if (r.get("punkte") or 0) < 60:
                continue
            try:
                neu.append(prepare(c, r))
            except Exception as e:
                print("Vorbereiten fehlgeschlagen:", c["id"], e, file=sys.stderr)

    if not neu and not schon:
        try:
            neu.append(eigenes_angebot())
        except Exception as e:
            print("Eigenes Angebot fehlgeschlagen:", e, file=sys.stderr)

    state["auftraege"] = (neu + state["auftraege"])[:KEEP]
    state.update({"stand": now().strftime("%d.%m.%Y %H:%M"), "paypal_me": PAYPAL_ME,
                  "letzter_lauf": {"gefunden": roh, "gefiltert": len(cand), "neu": len(neu)}})
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(state, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"Neu vorbereitet: {len(neu)} → {OUT}")

    for a in neu:
        notify(f"💼 Neuer Auftrag ({a['quelle']}): {a['titel']}\nPreis: {a['preis_eur']} €  ·  Lieferzeit: {a['lieferzeit']}\n"
               f"{a['url'] or a['paypal']}\n\nAngebot + fertiger Entwurf: Jarvis → KI-Stadt → Auftragsbüro")
    if not neu and not schon:
        notify("💼 Auftrags-Scout: heute nichts Passendes gefunden und kein eigenes Angebot erstellt (KI nicht erreichbar).")


if __name__ == "__main__":
    main()
