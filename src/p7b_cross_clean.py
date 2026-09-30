"""Sec 8 (clean): USD factor from pairs that do NOT contain GBP; GBP-specific = residual. Compared with all-hour control windows."""
import pandas as pd, numpy as np
from common import *
S = {s: m1(s, "2010-11-15").c.ffill(limit=5) for s in ("GBPUSD", "EURUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF", "SPXUSD")}
days = pd.date_range("2010-11-16", "2026-09-17", freq="B")
def ny_utc(hh):
    loc = pd.DatetimeIndex(days + pd.Timedelta(hours=hh)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    return loc[loc.notna()].tz_convert("UTC").tz_localize(None)
def lr(s, t, m): return (np.log(s.reindex(t + pd.Timedelta(minutes=m - 1)).values) - np.log(s.reindex(t - pd.Timedelta(minutes=1)).values)) * 1e4
def decompose(t0, m):
    R = pd.DataFrame({k: lr(v, t0, m) for k, v in S.items()}).dropna()
    usd = -(R.EURUSD + R.AUDUSD + R.NZDUSD) / 3 + (R.USDJPY + R.USDCAD + R.USDCHF) / 3        # +ve = USD strength (no GBP inside)
    y = -R.GBPUSD                                                                             # GBPUSD down = USD strength
    b = np.polyfit(usd, y, 1); res = y - np.polyval(b, usd)
    return len(R), 1 - res.var() / y.var(), b[0], np.abs(y).mean(), np.abs(res).mean(), (np.abs(res) > np.abs(y - 0).quantile(.9)).mean()
print("GBPUSD move = beta*USD_factor + GBP-specific residual  (share of variance explained by USD factor)")
print("hour_NY window   n    R2_usd  beta   mean|GBPUSD|bp  mean|GBP-specific|bp")
for hr in (0, 2, 8, 10, 17, 20, 23):
    for m in (15, 60):
        n, r2, b, a, ra, _ = decompose(ny_utc(hr), m); print(f"  {hr:02d}:00   {m:3d}m  {n:5d}   {r2:5.2f}  {b:5.2f}   {a:7.2f}      {ra:7.2f}")
# top-decile big midnight moves: USD-driven or GBP-driven?
t0 = ny_utc(0); R = pd.DataFrame({k: lr(v, t0, 60) for k, v in S.items()}).dropna()
usd = -(R.EURUSD + R.AUDUSD + R.NZDUSD) / 3 + (R.USDJPY + R.USDCAD + R.USDCHF) / 3; y = -R.GBPUSD
b = np.polyfit(usd, y, 1); res = y - np.polyval(b, usd); big = np.abs(y) >= np.abs(y).quantile(.9)
print(f"\nMidnight top-decile |GBPUSD| 60m moves (n={big.sum()}): share of |move| explained by USD factor = {np.abs(b[0]*usd[big]).sum()/np.abs(y[big]).sum():.0%}; mean|GBP-specific residual| = {np.abs(res[big]).mean():.1f}bp vs mean|residual| all days {np.abs(res).mean():.1f}bp")
