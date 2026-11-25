"""Forscherin Frieda – nächtliche Recherche: neue KI-Tools, Skills/Agenten und TikTok-Trends.
Quellen: GitHub (neue Repos mit vielen Sternen), Hacker News, Websuche über Groq Compound (inkl. TikTok-Trends).
Die KI bewertet alles für Lucas und macht Einbau-Vorschläge für Jarvis.
Nichts wird automatisch eingebaut: in der App per „Umsetzen ja/nein“ freigeben → GitHub-Issue → Claude baut ein.
Ergebnis → data/recherche.json"""
import hashlib, time, urllib.parse
from jlib import http, gh, ki, parse_json, load, store, darf_laufen

if not darf_laufen("recherche"):
    raise SystemExit(0)

now = int(time.time())
woche = time.strftime("%Y-%m-%d", time.gmtime(now - 7 * 86400))
roh = []

for q in ["topic:mcp", "topic:ai-agents", "topic:claude", "topic:llm", "topic:agent-skills", "topic:automation"]:
    try:
        j = gh(f"search/repositories?q={urllib.parse.quote(q + ' created:>=' + woche)}&sort=stars&order=desc&per_page=6")
        for r in j.get("items", []):
            if r["stargazers_count"] >= 30:
                roh.append({"quelle": "GitHub", "titel": r["full_name"], "url": r["html_url"],
                            "text": (r.get("description") or "")[:200], "score": r["stargazers_count"]})
    except Exception as e:
        print("GitHub", q, e)

try:
    j = http("https://hn.algolia.com/api/v1/search?tags=story&numericFilters=" +
             urllib.parse.quote(f"created_at_i>{now - 86400},points>40") + "&query=AI&hitsPerPage=15")
    for h in j.get("hits", []):
        roh.append({"quelle": "Hacker News", "titel": h["title"], "url": h.get("url") or
                    f"https://news.ycombinator.com/item?id={h['objectID']}", "text": "", "score": h.get("points", 0)})
except Exception as e:
    print("HN", e)

roh = list({r["url"]: r for r in roh}.values())
web = ki("Du bist ein Trend-Scout. Antworte auf Deutsch, knapp, mit Quellen-Links.",
         "Recherchiere im Web (Stand heute): 1) welche neuen KI-Tools, KI-Agenten oder Automatisierungen gerade auf "
         "TikTok viral gehen, 2) neue kostenlose KI-Tools/Skills/MCP-Server der letzten 7 Tage. "
         "Liste die 8 interessantesten mit Name, 1 Satz was es kann und Link.", search=True)

ziel = ("Lucas (Schichtarbeiter, baut nebenbei Online-Geschäfte: TikTok-KI-Videos, Etsy-Vorlagen, Social Media für "
        "Handwerker, Krypto-Spielgeld-Bot) hat eine eigene Assistenten-App 'Jarvis' (Web-App + GitHub-Actions-Bots, "
        "Groq-KI, kostenlos). Bewerte Funde danach, ob sie Jarvis oder seine Geschäfte kostenlos/günstig verbessern.")
prompt = (f"{ziel}\n\nFunde:\n" + "\n".join(f"- [{r['quelle']}] {r['titel']} – {r['text']} ({r['url']})" for r in roh[:40])
          + f"\n\nWeb/TikTok-Recherche:\n{web[:5000]}\n\n"
          "Wähle die 6 nützlichsten. Antworte NUR als JSON: {\"items\":[{\"titel\":..., \"url\":..., \"quelle\":..., "
          "\"was\": \"1 Satz was es ist\", \"nutzen\": \"1 Satz Nutzen für Lucas\", \"vorschlag\": \"konkreter Einbau in Jarvis\", "
          "\"punkte\": 0-100}], \"fazit\": \"1 Satz\"}")
try:
    res = parse_json(ki("Du antwortest nur mit gültigem JSON auf Deutsch.", prompt, json_mode=True))
except Exception as e:
    print("KI-Auswertung", e)
    res = {"items": [{"titel": r["titel"], "url": r["url"], "quelle": r["quelle"], "was": r["text"], "nutzen": "",
                      "vorschlag": "", "punkte": None} for r in sorted(roh, key=lambda x: -x["score"])[:6]], "fazit": ""}

echt = {r["url"] for r in roh}
res["items"] = [i for i in res.get("items", []) if i.get("url") in echt or (i.get("url") and i["url"] in web)]
if not res["items"]:  # nichts Belegbares → echte Rohfunde zeigen statt erfundener
    res = {"fazit": "", "items": [{"titel": r["titel"], "url": r["url"], "quelle": r["quelle"], "was": r["text"],
                                   "nutzen": "", "vorschlag": "", "punkte": None} for r in sorted(roh, key=lambda x: -x["score"])[:6]]}
alt = load("recherche.json", {"items": []})
alt["items"] = []  if not alt.get("v2") else alt["items"]
bekannt = {i["id"] for i in alt["items"]}
neu = []
for i in res.get("items", []):
    i["id"] = hashlib.md5((i.get("url") or i.get("titel", "")).encode()).hexdigest()[:10]
    i["t"] = now
    if i["id"] not in bekannt:
        neu.append(i)
store("recherche.json", {"v2": 1, "updated": now, "fazit": res.get("fazit", ""), "web": web[:3000],
                         "neu": [i["id"] for i in neu], "items": (neu + alt["items"])[:60]})
print(f"{len(roh)} Funde, {len(neu)} neue Vorschläge")
