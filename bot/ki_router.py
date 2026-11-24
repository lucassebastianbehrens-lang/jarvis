"""KI-Weiche: Wenn Groq ausfällt (Limit, Fehler, kein Schlüssel), weicht Jarvis automatisch auf andere
kostenlose KIs aus – kein Claude-Verbrauch. Reihenfolge (nur Anbieter mit Schlüssel/Adresse werden probiert):
  1. Groq           GROQ_KEY        (läuft schon in jlib/video_auto)
  2. Google Gemini  GEMINI_KEY      kostenloser Schlüssel: https://aistudio.google.com/apikey
  3. OpenRouter     OPENROUTER_KEY  kostenlose Modelle:    https://openrouter.ai/keys
  4. Ollama         OLLAMA_URL      eigene KI auf Laptop/Server, z. B. http://localhost:11434
Modelle lassen sich per GEMINI_MODEL / OPENROUTER_MODEL / OLLAMA_MODEL ändern (Komma-Liste)."""
import json, os, urllib.error, urllib.request

ZAEHLER = {}  # welcher Anbieter wie oft geantwortet hat (steht im Log)


def _liste(env, standard):
    return [m.strip() for m in (os.environ.get(env) or standard).split(",") if m.strip()]


def anbieter():
    """Alle Ausweich-Anbieter, für die ein Schlüssel bzw. eine Adresse da ist: (name, url, schlüssel, modelle)."""
    out = []
    if os.environ.get("GEMINI_KEY"):
        out.append(("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_KEY"], _liste("GEMINI_MODEL", "gemini-flash-latest,gemini-flash-lite-latest")))
    if os.environ.get("OPENROUTER_KEY"):
        out.append(("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_KEY"],
                    _liste("OPENROUTER_MODEL", "openrouter/free,meta-llama/llama-3.3-70b-instruct:free")))
    if os.environ.get("OLLAMA_URL"):
        out.append(("Ollama", os.environ["OLLAMA_URL"].rstrip("/") + "/v1/chat/completions", "ollama",
                    _liste("OLLAMA_MODEL", "qwen3.5:2b")))
    return out


def _post(url, key, body, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), {
        "Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "jarvis-bot",
        "HTTP-Referer": "https://github.com/lucassebastianbehrens-lang/jarvis", "X-Title": "Jarvis"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def weiter(msgs, json_mode=False, temp=None, timeout=150):
    """Fragt der Reihe nach die Ausweich-Anbieter. Rückgabe: Antworttext oder "" wenn keiner kann."""
    for name, url, key, modelle in anbieter():
        for m in modelle:
            body = {"model": m, "messages": msgs}
            if temp is not None:
                body["temperature"] = temp
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            try:
                j = _post(url, key, body, timeout)
                txt = (j["choices"][0]["message"].get("content") or "").strip()
                if txt:
                    ZAEHLER[name] = ZAEHLER.get(name, 0) + 1
                    print(f"KI-Weiche: Antwort von {name} ({m})")
                    return txt
            except urllib.error.HTTPError as e:
                print("KI-Weiche", name, m, e.code, e.read()[:160])
                if e.code in (401, 403):
                    break  # Schlüssel ungültig -> nächster Anbieter
            except Exception as e:
                print("KI-Weiche", name, m, e)
    return ""
