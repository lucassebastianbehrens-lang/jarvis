"""Jarvis live auf dem Server: antwortet in Telegram sofort (rund um die Uhr).
- normale Nachricht  -> KI-Antwort (Groq, bei Limit Pollinations ohne Schlüssel)
- "Idee: …" / 💡     -> wird gespeichert (/var/lib/jarvis/agents/ideen.json, über https abrufbar)
- /status            -> Server- und Bot-Status
- /hilfe             -> Befehle
Nur Nachrichten aus Lucas' eigenem Chat (TG_CHAT) werden beantwortet.
Konfiguration: /etc/jarvis/telegram.env (TG_TOKEN, TG_CHAT, optional GROQ_KEY)."""
import json, os, re, time, shutil, subprocess, urllib.request, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN, CHAT = os.environ.get("TG_TOKEN", ""), str(os.environ.get("TG_CHAT", ""))
GROQ = os.environ.get("GROQ_KEY", "")
BASE = "/var/lib/jarvis/agents"
F_IDEEN, F_HIST = f"{BASE}/ideen.json", "/var/lib/jarvis/live-verlauf.json"
TZ = ZoneInfo("Europe/Berlin")
PAT = re.compile(r"^\s*(?:💡|/idee(?:@\w+)?|idee)\s*[:\-–]?\s*", re.I)
SYSTEM = ("Du bist Jarvis, der persönliche Assistent von Lucas. Antworte immer auf Deutsch, kurz und konkret "
          "(höchstens 6 Sätze), Beträge in Euro. Lucas arbeitet im Schichtdienst und baut nebenbei drei Geschäfte auf: "
          "KC 'Handwerk sichtbar' (Social Media für Handwerker), ET 'Finanz-Vorlagen' (Etsy) und TT 'Früchte-Drama' "
          "(KI-Miniserie auf TikTok). Du bewegst kein echtes Geld, veröffentlichst nichts und schreibst keinen Fremden – "
          "dafür braucht es immer Lucas' Ja.")


def tg(method, **p):
    data = urllib.parse.urlencode(p).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{method}", data, timeout=70) as r:
        return json.load(r)


def say(text):
    for i in range(0, len(text), 3900):
        tg("sendMessage", chat_id=CHAT, text=text[i:i + 3900])


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def store(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def post_json(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def ki(msgs):
    if GROQ:
        for model in ("openai/gpt-oss-120b", "llama-3.1-8b-instant"):
            try:
                j = post_json("https://api.groq.com/openai/v1/chat/completions",
                              {"model": model, "messages": msgs}, {"Authorization": "Bearer " + GROQ})
                return j["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print("Groq:", model, e)
    j = post_json("https://text.pollinations.ai/openai", {"model": "openai", "messages": msgs}, {})
    return j["choices"][0]["message"]["content"].strip()


def status():
    du = shutil.disk_usage("/")
    up = subprocess.run(["uptime", "-p"], capture_output=True, text=True).stdout.strip()
    svc = lambda n: subprocess.run(["systemctl", "is-active", n], capture_output=True, text=True).stdout.strip()
    ft = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout
    return (f"🖥 Server {up}\n💾 frei: {du.free // 2**30} GB von {du.total // 2**30} GB\n"
            f"🤖 Agenten-Bot: {svc('jarvis-agents')}\n📈 Freqtrade: {'läuft' if 'freqtrade' in ft else 'aus'}\n"
            f"💬 Jarvis live: aktiv\n💡 Ideen gespeichert: {len(load(F_IDEEN, []))}")


def handle(m):
    txt = (m.get("text") or m.get("caption") or "").strip()
    if not txt:
        return say("Ich verstehe bisher nur Text. Schreib mir einfach.")
    low = txt.lower()
    if low.startswith("/start") or low.startswith("/hilfe") or low == "hilfe":
        return say("Jarvis ist live 🟢\n• Schreib mir einfach – ich antworte sofort\n• „Idee: …“ speichert eine Idee (landet nachts in Obsidian)\n• /status – Server & Bots")
    if low.startswith("/status"):
        return say(status())
    if PAT.match(txt):
        idee = PAT.sub("", txt, count=1).strip()
        if not idee:
            return say("Schreib die Idee direkt dahinter, z. B. „Idee: Gino bekommt einen Zwillingsbruder“.")
        ideen = load(F_IDEEN, [])
        ideen.append({"id": m["message_id"], "zeit": datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), "text": idee[:2000], "vault": False})
        store(F_IDEEN, ideen[-300:])
        return say("📥 Idee gespeichert – landet heute Nacht in deinem Obsidian (00 Inbox).")
    hist = load(F_HIST, [])[-10:]
    jetzt = datetime.now(TZ).strftime("%A, %d.%m.%Y %H:%M")
    msgs = [{"role": "system", "content": SYSTEM + f" Jetzt ist {jetzt}."}] + hist + [{"role": "user", "content": txt}]
    try:
        tg("sendChatAction", chat_id=CHAT, action="typing")
        ant = ki(msgs)
    except Exception as e:
        ant = f"Die KI ist gerade nicht erreichbar ({e}). Versuch es gleich nochmal."
    say(ant)
    store(F_HIST, (hist + [{"role": "user", "content": txt}, {"role": "assistant", "content": ant}])[-20:])


def main():
    if not TOKEN or not CHAT:
        print("TG_TOKEN/TG_CHAT fehlen in /etc/jarvis/telegram.env – warte.")
        time.sleep(600)
        return
    os.makedirs(BASE, exist_ok=True)
    try:
        tg("deleteWebhook")
        say("🟢 Jarvis läuft jetzt auf deinem Server und antwortet sofort. /hilfe zeigt die Befehle.")
    except Exception as e:
        print("Start:", e)
    off = 0
    while True:
        try:
            res = tg("getUpdates", offset=off, timeout=50, allowed_updates='["message"]')
            for u in res.get("result", []):
                off = u["update_id"] + 1
                m = u.get("message") or {}
                if str(m.get("chat", {}).get("id")) == CHAT:
                    try:
                        handle(m)
                    except Exception as e:
                        print("Fehler:", e)
        except Exception as e:
            print("Telegram:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
