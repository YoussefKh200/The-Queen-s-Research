import pandas as pd, numpy as np
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "data"
g = pd.read_parquet(D / "GBPUSD_M1_utc.parquet")
c = g.c.asfreq("1min")                      # gaps -> NaN, so returns only between adjacent real minutes
r = (c.diff() * 1e4).abs()                  # 1m |return| in pips (close-to-close)
df = pd.DataFrame({"r": r}).dropna()
df = df[df.index >= "2012-01-01"]
idx = df.index
ny = idx.tz_localize("UTC").tz_convert("America/New_York"); ldn = idx.tz_localize("UTC").tz_convert("Europe/London")
df["us"] = ny.map(lambda t: bool(t.dst())) if False else np.array([bool(t.dst()) for t in ny[:0]]).tolist() or 0
# vectorised DST flags: offset != standard
df["us"] = (ny.tz_localize(None) - idx.tz_localize(None)).total_seconds() == -4 * 3600
df["uk"] = (ldn.tz_localize(None) - idx.tz_localize(None)).total_seconds() == 3600
df["mod"] = idx.hour * 60 + idx.minute
df["dow"] = idx.dayofweek
df = df[df.dow.between(0, 4)]
reg = {"US-DST & UK-DST (summer)": (df.us & df.uk), "neither (winter)": (~df.us & ~df.uk), "US-DST only (mismatch)": (df.us & ~df.uk), "UK-DST only (mismatch)": (~df.us & df.uk)}
out = {}
for k, m in reg.items():
    s = df[m].groupby("mod").r.mean()
    out[k] = s
    print(f"\n== {k}: {m.sum():,} minute-obs; global mean |1m ret| {df[m].r.mean():.3f} pips")
    top = s.sort_values(ascending=False).head(8)
    print("top minutes (UTC):", ", ".join(f"{i//60:02d}:{i%60:02d}={v:.2f}" for i, v in top.items()))
pd.DataFrame(out).to_csv("out/p1_minute_profile.csv")
# hour-level: mean |1m ret| per UTC hour and regime
h = pd.DataFrame({k: df[m].groupby(df[m].index.hour).r.mean() for k, m in reg.items()}).round(3)
print("\nmean |1m ret| pips by UTC hour:\n", h.to_string())
