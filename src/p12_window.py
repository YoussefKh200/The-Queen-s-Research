"""User's real claim: big move between NY 00:00 and 05:00 (UTC-4). H1 bars in NY time + M1 execution."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from arch.bootstrap import SPA
import engine; engine.PRE = 200; engine.POST = 400
from engine import matrices, simulate
from common import *
pd.set_option("display.width", 220)
g = pd.read_parquet(D / "GBPUSD_M1_utc.parquet"); g = g[g.index >= "2010-11-15"]
g.index = g.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)     # NY wall-clock
H1 = g.resample("1h").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
H1["rng"] = (H1.h - H1.l) / PIP; H1["ret"] = (H1.c - H1.o) / PIP; H1["hr"] = H1.index.hour; H1["d"] = H1.index.normalize(); H1 = H1[H1.index.dayofweek < 5]
print("=== H1 (NY clock) mean bar range by hour, pips ===")
print(H1.groupby("hr").rng.mean().round(1).to_frame().T.to_string())
# 5-hour window range starting each hour
P = H1.pivot(index="d", columns="hr", values=["h", "l", "o", "c"]).dropna(subset=[("h", h) for h in range(0, 5)])
print("\n=== 5-hour window range (H-L, pips) by start hour; rank of 00:00-05:00 ===")
res = {}
for s in range(0, 24 - 4):
    cols = [(k, (s + i)) for i in range(5) for k in ("h",)]; 
    hh = np.maximum.reduce([P[("h", s + i)].values for i in range(5)]) if all(("h", s + i) in P.columns for i in range(5)) else None
    if hh is None: continue
    ll = np.minimum.reduce([P[("l", s + i)].values for i in range(5)]); res[s] = np.nanmean((hh - ll) / PIP)
r = pd.Series(res); print(r.round(1).to_frame("mean range").T.to_string()); print(f"00:00-05:00 window rank {int(r.rank(ascending=False)[0])}/{len(r)}; mean {r[0]:.1f} pips (~{r[0]/r.mean():.2f}x avg 5h window)")
w = pd.DataFrame({"hi": np.maximum.reduce([P[("h", i)] for i in range(5)]), "lo": np.minimum.reduce([P[("l", i)] for i in range(5)]), "o": P[("o", 0)], "c": P[("c", 4)], "c3": P[("c", 2)], "o3": P[("o", 3)]}, index=P.index).dropna()
w["rng"] = (w.hi - w.lo) / PIP; w["ret"] = (w.c - w.o) / PIP; w["pre"] = (w.c3 - w.o) / PIP; w["post"] = (w.c - w.o3) / PIP
lon_share = np.mean([(P[("h", 3)].iloc[i] - P[("l", 3)].iloc[i]) for i in range(len(P))]) / PIP
print(f"\nwindow n={len(w)} | range mean {w.rng.mean():.1f} median {w.rng.median():.1f} | P(range>=40 pips)={(w.rng>=40).mean():.2f} | net 00->05 return: P(up)={(w.ret>0).mean():.3f} mean {w.ret.mean():+.2f} t={stats.ttest_1samp(w.ret,0).statistic:+.2f}")
print(f"direction persistence: corr(00-03 ret, 03-05 ret) = {stats.spearmanr(w.pre, w.post).statistic:+.3f} (p={stats.spearmanr(w.pre, w.post).pvalue:.3f}); P(same sign)={(np.sign(w.pre)==np.sign(w.post)).mean():.3f}")
# where in the window does the range happen?
h1w = H1[H1.hr.between(0, 4)].groupby("hr").rng.mean(); print("share of summed hourly range by NY hour (00..04):", (h1w / h1w.sum()).round(2).to_dict())
# ---- strategies anchored at NY 03:00 (London open), signals from 00:00-03:00 H1/M1 -------------------------------------------------
days = pd.date_range("2010-11-16", "2026-09-17", freq="B")
loc = pd.DatetimeIndex(days + pd.Timedelta(hours=3)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT"); t0 = loc[loc.notna()].tz_convert("UTC").tz_localize(None)
M, t = matrices(t0); PRE = engine.PRE; o, h, l, c = M["o"], M["h"], M["l"], M["c"]
b0 = PRE - 180                                                                      # 00:00 NY bar index
hi = h[:, b0:PRE].max(1); lo = l[:, b0:PRE].min(1); rng = (hi - lo) / PIP; pre = (c[:, PRE - 1] - o[:, b0]) / PIP
med = pd.Series(rng).expanding(30).median().shift(1).values; p80 = pd.Series(np.abs(pre)).expanding(30).quantile(.8).shift(1).values
r60 = (c[:, PRE + 59] - o[:, PRE]) / PIP; g1 = np.sign(r60)
def brk(i, gate):
    if rng[i] < 5 or (gate and not rng[i] >= med[i]): return None
    up = np.argmax(h[i, PRE:PRE + 90] >= hi[i]) if (h[i, PRE:PRE + 90] >= hi[i]).any() else 999
    dn = np.argmax(l[i, PRE:PRE + 90] <= lo[i]) if (l[i, PRE:PRE + 90] <= lo[i]).any() else 999
    if up == dn: return None
    return dict(d=1, bar=PRE, kind="stop", level=hi[i], until=PRE + 90, sl=lo[i]) if up < dn else dict(d=-1, bar=PRE, kind="stop", level=lo[i], until=PRE + 90, sl=hi[i])
S = {"S1_break_0-3_range": lambda i, M: brk(i, False), "S2_break+volfilter": lambda i, M: brk(i, True),
     "S3_trend_00-03_continue": lambda i, M: dict(d=int(np.sign(pre[i])), bar=PRE, kind="mkt") if np.isfinite(pre[i]) and pre[i] != 0 else None,
     "S4_fade_00-03": lambda i, M: dict(d=-int(np.sign(pre[i])), bar=PRE, kind="mkt") if np.isfinite(pre[i]) and pre[i] != 0 else None,
     "S5_strong_trend_continue": lambda i, M: dict(d=int(np.sign(pre[i])), bar=PRE, kind="mkt") if abs(pre[i]) >= p80[i] else None,
     "S6_after_first_London_H1_continue": lambda i, M: dict(d=int(np.sign((c[i, PRE + 59] - o[i, PRE]))), bar=PRE + 60, kind="mkt") if np.isfinite(c[i, PRE + 59] - o[i, PRE]) and c[i, PRE + 59] != o[i, PRE] else None,
     "S7_after_first_London_H1_fade": lambda i, M: dict(d=-int(np.sign((c[i, PRE + 59] - o[i, PRE]))), bar=PRE + 60, kind="mkt") if np.isfinite(c[i, PRE + 59] - o[i, PRE]) and c[i, PRE + 59] != o[i, PRE] else None,
     "naive_long_03:00": lambda i, M: dict(d=1, bar=PRE, kind="mkt"), "naive_short_03:00": lambda i, M: dict(d=-1, bar=PRE, kind="mkt")}
# NB S6/S7 use bar PRE+60 entry, so hold measured from PRE: holds below are from 03:00 (120 => exit 05:00)
COST = {"gross": 0.0, "opt": 0.6, "normal": 1.5, "stress": 3.0}; rows = []; ser = {}
for sn, fn in S.items():
    for hd in (120, 180):
        for cn, cs in COST.items():
            v = pd.Series(simulate(M, fn, hd, cs), index=t); x = v.dropna()
            if cn == "normal": ser[(sn, hd)] = v
            if len(x) < 30: continue
            rows.append((sn, hd, cn, len(x), x.mean(), x.mean() / (x.std() / np.sqrt(len(x))), (x > 0).mean(), x[x.index.year <= 2018].mean(), x[x.index.year >= 2019].mean()))
T = pd.DataFrame(rows, columns=["strategy", "hold_min_from_03:00", "cost", "n", "mean_pips", "t", "win", "IS<=2018", "OOS>=2019"]); T.to_csv(OUT / "p12_window_strategies.csv", index=False)
for cn in ("gross", "normal"): print(f"\n=== {cn} costs ===\n", T[T.cost == cn].round(2).drop(columns="cost").to_string(index=False))
X = pd.DataFrame(ser).fillna(0.0); sp = SPA(np.zeros(len(X)), -X.values, block_size=10, reps=1000, bootstrap="stationary", seed=1); sp.compute()
print(f"\nSPA/Reality Check over {X.shape[1]} strategies (normal cost): best={X.mean().idxmax()} mean {X.mean().max():+.3f} pips/day | RC p={sp.pvalues['upper']:.3f} SPA p={sp.pvalues['consistent']:.3f}")
