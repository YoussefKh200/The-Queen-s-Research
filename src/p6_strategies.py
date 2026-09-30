"""Sec 10-13: strategies A-F + naive entry-timing controls; anchors A/B/C/E; holds 15/30/60/120; cost = gross/opt/normal/stress (RT pips)."""
import sys, pandas as pd, numpy as np
from concurrent.futures import ProcessPoolExecutor
from engine import *
COSTS = {"gross": 0.0, "opt": 0.6, "normal": 1.5, "stress": 3.0}; HOLDS = (15, 30, 60, 120)
def expmed(x, q=.5):     # expanding quantile of PRIOR days only (shift 1) -> no lookahead
    return pd.Series(x).expanding(30).quantile(q).shift(1).values
def make(M, ax):
    o, h, l, c = M["o"], M["h"], M["l"], M["c"]
    hi = h[:, :PRE].max(1); lo = l[:, :PRE].min(1); rng = (hi - lo) / PIP
    r5 = (c[:, PRE + 4] - o[:, PRE]) / PIP; pre15 = (c[:, PRE - 1] - c[:, PRE - 16]) / PIP
    th_r5_50, th_r5_80 = expmed(np.abs(r5)), expmed(np.abs(r5), .8); th_p15_80 = expmed(np.abs(pre15), .8); th_rng = expmed(rng)
    eu5 = np.sign(ax["EURUSD"][:, PRE + 4] - ax["EURUSD"][:, PRE - 1]); uj5 = np.sign(ax["USDJPY"][:, PRE + 4] - ax["USDJPY"][:, PRE - 1]); g5 = np.sign(r5)
    def brk(i, gate):
        if gate and not (rng[i] >= th_rng[i]): return None
        if rng[i] < 3: return None
        up = np.argmax(h[i, PRE:PRE + 60] >= hi[i]) if (h[i, PRE:PRE + 60] >= hi[i]).any() else 999
        dn = np.argmax(l[i, PRE:PRE + 60] <= lo[i]) if (l[i, PRE:PRE + 60] <= lo[i]).any() else 999
        if up == dn: return None
        return (dict(d=1, bar=PRE, kind="stop", level=hi[i], until=PRE + 60, sl=lo[i]) if up < dn else dict(d=-1, bar=PRE, kind="stop", level=lo[i], until=PRE + 60, sl=hi[i]))
    def sweep(i):
        for j in range(PRE, PRE + 30):
            if h[i, j] > hi[i] and c[i, j] < hi[i]: return dict(d=-1, bar=j + 1, kind="mkt", sl=max(h[i, PRE:j + 1]) + 1 * PIP)
            if l[i, j] < lo[i] and c[i, j] > lo[i]: return dict(d=1, bar=j + 1, kind="mkt", sl=min(l[i, PRE:j + 1]) - 1 * PIP)
        return None
    ok5 = lambda i: (abs(r5[i]) >= max(th_r5_50[i], 1.0)) if not np.isnan(th_r5_50[i]) else False
    S = {}
    for d0 in (0, 1, 2, 5):
        S[f"naive_long@{d0}"] = lambda i, M, d0=d0: dict(d=1, bar=PRE + d0, kind="mkt")
        S[f"naive_short@{d0}"] = lambda i, M, d0=d0: dict(d=-1, bar=PRE + d0, kind="mkt")
    S["A_breakout"] = lambda i, M: brk(i, False)
    S["B_breakout+volfilter"] = lambda i, M: brk(i, True)
    S["C_sweep_reversal"] = lambda i, M: sweep(i)
    S["D_momentum_after_5m"] = lambda i, M: dict(d=int(g5[i]), bar=PRE + 5, kind="mkt") if ok5(i) and g5[i] != 0 else None
    S["E_fade_abnormal_5m"] = lambda i, M: dict(d=-int(g5[i]), bar=PRE + 5, kind="mkt") if (not np.isnan(th_r5_80[i])) and abs(r5[i]) >= max(th_r5_80[i], 1.0) and g5[i] != 0 else None
    S["E2_fade_pre15"] = lambda i, M: dict(d=-int(np.sign(pre15[i])), bar=PRE, kind="mkt") if (not np.isnan(th_p15_80[i])) and abs(pre15[i]) >= max(th_p15_80[i], 1.0) else None
    S["F_momentum+crossasset"] = lambda i, M: dict(d=int(g5[i]), bar=PRE + 5, kind="mkt") if ok5(i) and g5[i] != 0 and eu5[i] == g5[i] and uj5[i] == -g5[i] else None
    return S
def run_anchor(nm):
    ev = pd.read_parquet(D / f"events_{nm}.parquet"); M, t = matrices(ev.index)
    ax = {s: matrices(ev.index, s)[0]["c"] for s in ("EURUSD", "USDJPY")}
    # matrices() may drop different rows per symbol -> align by anchor time
    ax = {s: matrices(ev.index, s) for s in ("EURUSD", "USDJPY")}
    keep = t
    for s in ax: assert len(ax[s][1]) == len(t) or True
    axc = {}
    for s, (Ms, ts) in ax.items():
        f = pd.DataFrame(Ms["c"], index=ts).reindex(t); axc[s] = f.values
    axo = {s: {"o": None} for s in axc}
    strat = make(M, {s: axc[s] for s in axc})
    rows, series = [], {}
    for sn, fn in strat.items():
        for hd in HOLDS:
            for cn, S in COSTS.items():
                r = simulate(M, fn, hd, S); v = pd.Series(r, index=t)
                if cn == "normal": series[f"{nm}|{sn}|{hd}"] = v
                x = v.dropna(); n = len(x)
                if n < 20: rows.append((nm, sn, hd, cn, n) + (np.nan,) * 6); continue
                is_, oos = x[x.index.year <= 2018], x[x.index.year >= 2019]
                pf = x[x > 0].sum() / max(-x[x < 0].sum(), 1e-9)
                rows.append((nm, sn, hd, cn, n, x.mean(), x.mean() / (x.std() / np.sqrt(n)), (x > 0).mean(), pf, is_.mean(), oos.mean()))
    return rows, series
if __name__ == "__main__":
    with ProcessPoolExecutor(4) as ex: R = list(ex.map(run_anchor, ["A", "B", "C", "E"]))
    cols = ["anchor", "strategy", "hold", "cost", "n", "mean_pips", "t", "win", "PF", "IS_mean(<=2018)", "OOS_mean(>=2019)"]
    T = pd.DataFrame([r for rows, _ in R for r in rows], columns=cols); T.to_csv(OUT / "p6_strategy_grid.csv", index=False)
    pd.concat({k: v for _, s in R for k, v in s.items()}, axis=1).to_parquet(OUT / "p6_daily_normal.parquet")
    pd.set_option("display.width", 250)
    for cn in ("gross", "normal"):
        x = T[T.cost == cn]; print(f"\n=== {cn}: best 12 cells by mean pips (n>=100) ===")
        print(x[x.n >= 100].sort_values("mean_pips", ascending=False).head(12).round(3).to_string(index=False))
    print("\ncells with normal-cost mean>0:", int(((T.cost == "normal") & (T.mean_pips > 0)).sum()), "of", int((T.cost == "normal").sum()))
