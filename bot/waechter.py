"""Wächter Willi – stündlicher Hintergrund-Check.
Prüft: letzter Lauf jedes Bots (Fehler? zu alt?), Spielgeld-Daten frisch?, Live-Seite erreichbar?, KI-Motor antwortet?
Repariert selbst: fehlgeschlagene geplante Läufe werden einmal neu gestartet.
Meldet per Telegram nur NEUE Probleme. Ergebnis → data/status.json (für den Jarvis-Tab)."""
import calendar, time, urllib.request
import jlib
from jlib import REPO, gh, load, store, tg, runs_since, wf_file, path, ki

now = int(time.time())
bots = load("bots.json", [])
old = load("status.json", {})
checks, repariert = [], []


def anstupsen(b):
    """Überfällige Bots selbst starten (GitHub verschiebt geplante Läufe manchmal um Stunden)."""
    try:
        if "workflow_dispatch" not in open(path(".github", "workflows", b["wf"]), encoding="utf-8").read():
            return " → kann nicht manuell starten"
        gh(f"repos/{REPO}/actions/workflows/{b['wf']}/dispatches", {"ref": "main"}, "POST")
        repariert.append(b["name"])
        return " → selbst gestartet"
    except Exception as e:
        return f" → Start ging nicht ({e})"


try:
    runs = runs_since(now - 30 * 3600, pages=4)
except Exception as e:
    runs = []
    checks.append({"name": "GitHub-API", "ok": False, "info": f"nicht erreichbar: {e}"})

last = {}
for r in runs:  # neueste zuerst
    last.setdefault(wf_file(r), r)

for b in bots:
    wf, max_h = b["wf"], b.get("max_h")
    if wf == "waechter.yml":
        continue
    r = last.get(wf)
    if not r:
        if max_h and max_h <= 3:
            checks.append({"name": b["name"], "ok": False, "info": f"seit 30 h kein Lauf (erwartet alle {max_h} h)" + anstupsen(b)})
        elif max_h:
            checks.append({"name": b["name"], "ok": True, "info": "wartet auf den nächsten Einsatz"})
        continue
    t = calendar.timegm(time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ"))
    age_h = (now - t) / 3600
    if r["status"] != "completed":
        checks.append({"name": b["name"], "ok": True, "info": "läuft gerade"})
        continue
    if r["conclusion"] in ("failure", "timed_out", "startup_failure"):
        info = f"letzter Lauf fehlgeschlagen ({r['conclusion']})"
        if r.get("event") == "schedule" and r.get("run_attempt", 1) < 2:
            try:
                gh(f"repos/{REPO}/actions/runs/{r['id']}/rerun-failed-jobs", {}, "POST")
                repariert.append(b["name"])
                info += " → automatisch neu gestartet"
            except Exception as e:
                info += f" → Neustart ging nicht ({e})"
        checks.append({"name": b["name"], "ok": False, "info": info, "url": r["html_url"]})
    elif max_h and age_h > max_h:
        checks.append({"name": b["name"], "ok": False, "info": f"letzter Lauf vor {age_h:.0f} h (erwartet alle {max_h} h)" + anstupsen(b)})
    else:
        checks.append({"name": b["name"], "ok": True, "info": f"ok · vor {age_h * 60:.0f} Min" if age_h < 1 else f"ok · vor {age_h:.0f} h"})

paper = load("paper.json", {})
age = (now - paper.get("updated", 0)) / 3600
checks.append({"name": "Spielgeld-Daten", "ok": age < 2, "info": f"zuletzt vor {age * 60:.0f} Min aktualisiert"})

try:
    owner, name = REPO.split("/")
    urllib.request.urlopen(f"https://{owner}.github.io/{name}/", timeout=20)
    checks.append({"name": "Jarvis-App online", "ok": True, "info": "erreichbar"})
except Exception as e:
    checks.append({"name": "Jarvis-App online", "ok": False, "info": f"nicht erreichbar ({e})"})

# KI-Motor (Groq) – ohne ihn denken weder App noch Bots
if jlib.GROQ:
    t0 = time.time()
    antwort = ki("Antworte nur mit dem Wort OK.", "Test")
    checks.append({"name": "KI-Motor (Groq)", "ok": bool(antwort), "info": f"antwortet in {time.time() - t0:.1f} s" if antwort else "keine Antwort – Schlüssel/Limit prüfen"})
else:
    checks.append({"name": "KI-Motor (Groq)", "ok": False, "info": "GROQ_KEY fehlt in den GitHub-Secrets"})

probleme = [c for c in checks if not c["ok"]]
alte = {c["name"] for c in old.get("checks", []) if not c["ok"]}
neu = [c for c in probleme if c["name"] not in alte]
if neu:
    tg("🛡️ Jarvis-Wächter:\n" + "\n".join(f"• {c['name']}: {c['info']}" for c in neu))

verlauf = (old.get("verlauf", []) + [{"t": now, "ok": len(checks) - len(probleme), "n": len(checks)}])[-48:]
store("status.json", {"updated": now, "ok": not probleme, "checks": checks, "repariert": repariert, "verlauf": verlauf})
print(f"{len(checks) - len(probleme)}/{len(checks)} ok, repariert: {repariert}")
