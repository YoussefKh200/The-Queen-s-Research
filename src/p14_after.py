"""What happens AFTER the big 00:00-05:00 NY move. Signal known at 05:00 NY; forward outcomes from 05:00 open."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from common import *
pd.set_option("display.width", 220)
g = pd.read_parquet(D / "GBPUSD_M1_utc.parquet"); g = g[g.index >= "2010-11-15"]
g.index = g.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None); c = g.c.ffill(limit=5); h, l = g.h, g.l
days = pd.DatetimeIndex(sorted({d for d in g.index.normalize() if d.dayofweek < 5}))
def at(d, hh, mm=0): return d + pd.Timedelta(hours=hh, minutes=mm)
rows = []
for d in days:
    t0, t5 = at(d, 0), at(d, 5); o0 = c.get(t0 - pd.Timedelta(minutes=1), np.nan); c5 = c.get(t5 - pd.Timedelta(minutes=1), np.nan)
    if np.isnan(o0) or np.isnan(c5): continue
    w = slice(t0, t5 - pd.Timedelta(minutes=1)); hi, lo = h[w].max(), l[w].min()
    r = {"date": d, "move": (c5 - o0) / PIP, "rng": (hi - lo) / PIP, "hi": hi, "lo": lo, "px5": c5}
    for lab, e in (("1h", at(d, 6)), ("3h", at(d, 8)), ("7h", at(d, 12)), ("12h", at(d, 17))):   # to 06:00, 08:00, 12:00, 17:00 NY
        r[f"f{lab}"] = (c.get(e - pd.Timedelta(minutes=1), np.nan) - c5) / PIP
    fw = slice(t5, at(d, 12) - pd.Timedelta(minutes=1)); r["f_hi"] = (h[fw].max() - c5) / PIP; r["f_lo"] = (c5 - l[fw].min()) / PIP   # 05:00-12:00 excursions
    rows.append(r)
T = pd.DataFrame(rows).set_index("date").dropna(); T["yr"] = T.index.year
T["thr75"] = T.move.abs().expanding(250).quantile(.75).shift(1)         # no-lookahead 'big' threshold (prior days only)
print(f"days n={len(T)} | window net move |mean| {T.move.abs().mean():.1f} pips, median {T.move.abs().median():.1f}, p75 {T.move.abs().quantile(.75):.1f}, p90 {T.move.abs().quantile(.9):.1f}")
def summ(sub, lab):
    s = np.sign(sub.move); out = {"bucket": lab, "n": len(sub)}
    for k in ("1h", "3h", "7h", "12h"):
        f = sub[f"f{k}"] * s; out[f"P_cont_{k}"] = (f > 0).mean(); out[f"mean_{k}"] = f.mean(); out[f"t_{k}"] = stats.ttest_1samp(f, 0).statistic if len(f) > 2 else np.nan
    # retracement: after a move, how often does price give back >=50% of the window move by 12:00 NY?
    adv = np.where(s > 0, sub.f_lo, sub.f_hi); fav = np.where(s > 0, sub.f_hi, sub.f_lo); m = sub.move.abs().values
    out["P_retrace>=50%"] = (adv >= 0.5 * m).mean(); out["P_new_extreme"] = (np.where(s > 0, sub.px5 + sub.f_hi * PIP > sub.hi, sub.px5 - sub.f_lo * PIP < sub.lo)).mean()
    out["med_fav_pips"] = np.median(fav); out["med_adv_pips"] = np.median(adv); return out
buckets = {"all days": T, "|move|<10": T[T.move.abs() < 10], "10-25": T[T.move.abs().between(10, 25)], "25-40": T[T.move.abs().between(25, 40)], ">=40": T[T.move.abs() >= 40],
           "big (>=p75, no-lookahead)": T[T.move.abs() >= T.thr75], "big UP (>=p75)": T[(T.move >= T.thr75)], "big DOWN (<=-p75)": T[(T.move <= -T.thr75)]}
R = pd.DataFrame([summ(v, k) for k, v in buckets.items()]).set_index("bucket"); R.to_csv(OUT / "p14_after_big_move.csv")
print("\nForward outcome in the DIRECTION of the 00-05 move (from 05:00 NY): P(cont) = share of days price ends further in that direction")
print(R[["n", "P_cont_1h", "P_cont_3h", "P_cont_7h", "P_cont_12h", "mean_1h", "mean_3h", "mean_7h", "mean_12h"]].round(2).to_string())
print("\nt-stats (mean != 0):"); print(R[["t_1h", "t_3h", "t_7h", "t_12h"]].round(2).to_string())
print("\nGiveback / extension by 12:00 NY:"); print(R[["P_retrace>=50%", "P_new_extreme", "med_fav_pips", "med_adv_pips"]].round(2).to_string())
B = T[T.move.abs() >= T.thr75]
print("\nBig-move days, halves (mean signed fwd pips 5->12 NY; +=continuation):", {p: round((B[m]["f7h"] * np.sign(B[m].move)).mean(), 2) for p, m in (("2010-17", B.yr <= 2017), ("2018-26", B.yr >= 2018))})
# unsigned expectation: how much further does it move in absolute terms?
print(f"\nAfter a big move, typical FURTHER range 05:00-12:00: median {np.median(B.f_hi+B.f_lo):.0f} pips (all days {np.median(T.f_hi+T.f_lo):.0f}); mean |7h move| {B.f7h.abs().mean():.1f} vs {T.f7h.abs().mean():.1f}")
# next-day-of-week and vs prior-day dependence skipped; also the 'day extreme' question
dh = T.hi; print(f"P(the 00-05 high or low is the day's (00-17) extreme): compute below")
ext = []
for d in T.index:
    day = slice(d, at(d, 17) - pd.Timedelta(minutes=1)); ext.append((h[day].max() <= T.loc[d, 'hi'] + 1e-9, l[day].min() >= T.loc[d, 'lo'] - 1e-9))
ext = np.array(ext); print(f"  window high stays day high {ext[:,0].mean():.2f}, window low stays day low {ext[:,1].mean():.2f}, both {(ext[:,0]&ext[:,1]).mean():.2f}, neither {(~ext[:,0]&~ext[:,1]).mean():.2f}")
