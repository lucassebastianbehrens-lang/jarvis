"""Jarvis Backtest: testet Strategien auf 12 Monaten echter 15-Min-Kerzen (20 Coins) MIT Gebühren.
Daten: data.binance.vision (öffentliche Monatsarchive, USDT-Paare als Kurs-Stellvertreter für die EUR-Paare bei Kraken).
Ergebnis: data/backtest.json + Zusammenfassung im Log.
Start: python3 bot/backtest.py [monate]   (braucht numpy + pandas)
Kein Handel, kein Geld – reine Simulation."""
import io, json, os, sys, time, urllib.request, zipfile
from datetime import date
import numpy as np
import pandas as pd

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "LINK", "AVAX", "LTC",
         "TRX", "ATOM", "BCH", "XLM", "NEAR", "SHIB", "PEPE", "POL", "SUI", "UNI"]
MORE = ["ARB", "OP", "APT", "INJ", "FET", "RENDER", "TIA", "SEI", "WIF", "BONK",
        "FIL", "ICP", "AAVE", "HBAR", "ALGO", "ETC", "SAND", "MANA", "GRT", "TAO"]
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "backtest.json")
CACHE = os.path.join(os.path.dirname(__file__), "..", ".bt_cache")


def months_back(n):
    d = date.today().replace(day=1)
    out = []
    for _ in range(n):
        y, m = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
        d = date(y, m, 1)
        out.append(f"{y}-{m:02d}")
    return sorted(out)


def load(coin, months):
    os.makedirs(CACHE, exist_ok=True)
    frames = []
    for ym in months:
        sym = f"{coin}USDT"
        f = os.path.join(CACHE, f"{sym}-{ym}.csv")
        if not os.path.exists(f):
            url = f"https://data.binance.vision/data/spot/monthly/klines/{sym}/15m/{sym}-15m-{ym}.zip"
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    z = zipfile.ZipFile(io.BytesIO(r.read()))
                open(f, "wb").write(z.read(z.namelist()[0]))
            except Exception as e:
                print(f"  fehlt {sym} {ym}: {e}")
                continue
        df = pd.read_csv(f, header=None, usecols=[0, 1, 2, 3, 4])
        if not str(df.iloc[0, 0]).isdigit():   # Kopfzeile
            df = df.iloc[1:].astype(float)
        frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames)
    df.columns = ["t", "o", "h", "l", "c"]
    t = df["t"].astype("int64")
    t = np.where(t > 1e14, t // 1000, t)        # ab 2025 Mikrosekunden
    df["t"] = (t // 1000).astype("int64")
    return df.drop_duplicates("t").set_index("t").sort_index().astype(float)


def ema(a, n):
    return pd.DataFrame(a).ewm(span=n, adjust=False).mean().values


def rsi(c, n):
    d = np.diff(c, axis=0, prepend=c[:1])
    up = pd.DataFrame(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    dn = pd.DataFrame(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean().values
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / dn)
    return np.nan_to_num(r, nan=50.0)


def simulate(O, H, L, C, entry, tp, sl, hold, fee, max_open=5, start=1000.0, be=None, split_t=None, T=None):
    """Portfolio-Simulation: Signal am Kerzenschluss, Kauf zur nächsten Eröffnung.
    Stop und Ziel innerhalb der Kerze; trifft beides, zählt der Stop (vorsichtig)."""
    n, P = C.shape
    cash, pos, trades = start, {}, []
    peak_eq, max_dd = start, 0.0
    pending = []
    for t in range(n):
        for p in pending:                                   # Käufe zur Eröffnung
            if p in pos or len(pos) >= max_open or np.isnan(O[t, p]):
                continue
            invested = sum(x["cost"] for x in pos.values())
            stake = min(cash, (cash + invested) / max_open)
            if stake < 10:
                continue
            cash -= stake
            px = O[t, p]
            pos[p] = {"px": px, "qty": stake * (1 - fee) / px, "cost": stake, "t": t, "hi": px}
        pending = []
        for p in list(pos):
            x = pos[p]
            if np.isnan(C[t, p]):
                continue
            x["hi"] = max(x["hi"], H[t, p])
            stop = x["px"] * (1 - sl)
            if be and x["hi"] >= x["px"] * (1 + be[0]):
                stop = max(stop, x["px"] * (1 + be[1]))
            out = None
            if L[t, p] <= stop:
                out = min(stop, O[t, p]) if t > x["t"] else stop
            elif H[t, p] >= x["px"] * (1 + tp):
                out = max(x["px"] * (1 + tp), O[t, p]) if t > x["t"] else x["px"] * (1 + tp)
            elif t - x["t"] >= hold:
                out = C[t, p]
            if out is not None:
                net = x["qty"] * out * (1 - fee)
                cash += net
                trades.append((x["t"], t, p, net - x["cost"], (net - x["cost"]) / x["cost"]))
                del pos[p]
        eq = cash + sum(x["qty"] * C[t, p] for p, x in pos.items() if not np.isnan(C[t, p]))
        peak_eq = max(peak_eq, eq)
        max_dd = max(max_dd, 1 - eq / peak_eq)
        if t + 1 < n and len(pos) < max_open:
            cand = np.nonzero(entry[t])[0]
            pending = [p for p in cand if p not in pos]
    eq = cash + sum(x["qty"] * C[-1, p] for p, x in pos.items() if not np.isnan(C[-1, p]))
    res = {"final": round(eq, 2), "trades": len(trades), "max_dd": round(max_dd * 100, 1)}
    for name, sel in (("all", lambda a: True), ("train", lambda a: a < split_t), ("test", lambda a: a >= split_t)):
        tr = [x for x in trades if sel(x[0])]
        w = sum(1 for x in tr if x[3] > 0)
        res[name] = {"n": len(tr), "wr": round(w / len(tr) * 100, 1) if tr else 0,
                     "avg_pct": round(float(np.mean([x[4] for x in tr])) * 100, 3) if tr else 0,
                     "pnl": round(sum(x[3] for x in tr), 2)}
    return res


def main():
    nmon = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    focus = len(sys.argv) > 2 and sys.argv[2] == "fokus"
    months = months_back(nmon)
    coin_list = COINS + MORE if focus else COINS
    print("Monate:", months[0], "bis", months[-1])
    data = {}
    for c in coin_list:
        df = load(c, months)
        if df is not None and len(df) > 1000:
            data[c] = df
            print(f"  {c}: {len(df)} Kerzen")
    idx = sorted(set().union(*[set(d.index) for d in data.values()]))
    coins = list(data)
    W = {k: pd.DataFrame({c: data[c][k] for c in coins}).reindex(idx).values for k in "ohlc"}
    O, H, L, C = W["o"], W["h"], W["l"], W["c"]
    Cf = pd.DataFrame(C).ffill().values
    n = len(idx)
    split = int(n * 0.75)
    print(f"{len(coins)} Coins, {n} Zeitpunkte, Training bis Index {split}, Test danach (letzte ~{nmon // 4} Monate)")

    ind = {"ema200": ema(Cf, 200), "ema800": ema(Cf, 800), "rsi2": rsi(Cf, 2), "rsi3": rsi(Cf, 3), "rsi14": rsi(Cf, 14),
           "e9": ema(Cf, 9), "e21": ema(Cf, 21), "e100": ema(Cf, 100)}
    sma20 = pd.DataFrame(Cf).rolling(20).mean().values
    sd20 = pd.DataFrame(Cf).rolling(20).std().values
    valid = ~np.isnan(C)

    entries = {}
    # A) bisherige Strategie (EMA-Kreuz)
    cross = (ind["e9"] > ind["e21"]) & (np.roll(ind["e9"], 1, 0) <= np.roll(ind["e21"], 1, 0))
    entries["A_ema_cross"] = cross & (ind["rsi14"] > 45) & (ind["rsi14"] < 70) & (Cf > ind["e100"]) & valid
    # B) Rücksetzer im Aufwärtstrend (RSI überverkauft)
    for tr in ("ema200", "ema800"):
        up = Cf > ind[tr]
        for rn, th in (("rsi2", 5), ("rsi2", 10), ("rsi3", 10), ("rsi3", 15), ("rsi14", 25), ("rsi14", 30)):
            entries[f"B_{rn}<{th}_{tr}"] = up & (ind[rn] < th) & valid
        # C) unteres Bollinger-Band
        for k in (2.0, 2.5):
            entries[f"C_bb{k}_{tr}"] = up & (Cf < sma20 - k * sd20) & valid
        # D) schneller Kursrutsch
        for bars in (4, 8):
            for d in (0.02, 0.03, 0.05):
                drop = Cf / np.roll(Cf, bars, 0) - 1
                entries[f"D_drop{int(d * 100)}%/{bars}_{tr}"] = up & (drop <= -d) & valid
    # E) Rutsch ohne Trendfilter (Gegenbewegung), nur tiefe Rücksetzer
    for d in (0.04, 0.06):
        drop = Cf / np.roll(Cf, 8, 0) - 1
        entries[f"E_drop{int(d * 100)}%/8_kein_trend"] = (drop <= -d) & (ind["rsi14"] < 30) & valid
    if focus:
        entries = {}
        for bars in (4, 8, 16):
            drop = Cf / np.roll(Cf, bars, 0) - 1
            for d in (0.04, 0.05, 0.06, 0.08):
                for rm in (25, 30, 35, 101):
                    entries[f"E_drop{int(d * 100)}%/{bars}_rsi<{rm}"] = (drop <= -d) & (ind["rsi14"] < rm) & valid
    for e in entries.values():
        e[:850] = False

    FEE = 0.0045          # 0,40 % Kraken-Taker + 0,05 % Slippage je Seite (vorsichtig)
    grid = [(tp, sl, hold, 5) for tp in (0.008, 0.012, 0.016, 0.02, 0.03) for sl in (0.03, 0.05, 0.08, 0.12)
            for hold in (32, 96, 288)]
    if focus:
        grid = [(tp, sl, hold, mo) for tp in (0.015, 0.02, 0.025, 0.03) for sl in (0.08, 0.12, 0.2)
                for hold in (288, 576) for mo in (3, 5)]
    results = []
    t0 = time.time()
    for name, e in entries.items():
        for tp, sl, hold, mo in grid:
            r = simulate(O, H, L, C, e, tp, sl, hold, FEE, max_open=mo, split_t=split)
            r.update({"strategy": name, "tp": tp, "sl": sl, "hold": hold, "max_open": mo})
            results.append(r)
        print(f"  {name}: fertig ({time.time() - t0:.0f}s)")

    def ok(r, part):
        return r[part]["wr"] >= 80 and r[part]["n"] >= (30 if part == "train" else 15) and r[part]["pnl"] > 0
    good = [r for r in results if ok(r, "train")]
    good.sort(key=lambda r: r["train"]["pnl"], reverse=True)
    both = [r for r in good if ok(r, "test")]
    best_any = sorted(results, key=lambda r: r["final"], reverse=True)[:15]
    # Top-Kandidaten zusätzlich mit Maker-Gebühren (Limit-Orders, 0,25 %)
    for r in (both[:10] or good[:10]):
        rr = simulate(O, H, L, C, entries[r["strategy"]], r["tp"], r["sl"], r["hold"], 0.0030,
                      max_open=r["max_open"], split_t=split)
        r["maker_final"] = rr["final"]
        r["maker_wr"] = rr["all"]["wr"]
    fam = {}
    for r in results:
        if r["strategy"] not in fam or r["final"] > fam[r["strategy"]]["final"]:
            fam[r["strategy"]] = {k: r[k] for k in ("final", "max_dd", "tp", "sl", "hold", "max_open")} | {"wr": r["all"]["wr"], "n": r["all"]["n"]}
    out = {"per_strategy_best": fam, "created": int(time.time()), "months": [months[0], months[-1]], "coins": coins, "fee_side": FEE,
           "configs": len(results), "train_ok": len(good), "train_and_test_ok": len(both),
           "best_both": both[:15], "best_train": good[:15], "best_return": best_any}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT.replace(".json", "_fokus.json") if focus else OUT, "w"), indent=1)

    def line(r):
        return (f"{r['strategy']:<24} slots {r['max_open']} TP {r['tp'] * 100:.1f}% SL {r['sl'] * 100:.0f}% max {r['hold'] // 4}h | "
                f"Endwert {r['final']:>9.0f} € DD {r['max_dd']}% | Trades {r['all']['n']} WR {r['all']['wr']}% | "
                f"Train WR {r['train']['wr']}% {r['train']['pnl']:+.0f}€ | Test WR {r['test']['wr']}% {r['test']['pnl']:+.0f}€"
                + (f" | Maker {r['maker_final']:.0f}€" if "maker_final" in r else ""))
    print(f"\n=== {len(results)} Varianten getestet, {len(good)} mit ≥80% Treffer + Gewinn im Training, "
          f"{len(both)} auch im Test ===")
    print("\n--- Beste: ≥80 % in Training UND Test ---")
    for r in both[:15]:
        print(line(r))
    print("\n--- Beste nur Training ---")
    for r in good[:10]:
        print(line(r))
    print("\n--- Bestes Ergebnis je Strategie ---")
    for k2, v in sorted(fam.items(), key=lambda x: -x[1]["final"])[:25]:
        print(f"{k2:<28} Endwert {v['final']:>8.0f} € WR {v['wr']}% n {v['n']} DD {v['max_dd']}%")
    print("\n--- Höchster Endwert (egal welche Trefferquote) ---")
    for r in best_any[:10]:
        print(line(r))


if __name__ == "__main__":
    main()
