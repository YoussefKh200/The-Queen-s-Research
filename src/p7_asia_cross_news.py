"""Sec 5 (Asian range breakouts vs hour-by-hour null), Sec 8 (cross-asset), Sec 7 (news/outlier proxies), Sec 16 (regimes)."""
import pandas as pd, numpy as np
from scipy import stats
from common import *
pd.set_option("display.width", 220)
G = m1("GBPUSD", "2010-11-15"); h, l, c = G.h, G.l, G.c.ffill(limit=5); ix = G.index
days = pd.date_range("2010-11-16", "2026-09-17", freq="B")
def ny_utc(hh, mm=0):
    loc = pd.DatetimeIndex(days + pd.Timedelta(hours=hh, minutes=mm)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    return loc[loc.notna()].tz_convert("UTC").tz_localize(None)
# ---- Sec 5: 5h trailing range (Asian-style) then first-60-min break behaviour, at every NY hour 20..05 -----------------------
H5, L5 = h.rolling(300, min_periods=200).max(), l.rolling(300, min_periods=200).min()
FH, FL = h[::-1].rolling(60, min_periods=40).max()[::-1], l[::-1].rolling(60, min_periods=40).min()[::-1]
print("=== Sec 5: break of trailing-5h range within first 60min after each NY-local hour (weekdays 2010-2026) ===")
rows = []
for hr in list(range(19, 24)) + list(range(0, 6)):
    t0 = ny_utc(hr); t0 = t0[(t0 > ix[400]) & (t0 < ix[-1] - pd.Timedelta(hours=2))]; tm = t0 - pd.Timedelta(minutes=1)
    hi, lo = H5.reindex(tm).values, L5.reindex(tm).values; fh, fl = FH.reindex(t0).values, FL.reindex(t0).values
    cl60 = c.reindex(t0 + pd.Timedelta(minutes=59)).values; op = c.reindex(tm).values
    up, dn = fh >= hi, fl <= lo; okv = ~(np.isnan(hi) | np.isnan(fh) | np.isnan(cl60))
    bu, bd = up & ~dn & okv, dn & ~up & okv
    cont_u = (cl60[bu] > hi[bu]); cont_d = (cl60[bd] < lo[bd])
    rev = np.r_[(cl60[bu] < hi[bu]), (cl60[bd] > lo[bd])]
    ft = np.r_[(cl60[bu] - hi[bu]), (lo[bd] - cl60[bd])] / PIP                     # follow-through beyond broken level, pips
    both = (up & dn & okv).mean(); pb = (bu | bd)[okv].mean()
    pc = np.r_[cont_u, cont_d].mean(); n = len(np.r_[cont_u, cont_d])
    rows.append(dict(hour_NY=hr, n=int(okv.sum()), P_break_one_side=pb, P_both=both, P_continue_given_break=pc, binom_p=stats.binomtest(int(np.r_[cont_u, cont_d].sum()), n).pvalue,
                     mean_follow_pips=ft.mean(), t_follow=stats.ttest_1samp(ft, 0).statistic, range_pips=np.nanmean((hi - lo) / PIP)))
T5 = pd.DataFrame(rows); T5.to_csv(OUT / "p7_asian_break_by_hour.csv", index=False); print(T5.round(3).to_string(index=False))
# ---- Sec 8: cross-asset at anchor A (NY 00:00) -----------------------------------------------------------------------------------
print("\n=== Sec 8: cross-asset moves at NY 00:00 (pips-equivalent returns in bp), 60min and 15min ===")
t0 = ny_utc(0); t0 = t0[(t0 > ix[400]) & (t0 < ix[-1] - pd.Timedelta(hours=2))]
S = {s: m1(s, "2010-11-15").c.ffill(limit=5) for s in ("GBPUSD", "EURUSD", "USDJPY", "SPXUSD", "NSXUSD")}
S["GBPJPY"] = S["GBPUSD"] * S["USDJPY"]; S["EURGBP"] = S["EURUSD"] / S["GBPUSD"]
def ret(s, t, m): return (np.log(s.reindex(t + pd.Timedelta(minutes=m - 1)).values) - np.log(s.reindex(t - pd.Timedelta(minutes=1)).values)) * 1e4
for m in (15, 60):
    R = pd.DataFrame({k: ret(v, t0, m) for k, v in S.items()}, index=t0).dropna(subset=["GBPUSD", "EURUSD", "USDJPY"])
    print(f"\n-- {m}min | n={len(R)} | corr with GBPUSD:", R.corr()["GBPUSD"].drop("GBPUSD").round(2).to_dict())
    big = R[np.abs(R.GBPUSD) >= np.abs(R.GBPUSD).quantile(.9)]
    usd = ((np.sign(big.EURUSD) == np.sign(big.GBPUSD)) & (np.sign(big.USDJPY) == -np.sign(big.GBPUSD))).mean()
    gbp = ((np.sign(big.EURGBP) == -np.sign(big.GBPUSD)) & (np.sign(big.GBPJPY) == np.sign(big.GBPUSD))).mean()
    print(f"   top-decile |GBPUSD| moves (n={len(big)}): USD-broad pattern {usd:.0%} | GBP-specific pattern {gbp:.0%} (independence would give ~{0.25:.0%} each)")
    Xr = R[["EURUSD", "EURGBP"]].dropna(); yy = R.loc[Xr.index, "GBPUSD"]
    beta = np.linalg.lstsq(np.c_[np.ones(len(Xr)), Xr.values], yy.values, rcond=None)[0]; res = yy.values - np.c_[np.ones(len(Xr)), Xr.values] @ beta
    print(f"   GBPUSD = a + b1*EURUSD + b2*EURGBP: R^2={1-res.var()/yy.var():.2f}  b(EURUSD)={beta[1]:.2f} b(EURGBP)={beta[2]:.2f}")
# ---- Sec 7: news/outlier robustness at anchor A -----------------------------------------------------------------------------------
print("\n=== Sec 7: robustness of the (null) midnight result to event/outlier exclusion. NOTE: no tier-1 release is scheduled 00:00-01:00 NY ===")
e = pd.read_parquet(D / "events_A.parquet")
first_fri = (e.index.dayofweek == 4) & (e.index.day <= 7)
xmas = ((e.month == 12) & (e.dom >= 23)) | ((e.month == 1) & (e.dom <= 3))
tail = np.abs(e.r15) >= np.abs(e.r15).quantile(.98)
for lab, m in {"all days": np.ones(len(e), bool), "excl first-Friday(NFP day)": ~first_fri, "excl Christmas/New-Year": ~xmas, "excl top-2% |r15| days": ~tail, "normal days (all three)": ~first_fri & ~xmas & ~tail}.items():
    v = e[m]; print(f"{lab:32s} n={len(v):4d}  mean|r15|={v.r15.abs().mean():.2f}  mean|r60|={v.r60.abs().mean():.2f}  P(up15)={(v.r15>0).mean():.3f}  mean r15={v.r15.mean():+.3f} (t={stats.ttest_1samp(v.r15,0).statistic:+.2f})")
# ---- Sec 16: regimes -------------------------------------------------------------------------------------------------------------
print("\n=== Sec 16: |r15| at NY 00:00 vs all-hours baseline by regime (ratio to same-year mean |15m| move at NY 00:00-06:00...) ===")
base15 = np.abs((c.shift(-14) - c.shift(1)) / PIP)
bmean = base15[(base15.index.dayofweek < 5)].groupby(base15[(base15.index.dayofweek < 5)].index.year).mean()
y = e.groupby("year").agg(n=("r15", "size"), mean_abs15=("r15", lambda v: v.abs().mean()), P_up15=("r15", lambda v: (v > 0).mean()), mean_abs60=("r60", lambda v: v.abs().mean()))
y["allday_mean_abs15"] = bmean.reindex(y.index).values; y["ratio_midnight/allday"] = y.mean_abs15 / y.allday_mean_abs15; print(y.round(3).to_string())
for lab, q in (("ATR14 tercile", "atr14"), ("range60 tercile", "rng60")):
    g = e.groupby(pd.qcut(e[q], 3, labels=["low", "mid", "high"]), observed=True).agg(mean_abs15=("r15", lambda v: v.abs().mean()), P_up15=("r15", lambda v: (v > 0).mean()), mean15=("r15", "mean"))
    print(f"\n{lab}:\n", g.round(3).to_string())
eras = {"2010-15": (2010, 2015), "2016-20": (2016, 2020), "2021-26": (2021, 2026)}
print("\nEras:"); [print(f"  {k}: mean|r15|={e[(e.year>=a)&(e.year<=b)].r15.abs().mean():.2f} mean|r60|={e[(e.year>=a)&(e.year<=b)].r60.abs().mean():.2f}") for k, (a, b) in eras.items()]
