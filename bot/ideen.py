"""Ideen-Eingang: liest neue Telegram-Nachrichten an den Jarvis-Bot.
Nachrichten, die mit "Idee", "/idee" oder 💡 beginnen, landen in data/ideen.json.
Der nächtliche Autopilot überträgt neue Ideen ins Obsidian-Vault (00 Inbox)."""
import json, os, re, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

TOKEN, CHAT = os.environ.get("TG_TOKEN", ""), str(os.environ.get("TG_CHAT", ""))
F_IDEEN, F_OFF = "data/ideen.json", "data/tg_offset.json"
BERLIN = timezone(timedelta(hours=1))
PAT = re.compile(r"^\s*(?:💡|/idee(?:@\w+)?|idee)\s*[:\-–]?\s*", re.I)


def api(method, **p):
    data = urllib.parse.urlencode(p).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{method}", data, timeout=20) as r:
        return json.load(r)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    if not TOKEN or not CHAT:
        print("TG_TOKEN/TG_CHAT fehlen")
        return
    off = load(F_OFF, {"offset": 0})
    ideen = load(F_IDEEN, [])
    res = api("getUpdates", offset=off["offset"], timeout=0, allowed_updates='["message"]')
    neu = 0
    for u in res.get("result", []):
        off["offset"] = u["update_id"] + 1
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != CHAT:
            continue  # nur Lucas' eigener Chat
        txt = (m.get("text") or m.get("caption") or "").strip()
        if not txt or txt.startswith("/start"):
            continue
        if PAT.match(txt):
            idee = PAT.sub("", txt, count=1).strip()
            if not idee:
                api("sendMessage", chat_id=CHAT, text="Schreib die Idee direkt dahinter, z. B. „Idee: Gino bekommt einen Zwillingsbruder“.")
                continue
            ts = datetime.fromtimestamp(m.get("date", time.time()), BERLIN)
            ideen.append({"id": u["update_id"], "zeit": ts.strftime("%Y-%m-%d %H:%M"), "text": idee[:2000], "vault": False})
            neu += 1
            api("sendMessage", chat_id=CHAT, text="📥 Idee gespeichert – landet heute Nacht in deinem Obsidian (00 Inbox).")
        else:
            api("sendMessage", chat_id=CHAT, text="Ich speichere hier Ideen: schreib „Idee: …“ oder 💡 davor. Für alles andere nutz die Jarvis-App.")
    with open(F_OFF, "w", encoding="utf-8") as f:
        json.dump(off, f)
    with open(F_IDEEN, "w", encoding="utf-8") as f:
        json.dump(ideen[-300:], f, ensure_ascii=False, indent=1)
    print(f"{neu} neue Idee(n)")


if __name__ == "__main__":
    main()
