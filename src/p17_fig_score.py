import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from common import *
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
t = pd.read_csv(OUT / "p16_stop_sizing.csv", index_col=0)
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
x = np.arange(1, 6); ax[0].bar(x - .27, t.rng_p50, .27, color="#b9c0cc", label="median"); ax[0].bar(x, t.rng_p75, .27, color="#2a6fdb", label="75th pct"); ax[0].bar(x + .27, t.rng_p90, .27, color="#d9483b", label="90th pct")
ax[0].set_xticks(x, ["Q1\ncalm", "Q2", "Q3", "Q4", "Q5\nbig night"]); ax[0].set_ylabel("pips"); ax[0].legend(frameon=False)
ax[0].set_title("High-low range, 03:00-08:00 NY, by frozen score (2016-26)")
ax[1].bar(x - .18, t.either_side_p50, .36, color="#b9c0cc", label="median"); ax[1].bar(x + .18, t.either_side_p90, .36, color="#d9483b", label="90th pct")
ax[1].set_xticks(x, ["Q1\ncalm", "Q2", "Q3", "Q4", "Q5\nbig night"]); ax[1].set_title("Worst excursion from the 03:00 open (either side): stop guide"); ax[1].legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig4_score_stop_sizing.png", dpi=140); print("ok")
