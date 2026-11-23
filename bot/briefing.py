"""Butler Bruno – Tages-Briefing: was die Bots in den letzten 24 h getan haben.
Ergebnis → data/briefing.json (Briefing-Tab in Jarvis, mit Vorlesen)."""
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from jlib import load, store, ki, runs_since, wf_file

now = int(time.time())
seit = now - 24 * 3600
bots = {b["wf"]: b for b in load("bots.json", [])}
zeilen, bot_info = [], []

try:
    runs = runs_since(seit)
except Exception as e:
    runs = []
    zeilen.append(f"⚠️ Bot-Läufe nicht lesbar: {e}")
stat = {}
for r in runs:
    s = stat.setdefault(wf_file(r), {"ok": 0, "fehler": 0})
    if r.get("conclusion") == "success":
        s["ok"] += 1
    elif r.get("conclusion") in ("failure", "timed_out"):
        s["fehler"] += 1
for wf, s in stat.items():
    if wf not in bots:
        continue
    b = bots[wf]
    bot_info.append({"name": b["name"], "icon": b.get("icon", "⚙️"), **s})
bot_info.sort(key=lambda x: -(x["ok"] + x["fehler"]))
ges_ok, ges_f = sum(b["ok"] for b in bot_info), sum(b["fehler"] for b in bot_info)
zeilen.append(f"🤖 {len(bot_info)} Bots haben {ges_ok + ges_f} Aufträge erledigt" + (f", {ges_f} mit Fehler." if ges_f else ", alle fehlerfrei."))


def eur(x):
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def equity_at(eq, t):
    pts = [v for ts, v in eq if ts <= t]
    return pts[-1] if pts else (eq[0][1] if eq else None)


trading = {}
for key, name in (("paper.json", "Krypto-Bot"), ("agents.json", "Memecoin-Bot")):
    d = load(key, {})
    eq = d.get("equity", [])
    if not eq:
        continue
    jetzt, vorher = eq[-1][1], equity_at(eq, seit)
    zu = [c for c in d.get("closed", []) if c.get("t_out", 0) >= seit]
    gew = sum(c["pnl"] for c in zu)
    trading[name] = {"wert": round(jetzt, 2), "diff": round(jetzt - vorher, 2), "trades": len(zu),
                     "gewinner": sum(c["pnl"] > 0 for c in zu), "pnl": round(gew, 2)}
    zeilen.append(f"📈 {name}: {eur(jetzt)} ({'+' if jetzt >= vorher else ''}{eur(jetzt - vorher)} in 24 h), {len(zu)} Trades – Spielgeld")

auf = [a for a in load("auftraege.json", {}).get("auftraege", []) if a.get("t", 0) >= seit]
if auf:
    zeilen.append(f"🔭 {len(auf)} neue Aufträge gefunden, z. B. „{auf[0].get('titel', '')}“.")

rec = load("recherche.json", {})
neu = [i for i in rec.get("items", []) if i.get("t", 0) >= seit]
if neu:
    zeilen.append(f"📚 {len(neu)} neue Tools/Trends entdeckt – Top: {neu[0].get('titel', '')}.")

st = load("status.json", {})
prob = [c for c in st.get("checks", []) if not c["ok"]]
zeilen.append("🛡️ Wächter: alles läuft." if not prob else f"🛡️ Wächter: {len(prob)} Problem(e) – {prob[0]['name']}: {prob[0]['info']}")
if st.get("repariert"):
    zeilen.append(f"🔧 Selbst repariert: {', '.join(st['repariert'])}.")

fazit = ki("Du bist Jarvis, Lucas' Assistent. Deutsch, locker, höchstens 2 kurze Sätze, keine Aufzählung.",
           "Fasse dieses Nacht-Briefing für Lucas zusammen und nenne die eine wichtigste Sache für heute:\n" + "\n".join(zeilen))
datum = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%A, %d.%m.%Y")
for en, de in (("Monday", "Montag"), ("Tuesday", "Dienstag"), ("Wednesday", "Mittwoch"), ("Thursday", "Donnerstag"),
               ("Friday", "Freitag"), ("Saturday", "Samstag"), ("Sunday", "Sonntag")):
    datum = datum.replace(en, de)
b = {"t": now, "datum": datum, "fazit": fazit, "zeilen": zeilen, "bots": bot_info, "trading": trading,
     "neu": [{"titel": i.get("titel"), "nutzen": i.get("nutzen"), "url": i.get("url")} for i in neu[:5]]}
alt = load("briefing.json", {})
verlauf = ([{k: alt[k] for k in ("t", "datum", "fazit", "zeilen")}] if alt.get("t") else []) + alt.get("verlauf", [])
b["verlauf"] = verlauf[:14]
store("briefing.json", b)
print("\n".join([datum, fazit] + zeilen))
