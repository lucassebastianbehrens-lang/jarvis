"""Agentin Ada – Lage-Zentrale ("Geheimdienst"): Weltnachrichten pro Land + Märkte.
Quellen: tagesschau + Deutsche Welle (RSS), CoinGecko, Frankfurter (EZB-Kurse). Kein Schlüssel nötig.
Ergebnis → data/lage.json (Tab „Lage“ in Jarvis)."""
import html, re, time, urllib.request
import xml.etree.ElementTree as ET
from jlib import load, store, ki, http

FEEDS = [
    ("tagesschau", "https://www.tagesschau.de/ausland/index~rss2.xml"),
    ("tagesschau", "https://www.tagesschau.de/index~rss2.xml"),
    ("DW", "https://rss.dw.com/rdf/rss-de-all"),
]

# Land: (Breite, Länge, Suchwörter) – Wortanfänge, damit „Russlands“, „ukrainische“ usw. passen
LAENDER = {
    "Deutschland": (51.2, 10.4, ["deutschland", "bundesregierung", "bundestag", "berlin", "merz", "bundeswehr"]),
    "USA": (39.8, -98.6, ["usa ", "us-", "vereinigte staaten", "washington", "trump", "weißes haus", "amerikan"]),
    "Russland": (61.5, 90.0, ["russland", "russisch", "moskau", "kreml", "putin"]),
    "Ukraine": (49.0, 31.3, ["ukrain", "kiew", "kyjiw", "selenskyj"]),
    "China": (35.9, 104.2, ["china", "chines", "peking", "xi jinping"]),
    "Israel": (31.0, 34.9, ["israel", "netanjahu", "jerusalem", "tel aviv"]),
    "Gaza": (31.4, 34.4, ["gaza", "hamas", "palästin"]),
    "Iran": (32.4, 53.7, ["iran ", "iranisch", "teheran"]),
    "Frankreich": (46.2, 2.2, ["frankreich", "französisch", "paris", "macron"]),
    "Großbritannien": (54.0, -2.5, ["großbritannien", "britisch", "london", "england", "starmer"]),
    "Italien": (42.8, 12.6, ["italien", "rom ", "meloni"]),
    "Spanien": (40.4, -3.7, ["spanien", "spanisch", "madrid"]),
    "Polen": (52.1, 19.4, ["polen ", "polnisch", "warschau"]),
    "Türkei": (39.0, 35.2, ["türkei", "türkisch", "ankara", "istanbul", "erdogan"]),
    "Syrien": (35.0, 38.5, ["syrien", "damaskus"]),
    "Libanon": (33.9, 35.9, ["libanon", "hisbollah", "beirut"]),
    "Indien": (21.0, 78.0, ["indien", "indisch", "neu-delhi", "modi"]),
    "Japan": (36.2, 138.3, ["japan", "tokio"]),
    "Nordkorea": (40.3, 127.5, ["nordkorea", "pjöngjang", "kim jong"]),
    "Südkorea": (36.5, 127.9, ["südkorea", "seoul"]),
    "Taiwan": (23.7, 121.0, ["taiwan"]),
    "Brasilien": (-14.2, -51.9, ["brasilien", "lula"]),
    "Argentinien": (-38.4, -63.6, ["argentinien", "milei"]),
    "Mexiko": (23.6, -102.6, ["mexiko"]),
    "Kanada": (56.1, -106.3, ["kanada"]),
    "Venezuela": (6.4, -66.6, ["venezuela", "maduro"]),
    "Südafrika": (-30.6, 22.9, ["südafrika"]),
    "Sudan": (12.9, 30.2, ["sudan", "khartum"]),
    "Ägypten": (26.8, 30.8, ["ägypten", "kairo"]),
    "Saudi-Arabien": (23.9, 45.1, ["saudi"]),
    "Afghanistan": (33.9, 67.7, ["afghanistan", "taliban", "kabul"]),
    "Australien": (-25.3, 133.8, ["australien"]),
    "Österreich": (47.5, 14.6, ["österreich", "wien"]),
    "Schweiz": (46.8, 8.2, ["schweiz", "zürich", "bern "]),
    "Niederlande": (52.1, 5.3, ["niederlande", "niederländisch", "den haag", "amsterdam"]),
    "Belgien/EU": (50.8, 4.4, ["brüssel", "eu-", "europäische union", "eu-kommission", "von der leyen"]),
    "Ungarn": (47.2, 19.5, ["ungarn", "orban", "budapest"]),
    "Griechenland": (39.1, 21.8, ["griechenland", "athen"]),
}
# Suchwort muss am Wortanfang stehen („neu-delhi“ ist kein „eu-“, „plus-“ kein „us-“)
MUSTER = {w: re.compile(r"(?<![a-zäöüß])" + re.escape(w.strip()) + (r"(?![a-zäöüß])" if w.endswith(" ") else "")) for _, _, ws in LAENDER.values() for w in ws}
STAERKE = re.compile(r"krieg|angriff|tote|getötet|explosion|anschlag|rakete|drohne|beschuss|eskal|sanktion|krise|erdbeben|flut|wahl", re.I)


def lade_feed(quelle, url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 jarvis-lage"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter():
        if not it.tag.split("}")[-1] == "item":
            continue
        f = {c.tag.split("}")[-1]: (c.text or "").strip() for c in it}
        titel = html.unescape(f.get("title", ""))
        text = re.sub(r"<[^>]+>", " ", html.unescape(f.get("description", "")))
        text = re.sub(r"\s+", " ", text).strip()
        if titel and f.get("link"):
            out.append({"titel": titel, "text": text[:240], "url": f["link"], "quelle": quelle})
    return out


def laender_von(m):
    t = " " + (m["titel"] + " " + m["text"]).lower() + " "
    return [n for n, (_, _, ws) in LAENDER.items() if any(MUSTER[w].search(t) for w in ws)]


def maerkte():
    out = []
    try:
        p = http("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur&include_24hr_change=true")
        for cid, name in (("bitcoin", "Bitcoin"), ("ethereum", "Ethereum"), ("solana", "Solana")):
            if cid in p:
                out.append({"name": name, "wert": p[cid]["eur"], "einheit": "€", "pct": round(p[cid].get("eur_24h_change") or 0, 2)})
        k = http("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=eur&days=7&interval=daily")
        if out:
            out[0]["verlauf"] = [round(v) for _, v in k.get("prices", [])]
    except Exception as e:
        print("CoinGecko", e)
    try:
        heute = http("https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,CHF")
        alt = load("lage.json", {}).get("fx", {})
        for cur, v in heute.get("rates", {}).items():
            vor = alt.get(cur)
            out.append({"name": f"EUR/{cur}", "wert": v, "einheit": "", "pct": round((v / vor - 1) * 100, 2) if vor else 0})
        fx = heute.get("rates", {})
    except Exception as e:
        print("Frankfurter", e)
        fx = load("lage.json", {}).get("fx", {})
    return out, fx


def main():
    alle, fehler = [], []
    for q, url in FEEDS:
        try:
            alle += lade_feed(q, url)
        except Exception as e:
            fehler.append(f"{q}: {e}")
            print("Feed", url, e)
    gesehen, meldungen = set(), []
    for m in alle:
        k = m["titel"].lower()[:70]
        if k in gesehen:
            continue
        gesehen.add(k)
        m["laender"] = laender_von(m)
        m["heiss"] = bool(STAERKE.search(m["titel"] + " " + m["text"]))
        meldungen.append(m)

    orte = {}
    for m in meldungen:
        for n in m["laender"]:
            o = orte.setdefault(n, {"land": n, "lat": LAENDER[n][0], "lon": LAENDER[n][1], "anzahl": 0, "heiss": 0, "meldungen": []})
            o["anzahl"] += 1
            o["heiss"] += m["heiss"]
            if len(o["meldungen"]) < 6:
                o["meldungen"].append({k: m[k] for k in ("titel", "text", "url", "quelle")})
    orte = sorted(orte.values(), key=lambda o: -(o["anzahl"] + 2 * o["heiss"]))

    lagebild = ""
    if meldungen:
        top = "\n".join(f"- [{', '.join(m['laender']) or 'Welt'}] {m['titel']}" for m in meldungen[:30])
        lagebild = ki("Du bist Jarvis' Nachrichtendienst. Schreib auf Deutsch ein Lagebild in genau 3 kurzen Sätzen: "
                      "was weltweit gerade am wichtigsten ist und was davon Lucas in Deutschland direkt betrifft (Preise, Sprit, Börse). Nur Fakten aus der Liste.", top)
    if not lagebild and orte:  # ohne KI: Lagebild aus den Schlagzeilen
        heiss = [m for m in meldungen if m["heiss"] and m["laender"]] or meldungen
        lagebild = (f"Am meisten los: {', '.join(o['land'] + ' (' + str(o['anzahl']) + ')' for o in orte[:3])}. "
                    f"Wichtigste Meldung: {heiss[0]['titel']}."
                    + (f" Außerdem: {heiss[1]['titel']}." if len(heiss) > 1 else ""))
    markt, fx = maerkte()
    alt = load("lage.json", {})
    data = {
        "updated": int(time.time()),
        "lagebild": lagebild or alt.get("lagebild", ""),
        "orte": orte[:25],
        "ohne_land": [{k: m[k] for k in ("titel", "url", "quelle")} for m in meldungen if not m["laender"]][:8],
        "maerkte": markt or alt.get("maerkte", []),
        "fx": fx,
        "fehler": fehler,
    }
    if not meldungen and alt.get("orte"):  # Quellen gestört → alten Stand behalten
        data["orte"], data["ohne_land"] = alt["orte"], alt.get("ohne_land", [])
    store("lage.json", data)
    print(f"{len(meldungen)} Meldungen, {len(orte)} Länder, {len(markt)} Marktwerte, Fehler: {fehler}")


if __name__ == "__main__":
    main()
