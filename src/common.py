import pandas as pd, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; D = ROOT / "data"; OUT = ROOT / "out"
PIP = 1e-4

def m1(sym="GBPUSD", start="2000-01-01"):
    """Gapless-index close/open/high/low frame in UTC (naive), NaN where no ticks."""
    g = pd.read_parquet(D / f"{sym}_M1_utc.parquet"); g = g[g.index >= start]
    return g.asfreq("1min")

def nyinfo(idx):
    """NY-local wall time and US-DST flag for a UTC-naive index."""
    ny = idx.tz_localize("UTC").tz_convert("America/New_York")
    return ny, ((ny.tz_localize(None) - idx).total_seconds() == -4 * 3600)

def uk_dst(idx):
    l = idx.tz_localize("UTC").tz_convert("Europe/London")
    return (l.tz_localize(None) - idx).total_seconds() == 3600

def window_moves(c, start_idx, mins):
    """Return c[start+mins]-c[start-1min] in pips for each start (open ~= prior minute close). NaN if either missing."""
    a = c.reindex(start_idx - pd.Timedelta(minutes=1)).values
    b = c.reindex(start_idx + pd.Timedelta(minutes=mins - 1)).values
    return (b - a) / PIP
