"""UK ONS releases (CPI, unemployment, retail sales, GDP) 2015-2026 vs the NY 00:00-05:00 window. Release time inferred from price reaction."""
import json, urllib.request, warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats
from common import *
pd.set_option("display.width", 200)
S = {"CPI": "economy/inflationandpriceindices/timeseries/d7g7/mm23", "Unemployment": "employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms",
     "RetailSales": "businessindustryandtrade/retailindustry/timeseries/j5ek/drsi", "GDP": "economy/grossdomesticproductgdp/timeseries/ybha/mgdp"}
ev = []
for k, p in S.items():
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://www.ons.gov.uk/{p}/data", headers={"User-Agent": "Mozilla/5.0"}), timeout=40))
        dates = pd.to_datetime([v["updateDate"] for v in d["versions"]] + [d["description"]["releaseDate"]]).tz_convert("Europe/London").normalize().tz_localize(None).unique()
        ev += [(k, x) for x in dates]; print(k, len(dates), dates.min().date(), dates.max().date())
    except Exception as e: print(k, "ERR", e)
E = pd.DataFrame(ev, columns=["type", "date"]).drop_duplicates(); E = E[(E.date >= "2015-12-01") & (E.date.dt.dayofweek < 5)]
E.to_csv(D / "news" / "ons_release_dates.csv", index=False)
c = m1("GBPUSD", "2015-01-01").c.ffill(limit=5)
def lon(d, hh, mm=0): return (pd.Timestamp(d) + pd.Timedelta(hours=hh, minutes=mm)).tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT")
def mv(d, hh, mm, m):
    t = lon(d, hh, mm)
    if pd.isna(t): return np.nan
    t = t.tz_convert("UTC").tz_localize(None); a, b = c.get(t - pd.Timedelta(minutes=1), np.nan), c.get(t + pd.Timedelta(minutes=m - 1), np.nan); return (b - a) / PIP
E["y"] = E.date.dt.year
print("\nInferred release clock (mean |5m move| in pips at candidate London times, by year):")
for y, g in E.groupby("y"):
    print(f"  {y}: n={len(g):3d}  07:00 -> {np.nanmean([abs(mv(d,7,0,5)) for d in g.date]):5.2f} | 09:30 -> {np.nanmean([abs(mv(d,9,30,5)) for d in g.date]):5.2f}")

# ---- release clock per type-year (majority of larger mean |5m|), then event timestamps ----------------------------------------
def pick(g): return 7.0 if np.nanmean([abs(mv(d, 7, 0, 5)) for d in g.date]) >= np.nanmean([abs(mv(d, 9, 30, 5)) for d in g.date]) else 9.5
clk = E.groupby(["type", "y"]).apply(pick).rename("clk"); E = E.join(clk, on=["type", "y"])
E["t_utc"] = [lon(d, int(k), int(round((k % 1) * 60))).tz_convert("UTC").tz_localize(None) if not pd.isna(lon(d, int(k), int(round((k % 1) * 60)))) else pd.NaT for d, k in zip(E.date, E.clk)]
E = E.dropna(subset=["t_utc"]); ny = E.t_utc.dt.tz_localize("UTC").dt.tz_convert("America/New_York"); E["ny_hour"] = ny.dt.hour + ny.dt.minute / 60
print("\nRelease clock in NY time: ", E.groupby("clk").ny_hour.agg(lambda v: sorted(set(np.round(v, 1)))).to_dict(), "| events:", len(E), E.type.value_counts().to_dict())
def rr(t, a, b): return (c.get(t + pd.Timedelta(minutes=b - 1), np.nan) - c.get(t + pd.Timedelta(minutes=a - 1), np.nan)) / PIP
E["r5"] = [rr(t, -0, 5) for t in E.t_utc]; E["pre"] = [ (c.get(t - pd.Timedelta(minutes=1), np.nan) - c.get(t - pd.Timedelta(minutes=61), np.nan)) / PIP for t in E.t_utc]
# baseline: same clock (NY) on all non-event weekdays same span
allc = c.index[(c.index.dayofweek < 5) & (c.index >= "2015-12-01")]
print("\n=== Reaction size: event vs same-clock non-event days (pips) ===")
for typ, g in [("ALL", E)] + list(E.groupby("type")):
    base = []
    for k in sorted(g.clk.unique()):
        ds = pd.date_range("2016-01-04", "2026-09-17", freq="B"); base += [abs(mv(d, int(k), int(round((k % 1) * 60)), 5)) for d in ds]
    e5 = g.r5.abs().dropna(); b5 = np.array(base); b5 = b5[~np.isnan(b5)]
    print(f"  {typ:13s} n={len(e5):3d}  mean|5m| event {e5.mean():5.2f} vs baseline {b5.mean():4.2f}  ({e5.mean()/b5.mean():.1f}x)  MWU p={stats.mannwhitneyu(e5, b5).pvalue:.1e}")
# ---- window (NY 00-05) range on release days vs others ----------------------------------------------------------------------
g1 = pd.read_parquet(D / "GBPUSD_M1_utc.parquet"); g1 = g1[g1.index >= "2015-12-01"]; g1.index = g1.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
w = g1.between_time("00:00", "04:59"); day = w.groupby(w.index.normalize()).agg(h=("h", "max"), l=("l", "min")); day = day[day.index.dayofweek < 5]; day["rng"] = (day.h - day.l) / PIP
evd = set(E.assign(d=E.t_utc.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)).d)
day["news"] = day.index.isin(evd)
print(f"\n=== NY 00:00-05:00 window range: UK-release days vs other days ===")
for lab, m in (("UK release in window", day.news), ("no UK release", ~day.news)): print(f"  {lab:22s} n={m.sum():4d}  mean {day.rng[m].mean():5.1f}  median {day.rng[m].median():5.1f}  P(>=40 pips) {(day.rng[m]>=40).mean():.2f}")
print(f"  MWU p={stats.mannwhitneyu(day.rng[day.news], day.rng[~day.news]).pvalue:.1e} | window mean with ALL days {day.rng.mean():.1f} vs excluding release days {day.rng[~day.news].mean():.1f} (release days are {day.news.mean():.0%} of days)")
# ---- direction: does first-5-min reaction continue? -----------------------------------------------------------------------------
print("\n=== Continuation after release: enter at +5min in direction of first-5min move, hold h, cost 0/0.6/1.5 pips ===")
rows = []
for typ, g in [("ALL", E)] + list(E.groupby("type")):
    g = g[g.r5.abs() >= 2]
    for h in (30, 60, 120):
        f = np.array([(c.get(t + pd.Timedelta(minutes=5 + h - 1), np.nan) - c.get(t + pd.Timedelta(minutes=4), np.nan)) / PIP for t in g.t_utc]) * np.sign(g.r5.values)
        ok = ~np.isnan(f); f = f[ok]; yrs = g.t_utc.dt.year.values[ok]
        p = stats.ttest_1samp(f, 0).pvalue
        rows.append((typ, h, len(f), (f > 0).mean(), f.mean(), stats.ttest_1samp(f, 0).statistic, f.mean() - .6, f.mean() - 1.5, f[yrs <= 2020].mean(), f[yrs >= 2021].mean(), p))
R = pd.DataFrame(rows, columns=["type", "hold", "n", "P(continue)", "gross", "t", "net0.6", "net1.5", "2016-20", "2021-26", "p"]); R["p_bonf"] = np.minimum(R.p * len(R), 1)
print(R.round(3).to_string(index=False)); R.to_csv(OUT / "p13_news_continuation.csv", index=False)
