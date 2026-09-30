"""Sec 6 + 17: Dukascopy bid/ask on random sampled weekdays. Separate mid vs bid vs ask vs spread at NY 00:00 and 17:00 rollover; feed compare vs HistData; rollover 'edge' with real ask."""
import pandas as pd, numpy as np
from common import *
fs = sorted((D / "duka" / "days").glob("GBPUSD_*.parquet")); K = pd.concat([pd.read_parquet(f) for f in fs]).sort_index(); K = K[~K.index.duplicated()]
K["mid_c"] = (K.c + K.ask_c) / 2; K["sp_c"] = (K.ask_c - K.c) / PIP; K["sp_mean_p"] = K.sp_mean / PIP
ndays = len({f.stem[-10:] for f in fs}); print(f"Dukascopy sample: {ndays} random weekdays 2018-2026, {len(K)} M1 bars with real tick bid/ask")
K = K.asfreq("1min")
ny = K.index.tz_localize("UTC").tz_convert("America/New_York"); K["nym"] = ny.hour * 60 + ny.minute; K["ndate"] = ny.date
K["rng_bid"] = (K.h - K.l) / PIP
wd = K[K.index.dayofweek < 5]
print("\n--- Spread (pips, mean of tick spreads within the minute) & 1-min bid range by NY clock (weekday sample) ---")
for lab, a in (("23:59", 23*60+59), ("00:00", 0), ("00:01", 1), ("00:05", 5), ("03:00", 180), ("16:59", 16*60+59), ("17:00", 17*60), ("17:01", 17*60+1), ("17:05", 17*60+5), ("17:30", 17*60+30)):
    x = wd[wd.nym == a]; print(f"  NY {lab}: n={x.sp_mean_p.notna().sum():3d} spread mean {x.sp_mean_p.mean():5.2f} median {x.sp_mean_p.median():5.2f} max {x.sp_mean_p.max():6.1f} | bid range mean {x.rng_bid.mean():5.2f} | ticks/min {x.n.mean():5.1f}")
def ev_utc(d, hh, mm=0):
    try: return (pd.Timestamp(d) + pd.Timedelta(hours=hh, minutes=mm)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None)
    except Exception: return None
DAYS = [d for d in pd.DatetimeIndex(K.index.tz_localize("UTC").tz_convert("America/New_York").normalize().tz_localize(None)).unique() if d.dayofweek < 5]
Hd = m1("GBPUSD", "2018-01-01")
def move(ev_nym, m):
    """per-day bid/mid/spread change from the minute before the NY-clock event to m minutes after (last tick of each minute)."""
    rows = []
    for d in DAYS:
        t = ev_utc(d, ev_nym // 60, ev_nym % 60)
        if t is None or (t - pd.Timedelta(minutes=1)) not in K.index or (t + pd.Timedelta(minutes=m - 1)) not in K.index: continue
        a, b = K.loc[t - pd.Timedelta(minutes=1)], K.loc[t + pd.Timedelta(minutes=m - 1)]
        if pd.isna(a.c) or pd.isna(b.c): continue
        rows.append((d, (b.c - a.c) / PIP, (b.mid_c - a.mid_c) / PIP, b.sp_c - a.sp_c, t))
    return pd.DataFrame(rows, columns=["d", "bid", "mid", "dspread", "t"])
print("\n--- Decomposition of first-minutes move: BID move = MID move - dSpread/2 (pips) ---")
for lab, ev in (("NY 00:00", 0), ("NY 17:00 (rollover)", 17 * 60)):
    for m in (1, 5, 30):
        x = move(ev, m)
        if len(x) > 5: print(f"  {lab:20s} +{m:2d}m (n={len(x)}): mean|bid| {x.bid.abs().mean():5.2f} | mean|mid| {x.mid.abs().mean():5.2f} | mean dSpread {x.dspread.mean():+5.2f} | mean bid {x.bid.mean():+5.2f} mean mid {x.mid.mean():+5.2f}")
ov = K.index.intersection(Hd.index); ov = ov[K.loc[ov, "c"].notna() & Hd.loc[ov, "c"].notna()]
d = (K.loc[ov, "c"] - Hd.loc[ov, "c"]) / PIP
print(f"\n--- Feed comparison, same UTC minute, Dukascopy bid close vs HistData bid close: n={len(ov)} median diff {d.median():+.2f}, mean|diff| {d.abs().mean():.2f}, p99|diff| {d.abs().quantile(.99):.2f} pips")
for lab, ev in (("NY 00:00", 0), ("NY 17:00", 17 * 60)):
    x = move(ev, 5); hm = []
    for t in x.t:
        a_, b_ = Hd.c.get(t - pd.Timedelta(minutes=1), np.nan), Hd.c.get(t + pd.Timedelta(minutes=4), np.nan)
        if not (np.isnan(a_) or np.isnan(b_)): hm.append(abs(b_ - a_) / PIP)
    print(f"  {lab} first-5m mean|bid move|: Dukascopy {x.bid.abs().mean():.2f} (n={len(x)}) vs HistData {np.mean(hm):.2f} (n={len(hm)}), same days")
rows = []
for d0 in DAYS:
    t = ev_utc(d0, 17)
    if t is None or t not in K.index or (t + pd.Timedelta(hours=2)) not in K.index: continue
    e0, x0 = K.loc[t], K.loc[t + pd.Timedelta(hours=2)]
    if pd.isna(e0.ask_c) or pd.isna(x0.c): continue
    rows.append(((x0.c - e0.c) / PIP, (x0.c - e0.ask_c) / PIP, (e0.ask_c - e0.c) / PIP))
R = np.array(rows); print(f"\n--- Rollover 'edge' check, naive long NY17:00 -> 19:00 (n={len(R)} days): gross-on-bid {R[:,0].mean():+.2f} pips | with REAL ask entry {R[:,1].mean():+.2f} pips | mean entry spread {R[:,2].mean():.2f}")
