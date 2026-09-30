"""Per-day minute-matrix strategy engine. Bars j=0..59 pre-anchor, j=60 is the t0 bar. Bid series; ask = bid + S (S = round-trip cost in pips).
Fills: market at bar OPEN; stop-entry at level (or open if gapped); SL/TP checked from the ENTRY bar onward, SL first on ties (no entry-bar skipping)."""
import numpy as np, pandas as pd
from common import *
PRE, POST = 60, 241
def matrices(anchor_times, sym="GBPUSD", start="2010-11-15"):
    G = m1(sym, start); ix = G.index
    pos = ix.get_indexer(pd.DatetimeIndex(anchor_times)); keep = pos >= PRE; pos = pos[keep]
    j = pos[:, None] + np.arange(-PRE, POST)[None, :]; j = np.clip(j, 0, len(ix) - 1)
    out = {}
    for k in "ohlc":
        a = G[k].values[j]
        # forward-fill NaN (no-tick minutes) along each row using last valid close
        cl = G["c"].values[j] if k != "c" else a
        out[k] = a
    c = pd.DataFrame(out["c"]).ffill(axis=1).bfill(axis=1).values
    for k in "ohl": out[k] = np.where(np.isnan(out[k]), c, out[k])
    out["c"] = c
    return out, pd.DatetimeIndex(anchor_times)[keep]

def exit_trade(d, e_bar, e_px, sl, tp, hold_end, o, h, l, c, S):
    """Levels are plain prices vs the executable side: longs exit at bid, shorts exit at ask (= bid + S). SL wins ties."""
    s = S * PIP
    for j in range(e_bar, hold_end):
        if d > 0:
            if sl is not None and l[j] <= sl: return (sl - e_px) / PIP
            if tp is not None and h[j] >= tp: return (tp - e_px) / PIP
        else:
            if sl is not None and h[j] + s >= sl: return (e_px - sl) / PIP
            if tp is not None and l[j] + s <= tp: return (e_px - tp) / PIP
    return (c[hold_end - 1] - e_px) / PIP if d > 0 else (e_px - (c[hold_end - 1] + s)) / PIP

def simulate(M, sig, hold, S):
    """sig: callable(day_index, M) -> dict(d, bar, kind, level, sl, tp) or None. Returns array of net pips per day (NaN = no trade)."""
    o, h, l, c = M["o"], M["h"], M["l"], M["c"]; N = len(c); res = np.full(N, np.nan)
    for i in range(N):
        s = sig(i, M)
        if s is None: continue
        d, b = s["d"], s["bar"]; end = min(PRE + hold, POST)
        if b >= end: continue
        if s["kind"] == "mkt": px = o[i, b] + (S * PIP if d > 0 else 0.0); eb = b
        else:   # stop entry at level within window [b, s['until'])
            lv, eb = s["level"], None
            for j in range(b, min(s["until"], end)):
                if d > 0 and h[i, j] + S * PIP >= lv: eb = j; px = max(lv, o[i, j] + S * PIP); break
                if d < 0 and l[i, j] <= lv: eb = j; px = min(lv, o[i, j]); break
            if eb is None: continue
        sl, tp = s.get("sl"), s.get("tp")
        res[i] = exit_trade(d, eb, px, sl, tp, end, o[i], h[i], l[i], c[i], S)
    return res
