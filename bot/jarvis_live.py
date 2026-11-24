"""Jarvis live auf dem Server: antwortet in Telegram sofort (rund um die Uhr).
- normale Nachricht  -> KI-Antwort (Groq, bei Limit Pollinations ohne Schlüssel)
- "Idee: …" / 💡     -> wird gespeichert (/var/lib/jarvis/agents/ideen.json, über https abrufbar)
- /status            -> Server- und Bot-Status
- "Erinnere mich …"  -> Erinnerung (in 20 min / um 18 Uhr / morgen 7 Uhr / am 24.12. um 10 Uhr)
- "Merk dir: …"      -> Langzeit-Gedächtnis (fließt in jede Antwort ein), /gedaechtnis, "Vergiss …"
- Sprachnachricht    -> wird abgetippt (Groq Whisper) und wie Text behandelt
- Herzschlag         -> prüft alle 30 Min still Bots/Server und meldet sich nur bei Problemen
- "Such …"           -> Websuche über eigene SearXNG-Suche auf dem Server (kein Schlüssel nötig)
- Foto vom Kassenbon -> Händler/Betrag/Kategorie erkannt, in ausgaben.json gespeichert (/ausgaben)
- "Aufgabe: …"       -> Warteschlange; Jarvis arbeitet sie im Herzschlag selbst ab (Entwürfe, Pläne, Texte) (/aufgaben)
- 👍/👎 unter Antworten -> Jarvis lernt, was dir gefällt
- /hilfe             -> Befehle
Nur Nachrichten aus Lucas' eigenem Chat (TG_CHAT) werden beantwortet.
Konfiguration: /etc/jarvis/telegram.env (TG_TOKEN, TG_CHAT, optional GROQ_KEY)."""
import json, os, re, time, shutil, subprocess, threading, uuid, urllib.request, urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TOKEN, CHAT = os.environ.get("TG_TOKEN", ""), str(os.environ.get("TG_CHAT", ""))
GROQ = os.environ.get("GROQ_KEY", "")
BASE = "/var/lib/jarvis/agents"
F_IDEEN, F_HIST = f"{BASE}/ideen.json", "/var/lib/jarvis/live-verlauf.json"
F_ERI, F_MEM, F_HB = "/var/lib/jarvis/erinnerungen.json", "/var/lib/jarvis/gedaechtnis.json", "/var/lib/jarvis/herzschlag.json"
F_AUS, F_Q, F_LERN = f"{BASE}/ausgaben.json", "/var/lib/jarvis/aufgaben.json", "/var/lib/jarvis/lernen.json"
SEARX = os.environ.get("SEARX_URL", "http://127.0.0.1:8888")
VISION = "qwen/qwen3.8-27b"  # Groq-Bildmodell (llama-4-scout gibt es nicht mehr)
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
    tmp = f"{path}.{threading.get_ident()}.tmp"  # eigene Datei je Helfer, sonst Kollision
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def post_json(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "jarvis-bot", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def ki(msgs):
    if GROQ:
        for model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"):
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
        if n is not None:
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
                                 {"Authorization": "Bearer " + GROQ, "User-Agent": "jarvis-bot", "Content-Type": "multipart/form-data; boundary=" + b})
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
    try:  # liegengebliebene Aufträge (z. B. nach Neustart) an freie Helfer geben
        q = load(F_Q, [])
        for a in q:
            if a["status"] == "in Arbeit" and not _belegt:
                a["status"] = "bereit"
        store(F_Q, q)
        for _ in range(min(3 - len(_belegt), sum(1 for a in q if a["status"] == "bereit"))):
            im_hintergrund("Warteschlange", lambda name: aufgabe_abarbeiten(name))
    except Exception as e:
        print("Warteschlange:", e)
    for k, msg in probleme.items():
        if time.time() - hb["gemeldet"].get(k, 0) > 6 * 3600:
            say("💓 Herzschlag: " + msg)
            hb["gemeldet"][k] = time.time()
    store(F_HB, hb)


# ---------- Websuche (SearXNG) ----------
def websuche(frage):
    url = SEARX + "/search?" + urllib.parse.urlencode({"q": frage, "format": "json", "language": "de"})
    with urllib.request.urlopen(url, timeout=25) as r:
        res = json.load(r).get("results", [])[:6]
    if not res:
        return say("Dazu habe ich nichts gefunden.")
    quellen = "\n".join(f"[{i+1}] {x.get('title','')}: {x.get('content','')[:300]} ({x.get('url','')})" for i, x in enumerate(res))
    ant = ki([{"role": "system", "content": SYSTEM + " Beantworte die Frage NUR mit den Suchergebnissen, nenne Zahlen konkret, markiere Quellen mit [1], [2]. Max. 5 Sätze."},
              {"role": "user", "content": f"Frage: {frage}\n\nSuchergebnisse:\n{quellen}"}])
    links = "\n".join(f"[{i+1}] {x.get('url','')}" for i, x in enumerate(res[:3]))
    say(f"🔎 {ant}\n\n{links}")


# ---------- Kassenbon ----------
def eur(v):
    return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def kassenbon(m):
    if not GROQ:
        return say("Für Kassenbons brauche ich den Groq-Schlüssel auf dem Server.")
    fid = m["photo"][-1]["file_id"]
    path = tg("getFile", file_id=fid)["result"]["file_path"]
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{path}", timeout=60) as r:
        import base64
        b64 = base64.b64encode(r.read()).decode()
    frage = ('Das ist vermutlich ein Kassenbon oder eine Rechnung. Antworte NUR mit JSON: {"bon": true/false, "haendler": "", "betrag": 0.0, "datum": "YYYY-MM-DD", '
             '"kategorie": "Lebensmittel|Auto|Haushalt|Freizeit|Business|Gesundheit|Sonstiges", "posten": ["max 5 wichtigste"]}. Betrag = Gesamtsumme in Euro.')
    j = post_json("https://api.groq.com/openai/v1/chat/completions",
                  {"model": VISION, "response_format": {"type": "json_object"},
                   "messages": [{"role": "user", "content": [{"type": "text", "text": frage},
                                                             {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}]},
                  {"Authorization": "Bearer " + GROQ})
    d = json.loads(j["choices"][0]["message"]["content"])
    if not d.get("bon"):
        return say("Auf dem Foto erkenne ich keinen Kassenbon. Schick mir gern ein schärferes Bild.")
    d["zeit"] = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    aus = load(F_AUS, []) + [d]
    store(F_AUS, aus[-1000:])
    monat = datetime.now(TZ).strftime("%Y-%m")
    summe = sum(float(x.get("betrag") or 0) for x in aus if str(x.get("datum", ""))[:7] == monat)
    betrag = eur(d.get('betrag') or 0)
    say(f"🧾 {d.get('haendler','?')} · {betrag} · {d.get('kategorie','Sonstiges')} – gespeichert.\nAusgaben diesen Monat: {eur(summe)}")


def ausgaben_text():
    aus = load(F_AUS, [])
    monat = datetime.now(TZ).strftime("%Y-%m")
    akt = [x for x in aus if str(x.get("datum", ""))[:7] == monat]
    if not akt:
        return "Diesen Monat noch keine Kassenbons. Schick mir einfach ein Foto."
    kat = {}
    for x in akt:
        kat[x.get("kategorie", "Sonstiges")] = kat.get(x.get("kategorie", "Sonstiges"), 0) + float(x.get("betrag") or 0)
    zeilen = "\n".join(f"• {k}: {eur(v)}" for k, v in sorted(kat.items(), key=lambda a: -a[1]))
    return f"🧾 Ausgaben {monat} ({len(akt)} Bons): {eur(sum(kat.values()))}\n{zeilen}"


# ---------- Aufgaben-Warteschlange ----------
# ---------- Leibgarde: Hintergrund-Helfer nur für Lucas ----------
# Bis zu 3 Aufträge laufen parallel in eigenen Threads – der Chat bleibt immer frei und antwortet sofort.
Q_LOCK, FREI, NAMEN = threading.Lock(), threading.Semaphore(3), ["Ben", "Lea", "Kai"]
_belegt = set()


def im_hintergrund(titel, fn):
    def lauf():
        with FREI:
            with Q_LOCK:
                name = next((n for n in NAMEN if n not in _belegt), "Ben")
                _belegt.add(name)
            try:
                fn(name)
            except Exception as e:
                say(f"⛔ {name}: {titel[:60]} hat nicht geklappt ({e}).")
            finally:
                _belegt.discard(name)
    threading.Thread(target=lauf, daemon=True).start()


def aufgabe_neu(text):
    with Q_LOCK:
      q = load(F_Q, [])
      q.append({"id": uuid.uuid4().hex[:5], "text": text[:1000], "status": "bereit", "zeit": datetime.now(TZ).strftime("%Y-%m-%d %H:%M")})
      store(F_Q, q)
    frei = 3 - len(_belegt)
    say(f"🛡️ {'Ein Helfer fängt sofort an' if frei > 0 else 'Alle 3 Helfer sind beschäftigt – deiner ist als Nächstes dran'}. "
        "Du kannst mir währenddessen ganz normal weiter schreiben.")
    im_hintergrund(text, lambda name: aufgabe_abarbeiten(name))


def aufgabe_abarbeiten(name="Jarvis"):
    with Q_LOCK:
        q = load(F_Q, [])
        a = next((x for x in q if x["status"] == "bereit"), None)
        if not a:
            return
        a["status"] = "in Arbeit"
        store(F_Q, q)
    for _ in [a]:
            try:
                erg = ki([{"role": "system", "content": SYSTEM + gedaechtnis_text() + lern_text() +
                           " Du arbeitest eine Aufgabe aus der Warteschlange selbstständig ab. Liefere ein fertiges, direkt nutzbares Ergebnis "
                           "(Entwurf, Plan, Text, Liste). Was du nicht selbst tun darfst (senden, bezahlen, veröffentlichen), bereitest du nur vor und schreibst am Ende „👉 Du musst: …“."},
                          {"role": "user", "content": a["text"]}])
                status, extra = "fertig", {"ergebnis": erg[:6000]}
                say(f"✅ {name} ist fertig: {a['text'][:80]}\n\n{erg}")
            except Exception as e:
                status, extra = "blockiert", {"fehler": str(e)[:200]}
                say(f"⛔ {name}: Aufgabe blockiert: {a['text'][:80]} ({e})")
            with Q_LOCK:  # frisch laden – andere Helfer haben die Datei inzwischen evtl. geändert
                q = load(F_Q, [])
                for x in q:
                    if x["id"] == a["id"]:
                        x["status"] = status
                        x.update(extra)
                store(F_Q, q[-100:])
            return


def aufgaben_text():
    q = load(F_Q, [])
    sym = {"bereit": "⏳", "in Arbeit": "⚙️", "fertig": "✅", "blockiert": "⛔"}
    offen = [a for a in q if a["status"] != "fertig"] + [a for a in q if a["status"] == "fertig"][-3:]
    return "\n".join(f"{sym.get(a['status'], '•')} {a['text'][:70]}" for a in offen) or "Keine Aufgaben. Schreib „Aufgabe: …“."


# ---------- Lernen aus 👍/👎 ----------
def lern_text():
    l = load(F_LERN, [])
    gut = [x["a"][:120] for x in l if x["ok"]][-5:]
    schlecht = [x["a"][:120] for x in l if not x["ok"]][-5:]
    t = ""
    if gut:
        t += " Antworten wie diese fand Lucas gut: " + " | ".join(gut) + "."
    if schlecht:
        t += " Antworten wie diese fand er schlecht – mach es anders (kürzer/konkreter): " + " | ".join(schlecht) + "."
    return t


def feedback(cb):
    ok = cb.get("data") == "gut"
    text = (cb.get("message") or {}).get("text", "")
    l = load(F_LERN, []) + [{"ok": ok, "a": text[:300]}]
    store(F_LERN, l[-100:])
    tg("answerCallbackQuery", callback_query_id=cb["id"], text="Danke, gemerkt 👍" if ok else "Verstanden – mache ich besser 👎")
    try:
        tg("editMessageReplyMarkup", chat_id=CHAT, message_id=cb["message"]["message_id"], reply_markup='{"inline_keyboard":[]}')
    except Exception:
        pass


def sprechen(text):
    """Antwort als Sprachnachricht mit natürlicher Microsoft-Neural-Stimme (edge-tts, kostenlos)."""
    import tempfile
    d = tempfile.mkdtemp()
    t = re.sub(r"https?://\S+", "Link", text)[:1500]
    subprocess.run(["edge-tts", "--voice", os.environ.get("JARVIS_VOICE", "de-DE-SeraphinaMultilingualNeural"), "--rate", "+5%",
                    "--text", t, "--write-media", f"{d}/a.mp3"], check=True, timeout=90)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/a.mp3", "-c:a", "libopus", "-b:a", "48k", f"{d}/a.ogg"], check=True, timeout=60)
    b = "----jv" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{CHAT}\r\n--{b}\r\n"
            f"Content-Disposition: form-data; name=\"voice\"; filename=\"a.ogg\"\r\nContent-Type: audio/ogg\r\n\r\n").encode() + open(f"{d}/a.ogg", "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendVoice", body, {"Content-Type": "multipart/form-data; boundary=" + b})
    urllib.request.urlopen(req, timeout=60).read()


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
    if m.get("photo") and not txt:
        try:
            return kassenbon(m)
        except Exception as e:
            return say(f"Den Bon konnte ich nicht lesen ({e}).")
    v = m.get("voice") or m.get("audio")
    if v and not txt:
        try:
            txt = abtippen(v["file_id"]) or ""
        except Exception as e:
            print("Whisper:", e)
        if not txt:
            return say("Sprachnachrichten kann ich erst abtippen, wenn ein Groq-Schlüssel auf dem Server hinterlegt ist." if not GROQ else "Ich konnte die Sprachnachricht nicht verstehen.")
        say("🎙 " + txt)
        m["_stimme"] = True
    if not txt:
        return say("Ich verstehe bisher nur Text. Schreib mir einfach.")
    low = txt.lower()
    if low.startswith("/start") or low.startswith("/hilfe") or low == "hilfe":
        return say("Jarvis ist live 🟢\n• Schreib mir einfach – ich antworte sofort\n• „Idee: …“ speichert eine Idee (landet nachts in Obsidian)\n• /status – Server & Bots\n• „Erinnere mich morgen um 7 an …“ · /erinnerungen\n• „Merk dir: …“ · /gedaechtnis · „Vergiss …“\n• Sprachnachrichten gehen auch 🎙\n• „Such …“ – Websuche\n• Foto vom Kassenbon · /ausgaben\n• „Aufgabe: …“ – meine Hintergrund-Helfer (bis zu 3 parallel) erledigen es, du kannst weiter schreiben · /aufgaben")
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
    if low.startswith("/ausgaben"):
        return say(ausgaben_text())
    if low.startswith("/aufgaben"):
        return say(aufgaben_text())
    m4 = re.match(r"^\s*(?:/aufgabe|aufgabe)\s*[:\-]?\s*(.+)", txt, re.I | re.S)
    if m4:
        return aufgabe_neu(m4.group(1).strip())
    m5 = re.match(r"^\s*(?:/such(?:e)?|such(?:e)?(?:\s+mal)?|google)\s*[:\-]?\s*(.+)", txt, re.I | re.S)
    if m5:
        frage = m5.group(1).strip()
        say("🔎 Ich suche im Hintergrund – schreib ruhig weiter.")
        return im_hintergrund(frage, lambda name: websuche(frage))
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
    msgs = [{"role": "system", "content": SYSTEM + f" Jetzt ist {jetzt}." + gedaechtnis_text() + lern_text()}] + hist + [{"role": "user", "content": txt}]
    try:
        tg("sendChatAction", chat_id=CHAT, action="typing")
        ant = ki(msgs)
    except Exception as e:
        ant = f"Die KI ist gerade nicht erreichbar ({e}). Versuch es gleich nochmal."
    if m.get("_stimme"):
        try:
            sprechen(ant)
        except Exception as e:
            print("Stimme:", e)
    tg("sendMessage", chat_id=CHAT, text=ant[:3900],
       reply_markup='{"inline_keyboard":[[{"text":"👍","callback_data":"gut"},{"text":"👎","callback_data":"schlecht"}]]}')
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
            res = tg("getUpdates", offset=off, timeout=20, allowed_updates='["message","callback_query"]')
            for u in res.get("result", []):
                off = u["update_id"] + 1
                cb = u.get("callback_query")
                if cb and str((cb.get("message") or {}).get("chat", {}).get("id")) == CHAT:
                    try:
                        feedback(cb)
                    except Exception as e:
                        print("Feedback:", e)
                    continue
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
