"""Smallest check that fails if fills/costs break: synthetic flat market, S=1 pip => every market trade nets exactly -1.0; SL hit on entry bar counted."""
import numpy as np
from engine import *
N = 3; base = 1.2500
M = {k: np.full((N, PRE + POST), base) for k in "ohlc"}
M["l"][1, 61] = base - 0.0010                                    # row 1: drops 10 pips in bar 61
long_mkt = lambda i, M: dict(d=1, bar=PRE, kind="mkt")
short_mkt = lambda i, M: dict(d=-1, bar=PRE, kind="mkt")
r = simulate(M, long_mkt, 30, 1.0); assert np.allclose(r, -1.0), r
r = simulate(M, short_mkt, 30, 1.0); assert np.allclose(r, -1.0), r
sl_long = lambda i, M: dict(d=1, bar=PRE, kind="mkt", sl=base - 0.0005)
r = simulate(M, sl_long, 30, 1.0); assert np.isclose(r[1], -6.0) and np.isclose(r[0], -1.0), r   # SL at -5 from bid, cost 1 => -6
M["h"][2, 60] = base + 0.0010                                    # entry-bar spike: stop-entry must fill AND be able to hit SL same bar
M["l"][2, 60] = base - 0.0010
stop = lambda i, M: dict(d=1, bar=PRE, kind="stop", level=base + 0.0005, until=PRE + 10, sl=base - 0.0005)
r = simulate(M, stop, 30, 1.0); assert np.isnan(r[0]) and np.isclose(r[2], -10.0), r          # buy-stop fills at ask level +5 (spread inherent), SL at bid -5 same bar => -10
print("engine ok")
