"""Jarvis-App: kompletter Klick-Test im echten Browser (Handy-Größe), ohne Internet.
Alle Fremd-Dienste (Groq, GitHub, Daten) werden nachgestellt. Start: python3 tests/test_app.py
Endet mit Fehlercode, sobald etwas nicht stimmt – dann wird nichts veröffentlicht."""
import asyncio, base64, json, os, pathlib, sys, time
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAGE = (ROOT / "tests" / "beispiel-lage.json").read_text()
TYP = {".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"}
APP = "<!doctype html><html><body onload=\"localStorage.setItem('a',1)\"><h1 id=x>Rechner OK</h1><script>x.textContent+=' ✓'</script></body></html>"
fehler, ok = [], []
dispatched, t_disp = [], [0]


def check(name, bedingung, info=""):
    (ok if bedingung else fehler).append(name)
    print(("✓ " if bedingung else "✕ ") + name + (f" – {info}" if info and not bedingung else ""))


def antwort(body):
    sysm, last = body["messages"][0]["content"], body["messages"][-1]["content"]
    if "Frontend-Entwickler" in sysm: return "```html\n" + APP + "\n```"
    if "WhatsApp" in sysm: return "Guten Tag Herr Müller, willkommen an Bord! Ich freue mich auf die Zusammenarbeit. Viele Grüße, Lucas"
    if "Hintergrund-Helfer" in sysm: return "**Fertig recherchiert.**\n- Punkt A https://example.org/a"
    if "Call mit" in last: return "1. Wer ist das?\n- Malerbetrieb in Magdeburg"
    if "Steuerberater" in last: return "Lea kümmert sich darum.\n[[HINTERGRUND: Recherchiere Steuerberater in Oschersleben]]"
    if "Zinsrechner" in last: return "Mach ich.\n[[BAUEN: Ein Zinsrechner]]"
    if "Liste" in last: return "## Überschrift\nHier ist **fett** und `code`:\n- eins\n- zwei\n1. erstens\n\nLink: https://tagesschau.de/x"
    return "Alles klar, Lucas."


async def route(r):
    u = r.request.url
    if u.startswith("http://local/"):
        f = ROOT / (u[len("http://local/"):].split("?")[0] or "index.html")
        if not f.exists():
            return await r.fulfill(status=404, body="")
        return await r.fulfill(body=f.read_bytes(), content_type=TYP.get(f.suffix, "application/octet-stream"))
    if "raw.githubusercontent" in u:
        n = u.split("/data/")[1].split("?")[0]
        if n == "automaton.json":
            return await r.fulfill(body=json.dumps({"modus": "sparsam", "topf": 31.5, "reichweite_tage": 100, "einnahmen_30t": 42, "einnahmen_gesamt": 42,
                "kosten": {"server_monat": 9.5}, "updated": int(time.time()), "paypal": {"verbunden": True, "kontostand": 120},
                "vorschlag": {"name": "Bea", "rolle": "bauer", "auftrag": "Shop für Haushaltsbücher", "warum": "digital", "budget": 9},
                "kinder": [{"id": "K-AB12", "name": "Kai", "rolle": "vermarkter", "status": "lebt", "einnahmen": 5, "ausgegeben": 1, "budget": 8, "schritte": [{"text": "Video geplant"}]}],
                "log": [{"t": int(time.time()), "text": "Stufe normal → sparsam"}]}), content_type="application/json")
        if n == "lage.json":
            return await r.fulfill(body=LAGE, content_type="application/json")
        f = ROOT / "data" / n
        return await r.fulfill(body=f.read_bytes() if f.exists() else "null", status=200 if f.exists() else 404)
    if "api.github.com" in u:
        if "/dispatches" in u:
            dispatched.append(json.loads(r.request.post_data)); t_disp[0] = time.time()
            return await r.fulfill(status=204, body="")
        if "/contents/data/hintergrund/" in u and dispatched and time.time() - t_disp[0] > 1:
            d = {"antwort": "**5 Steuerberater gefunden.**\n- Kanzlei X – https://x.de", "quellen": ["https://x.de"]}
            return await r.fulfill(body=json.dumps({"content": base64.b64encode(json.dumps(d).encode()).decode()}), content_type="application/json")
        if "/contents/" in u:
            return await r.fulfill(status=404, body="{}")
        return await r.fulfill(body='{"workflow_runs":[]}', content_type="application/json")
    if "api.groq.com" in u:
        body = json.loads(r.request.post_data); txt = antwort(body)
        if body.get("stream"):
            sse = "".join("data: " + json.dumps({"choices": [{"delta": {"content": txt[i:i + 12]}}]}) + "\n\n" for i in range(0, len(txt), 12))
            return await r.fulfill(body=sse + "data: [DONE]\n\n", content_type="text/event-stream")
        return await r.fulfill(body=json.dumps({"choices": [{"message": {"content": txt, "executed_tools": [{"search_results": {"results": [{"title": "T", "url": "https://quelle.de/a"}]}}]}}]}), content_type="application/json")
    return await r.abort()


async def main():
    async with async_playwright() as p:
        exe = os.environ.get("CHROME")
        b = await p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
        await ctx.add_init_script("if(window===top){if(!localStorage.jv_cfg)localStorage.setItem('jv_cfg',JSON.stringify({groq:'gsk_test',gh:'ghp_test'}));window.speechSynthesis&&(speechSynthesis.speak=()=>{})}")
        await ctx.route("**/*", route)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto("http://local/index.html"); await pg.wait_for_timeout(1500)
        check("App startet ohne Fehler", not errs, "; ".join(errs))
        check("Begrüßung sichtbar", await pg.locator(".msg.ai").count() >= 1)
        check("Design geladen", await pg.evaluate("getComputedStyle(document.body).backgroundColor") != "rgba(0, 0, 0, 0)")

        # Chat: Streaming + Markdown
        await pg.fill("#inp", "Gib mir eine Liste"); await pg.click("#send"); await pg.wait_for_timeout(1200)
        h = await pg.locator(".msg.ai").last.inner_html()
        check("Chat: Markdown (Liste, fett, Code, Link)", all(x in h for x in ["<ul>", "<b>fett</b>", "<code>code</code>", "tagesschau.de"]), h[:120])
        # Websuche mit Quellen
        await pg.fill("#inp", "Was kostet heute Sprit?"); await pg.click("#send"); await pg.wait_for_timeout(1200)
        check("Websuche zeigt Quellen", await pg.locator(".msg.ai").last.locator(".quellen a").count() >= 1)

        # Lage
        await pg.click("nav button[data-t=lage]"); await pg.wait_for_timeout(1200)
        check("Lage: Länder-Knöpfe", await pg.locator("#lands button").count() >= 4)
        await pg.click("#lands button[data-land=USA]"); await pg.wait_for_timeout(300)
        check("Lage: Land wählen zeigt Meldungen", "Fed" in await pg.inner_text("#news"))
        check("Lage: Märkte", await pg.locator("#mkt div").count() >= 3)
        await pg.click("nav button[data-t=stadt]"); await pg.wait_for_timeout(500)
        check("KI-Stadt zeichnet", await pg.evaluate("document.querySelector('#cityCv').width>0"))
        await pg.click("nav button[data-t=jarvis]")

        # Automaton: Topf, Stufe, Kinder, Klonen nur per Ja
        await pg.click("nav button[data-t=trading]"); await pg.wait_for_timeout(400)
        a = await pg.inner_text("#automaton")
        check("Automaton: Topf + Stufe + Kind sichtbar", all(x in a for x in ["31,50", "Sparsam", "Kai"]), a[:200])
        await pg.click("[data-klon=ja]"); await pg.wait_for_timeout(400)
        check("Automaton: Ja startet Klonen", dispatched and dispatched[-1].get("inputs", {}).get("aktion") == "ja", str(dispatched[-1:]))
        dispatched.clear()
        await pg.click("nav button[data-t=jarvis]")

        # Kunden-Onboarding
        await pg.click("#tKunde"); await pg.fill("#kFirma", "Tischlerei Müller"); await pg.fill("#kPreis", "290"); await pg.fill("#kTel", "0171 2345678")
        await pg.click("#kGo"); await pg.wait_for_selector("dialog.fx", timeout=10000)
        check("Onboarding: Feier erscheint", True)
        await pg.wait_for_timeout(4500)
        check("Onboarding: 100 %", (await pg.inner_text("#kPct")).startswith("100"))
        wa = await pg.locator("#kSteps a[href*='wa.me']").get_attribute("href")
        check("Onboarding: WhatsApp-Link mit +49", wa.startswith("https://wa.me/49171"), wa)
        async with pg.expect_download() as d:
            await pg.click("#ks3 button")
        check("Onboarding: Kalender-Datei", "BEGIN:VEVENT" in open(await (await d.value).path()).read())
        await pg.evaluate("document.querySelector('#dlgKunde').close()")

        # Call-Vorbereitung
        await pg.click("#tCall"); await pg.fill("#cWer", "Frau Schulz"); await pg.click("#cGo")
        await pg.wait_for_selector("#cOut:not([hidden])", timeout=8000)
        async with pg.expect_download() as d:
            await pg.click("#cIcs")
        check("Call: Wecker 5 Min vorher", "TRIGGER:-PT5M" in open(await (await d.value).path()).read())
        await pg.evaluate("document.querySelector('#dlgCall').close()")

        # Werkstatt über Chat
        await pg.fill("#inp", "Baue mir einen Zinsrechner"); await pg.click("#send")
        await pg.wait_for_selector("#bFrame:not([hidden])", timeout=10000); await pg.wait_for_timeout(800)
        check("Werkstatt baut App (abgeschirmt, mit Speicher-Ersatz)", "✓" in await pg.frame_locator("#bFrame").locator("#x").inner_text())
        await pg.evaluate("document.querySelector('#dlgBau').close()")

        # Leibgarde
        await pg.fill("#inp", "Such mir Steuerberater"); await pg.click("#send"); await pg.wait_for_timeout(1200)
        check("Leibgarde: Auftrag an GitHub", bool(dispatched) and "Steuerberater" in dispatched[-1]["inputs"]["aufgabe"])
        await pg.fill("#inp", "Hallo"); await pg.click("#send"); await pg.wait_for_timeout(1000)
        check("Leibgarde: Chat bleibt frei", "Alles klar" in await pg.locator(".msg.ai").last.inner_text())
        await pg.wait_for_timeout(1200); await pg.evaluate("pollJobs()"); await pg.wait_for_timeout(1200)
        check("Leibgarde: Ergebnis kommt an", "Steuerberater gefunden" in await pg.inner_text("#jobs"))

        # Gedächtnis / Archiv
        await pg.click("#btnBrain"); await pg.wait_for_timeout(500)
        check("Archiv speichert Gespräche", "Nachrichten gespeichert" in await pg.inner_text("#archInfo"))
        await pg.evaluate("document.querySelector('#dlgBrain').close()")
        n = await pg.evaluate("(async()=>{for(let i=0;i<20;i++)archivieren('user','Füller '+i);return (await erinnern('Steuerberater Oschersleben')).length})()")
        check("Erinnerung an alte Gespräche", n >= 1, str(n))

        # Schnellstart offline
        await ctx.unroute("**/*")
        async def nur_lokal(r):
            u = r.request.url
            if u.startswith("http://local/"):
                return await route(r)
            return await r.abort()
        await ctx.route("**/*", nur_lokal); await pg.reload(); await pg.wait_for_timeout(1200)
        await pg.click("nav button[data-t=lage]"); await pg.wait_for_timeout(500)
        check("Schnellstart: Daten auch ohne Netz", await pg.locator("#lands button").count() >= 4)
        check("Keine Programmfehler", not errs, "; ".join(errs))
        await b.close()
    print(f"\n{len(ok)} bestanden, {len(fehler)} fehlgeschlagen")
    sys.exit(1 if fehler else 0)


asyncio.run(main())
