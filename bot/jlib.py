"""Gemeinsame Helfer für Jarvis-Bots (GitHub-API, KI, Telegram, JSON)."""
import json, os, time, urllib.error, urllib.parse, urllib.request
import ki_router

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REPO = os.environ.get("GITHUB_REPOSITORY", "lucassebastianbehrens-lang/jarvis")
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
GROQ = os.environ.get("GROQ_KEY", "")
_GESPERRT = set()
QUELLEN = []  # Quellen der letzten Websuche (titel, url)


def path(*p):
    return os.path.join(ROOT, *p)


def load(name, default):
    try:
        with open(path("data", name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def store(name, obj):
    p = path("data", name)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def http(url, body=None, headers=None, method=None, timeout=60):
    h = {"User-Agent": "jarvis-bot", "Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data, h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw.strip() else {}


def gh(endpoint, body=None, method=None):
    h = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        h["Authorization"] = "Bearer " + GH_TOKEN
    url = endpoint if endpoint.startswith("http") else f"https://api.github.com/{endpoint.lstrip('/')}"
    return http(url, body, h, method)


def runs_since(ts, pages=5):
    """Alle Workflow-Läufe seit Zeitstempel ts (Sekunden)."""
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
    out = []
    for p in range(1, pages + 1):
        j = gh(f"repos/{REPO}/actions/runs?per_page=100&page={p}&created=%3E%3D{iso}")
        out += j.get("workflow_runs", [])
        if len(j.get("workflow_runs", [])) < 100:
            break
    return out


def wf_file(run):
    return os.path.basename(run.get("path", "").split("@")[0])


# Überlebens-Stufe aus dem Automaton (bot/automaton.py): steuert KI-Größe und welche Bots laufen dürfen
NEBENSACHEN = {"recherche", "lage", "video", "videos"}           # pausieren ab „kritisch“
UNVERZICHTBAR = {"waechter", "hintergrund", "ideen", "automaton", "auftraege", "shop_bau"}  # laufen sogar in „ruhe“


def modus():
    return (load("automaton.json", {}) or {}).get("modus", "normal")


def darf_laufen(bot):
    """False, wenn Jarvis gerade spart und dieser Bot warten soll (siehe docs/AUTOMATON.md)."""
    m = modus()
    if m == "kritisch" and bot in NEBENSACHEN or m == "ruhe" and bot not in UNVERZICHTBAR:
        print(f"Überlebensmodus „{m}“: {bot} pausiert, bis wieder Geld im Jarvis-Topf ist.")
        return False
    return True


def ki(system, user, search=False, json_mode=False):
    """KI-Antwort über Groq (mit Websuche), bei Ausfall über die KI-Weiche (ki_router). Ohne jeden Schlüssel: leerer Text."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if GROQ:
        # Websuche: 1) Compound-Systeme, 2) GPT-OSS mit eingebauter Browser-Suche (falls Compound fürs Konto gesperrt ist)
        versuche = ([("groq/compound", {}), ("groq/compound-mini", {}),
                     ("openai/gpt-oss-120b", {"tools": [{"type": "browser_search"}], "tool_choice": "required"}),
                     ("openai/gpt-oss-20b", {"tools": [{"type": "browser_search"}], "tool_choice": "required"})]
                    if search else [("openai/gpt-oss-120b", {}), ("openai/gpt-oss-20b", {}),
                                    ("qwen/qwen3.8-27b", {})])
        if modus() != "normal":  # Sparstufe: großes Modell überspringen
            versuche = [v for v in versuche if "120b" not in v[0]] or versuche
        for m, extra in versuche:
            if m in _GESPERRT:
                continue
            for versuch in range(2):  # bei Rate-Limit kurz warten und einmal wiederholen
              try:
                  body = {"model": m, "messages": msgs, **extra}
                  if json_mode and not search:
                      body["response_format"] = {"type": "json_object"}
                  j = http("https://api.groq.com/openai/v1/chat/completions", body,
                           {"Authorization": "Bearer " + GROQ}, timeout=150)
                  msg = j["choices"][0]["message"]
                  QUELLEN.clear()
                  for t in msg.get("executed_tools") or []:
                      sr = t.get("search_results") or {}
                      for r in (sr.get("results") if isinstance(sr, dict) else sr) or []:
                          if isinstance(r, dict) and r.get("url"):
                              QUELLEN.append({"titel": r.get("title", ""), "url": r["url"]})
                  return (msg.get("content") or "").strip()
              except urllib.error.HTTPError as e:
                  print("Groq", m, e.code, e.read()[:160])
                  if e.code in (403, 404):
                      _GESPERRT.add(m)  # nicht bei jeder Suche erneut probieren
                  if e.code == 429 and versuch == 0:
                      time.sleep(min(30, float(e.headers.get("retry-after") or 12)))
                      continue
                  break
              except Exception as e:
                  print("Groq", m, e)
                  break
    # Groq aus/kein Schlüssel -> KI-Weiche (Gemini, OpenRouter, Ollama). Websuche gibt es dort nicht, also ohne Quellen.
    QUELLEN.clear()
    return ki_router.weiter(msgs, json_mode=json_mode)


def parse_json(text):
    t = text.strip()
    if "```" in t:
        t = t.split("```")[1].lstrip("json").strip()
    a, b = min([i for i in (t.find("{"), t.find("[")) if i >= 0] or [0]), max(t.rfind("}"), t.rfind("]"))
    return json.loads(t[a:b + 1])


def tg(text):
    tok, chat = os.environ.get("TG_TOKEN", ""), os.environ.get("TG_CHAT", "")
    if not (tok and chat):
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900]}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
    except Exception as e:
        print("Telegram", e)
