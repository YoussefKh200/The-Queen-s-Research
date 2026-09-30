"""Frozen 'big-night' score (trained ONLY on 2010-2015, never refit) -> (1) calibration 2016-26, (2) does conditioning entries on it help, (3) stop-sizing table.
Score inputs known at 00:00 NY: ATR14, prior-day range, evening range/ATR, UK-data day."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from arch.bootstrap import SPA
import engine; engine.PRE = 200; engine.POST = 520
from engine import matrices, simulate
from common import *
pd.set_option("display.width", 220)

A = pd.read_parquet(OUT / "p15_day_table.parquet")
F = ["atr14", "prev_rng", "asia_rel", "ukdata"]; A = A.dropna(subset=F)
tr = A[A.yr <= 2015]; te = A[A.yr >= 2016]
model = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500)).fit(tr[F], tr.big_rng.astype(int))
A["score"] = model.predict_proba(A[F])[:, 1]
cuts = tr.assign(s=model.predict_proba(tr[F])[:, 1]).s.quantile([.2, .4, .6, .8]).values          # FIXED cutoffs from training data
A["q"] = np.digitize(A.score, cuts) + 1                                                          # 1 (calm) .. 5 (big-night)
te = A[A.yr >= 2016]
print(f"Frozen model trained on {len(tr)} days (2010-15). Test = {len(te)} days 2016-26, NO refit. coefs:", dict(zip(F, model[-1].coef_[0].round(2))))
print(f"OOS AUC (big 00-05 range) = {roc_auc_score(te.big_rng.astype(int), te.score):.3f} | (big 02-05 range) = {roc_auc_score(te.big25.astype(int), te.score):.3f}")
cal = te.groupby("q").agg(n=("rng", "size"), P_big=("big_rng", "mean"), mean_rng=("rng", "mean"), med_rng=("rng", "median"), p90_rng=("rng", lambda v: v.quantile(.9)), mean_rng25=("rng25", "mean"))
print("\n(1) CALIBRATION on 2016-26 by frozen-score quintile (1=calm ... 5=big night):\n", cal.round(2).to_string())
# stability by sub-period (top-quintile lift)
for a, b in ((2016, 2019), (2020, 2022), (2023, 2026)):
    s = te[(te.yr >= a) & (te.yr <= b)]; print(f"   {a}-{b}: Q5 P(big)={s[s.q == 5].big_rng.mean():.2f} (n={int((s.q==5).sum())}) vs Q1 {s[s.q == 1].big_rng.mean():.2f}; mean rng Q5 {s[s.q==5].rng.mean():.1f} vs Q1 {s[s.q==1].rng.mean():.1f}")

# ---- (2) entries at NY 03:00 conditioned on the score --------------------------------------------------------------------------------
days = pd.DatetimeIndex(A.index); loc = pd.DatetimeIndex(days + pd.Timedelta(hours=3)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
ok = loc.notna(); t0 = loc[ok].tz_convert("UTC").tz_localize(None); dmap = pd.Series(days[ok], index=t0)
M, t = matrices(t0); PRE = engine.PRE; o, h, l, c = M["o"], M["h"], M["l"], M["c"]; dts = dmap.reindex(t).values
b0 = PRE - 180; hi = h[:, b0:PRE].max(1); lo = l[:, b0:PRE].min(1); pre = (c[:, PRE - 1] - o[:, b0]) / PIP
def brk(i):
    if (hi[i] - lo[i]) / PIP < 5: return None
    a, b = h[i, PRE:PRE + 90] >= hi[i], l[i, PRE:PRE + 90] <= lo[i]
    up, dn = (np.argmax(a) if a.any() else 999), (np.argmax(b) if b.any() else 999)
    if up == dn: return None
    return dict(d=1, bar=PRE, kind="stop", level=hi[i], until=PRE + 90, sl=lo[i]) if up < dn else dict(d=-1, bar=PRE, kind="stop", level=lo[i], until=PRE + 90, sl=hi[i])
S = {"S1_break_00-03_range": lambda i, M: brk(i),
     "S3_trend_continue": lambda i, M: dict(d=int(np.sign(pre[i])), bar=PRE, kind="mkt") if np.isfinite(pre[i]) and pre[i] != 0 else None,
     "S4_fade": lambda i, M: dict(d=-int(np.sign(pre[i])), bar=PRE, kind="mkt") if np.isfinite(pre[i]) and pre[i] != 0 else None}
qs = A.q.reindex(pd.DatetimeIndex(dts)).values; yrs = pd.DatetimeIndex(dts).year
rows, ser = [], {}
print("\n(2) Net pips/trade by score quintile (2016-26 only), hold to 08:00 NY (300 min). cols: gross | net@0.6 | net@1.5")
for sn, fn in S.items():
    for hd in (120, 300):
        res = {cn: simulate(M, fn, hd, cs) for cn, cs in (("g", 0.0), ("o", 0.6), ("n", 1.5))}
        ser[(sn, hd)] = pd.Series(res["n"], index=pd.DatetimeIndex(dts))
        for q in (1, 2, 3, 4, 5, "all"):
            m = (yrs >= 2016) & ((qs == q) if q != "all" else True)
            g, o_, n_ = (res[k][m] for k in "gon"); v = ~np.isnan(g)
            if v.sum() < 30: continue
            rows.append((sn, hd, q, int(v.sum()), np.nanmean(g), np.nanmean(o_), np.nanmean(n_), stats.ttest_1samp(g[v], 0).statistic))
R = pd.DataFrame(rows, columns=["strategy", "hold", "quintile", "n", "gross", "net0.6", "net1.5", "t_gross"]); R.to_csv(OUT / "p16_score_conditioned.csv", index=False)
print(R.round(2).to_string(index=False))
# top-vs-bottom difference & SPA on top quintile only
X = pd.DataFrame({k: v.where((v.index.year >= 2016) & (pd.Series(qs, index=v.index) == 5).values, 0.0).fillna(0.0) for k, v in ser.items()})
X = X[X.index.year >= 2016]; sp = SPA(np.zeros(len(X)), -X.values, block_size=10, reps=1000, bootstrap="stationary", seed=1); sp.compute()
print(f"\nSPA/RC over {X.shape[1]} strategy-holds traded ONLY on Q5 nights (normal cost 1.5): best {X.mean().idxmax()} {X.mean().max():+.3f} pips/day | RC p={sp.pvalues['upper']:.3f}  SPA p={sp.pvalues['consistent']:.3f}")

# ---- (3) stop-sizing table: excursions from 03:00 open to 08:00 by quintile ------------------------------------------------------------
e = pd.DataFrame({"q": qs, "yr": yrs, "up": (h[:, PRE:PRE + 300].max(1) - o[:, PRE]) / PIP, "dn": (o[:, PRE] - l[:, PRE:PRE + 300].min(1)) / PIP, "rng": (h[:, PRE:PRE + 300].max(1) - l[:, PRE:PRE + 300].min(1)) / PIP}).dropna()
e = e[e.yr >= 2016]; e["worst"] = e[["up", "dn"]].max(1)
tab = e.groupby("q").agg(n=("rng", "size"), rng_p50=("rng", "median"), rng_p75=("rng", lambda v: v.quantile(.75)), rng_p90=("rng", lambda v: v.quantile(.9)),
                         either_side_p50=("worst", "median"), either_side_p90=("worst", lambda v: v.quantile(.9)))
print("\n(3) STOP-SIZING: pips from the 03:00 NY open over the next 5h (to 08:00), 2016-26, by frozen-score quintile:\n", tab.round(0).to_string())
tab.to_csv(OUT / "p16_stop_sizing.csv")
