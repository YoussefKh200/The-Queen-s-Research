import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from common import *
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, RED = "#2a6fdb", "#b9c0cc", "#d9483b"
# 1) hour-of-day
t = pd.read_csv(OUT / "p2_hour_abs_moves.csv", index_col=0)
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8), sharex=True)
for a, m in zip(ax, (5, 15, 60)):
    v = t[[f"abs{m}_S", f"abs{m}_W"]].mean(axis=1); a.bar(v.index, v.values, color=[RED if h == 0 else (BLUE if h in (3, 8, 10) else GREY) for h in v.index])
    a.set_title(f"Mean |move| over {m} min from each NY hour"); a.set_xlabel("New York hour of day"); a.set_ylabel("pips" if m == 5 else "")
ax[0].annotate("NY 00:00\n(24th of 24)", (0, v.iloc[0]), xytext=(13, 5.0), color=RED, arrowprops=dict(arrowstyle="->", color=RED))
fig.suptitle("GBPUSD 2012-2026, weekdays: the 00:00 New York hour is the QUIETEST of the day", y=1.03, fontweight="bold"); fig.tight_layout(); fig.savefig(OUT / "fig1_hour_of_day.png", dpi=140, bbox_inches="tight")
# 2) minute-of-day profile in NY clock (1m |ret|), summer vs winter
c = m1("GBPUSD", "2012-01-01").c; r = (c.diff() / PIP).abs().dropna(); ny, us = nyinfo(r.index); r = r[r.index.dayofweek < 5]; ny, us = nyinfo(r.index)
df = pd.DataFrame({"r": r.values, "nym": ny.hour * 60 + ny.minute, "us": us})
fig, ax = plt.subplots(figsize=(13, 4))
for k, col, lab in ((True, BLUE, "US summer (EDT)"), (False, "#e08a1e", "US winter (EST)")):
    s = df[df.us == k].groupby("nym").r.mean().rolling(5, center=True, min_periods=1).mean(); ax.plot(s.index / 60, s.values, color=col, lw=1.2, label=lab)
for x, lab in ((0, "NY 00:00"), (3, "London open"), (8.5, "US data 08:30"), (17, "17:00 rollover")): ax.axvline(x, color=RED if x == 0 else GREY, ls="--", lw=1); ax.text(x + .1, ax.get_ylim()[1] * .93, lab, color=RED if x == 0 else "#555", fontsize=9)
ax.set_xlim(0, 24); ax.set_xlabel("New York hour of day"); ax.set_ylabel("mean |1-min return|, pips"); ax.set_title("GBPUSD volatility by New York clock time (5-min smoothed): nothing happens at 00:00", fontweight="bold"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig2_minute_profile.png", dpi=140); plt.close("all")
# 3) broker spread & candle range around midnight and rollover (MT5)
mt = pd.read_parquet(D / "mt5_GBPUSD_M1.parquet"); mt.index = pd.DatetimeIndex(mt.time); nyb = mt.index.tz_localize("UTC").tz_convert("America/New_York"); mt["nym"] = nyb.hour * 60 + nyb.minute; mt = mt[mt.index.dayofweek < 5]
mt["rng"] = (mt.high - mt.low) / PIP; mt["sp"] = mt.spread / 10
fig, ax = plt.subplots(1, 2, figsize=(13, 3.9))
for a, ctr, lab in ((ax[0], 0, "around NY 00:00"), (ax[1], 17 * 60, "around NY 17:00 (daily rollover)")):
    xs = np.arange(-15, 16); g = mt.groupby("nym"); rg = g.rng.mean(); sp = g.sp.mean()
    idx = [(ctr + x) % 1440 for x in xs]; a.bar(xs, rg.reindex(idx).values, color=GREY, label="1-min candle range (pips)"); a.plot(xs, sp.reindex(idx).values, color=RED, lw=1.8, label="mean broker spread (pips)")
    a.axvline(0, color="k", lw=.8); a.set_title(f"MT5 broker feed {lab}"); a.set_xlabel("minutes from event"); a.legend(frameon=False)
fig.suptitle("Aug-Sep 2026 BrightFunded feed: the giant candle is the rollover, not midnight", y=1.03, fontweight="bold"); fig.tight_layout(); fig.savefig(OUT / "fig3_broker_spread.png", dpi=140, bbox_inches="tight")
print("figs ok")
