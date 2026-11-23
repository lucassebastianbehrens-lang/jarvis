"""Jarvis live auf dem Server: antwortet in Telegram sofort (rund um die Uhr).
- normale Nachricht  -> KI-Antwort (Groq, bei Limit Pollinations ohne Schlüssel)
- "Idee: …" / 💡     -> wird gespeichert (/var/lib/jarvis/agents/ideen.json, über https abrufbar)
- /status            -> Server- und Bot-Status
- "Erinnere mich …"  -> Erinnerung (in 20 min / um 18 Uhr / morgen 7 Uhr / am 24.12. um 10 Uhr)
- "Merk dir: …"      -> Langzeit-Gedächtnis (fließt in jede Antwort ein), /gedaechtnis, "Vergiss …"
- Sprachnachricht    -> wird abgetippt (Groq Whisper) und wie Text behandelt
- Herzschlag         -> prüft alle 30 Min still Bots/Server und meldet sich nur bei Problemen
- /hilfe             -> Befehle
Nur Nachrichten aus Lucas' eigenem Chat (TG_CHAT) werden beantwortet.
Konfiguration: /etc/jarvis/telegram.env (TG_TOKEN, TG_CHAT, optional GROQ_KEY)."""
import json, os, re, time, shutil, subprocess, uuid, urllib.request, urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TOKEN, CHAT = os.environ.get("TG_TOKEN", ""), str(os.environ.get("TG_CHAT", ""))
GROQ = os.environ.get("GROQ_KEY", "")
BASE = "/var/lib/jarvis/agents"
F_IDEEN, F_HIST = f"{BASE}/ideen.json", "/var/lib/jarvis/live-verlauf.json"
F_ERI, F_MEM, F_HB = "/var/lib/jarvis/erinnerungen.json", "/var/lib/jarvis/gedaechtnis.json", "/var/lib/jarvis/herzschlag.json"
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


# ---------- Erinnerungen ----------
WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
fmt = lambda d: f"{WT[d.weekday()]} {d.strftime('%d.%m. um %H:%M')}"
WORT = {"eins": 1, "einer": 1, "einem": 1, "zwei": 2, "drei": 3, "fünf": 5, "zehn": 10, "zwanzig": 20, "dreißig": 30, "halbe": 0.5}


def parse_zeit(txt):
    """gibt (datetime, rest_text) oder (None, txt) zurück"""
    now, t = datetime.now(TZ), txt.lower()
    m = re.search(r"in (\d+|\w+)\s*(min(?:uten|ute)?|std|stunden?|h|tag(?:en|e)?)\b", t)
    if m:
        n = float(m.group(1)) if m.group(1).isdigit() else WORT.get(m.group(1))
        if n:
            e = m.group(2)
            d = timedelta(minutes=n) if e.startswith("min") else timedelta(days=n) if e.startswith("tag") else timedelta(hours=n)
            return now + d, txt[:m.start()] + txt[m.end():]
    tag = None
    m = re.search(r"am (\d{1,2})\.(\d{1,2})\.?(\d{2,4})?", t)
    if m:
        y = int(m.group(3)) if m.group(3) else now.year
        y = y + 2000 if y < 100 else y
        tag = datetime(y, int(m.group(2)), int(m.group(1)), 9, 0, tzinfo=TZ)
        if not m.group(3) and tag < now - timedelta(days=1):
            tag = tag.replace(year=y + 1)
        txt_t = txt[:m.start()] + txt[m.end():]
    elif "übermorgen" in t:
        tag, txt_t = (now + timedelta(days=2)).replace(hour=9, minute=0), txt.replace("übermorgen", "").replace("Übermorgen", "")
    elif "morgen" in t:
        tag, txt_t = (now + timedelta(days=1)).replace(hour=9, minute=0), re.sub(r"[Mm]orgen", "", txt, count=1)
    else:
        txt_t = txt
    m = re.search(r"um (\d{1,2})(?::|\.)?(\d{2})?\s*(?:uhr)?", txt_t.lower())
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        base = tag or now
        z = base.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
        if not tag and z <= now:
            z += timedelta(days=1)
        return z, txt_t[:m.start()] + txt_t[m.end():]
    if tag:
        return tag.replace(second=0, microsecond=0), txt_t
    return None, txt


def erinnerung(txt):
    rest = re.sub(r"^\s*(?:bitte\s+)?erinnere?\s+mich\s*", "", txt, flags=re.I)
    zeit, rest = parse_zeit(rest)
    if not zeit:
        return say("Wann soll ich dich erinnern? z. B. „Erinnere mich in 20 Minuten an …“, „um 18 Uhr …“, „morgen um 7 …“ oder „am 24.12. um 10 Uhr …“.")
    rest = re.sub(r"^\s*(?:daran,?\s*)?(?:dass|an|zu)\s+", "", rest.strip(" ,.:"), flags=re.I).strip() or "(ohne Text)"
    eri = load(F_ERI, [])
    eri.append({"id": uuid.uuid4().hex[:6], "zeit": zeit.isoformat(), "text": rest})
    store(F_ERI, eri)
    say(f"⏰ Okay – {fmt(zeit)}: {rest}")


def erinnerungen_faellig():
    eri, jetzt, rest = load(F_ERI, []), datetime.now(TZ), []
    for e in eri:
        if datetime.fromisoformat(e["zeit"]) <= jetzt:
            say("⏰ Erinnerung: " + e["text"])
        else:
            rest.append(e)
    if len(rest) != len(eri):
        store(F_ERI, rest)


# ---------- Gedächtnis ----------
def gedaechtnis_text():
    mem = load(F_MEM, [])
    return (" Das sollst du dir über Lucas merken: " + "; ".join(mem[-40:]) + ".") if mem else ""


# ---------- Sprachnachrichten ----------
def abtippen(file_id):
    if not GROQ:
        return None
    path = tg("getFile", file_id=file_id)["result"]["file_path"]
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{path}", timeout=60) as r:
        audio = r.read()
    b = "----jarvis" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-large-v3-turbo\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\nde\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sprache.ogg\"\r\nContent-Type: audio/ogg\r\n\r\n").encode() + audio + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", body,
                                 {"Authorization": "Bearer " + GROQ, "Content-Type": "multipart/form-data; boundary=" + b})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r).get("text", "").strip()


# ---------- Herzschlag ----------
def herzschlag():
    hb = load(F_HB, {"t": 0, "gemeldet": {}})
    if time.time() - hb["t"] < 1800:
        return
    hb["t"] = time.time()
    probleme = {}
    if subprocess.run(["systemctl", "is-active", "jarvis-agents"], capture_output=True, text=True).stdout.strip() != "active":
        probleme["agents"] = "🤖 Der Agenten-Bot läuft nicht. Ich starte ihn neu."
        subprocess.run(["systemctl", "restart", "jarvis-agents"])
    if "freqtrade" not in subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout:
        probleme["ft"] = "📈 Freqtrade läuft nicht. Ich starte ihn neu."
        subprocess.run(["docker", "compose", "up", "-d"], cwd="/root/ft")
    du = shutil.disk_usage("/")
    if du.free / du.total < 0.1:
        probleme["disk"] = f"💾 Festplatte fast voll: nur noch {du.free // 2**30} GB frei."
    for k, msg in probleme.items():
        if time.time() - hb["gemeldet"].get(k, 0) > 6 * 3600:
            say("💓 Herzschlag: " + msg)
            hb["gemeldet"][k] = time.time()
    store(F_HB, hb)


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
    v = m.get("voice") or m.get("audio")
    if v and not txt:
        try:
            txt = abtippen(v["file_id"]) or ""
        except Exception as e:
            print("Whisper:", e)
        if not txt:
            return say("Sprachnachrichten kann ich erst abtippen, wenn ein Groq-Schlüssel auf dem Server hinterlegt ist." if not GROQ else "Ich konnte die Sprachnachricht nicht verstehen.")
        say("🎙 " + txt)
    if not txt:
        return say("Ich verstehe bisher nur Text. Schreib mir einfach.")
    low = txt.lower()
    if low.startswith("/start") or low.startswith("/hilfe") or low == "hilfe":
        return say("Jarvis ist live 🟢\n• Schreib mir einfach – ich antworte sofort\n• „Idee: …“ speichert eine Idee (landet nachts in Obsidian)\n• /status – Server & Bots\n• „Erinnere mich morgen um 7 an …“ · /erinnerungen\n• „Merk dir: …“ · /gedaechtnis · „Vergiss …“\n• Sprachnachrichten gehen auch 🎙")
    if low.startswith("/status"):
        return say(status())
    if re.match(r"^\s*(?:bitte\s+)?erinnere?\s+mich", low):
        return erinnerung(txt)
    if low.startswith("/erinnerungen"):
        eri = sorted(load(F_ERI, []), key=lambda e: e["zeit"])
        return say("\n".join(f"⏰ {fmt(datetime.fromisoformat(e['zeit']))} – {e['text']}" for e in eri) or "Keine offenen Erinnerungen.")
    m2 = re.match(r"^\s*merk\s*dir\s*[:,]?\s*(.+)", txt, re.I | re.S)
    if m2:
        mem = load(F_MEM, []) + [m2.group(1).strip()[:300]]
        store(F_MEM, mem[-60:])
        return say("🧠 Gemerkt.")
    if low.startswith("/gedaechtnis") or low.startswith("/gedächtnis"):
        return say("🧠 Das weiß ich über dich:\n" + "\n".join("• " + x for x in load(F_MEM, [])) if load(F_MEM, []) else "Noch nichts gemerkt. Schreib „Merk dir: …“.")
    m3 = re.match(r"^\s*vergiss\s+(.+)", txt, re.I)
    if m3:
        w = m3.group(1).strip(" .!").lower()
        mem = load(F_MEM, [])
        neu = [x for x in mem if w not in x.lower()]
        store(F_MEM, neu)
        return say(f"🗑 {len(mem) - len(neu)} Eintrag/Einträge vergessen." if len(neu) != len(mem) else "Dazu habe ich nichts gespeichert.")
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
    msgs = [{"role": "system", "content": SYSTEM + f" Jetzt ist {jetzt}." + gedaechtnis_text()}] + hist + [{"role": "user", "content": txt}]
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
            erinnerungen_faellig()
            herzschlag()
            res = tg("getUpdates", offset=off, timeout=20, allowed_updates='["message"]')
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
