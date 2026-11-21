"""Jarvis Spielgeld-Bot: Papierhandel mit echten Kraken-Kursen (kein echtes Geld).
Strategie: EMA9/EMA21-Kreuzung auf 15-Min-Kerzen, nur über EMA100 (Aufwärtstrend), RSI 45–70, Stop-Loss -3 %, Take-Profit +5 %.
Läuft alle 15 Min per GitHub Actions und speichert den Stand in data/paper.json."""
import json, os, time, urllib.request

PAIRS = {"BTC/EUR": "XBTEUR", "ETH/EUR": "ETHEUR", "SOL/EUR": "SOLEUR", "XRP/EUR": "XRPEUR", "ADA/EUR": "ADAEUR",
         "DOGE/EUR": "XDGEUR", "DOT/EUR": "DOTEUR", "LINK/EUR": "LINKEUR", "AVAX/EUR": "AVAXEUR", "LTC/EUR": "LTCEUR",
         "TRX/EUR": "TRXEUR", "ATOM/EUR": "ATOMEUR", "BCH/EUR": "BCHEUR", "XLM/EUR": "XLMEUR", "NEAR/EUR": "NEAREUR",
         "SHIB/EUR": "SHIBEUR", "PEPE/EUR": "PEPEEUR", "POL/EUR": "POLEUR", "SUI/EUR": "SUIEUR", "UNI/EUR": "UNIEUR"}
START, STAKE, MAX_OPEN = 1000.0, 150.0, 6
FEE, SL, TP = 0.004, -0.03, 0.05          # 0,4 % Gebühr je Seite (konservativ)
INTERVAL = 15
FILE = os.path.join(os.path.dirname(__file__), "..", "data", "paper.json")


def ema(vals, n):
    k, out = 2 / (n + 1), []
    for v in vals:
        out.append(v if not out else v * k + out[-1] * (1 - k))
    return out


def rsi(vals, n=14):
    out, g, l = [50.0] * len(vals), 0.0, 0.0
    for i in range(1, len(vals)):
        d = vals[i] - vals[i - 1]
        up, dn = max(d, 0), max(-d, 0)
        if i <= n:
            g += up / n; l += dn / n
        else:
            g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
        if i >= n:
            out[i] = 100 - 100 / (1 + g / l) if l else 100.0
    return out


def candles(code):
    url = f"https://api.kraken.com/0/public/OHLC?pair={code}&interval={INTERVAL}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-bot"}), timeout=20) as r:
        d = json.load(r)
    if d.get("error"):
        raise RuntimeError(d["error"])
    rows = next(v for k, v in d["result"].items() if k != "last")
    return [(int(c[0]), float(c[2]), float(c[3]), float(c[4])) for c in rows[:-1]]  # nur abgeschlossene Kerzen


def close_pos(S, pair, price, ts, why):
    p = S["open"].pop(pair)
    gross = p["qty"] * price
    net = gross * (1 - FEE)
    pnl = net - p["cost"]
    S["cash"] += net
    S["closed"].append({"pair": pair, "in": p["price"], "out": price, "pnl": round(pnl, 2),
                        "pct": round(pnl / p["cost"] * 100, 2), "t_in": p["t"], "t_out": ts, "why": why})
    day = time.strftime("%Y-%m-%d", time.gmtime(ts))
    S["daily"][day] = round(S["daily"].get(day, 0) + pnl, 2)


def step(S, pair, cs):
    closes = [c[3] for c in cs]
    e9, e21, e100, r = ema(closes, 9), ema(closes, 21), ema(closes, 100), rsi(closes)
    last = S["last_ts"].get(pair, cs[-1][0])            # erster Lauf: ab jetzt starten
    for i in range(max(1, len(cs) - 200), len(cs)):
        ts, hi, lo, cl = cs[i]
        if ts <= last:
            continue
        if pair in S["open"]:
            p = S["open"][pair]
            if lo <= p["price"] * (1 + SL):
                close_pos(S, pair, round(p["price"] * (1 + SL), 8), ts, "Stop-Loss")
            elif hi >= p["price"] * (1 + TP):
                close_pos(S, pair, round(p["price"] * (1 + TP), 8), ts, "Take-Profit")
            elif e9[i] < e21[i] and e9[i - 1] >= e21[i - 1]:
                close_pos(S, pair, cl, ts, "Signal")
        elif (e9[i] > e21[i] and e9[i - 1] <= e21[i - 1] and 45 < r[i] < 70 and cl > e100[i]   # nur im Aufwärtstrend
              and len(S["open"]) < MAX_OPEN and S["cash"] >= STAKE):
            S["cash"] -= STAKE
            S["open"][pair] = {"price": cl, "qty": STAKE * (1 - FEE) / cl, "cost": STAKE, "t": ts}
        last = ts
    S["last_ts"][pair] = last
    S["prices"][pair] = closes[-1]


def main():
    try:
        S = json.load(open(FILE))
    except (FileNotFoundError, ValueError):
        S = {"start": START, "cash": START, "open": {}, "closed": [], "daily": {}, "last_ts": {}, "prices": {},
             "equity": [], "started": int(time.time()), "strategy": "EMA 9/21 + Trendfilter EMA 100 + RSI 45–70, SL -3 %, TP +5 %"}
    errors = []
    for pair, code in PAIRS.items():
        try:
            step(S, pair, candles(code))
        except Exception as e:  # ein Paar darf ausfallen, der Rest läuft weiter
            errors.append(f"{pair}: {e}")
    val = S["cash"] + sum(p["qty"] * S["prices"].get(k, p["price"]) * (1 - FEE) for k, p in S["open"].items())
    S["value"] = round(val, 2)
    S["equity"] = (S["equity"] + [[int(time.time()), S["value"]]])[-700:]
    S["closed"] = S["closed"][-300:]
    S["updated"] = int(time.time())
    S["errors"] = errors
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    json.dump(S, open(FILE, "w"), indent=1)
    print(f"Wert {val:.2f} EUR | offen {len(S['open'])} | Trades {len(S['closed'])} | Fehler {errors}")


if __name__ == "__main__":
    main()
