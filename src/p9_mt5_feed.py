"""Sec 17: broker feed (MT5 BrightFunded, server clock == UTC verified via live tick) vs HistData, same timestamps; broker spread profile by NY minute."""
import pandas as pd, numpy as np
from common import *
mt = pd.read_parquet(D / "mt5_GBPUSD_M1.parquet"); mt.index = pd.DatetimeIndex(mt.time); mt = mt[~mt.index.duplicated()]
hd = m1("GBPUSD", "2026-08-01").dropna(subset=["c"])
ov = mt.index.intersection(hd.index); print(f"MT5 bars {len(mt)} ({mt.index[0]} .. {mt.index[-1]}); overlap with HistData: {len(ov)} bars ({ov[0]} .. {ov[-1]})")
d = (mt.loc[ov, "close"] - hd.loc[ov, "c"]) / PIP
print(f"close diff MT5-HistData (pips): median {d.median():+.2f}, mean |diff| {d.abs().mean():.2f}, p99 |diff| {d.abs().quantile(.99):.2f}; corr of 1m returns {np.corrcoef(mt.loc[ov,'close'].diff().dropna().reindex(ov).fillna(0), hd.loc[ov,'c'].diff().fillna(0))[0,1]:.3f}")
ny = mt.index.tz_localize("UTC").tz_convert("America/New_York"); mt["nym"] = ny.hour * 60 + ny.minute; mt["sp"] = mt.spread / 10.0     # points -> pips
wd = mt[mt.index.dayofweek < 5]
print("\nBroker (MT5) spread by NY-local time, weekdays, pips [median / mean / max-bar-mean]:")
for lab, a in (("23:55", 23*60+55), ("23:59", 23*60+59), ("00:00", 0), ("00:01", 1), ("00:05", 5), ("00:30", 30), ("03:00 London open", 180), ("08:30 US data", 510), ("16:55", 16*60+55), ("17:00 rollover", 17*60), ("17:05", 17*60+5), ("17:30", 17*60+30), ("18:00", 18*60)):
    x = wd[wd.nym == a].sp
    if len(x): print(f"  NY {lab:18s} n={len(x):3d}  median {x.median():5.2f}  mean {x.mean():5.2f}  p90 {x.quantile(.9):5.2f}  max {x.max():5.1f}")
allsp = wd.sp.median(); print(f"  all-day median spread {allsp:.2f} pips")
# does the broker candle at NY 00:00 look bigger than at neighbours (range in pips, broker feed)?
wd = wd.assign(rngp=(wd.high - wd.low) / PIP)
print("\nBroker 1-min candle range (pips) mean by NY minute around 00:00 and 17:00:")
for lab, a in (("23:58", 23*60+58), ("23:59", 23*60+59), ("00:00", 0), ("00:01", 1), ("00:02", 2), ("17:00", 17*60), ("17:01", 17*60+1)):
    x = wd[wd.nym == a].rngp; print(f"  NY {lab}: mean range {x.mean():.2f} (median {x.median():.2f}, n={len(x)})")
