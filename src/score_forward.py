"""Forward test of the FROZEN big-night score on live MT5 data (server clock == UTC).
usage: python score_forward.py            -> scores every unseen night (>= 2026-09-21) + the next night, appends to out/forward_log.csv
The model is re-created deterministically from 2010-15 data (identical to p16); nothing is refit on new data."""
import warnings; warnings.filterwarnings("ignore")
import json, re, urllib.request
import pandas as pd, numpy as np
import MetaTrader5 as mt5
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from common import *
UNSEEN_FROM = pd.Timestamp("2026-09-21")          # HistData (all prior analysis) ends 2026-09-18
F = ["atr14", "prev_rng", "asia_rel", "ukdata"]; MIN = pd.Timedelta(minutes=1)
# ---- frozen model (same recipe as p16) ------------------------------------------------------------------------------------------
A = pd.read_parquet(OUT / "p15_day_table.parquet").dropna(subset=F); tr = A[A.yr <= 2015]
model = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500)).fit(tr[F], tr.big_rng.astype(int))
cuts = pd.Series(model.predict_proba(tr[F])[:, 1]).quantile([.2, .4, .6, .8]).values
guide = pd.read_csv(OUT / "p16_stop_sizing.csv", index_col=0)
# ---- live data ------------------------------------------------------------------------------------------------------------------
assert mt5.initialize(), mt5.last_error(); r = mt5.copy_rates_from_pos("GBPUSD", mt5.TIMEFRAME_M1, 0, 50000); mt5.shutdown()
B = pd.DataFrame(r); B.index = pd.DatetimeIndex(pd.to_datetime(B.time, unit="s")).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
B = B.rename(columns={"high": "h", "low": "l", "close": "c"})[["h", "l", "c"]]
print(f"MT5 bars {B.index[0]} .. {B.index[-1]} (NY clock)")
# ---- UK release days: history + upcoming (ONS nextRelease) ---------------------------------------------------------------------
ons = set(pd.read_csv(D / "news" / "ons_release_dates.csv", parse_dates=["date"]).date)
P = {"CPI": "economy/inflationandpriceindices/timeseries/d7g7/mm23", "Unemp": "employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms", "Retail": "businessindustryandtrade/retailindustry/timeseries/j5ek/drsi"}
for k, p in P.items():
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://www.ons.gov.uk/{p}/data", headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
        nx = pd.to_datetime(d["description"].get("nextRelease", ""), errors="coerce")
        if pd.notna(nx): ons.add(nx.normalize()); print(f"  next UK {k} release: {nx.date()}")
        ons |= set(pd.to_datetime([v["updateDate"] for v in d["versions"]] + [d["description"]["releaseDate"]]).tz_convert("Europe/London").normalize().tz_localize(None))
    except Exception as e: print("  ONS", k, "unavailable:", e)
def rg(a, b):
    s = B.loc[a:b - MIN]; return np.nan if s.empty else (s.h.max() - s.l.min()) / PIP
def prev_day(d): return d - pd.Timedelta(days=1 if d.dayofweek else 3)
def features(D_):
    days, y = [], D_
    for _ in range(14): y = prev_day(y); days.append(y)                       # 14 prior trading days incl. y(D-1)
    pr = [rg(x, x + pd.Timedelta(hours=17)) for x in days]
    if np.isnan(pr).any(): return None
    atr = float(np.mean(pr)); asia = rg(D_ - pd.Timedelta(hours=5), D_)
    return dict(atr14=atr, prev_rng=pr[0], asia_rel=asia / atr if not np.isnan(asia) else np.nan, ukdata=int(D_ in ons))
rows = []; today = pd.Timestamp.now(tz="UTC").tz_convert("America/New_York").tz_localize(None)
last = B.index[-1].normalize() + pd.Timedelta(days=1)                          # night after the last data day
for D_ in [d for d in pd.date_range(UNSEEN_FROM, last, freq="B")]:
    f = features(D_)
    if f is None or np.isnan(f["asia_rel"]): print(D_.date(), "insufficient data for features (evening 19-00 NY not yet complete or gap)"); continue
    s = float(model.predict_proba(pd.DataFrame([f])[F])[:, 1][0]); q = int(np.digitize(s, cuts)) + 1
    done = today >= D_ + pd.Timedelta(hours=5)
    out = dict(date=D_.date(), **{k: round(v, 3) for k, v in f.items()}, score=round(s, 3), quintile=q, hist_median_range=guide.rng_p50[q], hist_p90_range=guide.rng_p90[q])
    if done and B.index[-1] >= D_ + pd.Timedelta(hours=5):
        out["realized_rng_00_05"] = round(rg(D_, D_ + pd.Timedelta(hours=5)), 1); out["realized_rng_03_08"] = round(rg(D_ + pd.Timedelta(hours=3), D_ + pd.Timedelta(hours=8)), 1) if B.index[-1] >= D_ + pd.Timedelta(hours=8) else np.nan
    rows.append(out)
L = pd.DataFrame(rows); pd.set_option("display.width", 250); print(L.to_string(index=False))
old = pd.read_csv(OUT / "forward_log.csv") if (OUT / "forward_log.csv").exists() else pd.DataFrame()
pd.concat([old, L]).drop_duplicates("date", keep="last").to_csv(OUT / "forward_log.csv", index=False)
if "realized_rng_00_05" in L:
    z = L.dropna(subset=["realized_rng_00_05"]); print(f"\nrealized 00-05 ranges on {len(z)} unseen nights: mean {z.realized_rng_00_05.mean():.1f} | by score quintile:", z.groupby("quintile").realized_rng_00_05.mean().round(1).to_dict())
    if len(z) > 3: print("rank correlation score vs realized range (unseen nights):", round(z.score.corr(z.realized_rng_00_05, method="spearman"), 2))
