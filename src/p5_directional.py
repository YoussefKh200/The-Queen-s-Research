"""Sec 4 + 9: directional stats at anchor A (NY 00:00) and comparison anchors; every slice tested, BH-FDR reported."""
import pandas as pd, numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from common import *
pd.set_option("display.width", 220)
def desc(v):
    v = v[~np.isnan(v)]; return dict(n=len(v), pup=(v > 0).mean(), mean=v.mean(), med=np.median(v), mabs=np.abs(v).mean(), sd=v.std(), skew=stats.skew(v), kurt=stats.kurtosis(v), t=stats.ttest_1samp(v, 0).statistic, p_sign=stats.binomtest(int((v > 0).sum()), len(v[v != 0])).pvalue)
for nm in ("A", "B", "C", "E"):
    e = pd.read_parquet(D / f"events_{nm}.parquet")
    print(f"\n===== anchor {nm}: full sample {e.index[0].date()}..{e.index[-1].date()} =====")
    print(pd.DataFrame({f"r{m}": desc(e[f"r{m}"].values) for m in (1, 5, 15, 30, 60, 120)}).round(3).to_string())
e = pd.read_parquet(D / "events_A.parquet")
tests = []
def add(label, sub, col="r60"):
    v = sub[col].dropna().values
    if len(v) >= 30: tests.append((label, col, len(v), v.mean(), stats.ttest_1samp(v, 0).pvalue))
for col in ("r15", "r60"):
    for k, g in e.groupby("dow"): add(f"dow={k}", g, col)
    for k, g in e.groupby("month"): add(f"month={k}", g, col)
    for k, g in e.groupby("year"): add(f"year={k}", g, col)
    for k, g in e.groupby("us_dst"): add(f"us_dst={k}", g, col)
    for k, g in e.groupby(["uk_dst", "us_dst"]): add(f"uk,us_dst={k}", g, col)
    # conditional-on-known-before features: sign / tercile of each
    for f in ("pre15", "pre60", "pre300", "pre1440", "pos300", "pos60", "rng300", "rng60", "atr14", "dist_pdh", "dist_pdl", "dist_pwh", "dist_pwl", "EURUSD_pre60", "USDJPY_pre60"):
        q = pd.qcut(e[f], 3, labels=["lo", "mid", "hi"], duplicates="drop")
        for k, g in e.groupby(q, observed=True): add(f"{f}={k}", g, col)
        # continuous predictive corr (Spearman) of feature with signed outcome
        r, p = stats.spearmanr(e[f], e[col], nan_policy="omit"); tests.append((f"spearman({f})", col, e[[f, col]].dropna().shape[0], r, p))
T = pd.DataFrame(tests, columns=["slice", "outcome", "n", "stat", "p"])
T["q_BH"] = multipletests(T.p, method="fdr_bh")[1]; T["p_bonf"] = np.minimum(T.p * len(T), 1)
T.to_csv(OUT / "p5_directional_slices.csv", index=False)
print(f"\n{len(T)} slice-tests at anchor A; raw p<0.05: {(T.p<0.05).sum()} (expected by chance ~{0.05*len(T):.1f}); BH q<0.05: {(T.q_BH<0.05).sum()}; Bonferroni<0.05: {(T.p_bonf<0.05).sum()}")
print(T.sort_values("p").head(10).round(4).to_string(index=False))
