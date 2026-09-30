"""Sec 15: White Reality Check + Hansen SPA over the strategy grid (normal costs), Deflated Sharpe; Strategy G walk-forward ML."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from arch.bootstrap import SPA
from common import *
P = pd.read_parquet(OUT / "p6_daily_normal.parquet")
P.columns = pd.MultiIndex.from_tuples([tuple(c.split("|")) for c in P.columns], names=["anchor", "strategy", "hold"])
P = P.fillna(0.0)                                                    # no trade = 0 pips
def spa_block(cols, label):
    X = P[cols]; X = X.loc[:, X.abs().sum() > 0]
    sp = SPA(np.zeros(len(X)), -X.values, block_size=10, reps=1000, bootstrap="stationary", seed=1); sp.compute()
    p = sp.pvalues; best = X.mean().idxmax()
    print(f"{label:34s} n_strategies={X.shape[1]:3d}  best={best}  best mean={X[best].mean():+.3f} pips/day  | RC p={p['upper']:.3f}  SPA p={p['consistent']:.3f}  (lower p={p['lower']:.3f})")
    return X
print("=== White Reality Check / Hansen SPA (H0: no strategy beats 'do nothing' after NORMAL costs) ===")
XA = spa_block([c for c in P.columns if c[0] == "A"], "Anchor A (NY 00:00) only")
for a, lab in (("B", "Anchor B (04:00 UTC)"), ("C", "Anchor C (00:00 UTC)"), ("E", "Anchor E (17:00 NY rollover)")): spa_block([c for c in P.columns if c[0] == a], lab)
XAll = spa_block(list(P.columns), "ALL anchors pooled")
# ---- Deflated Sharpe for best-of-all -------------------------------------------------------------------------------
def dsr(best, X):
    sr = X.mean() / X.std(); N = X.shape[1]; T = len(X); sk = stats.skew(X[best]); ku = stats.kurtosis(X[best], fisher=False)
    g = 0.5772156649; sr0 = np.sqrt(sr.var()) * ((1 - g) * stats.norm.ppf(1 - 1 / N) + g * stats.norm.ppf(1 - 1 / (N * np.e)))
    z = (sr[best] - sr0) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr[best] + (ku - 1) / 4 * sr[best] ** 2)
    return sr[best] * np.sqrt(252), sr0 * np.sqrt(252), stats.norm.cdf(z), N
b = XAll.mean().idxmax(); a1, a0, d, N = dsr(b, XAll); print(f"\nDeflated Sharpe, best of {N} trials {b}: SR_ann={a1:.2f} vs null-expected-max SR_ann={a0:.2f} -> DSR probability(true SR>0)={d:.3f}")
bA = XA.mean().idxmax(); a1, a0, d, N = dsr(bA, XA); print(f"Deflated Sharpe, anchor A only, best of {N} {bA}: SR_ann={a1:.2f} vs null-max {a0:.2f} -> DSR={d:.3f}")
# ---- Strategy G: walk-forward ML ------------------------------------------------------------------------------------
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
FEAT = ["pre15", "pre60", "pre300", "pre1440", "rng15", "rng60", "rng300", "pos60", "pos300", "dist_pdh", "dist_pdl", "dist_pwh", "dist_pwl", "atr14", "EURUSD_pre60", "USDJPY_pre60", "dow", "month", "us_dst"]
print("\n=== Strategy G: walk-forward (expanding, yearly refit, test 2016-2026) predicting sign(60-min return); trade if p>0.55 long / p<0.45 short; cost=1.5 pips ===")
for anc in ("A", "C", "E"):
    e = pd.read_parquet(D / f"events_{anc}.parquet").dropna(subset=FEAT + ["r60"]); e = e[e.r60 != 0]; y = (e.r60 > 0).astype(int)
    for name, mk in (("logit", lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))), ("gbm", lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=5.0))):
        ps = pd.Series(np.nan, index=e.index)
        for yr in range(2016, 2027):
            tr = e.year < yr - 0; te = e.year == yr
            if te.sum() == 0: continue
            m = mk().fit(e.loc[tr, FEAT].astype(float), y[tr]); ps[te] = m.predict_proba(e.loc[te, FEAT].astype(float))[:, 1]
        ok = ps.notna(); auc = roc_auc_score(y[ok], ps[ok]); acc = ((ps[ok] > .5) == y[ok]).mean()
        d = np.where(ps > .55, 1, np.where(ps < .45, -1, 0)); pnl = pd.Series(np.where(d != 0, d * e.r60 - 1.5, np.nan), index=e.index)[ok].dropna()
        gross = pd.Series(np.where(d != 0, d * e.r60, np.nan), index=e.index)[ok].dropna()
        print(f"anchor {anc} {name:5s}: OOS n={ok.sum()} AUC={auc:.3f} acc={acc:.3f} | trades={len(pnl)} gross={gross.mean():+.2f} net={pnl.mean():+.2f} pips/trade (t={stats.ttest_1samp(pnl,0).statistic if len(pnl)>2 else np.nan:+.2f}) win={(pnl>0).mean():.2f}")
