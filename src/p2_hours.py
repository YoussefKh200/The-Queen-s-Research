"""Sec 3: window moves from every NY-local hour boundary, weekdays, 2012+. Rank 00:00 NY vs all hours."""
import pandas as pd, numpy as np
from common import *
g = m1(start="2012-01-01"); c = g.c
days = pd.date_range("2012-01-02", "2026-09-17", freq="B")
rows = []
for h in range(24):
    # NY-local h:00 on each weekday -> UTC start (handles DST per-date; nonexistent/ambiguous hour never at h:00 on weekday except 02:00 spring gap -> NaT dropped)
    loc = pd.DatetimeIndex(days + pd.Timedelta(hours=h)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    loc = loc[loc.notna()]; st = loc.tz_convert("UTC").tz_localize(None)
    _, us = nyinfo(st)
    rec = {"h": h}
    for m in (1, 5, 15, 30, 60):
        mv = window_moves(c, st, m)
        for tag, msk in (("S", us), ("W", ~us)):
            v = mv[msk & ~np.isnan(mv)]; rec[f"abs{m}_{tag}"] = np.abs(v).mean() if len(v) else np.nan
        rec[f"n{m}"] = int((~np.isnan(mv)).sum())
    rows.append(rec)
t = pd.DataFrame(rows).set_index("h"); t.to_csv(OUT / "p2_hour_abs_moves.csv")
pd.set_option("display.width", 200)
for m in (5, 15, 60):
    x = t[[f"abs{m}_S", f"abs{m}_W"]].copy(); x["avg"] = x.mean(axis=1)
    x["rank(1=largest)"] = x.avg.rank(ascending=False).astype(int)
    print(f"\nMean |move| pips over {m}min starting at NY-local hour boundary (S=EDT, W=EST); n~{int(t[f'n{m}'].median())}")
    print(x.round(2).T.to_string())
