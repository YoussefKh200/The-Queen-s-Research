import pandas as pd, numpy as np
g = pd.read_parquet("data/GBPUSD_M1_utc.parquet"); c = g.c.asfreq("1min"); r = (c.diff()*1e4).abs()
rows = []
for y in range(2005, 2027):
    for m in range(1, 13):
        d = pd.Timestamp(y, m, 1); f = d + pd.Timedelta(days=(4 - d.dayofweek) % 7)   # first Friday (NFP proxy, most months)
        if f > pd.Timestamp("2026-09-18"): continue
        s = r[f + pd.Timedelta(hours=11): f + pd.Timedelta(hours=15)].dropna()
        if len(s) < 100: continue
        t = s.idxmax(); ny = t.tz_localize("UTC").tz_convert("America/New_York")
        rows.append((y, m, bool(ny.dst()), t.strftime("%H:%M"), round(s.max(), 1)))
x = pd.DataFrame(rows, columns=["y", "m", "usdst", "peak_utc", "pips"])
print(x.groupby(["y", "usdst"]).peak_utc.agg(lambda v: v.value_counts().index[0] + f" ({v.value_counts().iloc[0]}/{len(v)})").unstack().to_string())
