"""Scan all 1440 anchor minutes (NY-local DST-aware AND fixed-UTC): vol jump = mean|5m after| / mean|5m before|, weekdays 2012+."""
import pandas as pd, numpy as np
from common import *
c = m1(start="2012-01-01").c
post = (c.shift(-4) - c.shift(1)).abs() / PIP; pre = (c.shift(1) - c.shift(6)).abs() / PIP
df = pd.DataFrame({"post": post, "pre": pre}).dropna(); df = df[df.index.dayofweek < 5]
ny, us = nyinfo(df.index)
df["ny"] = ny.hour * 60 + ny.minute; df["utc"] = df.index.hour * 60 + df.index.minute; df["us"] = us
def show(keycol, sub, title, topn=10):
    g = sub.groupby(keycol)[["post", "pre"]].mean(); g["ratio"] = g.post / g.pre; g["n"] = sub.groupby(keycol).size()
    g = g[g.n > 800]
    print(f"\n{title}: top {topn} by ratio (post/pre) [median ratio all minutes {g.ratio.median():.2f}]")
    for i, r in g.sort_values("ratio", ascending=False).head(topn).iterrows():
        print(f"  {i//60:02d}:{i%60:02d}  pre={r.pre:.2f} post={r.post:.2f} ratio={r.ratio:.2f} n={int(r.n)}")
    return g
for nm, sub in (("SUMMER (EDT)", df[df.us]), ("WINTER (EST)", df[~df.us])):
    gn = show("ny", sub, f"NY-local anchors, {nm}")
    gu = show("utc", sub, f"Fixed-UTC anchors, {nm}")
    for lab, gg, key in (("NY 00:00", gn, 0), ("UTC 00:00", gu, 0), ("UTC 04:00", gu, 240), ("UTC 05:00", gu, 300)):
        r = gg.loc[key]; print(f"   >> {nm} {lab}: pre={r.pre:.2f} post={r.post:.2f} ratio={r.ratio:.2f}, rank {int((gg.ratio > r.ratio).sum())+1}/{len(gg)}")
