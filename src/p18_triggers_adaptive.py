"""(1) which clock minutes inside 01:30-05:30 NY drive the range; (2) calendar proxies (day-of-month ~ EZ PMI/Ifo/ZEW/HICP) as a substitute for the missing EU calendar;
(3) regime-adaptive score (ATR relative to its own trailing 250d median) vs the absolute-pip score."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from common import *
pd.set_option("display.width", 220)
A = pd.read_parquet(OUT / "p15_day_table.parquet")

# ---- (1) minute-of-day surge inside the window -------------------------------------------------------------------------------------
g = pd.read_parquet(D / "GBPUSD_M1_utc.parquet"); g = g[g.index >= "2016-01-01"]
g.index = g.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None); c = g.c.asfreq("1min").ffill(limit=5)
mv = (c.shift(-4) - c.shift(1)).abs() / PIP                                   # |5-min move| starting at each minute
mv = mv[(mv.index.dayofweek < 5)].dropna(); mod = mv.index.hour * 60 + mv.index.minute
ons = set(pd.read_csv(D / "news" / "ons_release_dates.csv", parse_dates=["date"]).date); isuk = pd.Series(mv.index.normalize().isin(ons), index=mv.index)
w = (mod >= 90) & (mod < 330); base = mv[w].median()
prof = mv[w].groupby(mod[w]).mean(); prof_uk = mv[w & isuk.values].groupby(mod[w & isuk.values]).mean(); prof_no = mv[w & ~isuk.values].groupby(mod[w & ~isuk.values]).mean()
print(f"(1) mean |5-min move| by NY start minute, 01:30-05:30 (2016-26, median minute {base:.1f} pips). Top 12 minutes:")
top = prof.sort_values(ascending=False).head(12)
for m_, v in top.items(): print(f"    {m_//60:02d}:{m_%60:02d}  all {v:5.1f} | UK-release days {prof_uk.get(m_, np.nan):5.1f} | other days {prof_no.get(m_, np.nan):5.1f}  ({v/base:.1f}x median)")
marks = {"02:00": 120, "02:30": 150, "03:00": 180, "03:30": 210, "04:00": 240, "04:30": 270, "05:00": 300}
print("    clock marks:", {k: round(prof[v], 1) for k, v in marks.items()}, "| non-UK days:", {k: round(prof_no[v], 1) for k, v in marks.items()})

# ---- (2) calendar proxies ----------------------------------------------------------------------------------------------------------
A["dom"] = A.index.day; A["wom"] = (A.dom - 1) // 7
A["last_week"] = (A.dom >= 22).astype(int); A["mid_month_tue"] = ((A.dom.between(10, 17)) & (A.index.dayofweek == 1)).astype(int); A["month_turn"] = ((A.dom <= 2) | (A.dom >= 29)).astype(int)
print("\n(2) calendar proxies, P(big range) [base %.3f] and mean 00-05 range:" % A.big_rng.mean())
for f in ("wom", "last_week", "mid_month_tue", "month_turn"):
    t = A.groupby(f).agg(n=("rng", "size"), P_big=("big_rng", "mean"), rng=("rng", "mean")); print(f"  {f}:", {k: (int(r.n), round(r.P_big, 3), round(r.rng, 1)) for k, r in t.iterrows()})
# lift after controlling for ATR
import statsmodels.api as sm
Xc = sm.add_constant(A[["atr14", "last_week", "mid_month_tue", "month_turn", "ukdata"]].astype(float)); m = sm.Logit(A.big_rng.astype(int), (Xc - Xc.mean()) / Xc.std().replace(0, 1) if False else Xc).fit(disp=0)
print("  logit (raw units) big_rng ~ atr14 + flags: ", {k: (round(v, 3), round(m.pvalues[k], 3)) for k, v in m.params.items() if k != "const"})

# ---- (3) adaptive vs absolute score --------------------------------------------------------------------------------------------------
A["atr_rel"] = A.atr14 / A.atr14.rolling(250, min_periods=120).median().shift(1); A["prev_rel"] = A.prev_rng / A.atr14
Ab = ["atr14", "prev_rng", "asia_rel", "ukdata"]; Ad = ["atr_rel", "prev_rel", "asia_rel", "ukdata"]; Ad2 = Ad + ["last_week", "mid_month_tue", "month_turn"]
A = A.dropna(subset=Ab + Ad); tr = A[A.yr <= 2015]; te = A[A.yr >= 2016]
def build(F):
    mdl = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500)).fit(tr[F], tr.big_rng.astype(int)); s = mdl.predict_proba(A[F])[:, 1]
    cuts = pd.Series(mdl.predict_proba(tr[F])[:, 1]).quantile([.2, .4, .6, .8]).values; return s, np.digitize(s, cuts) + 1
res = {}
for lab, F in (("absolute-pip score", Ab), ("regime-adaptive score", Ad), ("adaptive + calendar flags", Ad2)):
    s, q = build(F); A[f"s_{lab}"], A[f"q_{lab}"] = s, q; T2 = A[A.yr >= 2016]
    auc = roc_auc_score(T2.big_rng.astype(int), T2[f"s_{lab}"]); by = {}
    for a, b in ((2016, 2019), (2020, 2022), (2023, 2026)):
        z = T2[(T2.yr >= a) & (T2.yr <= b)]; by[f"{a}-{b}"] = (round(roc_auc_score(z.big_rng.astype(int), z[f"s_{lab}"]), 3), round((z[f"q_{lab}"] == 5).mean(), 2), round(z[z[f"q_{lab}"] == 5].big_rng.mean(), 2) if (z[f"q_{lab}"] == 5).any() else np.nan)
    print(f"\n(3) {lab}: OOS AUC 2016-26 = {auc:.3f} | per period (AUC, share of nights in Q5, P(big|Q5)): {by}")
    cal = T2.groupby(f"q_{lab}").agg(n=("rng", "size"), P_big=("big_rng", "mean"), rng=("rng", "mean")); print("   quintile P(big):", cal.P_big.round(2).tolist(), "| mean range:", cal.rng.round(0).tolist(), "| n:", cal.n.tolist())
