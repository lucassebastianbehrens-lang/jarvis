"""Jarvis Spielgeld-Bot v2: Papierhandel mit echten Kraken-Kursen (kein echtes Geld).
Strategie siehe CFG/STRAT unten (per Backtest über 12 Monate ausgewählt, bot/backtest.py).
Signal am Kerzenschluss → Kauf zur Eröffnung der nächsten Kerze (wie im Backtest).
Einsatz wächst mit dem Konto (Konto / MAX_OPEN je Trade). Gebühren 0,45 % je Seite eingerechnet.
Freigabe für Echtgeld (gate): ≥80 % Gewinntrades nach Gebühren, Konto ≥3.500 €, ≥100 Trades.
Läuft alle 15 Min per GitHub Actions und speichert den Stand in data/paper.json."""
import json, os, time, urllib.parse, urllib.request

PAIRS = {"BTC/EUR": "XBTEUR", "ETH/EUR": "ETHEUR", "SOL/EUR": "SOLEUR", "XRP/EUR": "XRPEUR", "ADA/EUR": "ADAEUR",
         "DOGE/EUR": "XDGEUR", "DOT/EUR": "DOTEUR", "LINK/EUR": "LINKEUR", "AVAX/EUR": "AVAXEUR", "LTC/EUR": "LTCEUR",
         "TRX/EUR": "TRXEUR", "ATOM/EUR": "ATOMEUR", "BCH/EUR": "BCHEUR", "XLM/EUR": "XLMEUR", "NEAR/EUR": "NEAREUR",
         "SHIB/EUR": "SHIBEUR", "PEPE/EUR": "PEPEEUR", "POL/EUR": "POLEUR", "SUI/EUR": "SUIEUR", "UNI/EUR": "UNIEUR",
         "ARB/EUR": "ARBEUR", "OP/EUR": "OPEUR", "APT/EUR": "APTEUR", "INJ/EUR": "INJEUR", "FET/EUR": "FETEUR",
         "RENDER/EUR": "RENDEREUR", "TIA/EUR": "TIAEUR", "SEI/EUR": "SEIEUR", "WIF/EUR": "WIFEUR", "BONK/EUR": "BONKEUR",
         "FIL/EUR": "FILEUR", "ICP/EUR": "ICPEUR", "AAVE/EUR": "AAVEEUR", "HBAR/EUR": "HBAREUR", "ALGO/EUR": "ALGOEUR",
         "ETC/EUR": "ETCEUR", "SAND/EUR": "SANDEUR", "MANA/EUR": "MANAEUR", "GRT/EUR": "GRTEUR", "TAO/EUR": "TAOEUR"}
VERSION = 2
START, MAX_OPEN = 1000.0, 5
FEE = 0.0045                               # 0,40 % Kraken-Taker + 0,05 % Schlupf je Seite (vorsichtig)
# Backtest 11/2025–10/2026, 40 Coins, 0,45 % Gebühr je Seite: 1.000 → 1.153 €, 92 % Gewinntrades,
# max. Rückgang 6,8 %, im Testzeitraum (letzte 3 Monate, nicht zum Optimieren benutzt) 89,7 % Treffer.
CFG = {"kind": "drop", "drop": 0.08, "drop_bars": 8, "rsi_max": 35, "trend": 0, "tp": 0.025, "sl": 0.08, "hold_bars": 288}
TP, SL = CFG["tp"], -CFG["sl"]
GATE = {"wr": 80.0, "value": 3500.0, "trades": 100}
INTERVAL = 15
FILE = os.path.join(os.path.dirname(__file__), "..", "data", "paper.json")
STRAT = "wird unten aus CFG erzeugt"


def describe(c):
    e = {"rsi": f"RSI{c.get('rsi_n')} < {c.get('rsi_max')}", "bb": f"Kurs unter Bollinger-Band ({c.get('bb_k')}σ)",
         "drop": f"Kursrutsch ≥{c.get('drop', 0) * 100:.0f} % in {c.get('drop_bars', 0) * 15} Min"
                 + (f" und RSI < {c['rsi_max']}" if c.get("rsi_max", 101) <= 100 else "")}[c["kind"]]
    tr = f", Kurs über EMA{c['trend']}" if c.get("trend") else ""
    return (f"v{VERSION}: Panik-Rücksetzer kaufen – {e}{tr}; "
            f"Ziel +{c['tp'] * 100:.1f} %, Stop −{c['sl'] * 100:.0f} %, max. {c['hold_bars'] // 4} h")


STRAT = describe(CFG)


def ema(vals, n):
    k, out = 2 / (n + 1), []
    for v in vals:
        out.append(v if not out else v * k + out[-1] * (1 - k))
    return out


def rsi(vals, n=14):
    """RSI nach Wilder (wie pandas ewm alpha=1/n im Backtest)."""
    out, g, l = [50.0] * len(vals), 0.0, 0.0
    a = 1 / n
    for i in range(1, len(vals)):
        d = vals[i] - vals[i - 1]
        g = g * (1 - a) + max(d, 0) * a
        l = l * (1 - a) + max(-d, 0) * a
        out[i] = 100 - 100 / (1 + g / l) if l else 100.0
    return out


def signals(closes, c=CFG):
    """True an Index i, wenn am Schluss von Kerze i ein Kaufsignal besteht."""
    trend = ema(closes, c.get("trend") or 1)
    n = len(closes)
    sig = [False] * n
    if c["kind"] == "rsi":
        r = rsi(closes, c["rsi_n"])
        for i in range(n):
            sig[i] = closes[i] > trend[i] and r[i] < c["rsi_max"]
    elif c["kind"] == "bb":
        for i in range(19, n):
            w = closes[i - 19:i + 1]
            m = sum(w) / 20
            sd = (sum((x - m) ** 2 for x in w) / 19) ** 0.5
            sig[i] = closes[i] > trend[i] and closes[i] < m - c["bb_k"] * sd
    elif c["kind"] == "drop":                   # Kursrutsch (+ optional RSI-Filter, optional Trendfilter)
        b = c["drop_bars"]
        r = rsi(closes, 14)
        for i in range(b, n):
            sig[i] = (closes[i] / closes[i - b] - 1 <= -c["drop"] and r[i] < c.get("rsi_max", 101)
                      and (not c.get("trend") or closes[i] > trend[i]))
    return sig


def candles(code):
    url = f"https://api.kraken.com/0/public/OHLC?pair={code}&interval={INTERVAL}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-bot"}), timeout=20) as r:
        d = json.load(r)
    if d.get("error"):
        raise RuntimeError(d["error"])
    rows = next(v for k, v in d["result"].items() if k != "last")
    return [(int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4])) for c in rows[:-1]]  # nur abgeschlossene


def notify(text):
    """Telegram-Nachricht (nur wenn TG_TOKEN/TG_CHAT gesetzt sind)."""
    t, c = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not t or not c:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": c, "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{t}/sendMessage", data, timeout=10)
    except Exception:
        pass


def event(S, typ, pair, ts, **kw):
    S["seq"] = S.get("seq", 0) + 1
    S["events"] = (S.get("events", []) + [{"id": S["seq"], "type": typ, "pair": pair, "t": ts, **kw}])[-200:]


def close_pos(S, pair, price, ts, why):
    p = S["open"].pop(pair)
    net = p["qty"] * price * (1 - FEE)
    pnl = net - p["cost"]
    S["cash"] += net
    S["closed"].append({"pair": pair, "in": p["price"], "out": price, "pnl": round(pnl, 2),
                        "pct": round(pnl / p["cost"] * 100, 2), "t_in": p["t"], "t_out": ts, "why": why, "v": VERSION})
    S["n_closed"] = S.get("n_closed", 0) + 1
    S["n_win"] = S.get("n_win", 0) + (pnl > 0)
    event(S, "sell", pair, int(time.time()), why=why)
    notify(f"{'✅' if pnl >= 0 else '🔴'} Krypto-Bot: {pair} verkauft {pnl:+.2f} € ({why}) – Spielgeld")
    day = time.strftime("%Y-%m-%d", time.gmtime(ts))
    S["daily"][day] = round(S["daily"].get(day, 0) + pnl, 2)


def stake(S):
    invested = sum(p["cost"] for p in S["open"].values())
    return min(S["cash"], (S["cash"] + invested) / MAX_OPEN)


def step(S, pair, cs):
    closes = [c[4] for c in cs]
    sig = signals(closes)
    last = S["last_ts"].get(pair, cs[-1][0])            # erster Lauf: ab jetzt starten
    for i in range(max(1, len(cs) - 200), len(cs)):
        ts, op, hi, lo, cl = cs[i]
        if ts <= last:
            continue
        if pair in S["pending"]:                        # Kauf zur Eröffnung dieser Kerze
            del S["pending"][pair]
            st = stake(S)
            if pair not in S["open"] and len(S["open"]) < MAX_OPEN and st >= 10:
                S["cash"] -= st
                S["open"][pair] = {"price": op, "qty": st * (1 - FEE) / op, "cost": round(st, 2), "t": ts, "i": 0}
        if pair in S["open"]:
            p = S["open"][pair]
            p["i"] = p.get("i", 0) + (0 if p["t"] == ts else 1)
            stop, tp = p["price"] * (1 + SL), p["price"] * (1 + TP)
            if lo <= stop:
                close_pos(S, pair, round(min(stop, op) if p["t"] != ts else stop, 10), ts, "Stop-Loss")
            elif hi >= tp:
                close_pos(S, pair, round(max(tp, op) if p["t"] != ts else tp, 10), ts, "Take-Profit")
            elif p["i"] >= CFG["hold_bars"]:
                close_pos(S, pair, cl, ts, "Zeitlimit")
        if (sig[i] and pair not in S["open"] and len(S["open"]) + len(S["pending"]) < MAX_OPEN
                and i == len(cs) - 1 and ts >= time.time() - 2 * 900):   # nur frische Signale handeln
            S["pending"][pair] = ts
            event(S, "buy", pair, int(time.time()))
        last = ts
    S["last_ts"][pair] = last
    S["prices"][pair] = closes[-1]


def check_gate(S):
    n, w = S.get("n_closed", 0), S.get("n_win", 0)
    wr = w / n * 100 if n else 0.0
    g = S.setdefault("gate", {})
    g.update({"wr": round(wr, 1), "trades": n, "value": S["value"], "need": GATE})
    ok = wr >= GATE["wr"] and S["value"] >= GATE["value"] and n >= GATE["trades"]
    if ok and not g.get("passed"):
        g["passed"], g["passed_at"] = True, int(time.time())
        notify(f"🏁 FREIGABE ERREICHT: {S['value']:.0f} € Spielgeld, {wr:.1f} % Gewinntrades bei {n} Trades. "
               "Jetzt kann Echtgeld eingerichtet werden – frag Claude nach den nächsten Schritten.")
    return ok


def new_state():
    return {"start": START, "cash": START, "open": {}, "pending": {}, "closed": [], "daily": {}, "last_ts": {},
            "prices": {}, "equity": [], "started": int(time.time()), "strategy": STRAT, "version": VERSION,
            "n_closed": 0, "n_win": 0, "events": [], "seq": 0}


def main():
    try:
        S = json.load(open(FILE))
    except (FileNotFoundError, ValueError):
        S = new_state()
    if S.get("version") != VERSION:                     # neue Strategie → neuer, sauberer Zähler
        old = {k: S.get(k) for k in ("strategy", "started", "value", "closed")}
        S = new_state()
        S["previous"] = {"strategy": old["strategy"], "started": old["started"], "value": old["value"],
                         "trades": len(old["closed"] or []),
                         "wins": sum(1 for x in old["closed"] or [] if x["pnl"] > 0)}
        notify(f"🔄 Spielgeld-Bot neu gestartet mit 1.000 €: {STRAT}")
    S["strategy"] = STRAT
    S.setdefault("pending", {})
    errors = []
    for pair, code in PAIRS.items():
        try:
            time.sleep(0.4)                                # Kraken-Limit für öffentliche Abfragen
            step(S, pair, candles(code))
        except Exception as e:  # ein Paar darf ausfallen, der Rest läuft weiter
            errors.append(f"{pair}: {e}")
    val = S["cash"] + sum(p["qty"] * S["prices"].get(k, p["price"]) * (1 - FEE) for k, p in S["open"].items())
    S["value"] = round(val, 2)
    check_gate(S)
    S["equity"] = (S["equity"] + [[int(time.time()), S["value"]]])[-700:]
    S["closed"] = S["closed"][-300:]
    S["updated"] = int(time.time())
    S["errors"] = errors
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    json.dump(S, open(FILE, "w"), indent=1)
    g = S["gate"]
    print(f"Wert {val:.2f} EUR | offen {len(S['open'])} | Trades {g['trades']} | Treffer {g['wr']} % | "
          f"Freigabe {'JA' if g.get('passed') else 'nein'} | Fehler {errors}")


if __name__ == "__main__":
    main()
