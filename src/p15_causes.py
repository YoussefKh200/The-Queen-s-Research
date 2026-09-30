"""What precedes / causes the big 00:00-05:00 NY move.
(a) pre-window conditions -> P(big); (b) intrawindow build-up & trigger; (c) mechanism (USD vs GBP, sweep, news)."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from common import *
pd.set_option("display.width", 230)

def ny_frame(sym):
    g = pd.read_parquet(D / f"{sym}_M1_utc.parquet"); g = g[g.index >= "2010-11-15"]
    g.index = g.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None); return g

G = ny_frame("GBPUSD"); c, h, l = G.c.ffill(limit=5), G.h, G.l
X = {s: ny_frame(s).c.ffill(limit=5) for s in ("EURUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF")}
ons = pd.read_csv(D / "news" / "ons_release_dates.csv", parse_dates=["date"]); onsd = set(ons.date)
days = pd.DatetimeIndex(sorted({d for d in G.index.normalize() if d.dayofweek < 5}))
MIN = pd.Timedelta(minutes=1)
def T(d, hh, mm=0): return d + pd.Timedelta(hours=hh, minutes=mm)
def px(s, t): return s.get(t - MIN, np.nan)                       # price at open of minute t
def rg(a, b):
    w = slice(a, b - MIN); return (h[w].max() - l[w].min()) / PIP, h[w].max(), l[w].min()

rows = []
for d in days:
    t0, t2, t5 = T(d, 0), T(d, 2), T(d, 5); o0, p2, c5 = px(c, t0), px(c, t2), px(c, t5)
    if np.isnan([o0, p2, c5]).any(): continue
    wr, _, _ = rg(t0, t5); r02, h02, l02 = rg(t0, t2); r25, h25, l25 = rg(t2, t5); asia, _, _ = rg(T(d, -5), t0)
    y = d - pd.Timedelta(days=1 if d.dayofweek else 3)
    pdr, _, _ = rg(T(y, 0), T(y, 17))
    row = dict(date=d, move=(c5 - o0) / PIP, rng=wr, rng25=r25, net25=(c5 - p2) / PIP, net02=(p2 - o0) / PIP, rng02=r02, asia=asia, prev_rng=pdr,
               prev_ny_ret=(px(c, T(y, 17)) - px(c, T(y, 8))) / PIP, prev_lon_ret=(px(c, T(y, 8)) - px(c, T(y, 3))) / PIP,
               eve_drift=(o0 - px(c, T(y, 17))) / PIP, prev_absret=abs(px(c, T(y, 17)) - px(c, T(y, 0))) / PIP,
               dow=d.dayofweek, month=d.month, ukdata=int(d in onsd), break_up=int(h25 > h02), break_dn=int(l25 < l02))
    seg_h, seg_l = h[t2:t5 - MIN], l[t2:t5 - MIN]; tu, td = seg_h > h02, seg_l < l02
    fu = tu.idxmax() if tu.any() else pd.NaT; fd = td.idxmax() if td.any() else pd.NaT
    if pd.notna(fu) or pd.notna(fd):
        row["first_break"] = 1 if (pd.isna(fd) or (pd.notna(fu) and fu <= fd)) else -1; row["both_breaks"] = int(pd.notna(fu) and pd.notna(fd))
    cm = (c[t0:t5 - MIN].iloc[::5] - o0) / PIP; fin = abs((c5 - o0) / PIP)
    hit = cm[cm.abs() >= 0.5 * fin] if fin > 0 else cm[:0]; row["onset_h"] = ((hit.index[0] - t0).total_seconds() / 3600) if len(hit) else np.nan
    lr = lambda s: np.log(px(s, t5) / px(s, t0)) * 1e4
    try: row["usd_fac"] = -(lr(X["EURUSD"]) + lr(X["AUDUSD"]) + lr(X["NZDUSD"])) / 3 + (lr(X["USDJPY"]) + lr(X["USDCAD"]) + lr(X["USDCHF"])) / 3
    except Exception: row["usd_fac"] = np.nan
    rows.append(row)

A = pd.DataFrame(rows).set_index("date"); A["yr"] = A.index.year
A["atr14"] = A.prev_rng.rolling(14).mean(); A["asia_rel"] = A.asia / A.atr14; A["rng02_rel"] = A.rng02 / A.atr14
ex = lambda s: s.expanding(250).quantile(.75).shift(1)
A["big_rng"] = A.rng >= ex(A.rng); A["big_net"] = A.move.abs() >= ex(A.move.abs()); A["big25"] = A.rng25 >= ex(A.rng25)
A = A.dropna(subset=["atr14", "prev_rng"]); A = A[A.index >= A.index[0]].copy()
A = A[~ex(A.rng).isna()]; A.to_parquet(OUT / "p15_day_table.parquet")
print(f"days n={len(A)}; base P(big range)={A.big_rng.mean():.3f}, P(big net)={A.big_net.mean():.3f}")

# (a) univariate lift -----------------------------------------------------------------------------------------------------------
print("\n(a) PRE-WINDOW conditions (known at 00:00 NY): P(big) by quartile of feature [base ~0.25]")
parts = []
for f in ("asia", "asia_rel", "prev_rng", "atr14", "prev_absret", "eve_drift", "prev_ny_ret", "prev_lon_ret"):
    s = A[f].abs() if f in ("eve_drift", "prev_ny_ret", "prev_lon_ret") else A[f]
    q = pd.qcut(s, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"], duplicates="drop")
    parts.append(pd.concat({f + (" (abs)" if f in ("eve_drift", "prev_ny_ret", "prev_lon_ret") else ""): A.groupby(q, observed=True).agg(P_bigrng=("big_rng", "mean"), P_bignet=("big_net", "mean"), mean_rng=("rng", "mean"))}, names=["feature"]))
print(pd.concat(parts).round(3).to_string())
print("\nweekday (Mon..Fri) P(big range):", A.groupby("dow").big_rng.mean().round(2).tolist(), "| mean range:", A.groupby("dow").rng.mean().round(1).tolist())
u1, u0 = A[A.ukdata == 1], A[A.ukdata == 0]
print(f"UK data day: P(big rng) {u1.big_rng.mean():.3f} vs {u0.big_rng.mean():.3f} | mean rng {u1.rng.mean():.1f} vs {u0.rng.mean():.1f} (n={len(u1)})")

# (a2) multivariate walk-forward ------------------------------------------------------------------------------------------------
F0 = ["asia_rel", "prev_rng", "atr14", "prev_absret", "eve_drift", "prev_ny_ret", "prev_lon_ret", "dow", "ukdata", "month"]
F2 = F0 + ["rng02_rel", "rng02", "net02"]
def wf(F, target, lab):
    e = A.dropna(subset=F); y = e[target].astype(int); ps = pd.Series(np.nan, index=e.index)
    mk = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500))
    for yr in range(2016, 2027):
        tr, te = e.yr < yr, e.yr == yr
        if te.sum(): ps[te] = mk().fit(e.loc[tr, F], y[tr]).predict_proba(e.loc[te, F])[:, 1]
    ok = ps.notna(); coef = pd.Series(mk().fit(e[F], y)[-1].coef_[0], index=F).sort_values(key=abs, ascending=False); top = ps[ok] >= ps[ok].quantile(.8)
    print(f"  {lab}: OOS AUC {roc_auc_score(y[ok], ps[ok]):.3f} | top-quintile predicted: P(big)={y[ok][top].mean():.2f} vs base {y[ok].mean():.2f} | std coefs: " + ", ".join(f"{k} {v:+.2f}" for k, v in coef.head(5).items()))
print("\n(a2) Walk-forward logit 2016-26:")
wf(F0, "big_rng", "known at 00:00 NY -> big 00-05 range"); wf(F2, "big25", "known at 02:00 NY -> big 02-05 range")

# (b) timeline ----------------------------------------------------------------------------------------------------------------------
Bg, Nm = A[A.big_net], A[~A.big_net]
pct = lambda s: s.dropna().apply(lambda v: int(np.floor(v))).value_counts(normalize=True).sort_index().round(2).to_dict()
print(f"\n(b) TIMELINE. Hour (NY) when 50% of the final 00-05 move is done: big days {pct(Bg.onset_h)} | normal {pct(Nm.onset_h)}")
print(f"    before the window: 19-00 Asia range big {Bg.asia.mean():.1f} vs normal {Nm.asia.mean():.1f} pips | 00-02 range {Bg.rng02.mean():.1f} vs {Nm.rng02.mean():.1f} | |net 00-02| {Bg.net02.abs().mean():.1f} vs {Nm.net02.abs().mean():.1f}")
print(f"    02-05 breaks the 00-02 range: big days up {Bg.break_up.mean():.2f} / down {Bg.break_dn.mean():.2f} | normal {Nm.break_up.mean():.2f} / {Nm.break_dn.mean():.2f} | both sides swept: big {Bg.both_breaks.mean():.2f} vs normal {Nm.both_breaks.mean():.2f}")
S = A.dropna(subset=["first_break"]); fin = np.sign(S.net25)
for lab, m in (("big-net days", S.big_net), ("normal days", ~S.big_net)):
    print(f"    {lab}: first break of the 00-02 range goes AGAINST the final 02-05 direction (stop-run then reverse) {(S.first_break[m] != fin[m]).mean():.2f}; with it {(S.first_break[m] == fin[m]).mean():.2f}; n={m.sum()}")

# (c) mechanism ---------------------------------------------------------------------------------------------------------------------
M = A.dropna(subset=["usd_fac"])
for lab, m in (("big-net", M.big_net), ("normal", ~M.big_net)):
    r = np.corrcoef(M[m].usd_fac, -M[m].move)[0, 1]; print(f"(c) {lab:8s}: corr(USD factor, -GBPUSD move) {r:+.2f} (R2 {r*r:.2f})")
print(f"    UK data present on {Bg.ukdata.mean():.0%} of big-net days vs {Nm.ukdata.mean():.0%} of normal days")
