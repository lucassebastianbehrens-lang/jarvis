"""Jarvis-Automaton – „KI, die sich selbst finanziert und klont“ (Idee: Conway-Research/automaton), mit PayPal statt Krypto.

Jarvis hat einen eigenen Topf (Wallet):  Startguthaben + PayPal-Einnahmen seit Start − Server-Kosten − Kind-Budgets.
Je nach Topf läuft Jarvis in einer von vier Überlebens-Stufen (wirkt automatisch auf alle Bots über jlib):
  normal    ≥ 50 €   volle KI (großes Modell), alle Bots, darf Kinder vorschlagen
  sparsam   ≥ 15 €   kleineres KI-Modell, alles läuft weiter
  kritisch  >  0 €   kleines Modell, Nebensachen (Recherche, Lage, Videos) pausieren – nur noch Geld-Suche
  ruhe      ≤  0 €   nur Wächter, Leibgarde, Ideen und Geld-Bots laufen; Jarvis wartet auf Einnahmen
Klonen: Ist genug im Topf, schlägt Jarvis einen Kind-Bot vor (Bauer = Shops/Seiten, Vermarkter = Videos/Reichweite,
Sicherung = sichert und prüft). Ein Kind entsteht NUR nach Lucas' „Ja“ in der App. Es bekommt ein eigenes Budget
aus dem Topf (rein rechnerisch), arbeitet Schritt für Schritt an seinem Auftrag und stirbt, wenn das Budget leer ist
und nichts reinkam. Einnahmen mit „[K-xxxx]“ im PayPal-Verwendungszweck zählen fürs jeweilige Kind.

SICHERHEIT: Der Bot LIEST PayPal nur (Kontostand, Umsätze). Er kann kein Geld senden, abheben oder ausgeben.
Schlüssel (GitHub-Secrets): PAYPAL_CLIENT_ID, PAYPAL_SECRET – Anleitung: docs/AUTOMATON.md
Aufruf: python3 bot/automaton.py [lauf|ja|nein]      Ergebnis → data/automaton.json"""
import base64, json, os, random, re, sys, time, urllib.parse, urllib.request
import jlib

DATEI = "automaton.json"
STUFEN = [("normal", 50), ("sparsam", 15), ("kritisch", 0.01)]  # darunter: ruhe
ROLLEN = {
    "bauer": {"icon": "🏗️", "workflow": "shop-bau.yml", "was": "baut Shops/Webseiten, die verkaufen"},
    "vermarkter": {"icon": "📣", "workflow": "video-auto.yml", "was": "macht Reichweite (Videos, Posts) für bestehende Angebote"},
    "sicherung": {"icon": "💾", "workflow": None, "was": "prüft Shops/Seiten auf Fehler und hält Jarvis am Laufen"},
}
STANDARD = {
    "start": None, "startguthaben": 25.0, "server_eur_monat": 9.50, "kosten_pro_schritt": 0.05,
    "klon_ab": 40.0, "max_kinder": 3, "kind_budget_max": 10.0, "kind_lebenstage_ohne_einnahmen": 30,
    "modus": "normal", "topf": 0.0, "paypal": None, "kinder": [], "vorschlag": None, "log": [],
}
PAYPAL_API = "https://api-m.sandbox.paypal.com" if os.environ.get("PAYPAL_ENV") == "sandbox" else "https://api-m.paypal.com"


def stufe(topf):
    for name, ab in STUFEN:
        if topf >= ab:
            return name
    return "ruhe"


# ---------- PayPal (nur lesen) ----------
def _paypal_token():
    cid, sec = os.environ.get("PAYPAL_CLIENT_ID", ""), os.environ.get("PAYPAL_SECRET", "")
    if not (cid and sec):
        return None
    req = urllib.request.Request(PAYPAL_API + "/v1/oauth2/token", b"grant_type=client_credentials", {
        "Authorization": "Basic " + base64.b64encode(f"{cid}:{sec}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def _iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S-0000", time.gmtime(ts))


def paypal_lesen(seit):
    """→ {"kontostand": €|None, "eingaenge": [{"t","eur","text"}]} oder None ohne Schlüssel. PayPal erlaubt max. 31 Tage pro Abfrage."""
    tok = _paypal_token()
    if not tok:
        return None
    h = {"Authorization": "Bearer " + tok}
    out = {"kontostand": None, "eingaenge": []}
    try:
        b = jlib.http(PAYPAL_API + "/v1/reporting/balances?currency_code=EUR", headers=h)
        for x in b.get("balances", []):
            if x.get("currency") == "EUR":
                out["kontostand"] = float(x["total_balance"]["value"])
    except Exception as e:
        print("PayPal Kontostand", e)
    jetzt, a = time.time(), max(seit, time.time() - 3 * 365 * 86400)
    while a < jetzt:
        e = min(a + 31 * 86400 - 60, jetzt)
        seite = 1
        while True:
            q = urllib.parse.urlencode({"start_date": _iso(a), "end_date": _iso(e), "fields": "transaction_info",
                                        "page_size": 500, "page": seite})
            j = jlib.http(f"{PAYPAL_API}/v1/reporting/transactions?{q}", headers=h)
            for d in j.get("transaction_details", []):
                ti = d.get("transaction_info", {})
                amt = ti.get("transaction_amount", {})
                wert = float(amt.get("value") or 0)
                if amt.get("currency_code") == "EUR" and wert > 0 and ti.get("transaction_status", "S") == "S":
                    out["eingaenge"].append({"id": ti.get("transaction_id"), "eur": wert,
                                             "text": f'{ti.get("transaction_subject", "")} {ti.get("transaction_note", "")}'.strip(),
                                             "t": ti.get("transaction_initiation_date", "")})
            if seite >= int(j.get("total_pages") or 1):
                break
            seite += 1
        a = e
    return out


# ---------- Rechnen ----------
def bilanz(s, pp, jetzt):
    """Topf und Kind-Einnahmen aus PayPal-Eingängen + Kosten neu berechnen (immer komplett, damit nichts doppelt zählt)."""
    eing = pp["eingaenge"] if pp else []
    kind_ein = {k["id"]: 0.0 for k in s["kinder"]}
    jarvis_ein = 0.0
    for x in eing:
        m = re.search(r"\[(K-[0-9a-z]{4})\]", x["text"], re.I)
        kid = m.group(1).upper() if m else None
        if kid in kind_ein:
            kind_ein[kid] += x["eur"]
        else:
            jarvis_ein += x["eur"]
    for k in s["kinder"]:
        k["einnahmen"] = round(kind_ein.get(k["id"], 0.0), 2)
    monate = max(0.0, (jetzt - s["start"]) / (30.44 * 86400))
    server = round(monate * s["server_eur_monat"], 2)
    # Kinder: Budget ist aus dem Topf reserviert; was sie verdienen, fließt zurück
    kinder_netto = sum(k["einnahmen"] - (k["budget"] if k["status"] == "lebt" else min(k["ausgegeben"], k["budget"])) for k in s["kinder"])
    s["topf"] = round(s["startguthaben"] + jarvis_ein - server + kinder_netto, 2)
    s["kosten"] = {"server_bisher": server, "server_monat": s["server_eur_monat"]}
    s["einnahmen_gesamt"] = round(jarvis_ein + sum(kind_ein.values()), 2)
    s["einnahmen_30t"] = round(sum(x["eur"] for x in eing if _ts(x["t"]) >= jetzt - 30 * 86400), 2)
    tages_kosten = s["server_eur_monat"] / 30.44
    s["reichweite_tage"] = int(s["topf"] / tages_kosten) if s["topf"] > 0 else 0


def _ts(iso):
    try:
        return time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception:
        return 0


def log(s, text):
    s["log"].insert(0, {"t": int(time.time()), "text": text})
    s["log"] = s["log"][:40]
    print(text)


# ---------- Kinder ----------
def vorschlagen(s):
    lebend = [k for k in s["kinder"] if k["status"] == "lebt"]
    if s["modus"] != "normal" or s["topf"] < s["klon_ab"] or len(lebend) >= s["max_kinder"] or s.get("vorschlag") \
            or time.time() - s.get("letzter_vorschlag", 0) < 3 * 86400:  # höchstens alle 3 Tage ein neuer Klon
        return
    budget = round(min(s["kind_budget_max"], s["topf"] * 0.3), 2)
    vorhanden = ", ".join(f'{k["rolle"]}: {k["auftrag"][:60]}' for k in lebend) or "keine"
    try:
        v = jlib.parse_json(jlib.ki(
            "Du bist Jarvis, Lucas' KI. Du darfst dich klonen: ein Kind-Bot mit eigenem Budget soll Geld einbringen, "
            "das per PayPal zu Lucas fließt. Nur legale Ideen mit wenig Eigenarbeit für Lucas, keine Haftungsrisiken, "
            "keine erfundenen Bewertungen, kein Spam. Antworte nur als JSON.",
            f"Topf: {s['topf']} €, Kind-Budget: {budget} €. Lebende Kinder: {vorhanden}.\n"
            f"Rollen: {json.dumps({r: x['was'] for r, x in ROLLEN.items()}, ensure_ascii=False)}\n"
            'Format: {"rolle": "bauer|vermarkter|sicherung", "name": "kurzer Vorname", "auftrag": "Genesis-Auftrag in 1–2 Sätzen", '
            '"warum": "1 Satz, wie das Geld bringt"}', json_mode=True))
        if v.get("rolle") not in ROLLEN or not v.get("auftrag"):
            raise ValueError(v)
    except Exception as e:
        print("Vorschlag", e)
        return
    s["vorschlag"] = {"rolle": v["rolle"], "name": str(v.get("name") or "Kind")[:20], "auftrag": v["auftrag"][:300],
                      "warum": str(v.get("warum", ""))[:200], "budget": budget, "t": int(time.time())}
    s["letzter_vorschlag"] = int(time.time())
    log(s, f"🧬 Klon-Vorschlag: {s['vorschlag']['name']} ({v['rolle']}) mit {budget:.2f} € – wartet auf dein Ja")
    jlib.tg(f"🧬 Jarvis will sich klonen: {s['vorschlag']['name']} ({v['rolle']}), Budget {budget:.2f} €.\n"
            f"Auftrag: {s['vorschlag']['auftrag']}\nIn der Jarvis-App → Trading → „Klonen? Ja/Nein“.")


def geboren(s):
    v = s.pop("vorschlag")
    s["vorschlag"] = None
    kid = "K-" + "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(4)).upper()
    s["kinder"].append({"id": kid, "name": v["name"], "rolle": v["rolle"], "auftrag": v["auftrag"], "budget": v["budget"],
                        "ausgegeben": 0.0, "einnahmen": 0.0, "status": "lebt", "geboren": int(time.time()), "schritte": []})
    log(s, f"👶 {v['name']} ({kid}) geboren – Budget {v['budget']:.2f} €. Einnahmen mit „[{kid}]“ im PayPal-Zweck zählen für {v['name']}.")


def kind_schritt(s, k):
    """Ein Herzschlag eines Kindes: KI plant den nächsten Schritt, startet höchstens einen sicheren Jarvis-Dienst."""
    if k["ausgegeben"] + s["kosten_pro_schritt"] > k["budget"] + k["einnahmen"]:
        k["status"] = "tot"
        log(s, f"💀 {k['name']} ({k['id']}): Budget aufgebraucht, {k['einnahmen']:.2f} € verdient.")
        return
    if k["einnahmen"] == 0 and time.time() - k["geboren"] > s["kind_lebenstage_ohne_einnahmen"] * 86400:
        k["status"] = "tot"
        log(s, f"💀 {k['name']} ({k['id']}): {s['kind_lebenstage_ohne_einnahmen']} Tage ohne Einnahme – abgeschaltet.")
        return
    rolle = ROLLEN[k["rolle"]]
    verlauf = "\n".join(f"- {x['text']}" for x in k["schritte"][-6:]) or "- noch nichts"
    sparsam = s["modus"] != "normal"
    try:
        p = jlib.parse_json(jlib.ki(
            f"Du bist {k['name']}, ein Kind-Bot von Jarvis (Rolle: {k['rolle']} – {rolle['was']}). Genesis-Auftrag: {k['auftrag']}\n"
            "Plane den EINEN nächsten sinnvollen Schritt Richtung Einnahmen. Regeln: legal, ehrlich, keine erfundenen Bewertungen, "
            "kein Spam, Lucas haftet nie. Du kannst kein Geld ausgeben. Antworte nur als JSON.",
            f"Bisher:\n{verlauf}\nBudget übrig: {k['budget'] + k['einnahmen'] - k['ausgegeben']:.2f} €.\n"
            + ("Jarvis spart gerade – nur Schritte, die schnell Geld bringen.\n" if sparsam else "")
            + 'Format: {"schritt": "was du jetzt tust (1 Satz)", "starten": true|false, "wunsch": "kurze Beschreibung für den Dienst"}',
            json_mode=True))
    except Exception as e:
        print("Kind", k["id"], e)
        return
    k["ausgegeben"] = round(k["ausgegeben"] + s["kosten_pro_schritt"], 2)
    text = str(p.get("schritt", ""))[:200]
    wf = rolle["workflow"]
    if p.get("starten") and wf and jlib.GH_TOKEN:
        inputs = {"wunsch": f"{p.get('wunsch') or k['auftrag']} [{k['id']}]"[:300]} if wf == "shop-bau.yml" else {}
        try:
            jlib.gh(f"repos/{jlib.REPO}/actions/workflows/{wf}/dispatches", {"ref": "main", "inputs": inputs}, "POST")
            text += f" → {wf} gestartet"
        except Exception as e:
            text += f" (Start von {wf} fehlgeschlagen: {e})"
    k["schritte"].append({"t": int(time.time()), "text": text})
    k["schritte"] = k["schritte"][-20:]


# ---------- Ablauf ----------
def laden():
    s = {**STANDARD, **jlib.load(DATEI, {})}
    s["start"] = s["start"] or int(time.time())
    return s


def main(aktion="lauf"):
    s, jetzt = laden(), int(time.time())
    if aktion == "ja" and s.get("vorschlag"):
        geboren(s)
    elif aktion == "nein" and s.get("vorschlag"):
        log(s, f"🙅 Klon-Vorschlag {s['vorschlag']['name']} abgelehnt.")
        s["vorschlag"] = None
    pp = None
    try:
        pp = paypal_lesen(s["start"])
    except Exception as e:
        print("PayPal", e)
    s["paypal"] = {"verbunden": pp is not None, "kontostand": pp and pp["kontostand"], "geprueft": jetzt}
    bilanz(s, pp, jetzt)
    alt, s["modus"] = s["modus"], stufe(s["topf"]) if pp is not None else "normal"
    if pp is None:
        s["hinweis"] = "PayPal noch nicht verbunden – Jarvis läuft normal weiter. Anleitung: docs/AUTOMATON.md"
    else:
        s.pop("hinweis", None)
    if s["modus"] != alt and pp is not None:
        log(s, f"⚙️ Stufe {alt} → {s['modus']} (Topf {s['topf']:.2f} €)")
        jlib.tg(f"⚙️ Jarvis-Überlebensmodus: {alt} → {s['modus']} · Topf {s['topf']:.2f} € · reicht ~{s['reichweite_tage']} Tage")
    if aktion == "lauf":
        for k in s["kinder"]:
            if k["status"] == "lebt" and s["modus"] != "ruhe":
                kind_schritt(s, k)
        bilanz(s, pp, jetzt)
        vorschlagen(s)
    s["updated"] = jetzt
    jlib.store(DATEI, s)
    return s


if __name__ == "__main__":
    main((sys.argv[1:] or [os.environ.get("AKTION") or "lauf"])[0])
