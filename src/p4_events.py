"""Event table per anchor: strictly-pre-anchor features + forward outcomes (pips). Open of event = close of minute t0-1."""
import pandas as pd, numpy as np
from common import *
S = "2010-11-15"
G = m1("GBPUSD", S); idx = G.index
def wk(days, h, m=0, tz="America/New_York"):
    loc = pd.DatetimeIndex(days + pd.Timedelta(hours=h, minutes=m)).tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
    return loc[loc.notna()].tz_convert("UTC").tz_localize(None)
days = pd.date_range("2010-11-16", "2026-09-17", freq="B")
ANCH = {"A": wk(days, 0), "B": pd.DatetimeIndex(days + pd.Timedelta(hours=4)), "C": pd.DatetimeIndex(days), "E": wk(days, 17)}
o, h, l, c = (G[k] for k in "ohlc")
cc = c.ffill(limit=5)                                     # tolerate <=5min holes in price *levels* used for features only
rmax = {k: h.rolling(k, min_periods=int(k * .6)).max() for k in (15, 30, 60, 300)}
rmin = {k: l.rolling(k, min_periods=int(k * .6)).min() for k in (15, 30, 60, 300)}
X = {s: m1(s, S).c for s in ("EURUSD", "USDJPY")}
def at(s, t): return s.reindex(t).values
def build(name, t0):
    t0 = pd.DatetimeIndex(t0); t0 = t0[(t0 >= idx[0]) & (t0 < idx[-1] - pd.Timedelta(hours=3))]
    tm1 = t0 - pd.Timedelta(minutes=1)
    e = pd.DataFrame(index=t0); e["open"] = at(cc, tm1); ok = ~np.isnan(e.open.values)
    for m in (1, 5, 15, 30, 60, 120): e[f"r{m}"] = (at(cc, t0 + pd.Timedelta(minutes=m - 1)) - e.open) / PIP
    # MFE/MAE over 60 & 120 min (forward, bid-based, long perspective)
    for m in (60, 120):
        fh = h[::-1].rolling(m, min_periods=int(m * .6)).max()[::-1]; fl = l[::-1].rolling(m, min_periods=int(m * .6)).min()[::-1]
        e[f"up{m}"] = (at(fh, t0) - e.open) / PIP; e[f"dn{m}"] = (e.open - at(fl, t0)) / PIP
    # pre-anchor features (windows end at t0-1)
    for k in (15, 30, 60, 300):
        e[f"rng{k}"] = (at(rmax[k], tm1) - at(rmin[k], tm1)) / PIP
        e[f"pos{k}"] = (e.open - at(rmin[k], tm1)) / PIP / e[f"rng{k}"].replace(0, np.nan)
    for k in (15, 60, 300, 1440): e[f"pre{k}"] = (e.open - at(cc, t0 - pd.Timedelta(minutes=k + 1))) / PIP
    # yesterday: 24h ago ret sessions (NY-local session dirs from t0's date)
    d0 = t0.normalize()
    def sess(h0, h1, shift=0):  # NY-local clock session on the calendar day (t0 date - shift)
        s0 = wk(pd.DatetimeIndex(d0 - pd.Timedelta(days=shift)), h0); s1 = wk(pd.DatetimeIndex(d0 - pd.Timedelta(days=shift)), h1)
        return s0, s1
    return e, tm1, ok
def finish(name, t0):
    e, tm1, ok = build(name, t0)
    d0 = e.index.normalize()
    # session directions of the previous 24h ending at t0 in *fixed offsets back from t0* -> avoids calendar/tz confusion
    for lab, (a, b) in {"asia": (-300, 0), "london": (-960, -720), "ny": (-1200, -840)}.items():
        pass
    # previous-day (trailing 24h before the previous-day-close) and previous-week levels from daily NY-17:00 bars
    e["prev_dir"] = np.sign(e["pre1440"])
    dh = h.rolling(1440, min_periods=900).max(); dl = l.rolling(1440, min_periods=900).min()
    e["dist_pdh"] = (at(dh, tm1) - e.open) / PIP; e["dist_pdl"] = (e.open - at(dl, tm1)) / PIP
    wh = h.rolling(7200, min_periods=4000).max(); wl = l.rolling(7200, min_periods=4000).min()
    e["dist_pwh"] = (at(wh, tm1) - e.open) / PIP; e["dist_pwl"] = (e.open - at(wl, tm1)) / PIP
    dr = (dh - dl); e["atr14"] = at(dr.rolling(14 * 1440, min_periods=5 * 1440).mean(), tm1) / PIP
    # cross-asset trend into anchor
    for s, x in X.items(): e[f"{s}_pre60"] = (at(x.ffill(limit=5), tm1) - at(x.ffill(limit=5), tm1 - pd.Timedelta(minutes=60))) / (PIP if s == "EURUSD" else 1e-2)
    ny, us = nyinfo(e.index); e["us_dst"] = us; e["uk_dst"] = uk_dst(e.index)
    e["dow"] = e.index.dayofweek; e["month"] = e.index.month; e["year"] = e.index.year; e["dom"] = e.index.day
    e["date"] = d0
    e = e.dropna(subset=["open", "r5", "r15", "r60"])
    e.to_parquet(D / f"events_{name}.parquet"); return name, len(e)
for k, v in ANCH.items(): print(finish(k, v))
