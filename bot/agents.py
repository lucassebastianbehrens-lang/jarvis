"""Jarvis Agenten-Bot – Papierhandel mit Solana-Memecoins (KEIN echtes Geld).

4 Agenten wie im Video:
  Scanner  – findet neue/beworbene Solana-Tokens (DexScreener, öffentlich)
  Analyst  – bewertet jeden Token mit 0–100 Punkten + Sicherheitsprüfung (RugCheck)
  Executor – kauft ab Mindestpunktzahl (Start 75) mit 8 % des Kontos (Spielgeld)
  Risk     – Stop −6 %, Gewinn sichern ab +4 %, Take-Profit, Trailing-Stop 12 %, Rug-Schutz
Optimierer – jeden Tag um 10 Uhr: passt Regeln an (Ziel ≥75 % Trefferquote UND Gewinn)
Läuft dauerhaft (alle 15 s). Stand → /var/lib/jarvis/agents/state.json (für Jarvis).
Start: python3 agents.py          Test: python3 agents.py --once
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

OUT = os.environ.get("AGENTS_OUT", "/var/lib/jarvis/agents/state.json")
START_EUR, STAKE_PCT, MAX_OPEN = 1000.0, 0.08, 7
TARGET_WR = 0.75                     # Ziel-Trefferquote
OPT_HOUR = 10                        # tägliche Selbst-Optimierung um 10 Uhr (Berlin)
DEFAULTS = {"min_score": 75, "stop": -0.07, "trail": 0.12, "tp": 0.065, "be_trigger": 0.05, "be_lock": 0.035}
PARAMS_VERSION = 2   # v2: viele kleine Gewinne (~2–3 € netto), Absicherung deckt Gebühren
COST = 0.015            # Gebühren + Slippage je Seite (Memecoins: konservativ)
LOOP, SCAN_EVERY = 15, 60
COOLDOWN = 2 * 3600
API = "https://api.dexscreener.com"
RUG_API = "https://api.rugcheck.xyz/v1/tokens/{}/report/summary"
RUG_MAX = 50                       # normierter RugCheck-Risikowert: darüber kein Kauf
TG_FILE = "/etc/jarvis/telegram.env"  # optional: TG_TOKEN=... und TG_CHAT=...
_rug_cache, _tg = {}, None


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jarvis-agents/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def usd_eur():
    try:
        return float(get("https://api.frankfurter.app/latest?from=USD&to=EUR")["rates"]["EUR"])
    except Exception:
        return None


def tg_conf():
    global _tg
    if _tg is None:
        _tg = {k: os.environ[k] for k in ("TG_TOKEN", "TG_CHAT") if os.environ.get(k)}
        try:
            for line in open(TG_FILE):
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    _tg[k] = v.strip().strip('"')
        except OSError:
            pass
    return _tg


def notify(text):
    """Telegram-Nachricht aufs Handy (nur wenn eingerichtet)."""
    c = tg_conf()
    if not c.get("TG_TOKEN") or not c.get("TG_CHAT"):
        return
    try:
        data = urllib.parse.urlencode({"chat_id": c["TG_CHAT"], "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{c['TG_TOKEN']}/sendMessage", data, timeout=10)
    except Exception:
        pass


def rugcheck(mint):
    """Sicherheitsprüfung (RugCheck, kostenlos). Rückgabe: (ok, grund)."""
    hit = _rug_cache.get(mint)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    try:
        d = get(RUG_API.format(mint))
        risks = d.get("risks") or []
        danger = [r.get("name", "?") for r in risks if r.get("level") == "danger"]
        norm = d.get("score_normalised")
        if danger:
            res = (False, "Gefahr: " + ", ".join(danger[:3]))
        elif norm is not None and norm > RUG_MAX:
            res = (False, f"Risikowert {norm}")
        else:
            res = (True, f"RugCheck ok ({norm if norm is not None else '?'})")
    except Exception as e:
        res = (None, f"RugCheck nicht erreichbar: {e}")   # None = unbekannt -> kein Kauf
    _rug_cache[mint] = (time.time(), res)
    return res


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
                        "t_in": p["t"], "t_out": int(time.time()), "why": why, "score": p.get("score", 0),
                        "peak": round(p["peak"] / p["price"] - 1, 4), "cost": p["cost"]})
    S["closed"] = S["closed"][-500:]
    S["cool"][a] = int(time.time())
    day = time.strftime("%Y-%m-%d")
    S["daily"][day] = round(S["daily"].get(day, 0) + pnl, 2)
    log(S, "Gestoppt" if pnl < 0 else "Verkauft", p["sym"], val, pnl, why)
    notify(f"{'🔴' if pnl < 0 else '✅'} {p['sym']} verkauft: {pnl:+.2f} € ({why}) · Konto {value(S):.2f} € – Spielgeld")


def tick(S, do_scan):
    now = time.time()
    if do_scan:
        scan(S)
        r = usd_eur()
        if r:
            S["usd_eur"] = r
    fx = S["usd_eur"]
    K = S["params"]
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
        stop = p["price"] * (1 + K["stop"])
        if p["peak"] >= p["price"] * (1 + K["be_trigger"]):      # Gewinn absichern
            stop = max(stop, p["price"] * (1 + K["be_lock"]))
        if liq < p["liq"] * 0.5:
            sell(S, a, px, "Rug-Schutz: Liquidität weg")
        elif K["tp"] and px >= p["price"] * (1 + K["tp"]):
            sell(S, a, px, f"Take-Profit +{K['tp']*100:.1f} %")
        elif px <= stop:
            sell(S, a, px, "Gewinn gesichert" if stop > p["price"] else f"Stop {K['stop']*100:.0f} %")
        elif px <= p["peak"] * (1 - K["trail"]) and p["peak"] > p["price"]:
            sell(S, a, px, "Trailing-Stop")
    S["agents"]["risk"] = {"watching": len(S["open"]), "stop": K["stop"], "trail": K["trail"]}
    # Analyst + Executor
    cands = []
    for a in S["watch"]:
        q = P.get(a)
        if not q or a in S["open"] or now - S["cool"].get(a, 0) < COOLDOWN or not q.get("priceUsd"):
            continue
        cands.append((score(q, now), a, q))
    cands.sort(key=lambda c: -c[0])
    best, safety = (cands[0] if cands else None), ""
    if len(S["open"]) < MAX_OPEN:
        for c in [c for c in cands if c[0] >= K["min_score"]][:3]:   # max. 3 Sicherheitsprüfungen je Runde
            ok, why = rugcheck(c[1])
            if ok:
                best, safety = c, why
                break
            S["cool"][c[1]] = int(now)                                # unsicher: 2 h sperren
            S["rejected"] = S.get("rejected", 0) + 1
            log(S, "Abgelehnt", c[2]["baseToken"].get("symbol", "?"), 0, None, f"{c[0]} Pkt, aber {why}")
            best = None
    if best:
        S["agents"]["analyst"] = {"score": best[0], "sym": best[2]["baseToken"].get("symbol", "?"),
                                  "passed": best[0] >= K["min_score"] and bool(safety), "safety": safety,
                                  "rejected": S.get("rejected", 0)}
    eq = value(S)
    if best and safety and best[0] >= K["min_score"] and len(S["open"]) < MAX_OPEN:
        stake = round(eq * STAKE_PCT, 2)
        if S["cash"] >= stake > 1:
            sc, a, q = best
            px = float(q["priceUsd"]) * fx
            S["cash"] -= stake
            S["open"][a] = {"sym": q["baseToken"].get("symbol", "?"), "price": px, "now": px, "peak": px,
                            "qty": stake * (1 - COST) / px, "cost": stake, "t": int(now), "score": sc,
                            "liq": (q.get("liquidity") or {}).get("usd") or 0, "url": q.get("url", "")}
            S["trades"] += 1
            log(S, "Gekauft", S["open"][a]["sym"], stake, None, f"{sc} Punkte · {safety}")
            notify(f"🟢 Gekauft {S['open'][a]['sym']} für {stake:.2f} € ({sc} Pkt, {safety}) – Spielgeld")
    S["agents"]["executor"] = {"trades": S["trades"], "open": len(S["open"])}
    S["value"] = round(value(S), 2)
    if not S["equity"] or now - S["equity"][-1][0] >= 300:
        S["equity"] = (S["equity"] + [[int(now), S["value"]]])[-2000:]
    S["updated"] = int(now)


def strategy_text(K):
    tp = f" · TP +{K['tp']*100:.1f} %".replace(".0 %", " %") if K["tp"] else ""
    return (f"ab {K['min_score']} Pkt · Stop {K['stop']*100:.0f} % · ab +{K['be_trigger']*100:.1f} % "
            f"auf +{K['be_lock']*100:.1f} % gesichert{tp} · Trail {K['trail']*100:.0f} %")


def winrate(T):
    return sum(t["pnl"] > 0 for t in T) / len(T) if T else 0


def sim_pnl(t, tp, bt, bl):
    """Schätzt das Ergebnis eines alten Trades mit anderen Ausstiegsregeln (aus Höchststand)."""
    cost, pk = t.get("cost") or 80, t.get("peak", 0)
    if tp and pk >= tp:
        return cost * ((1 + tp) * (1 - 0.015) ** 2 - 1)
    if pk >= bt and t["pct"] / 100 < bl:
        return cost * ((1 + bl) * (1 - 0.015) ** 2 - 1)
    return t["pnl"]


def optimize(S):
    """Tägliche Selbst-Optimierung: Ziel ≥75 % Trefferquote UND Gewinn > 0."""
    K, T = S["params"], [t for t in S["closed"] if "peak" in t][-300:]
    old, notes = dict(K), []
    if len(T) < 15:
        notes.append(f"nur {len(T)} Trades – zu wenig Daten, Regeln bleiben")
    else:
        best = None
        for tp in (0.05, 0.06, 0.065, 0.075, 0.09):          # kleine, schnelle Gewinne
            for bt, bl in ((0.045, 0.032), (0.05, 0.035), (0.06, 0.04)):   # gesicherter Gewinn > Gebühren
                for ms in range(60, 96, 5):
                    sel = [t for t in T if t.get("score", 0) >= ms]
                    if len(sel) < 10:
                        continue
                    pn = [sim_pnl(t, tp, bt, bl) for t in sel]
                    wr, tot = sum(x > 0 for x in pn) / len(pn), sum(pn)
                    key = (wr >= TARGET_WR and tot > 0, tot > 0, tot if wr >= TARGET_WR else wr, len(sel))
                    if not best or key > best[0]:
                        best = (key, tp, bt, bl, ms, wr, tot, len(sel))
        if best:
            _, tp, bt, bl, ms, wr, tot, n = best
            # behutsam ändern: Mindestpunkte max. ±5 pro Tag
            K["min_score"] = max(K["min_score"] - 5, min(K["min_score"] + 5, ms))
            K["tp"], K["be_trigger"], K["be_lock"] = tp, bt, bl
            notes.append(f"Test auf {n} alten Trades: Trefferquote {wr*100:.0f} %, Ergebnis {tot:+.2f} €")
            if wr < TARGET_WR:
                notes.append("75 % noch nicht erreichbar – beste gefundene Einstellung genommen")
        else:
            K["min_score"] = min(95, K["min_score"] + 5)
            notes.append("zu wenig Trades je Stufe – Mindestpunkte +5")
    names = {"min_score": "Mindestpunkte", "tp": "Take-Profit", "be_trigger": "Gewinn sichern ab",
             "be_lock": "gesicherter Gewinn", "stop": "Stop", "trail": "Trailing"}
    fmt = lambda k, v: str(v) if k == "min_score" else ("aus" if v is None else f"{v*100:+.0f} %")
    changes = [f"{names.get(k, k)} {fmt(k, old[k])} → {fmt(k, K[k])}" for k in K if old[k] != K[k]]
    S["opt"] = ([{"t": int(time.time()), "wr": round(winrate(T) * 100, 1), "n": len(T),
                  "changes": changes, "notes": notes}] + S.get("opt", []))[:30]
    S["strategy"] = strategy_text(K)
    log(S, "Optimiert", "Regeln", 0, None, "; ".join(changes) or "keine Änderung")
    notify(f"🧠 Tages-Optimierung: Trefferquote {winrate(T)*100:.0f} % ({len(T)} Trades), Konto {value(S):.2f} €. "
           + ("; ".join(changes) or "keine Änderung"))


def value(S):
    return S["cash"] + sum(p["qty"] * p["now"] * (1 - COST) for p in S["open"].values())


def load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {"start": START_EUR, "cash": START_EUR, "open": {}, "closed": [], "activity": [], "daily": {},
                "watch": [], "cool": {}, "equity": [], "trades": 0, "usd_eur": usd_eur() or 0.92,
                "agents": {}, "errors": [], "started": int(time.time()), "mode": "TEST",
                "strategy": ""}


def save(S):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(S, open(tmp, "w"))
    os.replace(tmp, OUT)


def main():
    S, n = load(), 0
    S.setdefault("params", dict(DEFAULTS))
    if S.get("pv") != PARAMS_VERSION:
        S["params"] = dict(DEFAULTS, min_score=S["params"].get("min_score", DEFAULTS["min_score"])); S["pv"] = PARAMS_VERSION
    for k, v in DEFAULTS.items():
        S["params"].setdefault(k, v)
    S["strategy"] = strategy_text(S["params"])
    S["target_wr"] = TARGET_WR
    once = "--once" in sys.argv
    while True:
        try:
            tick(S, n % (SCAN_EVERY // LOOP) == 0)
            berlin = datetime.now(ZoneInfo("Europe/Berlin"))
            if berlin.hour >= OPT_HOUR and S.get("opt_day") != berlin.strftime("%Y-%m-%d"):
                S["opt_day"] = berlin.strftime("%Y-%m-%d")
                optimize(S)
            S["winrate"] = round(winrate(S["closed"]) * 100, 1)
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
