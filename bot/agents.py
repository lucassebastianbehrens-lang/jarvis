"""Jarvis Agenten-Bot – Papierhandel mit Solana-Memecoins (KEIN echtes Geld).

4 Agenten wie im Video:
  Scanner  – findet neue/beworbene Solana-Tokens (DexScreener, öffentlich)
  Analyst  – bewertet jeden Token mit 0–100 Punkten
  Executor – kauft ab 70 Punkten mit 8 % des Kontos (Spielgeld)
  Risk     – Stop-Loss −6 %, Trailing-Stop 12 % unter Höchststand, Rug-Schutz
Läuft dauerhaft (alle 15 s). Stand → /var/lib/jarvis/agents/state.json (für Jarvis).
Start: python3 agents.py          Test: python3 agents.py --once
"""
import json, os, sys, time, urllib.request

OUT = os.environ.get("AGENTS_OUT", "/var/lib/jarvis/agents/state.json")
START_EUR, STAKE_PCT, MAX_OPEN = 1000.0, 0.08, 7
STOP, TRAIL, MIN_SCORE = -0.06, 0.12, 70
COST = 0.015            # Gebühren + Slippage je Seite (Memecoins: konservativ)
LOOP, SCAN_EVERY = 15, 60
COOLDOWN = 2 * 3600
API = "https://api.dexscreener.com"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jarvis-agents/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def usd_eur():
    try:
        return float(get("https://api.frankfurter.app/latest?from=USD&to=EUR")["rates"]["EUR"])
    except Exception:
        return None


def scan(S):
    """Scanner: neue Token-Profile + Boosts auf Solana."""
    found = []
    for path in ("/token-profiles/latest/v1", "/token-boosts/latest/v1", "/token-boosts/top/v1"):
        try:
            for t in get(API + path):
                if t.get("chainId") == "solana" and t.get("tokenAddress"):
                    found.append(t["tokenAddress"])
        except Exception as e:
            S["errors"] = (S["errors"] + [f"Scanner {path}: {e}"])[-5:]
    wl = S["watch"]
    for a in found:
        if a in wl:
            wl.remove(a)
        wl.insert(0, a)
    S["watch"] = wl[:90]
    S["agents"]["scanner"] = {"pools": len(S["watch"]), "last": int(time.time())}


def pairs(addrs):
    """Bester Pool (höchste Liquidität) je Token."""
    best = {}
    for i in range(0, len(addrs), 30):
        try:
            for p in get(f"{API}/tokens/v1/solana/{','.join(addrs[i:i+30])}") or []:
                a = p.get("baseToken", {}).get("address")
                liq = (p.get("liquidity") or {}).get("usd") or 0
                if a and (a not in best or liq > ((best[a].get("liquidity") or {}).get("usd") or 0)):
                    best[a] = p
        except Exception:
            pass
    return best


def score(p, now):
    """Analyst: 0–100 Punkte."""
    liq = (p.get("liquidity") or {}).get("usd") or 0
    vol1 = (p.get("volume") or {}).get("h1") or 0
    tx = (p.get("txns") or {}).get("m5") or {}
    buys, sells = tx.get("buys", 0), tx.get("sells", 0)
    ch5 = (p.get("priceChange") or {}).get("m5") or 0
    ch1 = (p.get("priceChange") or {}).get("h1") or 0
    mc = p.get("marketCap") or p.get("fdv") or 0
    age_h = (now - (p.get("pairCreatedAt") or now * 1000) / 1000) / 3600
    if liq < 15000 or mc < 50000 or age_h < 0.25 or sells == 0 and buys < 5:
        return 0
    s = 0
    s += min(25, liq / 4000)                                  # Liquidität bis 100k
    s += min(20, vol1 / 10000)                                # Volumen 1h bis 200k
    s += min(20, max(0, (buys / max(1, sells) - 1) * 20))     # Kaufdruck
    s += 15 if 1 <= ch5 <= 25 else 5 if 0 < ch5 < 1 else 0    # gesunder Anstieg, kein Pump
    s += 10 if 0 < ch1 < 150 else 0
    s += 10 if 0.5 <= age_h <= 48 else 3
    if ch5 > 40 or liq / max(mc, 1) < 0.03:                   # Pump oder dünne Liquidität
        s -= 30
    return max(0, min(100, round(s)))


def log(S, kind, sym, eur, pnl=None, note=""):
    S["activity"].insert(0, {"t": int(time.time()), "kind": kind, "sym": sym, "eur": round(eur, 2),
                             "pnl": None if pnl is None else round(pnl, 2), "note": note})
    S["activity"] = S["activity"][:150]


def sell(S, a, price_eur, why):
    p = S["open"].pop(a)
    val = p["qty"] * price_eur * (1 - COST)
    pnl = val - p["cost"]
    S["cash"] += val
    S["closed"].append({"sym": p["sym"], "pnl": round(pnl, 2), "pct": round(pnl / p["cost"] * 100, 1),
                        "t_in": p["t"], "t_out": int(time.time()), "why": why})
    S["closed"] = S["closed"][-500:]
    S["cool"][a] = int(time.time())
    day = time.strftime("%Y-%m-%d")
    S["daily"][day] = round(S["daily"].get(day, 0) + pnl, 2)
    log(S, "Gestoppt" if pnl < 0 else "Verkauft", p["sym"], val, pnl, why)


def tick(S, do_scan):
    now = time.time()
    if do_scan:
        scan(S)
        r = usd_eur()
        if r:
            S["usd_eur"] = r
    fx = S["usd_eur"]
    addrs = list(dict.fromkeys(list(S["open"]) + S["watch"]))
    P = pairs(addrs)
    # Risk
    for a in list(S["open"]):
        p, q = S["open"][a], P.get(a)
        if not q or not q.get("priceUsd"):
            continue
        px = float(q["priceUsd"]) * fx
        liq = (q.get("liquidity") or {}).get("usd") or 0
        p["now"], p["peak"] = px, max(p["peak"], px)
        if liq < p["liq"] * 0.5:
            sell(S, a, px, "Rug-Schutz: Liquidität weg")
        elif px <= p["price"] * (1 + STOP):
            sell(S, a, px, "Stop −6 %")
        elif px <= p["peak"] * (1 - TRAIL) and p["peak"] > p["price"]:
            sell(S, a, px, "Trailing-Stop")
    S["agents"]["risk"] = {"watching": len(S["open"]), "stop": STOP, "trail": TRAIL}
    # Analyst + Executor
    best = None
    for a in S["watch"]:
        q = P.get(a)
        if not q or a in S["open"] or now - S["cool"].get(a, 0) < COOLDOWN or not q.get("priceUsd"):
            continue
        sc = score(q, now)
        if not best or sc > best[0]:
            best = (sc, a, q)
    if best:
        S["agents"]["analyst"] = {"score": best[0], "sym": best[2]["baseToken"].get("symbol", "?"), "passed": best[0] >= MIN_SCORE}
    eq = value(S)
    if best and best[0] >= MIN_SCORE and len(S["open"]) < MAX_OPEN:
        stake = round(eq * STAKE_PCT, 2)
        if S["cash"] >= stake > 1:
            sc, a, q = best
            px = float(q["priceUsd"]) * fx
            S["cash"] -= stake
            S["open"][a] = {"sym": q["baseToken"].get("symbol", "?"), "price": px, "now": px, "peak": px,
                            "qty": stake * (1 - COST) / px, "cost": stake, "t": int(now), "score": sc,
                            "liq": (q.get("liquidity") or {}).get("usd") or 0, "url": q.get("url", "")}
            S["trades"] += 1
            log(S, "Gekauft", S["open"][a]["sym"], stake, None, f"{sc} Punkte · {STAKE_PCT*100:.0f} % vom Konto")
    S["agents"]["executor"] = {"trades": S["trades"], "open": len(S["open"])}
    S["value"] = round(value(S), 2)
    if not S["equity"] or now - S["equity"][-1][0] >= 300:
        S["equity"] = (S["equity"] + [[int(now), S["value"]]])[-2000:]
    S["updated"] = int(now)


def value(S):
    return S["cash"] + sum(p["qty"] * p["now"] * (1 - COST) for p in S["open"].values())


def load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {"start": START_EUR, "cash": START_EUR, "open": {}, "closed": [], "activity": [], "daily": {},
                "watch": [], "cool": {}, "equity": [], "trades": 0, "usd_eur": usd_eur() or 0.92,
                "agents": {}, "errors": [], "started": int(time.time()), "mode": "TEST",
                "strategy": "4 Agenten · ab 70 Punkte · 8 % je Trade · Stop −6 % · Trailing 12 %"}


def save(S):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(S, open(tmp, "w"))
    os.replace(tmp, OUT)


def main():
    S, n = load(), 0
    once = "--once" in sys.argv
    while True:
        try:
            tick(S, n % (SCAN_EVERY // LOOP) == 0)
            save(S)
            print(f"{time.strftime('%H:%M:%S')} Wert {S['value']:.2f} EUR | offen {len(S['open'])} | "
                  f"Trades {S['trades']} | Watchlist {len(S['watch'])}", flush=True)
        except Exception as e:
            S["errors"] = (S["errors"] + [str(e)])[-5:]
            print("Fehler:", e, flush=True)
        if once:
            break
        n += 1
        time.sleep(LOOP)


if __name__ == "__main__":
    main()
