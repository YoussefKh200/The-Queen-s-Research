"""Score each candidate '00:00' definition on the same metrics + directional stats. Weekdays 2012+ (M1 close-to-close)."""
import pandas as pd, numpy as np
from scipy import stats
from common import *
c = m1(start="2005-01-01").c
days = pd.date_range("2005-01-03", "2026-09-17", freq="B")
def ny_local(h, m=0):
    loc = pd.DatetimeIndex(days + pd.Timedelta(hours=h, minutes=m)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    return loc[loc.notna()].tz_convert("UTC").tz_localize(None)
def utc_fixed(h): return pd.DatetimeIndex(days + pd.Timedelta(hours=h))
A = {"A  NY 00:00 (DST-aware)": ny_local(0), "B  fixed 04:00 UTC (=00:00 UTC-4)": utc_fixed(4), "B2 fixed 05:00 UTC (=00:00 EST)": utc_fixed(5),
     "C  00:00 UTC (Tokyo open)": utc_fixed(0), "E  NY 17:00 (rollover = MT5 00:00 server)": ny_local(17),
     "ctl London 08:00 local": pd.DatetimeIndex(days + pd.Timedelta(hours=8)).tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT").dropna().tz_convert("UTC").tz_localize(None),
     "ctl NY 08:30 (US data)": ny_local(8, 30)}
ref5 = None
rows = []
allst = pd.DatetimeIndex(c.index[(c.index.dayofweek < 5) & (c.index.minute % 5 == 0) & (c.index >= "2012-01-01")])
ref5 = np.abs(window_moves(c, allst, 5)); ref5 = np.nanmean(ref5)     # all-day mean |5m move| (baseline)
for name, st in A.items():
    for era, (a, b) in {"2005-11": ("2005", "2011"), "2012-26": ("2012", "2026")}.items():
        s = st[(st >= a) & (st < pd.Timestamp(int(b) + 1, 1, 1))]
        r = {"anchor": name, "era": era}
        for m in (1, 5, 15, 60):
            v = window_moves(c, s, m); v = v[~np.isnan(v)]
            r[f"|{m}m|"] = np.abs(v).mean(); r[f"n{m}"] = len(v)
            if m in (5, 60):
                r[f"P(up){m}"] = (v > 0).mean(); tt = stats.ttest_1samp(v, 0); r[f"mean{m}"] = v.mean(); r[f"t{m}"] = tt.statistic
        r["5m/baseline"] = r["|5m|"] / ref5
        rows.append(r)
t = pd.DataFrame(rows); t.to_csv(OUT / "p3_candidates.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(f"baseline all-day mean|5m move| = {ref5:.2f} pips")
print(t[["anchor", "era", "|1m|", "|5m|", "|15m|", "|60m|", "5m/baseline", "P(up)5", "mean5", "t5", "P(up)60", "mean60", "t60", "n5"]].round(3).to_string(index=False))
