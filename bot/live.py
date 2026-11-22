"""Jarvis Echtgeld-Modul für Kraken – spiegelt die Käufe/Verkäufe des Spielgeld-Bots.

STANDARD: AUS. Echte Orders gibt es nur, wenn ALLES erfüllt ist:
  1. Freigabe erreicht (data/paper.json → gate.passed): ≥80 % Gewinntrades nach Gebühren,
     Spielgeld ≥ 3.500 €, mindestens 100 abgeschlossene Trades mit der aktuellen Strategie
  2. GitHub-Variable LIVE_MODE = "an"   ("test" = Kraken prüft die Orders nur, nichts wird ausgeführt)
  3. GitHub-Secrets KRAKEN_KEY und KRAKEN_SECRET sind gesetzt (Schlüssel OHNE Abhebe-Recht)
Sicherungen: Höchstbetrag LIVE_MAX_EUR, Tagesverlust-Limit LIVE_MAX_DAY_LOSS, Pause bei schwacher
Trefferquote (letzte 30 Spielgeld-Trades < 70 %), Stop-Loss-Order direkt bei Kraken nach jedem Kauf.
Not-Aus: LIVE_MODE auf "aus" setzen (dann werden keine neuen Käufe gemacht; offene Positionen werden
weiter nach Signal verkauft) oder "stop" (alles sofort verkaufen)."""
import base64, hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from paper import notify, PAIRS, MAX_OPEN, SL  # noqa: E402

API = "https://api.kraken.com"
BASE = os.path.join(os.path.dirname(__file__), "..", "data")
PAPER, FILE = os.path.join(BASE, "paper.json"), os.path.join(BASE, "live.json")
MIN_WR_RECENT = 70.0


def env_float(k, d):
    try:
        return float(os.environ.get(k) or d)
    except ValueError:
        return d


class Kraken:
    def __init__(self, key, secret, validate):
        self.key, self.secret, self.validate = key, base64.b64decode(secret), validate

    def public(self, method, **q):
        url = f"{API}/0/public/{method}?{urllib.parse.urlencode(q)}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-bot"}), timeout=20) as r:
            d = json.load(r)
        if d.get("error"):
            raise RuntimeError(d["error"])
        return d["result"]

    def private(self, method, **data):
        path = f"/0/private/{method}"
        data["nonce"] = str(int(time.time() * 1000))
        body = urllib.parse.urlencode(data)
        msg = path.encode() + hashlib.sha256((data["nonce"] + body).encode()).digest()
        sig = base64.b64encode(hmac.new(self.secret, msg, hashlib.sha512).digest()).decode()
        req = urllib.request.Request(API + path, body.encode(), {"API-Key": self.key, "API-Sign": sig,
                                                                 "User-Agent": "jarvis-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        if d.get("error"):
            raise RuntimeError(d["error"])
        return d["result"]

    def order(self, code, side, vol, otype="market", price=None):
        args = {"pair": code, "type": side, "ordertype": otype, "volume": vol}
        if price:
            args["price"] = price
        if self.validate:
            args["validate"] = "true"
        return self.private("AddOrder", **args)


def fmt(x, dec):
    return f"{x:.{dec}f}"


def main():
    mode = (os.environ.get("LIVE_MODE") or "aus").strip().lower()
    key, secret = os.environ.get("KRAKEN_KEY"), os.environ.get("KRAKEN_SECRET")
    try:
        P = json.load(open(PAPER))
    except (FileNotFoundError, ValueError):
        print("Kein Spielgeld-Stand – nichts zu tun."); return
    try:
        S = json.load(open(FILE))
    except (FileNotFoundError, ValueError):
        S = {"done": [], "pos": {}, "daily": {}, "log": [], "paused": ""}
    gate = P.get("gate", {})
    status = {"mode": mode, "gate": bool(gate.get("passed")), "keys": bool(key and secret)}
    if mode not in ("test", "an", "stop") or not status["keys"]:
        S["status"] = status | {"info": "Echtgeld aus"}
        json.dump(S, open(FILE, "w"), indent=1)
        print("Echtgeld aus:", status); return
    if not gate.get("passed") and mode != "test":
        S["status"] = status | {"info": "Freigabe noch nicht erreicht"}
        json.dump(S, open(FILE, "w"), indent=1)
        print("Freigabe fehlt – keine echten Orders."); return

    k = Kraken(key, secret, validate=(mode == "test"))
    max_eur = env_float("LIVE_MAX_EUR", 100)
    max_day_loss = env_float("LIVE_MAX_DAY_LOSS", 15)
    info = k.public("AssetPairs", pair=",".join(PAIRS.values()))
    meta = {v.get("altname"): v for v in info.values()}
    today = time.strftime("%Y-%m-%d")
    day_pnl = S["daily"].get(today, 0.0)
    recent = P.get("closed", [])[-30:]
    recent_wr = sum(1 for x in recent if x["pnl"] > 0) / len(recent) * 100 if recent else 100
    pause = ""
    if day_pnl <= -max_day_loss:
        pause = f"Tagesverlust {day_pnl:.2f} € erreicht Limit"
    elif len(recent) >= 30 and recent_wr < MIN_WR_RECENT:
        pause = f"Trefferquote letzte 30 Trades {recent_wr:.0f} % < {MIN_WR_RECENT:.0f} %"
    if pause and pause != S.get("paused"):
        notify(f"⏸️ Echtgeld-Bot pausiert keine neuen Käufe: {pause}")
    S["paused"] = pause

    def log(txt):
        S["log"] = (S["log"] + [[int(time.time()), txt]])[-200:]
        print(txt)

    def sell(pair, why):
        p = S["pos"].get(pair)
        if not p:
            return
        code = PAIRS[pair]
        if p.get("test") and mode != "test":
            del S["pos"][pair]; return
        if p.get("stop_txid") and mode != "test":
            try:
                k.private("CancelOrder", txid=p["stop_txid"])
            except Exception as e:
                log(f"Stop-Order {pair} nicht storniert (evtl. schon ausgeführt): {e}")
        bal = k.private("Balance")
        base = meta[code]["base"]
        have = float(bal.get(base, 0))
        vol = min(have, p["vol"]) if mode != "test" else p["vol"]
        price = float(next(iter(k.public("Ticker", pair=code).values()))["c"][0])
        if vol * price >= 1:
            k.order(code, "sell", fmt(vol, meta[code]["lot_decimals"]))
        pnl = vol * price * (1 - 0.004) - p["cost"] if vol * price >= 1 else -p["cost"] + have * price
        S["daily"][today] = round(S["daily"].get(today, 0) + pnl, 2)
        del S["pos"][pair]
        log(f"VERKAUF {pair} {vol} @ {price} ({why}) ca. {pnl:+.2f} €" + (" [TEST]" if mode == "test" else ""))
        notify(f"{'💶' if pnl >= 0 else '🔻'} ECHTGELD {pair} verkauft ca. {pnl:+.2f} € ({why})"
               + (" [nur Test]" if mode == "test" else ""))

    if mode == "stop":
        for pair in list(S["pos"]):
            sell(pair, "Not-Aus")
        S["status"] = status | {"info": "Not-Aus: alles verkauft"}
        json.dump(S, open(FILE, "w"), indent=1); return

    if mode == "an":                 # Test-Positionen beim echten Start verwerfen
        S["pos"] = {k2: v for k2, v in S["pos"].items() if not v.get("test")}
    for ev in P.get("events", []):
        if ev["id"] in S["done"]:
            continue
        S["done"] = (S["done"] + [ev["id"]])[-500:]
        if ev["t"] < time.time() - 3 * 3600:      # alte Signale nicht nachholen
            continue
        pair, code = ev["pair"], PAIRS[ev["pair"]]
        try:
            if ev["type"] == "sell":
                sell(pair, ev.get("why", "Signal"))
                continue
            if pause or pair in S["pos"] or mode not in ("an", "test"):
                continue
            invested = sum(p["cost"] for p in S["pos"].values())
            eur = float(k.private("Balance").get("ZEUR", 0)) if mode != "test" else max_eur
            stake = min(max_eur / MAX_OPEN, max_eur - invested, eur * 0.98)
            m = meta[code]
            price = float(next(iter(k.public("Ticker", pair=code).values()))["a"][0])
            vol = stake / price
            if stake < float(m.get("costmin") or 5) or vol < float(m["ordermin"]):
                log(f"Kauf {pair} übersprungen: Betrag {stake:.2f} € zu klein"); continue
            r = k.order(code, "buy", fmt(vol, m["lot_decimals"]))
            vol_net = vol * (1 - 0.004)
            stop_px = fmt(price * (1 + SL), m["pair_decimals"])
            sr = k.order(code, "sell", fmt(vol_net, m["lot_decimals"]), "stop-loss", stop_px)
            S["pos"][pair] = {"vol": vol_net, "cost": round(stake, 2), "price": price, "t": int(time.time()),
                              "txid": (r.get("txid") or [""])[0], "stop_txid": (sr.get("txid") or [""])[0],
                              "test": mode == "test"}
            log(f"KAUF {pair} {vol:.6f} @ {price} für {stake:.2f} €, Stop {stop_px}" + (" [TEST]" if mode == "test" else ""))
            notify(f"🟢 ECHTGELD Kauf {pair} für {stake:.2f} € (Stop {stop_px})" + (" [nur Test]" if mode == "test" else ""))
        except Exception as e:
            log(f"FEHLER {ev['type']} {pair}: {e}")
            notify(f"⚠️ Echtgeld-Bot Fehler bei {pair}: {e}")
    S["status"] = status | {"info": pause or "aktiv", "max_eur": max_eur, "updated": int(time.time())}
    json.dump(S, open(FILE, "w"), indent=1)


if __name__ == "__main__":
    main()
