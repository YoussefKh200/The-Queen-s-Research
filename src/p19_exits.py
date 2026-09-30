"""Sec 12 completion: exit-model grid (fixed SL/TP, trailing stop, break-even) on London-open (NY 03:00) breakout of the 00-03 range and naive-direction entries.
Entry fills as in engine.simulate; exits evaluated from the entry bar, SL first on ties, trailing/BE updated at bar end (conservative). Hold cap = 300 min."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from arch.bootstrap import SPA
import engine; engine.PRE = 200; engine.POST = 520
from engine import matrices
from common import *
PRE = engine.PRE; HOLD = 300
days = pd.date_range("2010-11-16", "2026-09-17", freq="B")
loc = pd.DatetimeIndex(days + pd.Timedelta(hours=3)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT"); t0 = loc[loc.notna()].tz_convert("UTC").tz_localize(None)
M, t = matrices(t0); o, h, l, c = M["o"], M["h"], M["l"], M["c"]; N = len(t)
b0 = PRE - 180; hi = h[:, b0:PRE].max(1); lo = l[:, b0:PRE].min(1); pre = (c[:, PRE - 1] - o[:, b0]) / PIP

def entry_breakout(i, S):
    if (hi[i] - lo[i]) / PIP < 5: return None
    a, b = h[i, PRE:PRE + 90] >= hi[i], l[i, PRE:PRE + 90] <= lo[i]; up, dn = (np.argmax(a) if a.any() else 999), (np.argmax(b) if b.any() else 999)
    if up == dn: return None
    if up < dn:
        for j in range(PRE, PRE + 90):
            if h[i, j] + S * PIP >= hi[i]: return 1, j, max(hi[i], o[i, j] + S * PIP)
    else:
        for j in range(PRE, PRE + 90):
            if l[i, j] <= lo[i]: return -1, j, min(lo[i], o[i, j])
    return None
def entry_naive(i, S, d):      # market at 03:00 open in fixed direction d
    return d, PRE, o[i, PRE] + (S * PIP if d > 0 else 0.0)
def entry_trend(i, S):
    if not np.isfinite(pre[i]) or pre[i] == 0: return None
    return entry_naive(i, S, int(np.sign(pre[i])))

def run_exit(i, ent, S, sl, tp, trail, be):
    d, eb, px = ent; s = S * PIP; end = PRE + HOLD
    slv = None if sl is None else (px - sl * PIP if d > 0 else px + sl * PIP)       # level in executable-price terms
    tpv = None if tp is None else (px + tp * PIP if d > 0 else px - tp * PIP)
    ext = px if d > 0 else px                                                        # best favourable price seen (bid for long, ask for short)
    for j in range(eb, end):
        if d > 0:
            if slv is not None and l[i, j] <= slv: return (slv - px) / PIP
            if tpv is not None and h[i, j] >= tpv: return (tpv - px) / PIP
            ext = max(ext, h[i, j])
            if trail is not None: slv = max(slv if slv is not None else -1e9, ext - trail * PIP)
            if be is not None and ext - px >= be * PIP: slv = max(slv if slv is not None else -1e9, px)
        else:
            if slv is not None and h[i, j] + s >= slv: return (px - slv) / PIP
            if tpv is not None and l[i, j] + s <= tpv: return (px - tpv) / PIP
            ext = min(ext, l[i, j] + s)
            if trail is not None: slv = min(slv if slv is not None else 1e9, ext + trail * PIP)
            if be is not None and px - ext >= be * PIP: slv = min(slv if slv is not None else 1e9, px)
    x = c[i, end - 1]; return (x - px) / PIP if d > 0 else (px - (x + s)) / PIP

VARS = {}
for sl in (10, 20, 30):
    for tp in (None, 10, 20, 40): VARS[f"SL{sl}/TP{tp or 'none'}"] = dict(sl=sl, tp=tp, trail=None, be=None)
for tr in (10, 20): VARS[f"trail{tr}(init SL20)"] = dict(sl=20, tp=None, trail=tr, be=None)
for bt in (10, 20):
    for tp in (None, 40): VARS[f"BE@{bt}+SL20/TP{tp or 'none'}"] = dict(sl=20, tp=tp, trail=None, be=bt)
ENTRIES = {"breakout(00-03 range)": entry_breakout, "trend_continue": entry_trend, "naive_long": lambda i, S: entry_naive(i, S, 1), "naive_short": lambda i, S: entry_naive(i, S, -1)}
rows, ser = [], {}
for en, ef in ENTRIES.items():
    for vn, kw in VARS.items():
        res = {}
        for cn, S in (("gross", 0.0), ("opt", 0.6), ("normal", 1.5)):
            r = np.full(N, np.nan)
            for i in range(N):
                e = ef(i, S)
                if e is not None: r[i] = run_exit(i, e, S, **kw)
            res[cn] = r
        ser[(en, vn)] = pd.Series(res["normal"], index=t)
        for cn, r in res.items():
            x = r[~np.isnan(r)]; rows.append((en, vn, cn, len(x), x.mean(), x.mean() / (x.std() / np.sqrt(len(x))), (x > 0).mean()))
T = pd.DataFrame(rows, columns=["entry", "exit", "cost", "n", "mean_pips", "t", "win"]); T.to_csv(OUT / "p19_exit_grid.csv", index=False)
pd.set_option("display.width", 200)
for cn in ("gross", "opt", "normal"):
    x = T[T.cost == cn]; print(f"\n=== {cn}: top 6 of {len(x)} cells; cells with mean>0: {(x.mean_pips>0).sum()} ==="); print(x.sort_values("mean_pips", ascending=False).head(6).round(2).to_string(index=False))
X = pd.DataFrame(ser).fillna(0.0); sp = SPA(np.zeros(len(X)), -X.values, block_size=10, reps=1000, bootstrap="stationary", seed=1); sp.compute()
print(f"\nSPA / Reality Check over {X.shape[1]} entry x exit variants (normal cost): best {X.mean().idxmax()} {X.mean().max():+.3f} pips/day | RC p={sp.pvalues['upper']:.3f} SPA p={sp.pvalues['consistent']:.3f}")
