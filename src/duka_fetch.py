"""Resumable Dukascopy GBPUSD tick->M1 (bid OHLC, mean/max spread, ticks). Own bi5 parser: lzma + 20-byte BE records."""
import lzma, struct, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import numpy as np, pandas as pd

class _NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
urllib.request.install_opener(urllib.request.build_opener(_NoRedir))
SYM = sys.argv[1]; Y0, Y1 = int(sys.argv[2]), int(sys.argv[3])
DIV = 1000 if "JPY" in SYM else 100000
OUT = Path(__file__).resolve().parent.parent / "data" / "duka"
URL = "http://datafeed.dukascopy.com/datafeed/{s}/{y}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"
HRS = list(range(21, 24)) + list(range(0, 9))  # UTC hours around all candidate anchors (rollover, Sydney/Tokyo, NY-midnight, London open)
REC = np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("av", ">f4"), ("bv", ">f4")])

def hour(day, h):
    u = URL.format(s=SYM, y=day.year, m=day.month - 1, d=day.day, h=h)
    for a in range(8):
        try:
            with urllib.request.urlopen(u, timeout=30) as r: raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(min(5 * 2 ** a, 120))   # 301/429/403 = throttled: back off hard
        except Exception: time.sleep(1 + a)
    else: return "ERR"
    if not raw: return None
    t = np.frombuffer(lzma.decompress(raw), dtype=REC)
    if not len(t): return None
    ts = pd.Timestamp(day.year, day.month, day.day, h) + pd.to_timedelta(t["ms"].astype("int64"), unit="ms")
    return pd.DataFrame({"bid": t["bid"] / DIV, "ask": t["ask"] / DIV}, index=ts)

def day(d):
    parts, err = [], 0
    for h in HRS:
        r = hour(d, h)
        if isinstance(r, str): err += 1
        elif r is not None: parts.append(r)
    if not parts: return None, err
    t = pd.concat(parts); t["sp"] = t.ask - t.bid
    g = t.resample("1min")
    m = pd.DataFrame({"o": g.bid.first(), "h": g.bid.max(), "l": g.bid.min(), "c": g.bid.last(),
                      "ask_c": g.ask.last(), "sp_mean": g.sp.mean(), "sp_max": g.sp.max(), "n": g.bid.count()}).dropna(subset=["o"])
    return m, err

import random
rnd = random.Random(7); pool = [d for d in (date(2018, 1, 1) + timedelta(i) for i in range((date(2026, 9, 15) - date(2018, 1, 1)).days)) if d.weekday() < 5]
sample = sorted(rnd.sample(pool, int(sys.argv[4]) if len(sys.argv) > 4 else 90))   # unbiased random weekdays
CD = OUT / "days"; CD.mkdir(exist_ok=True)
def one(d):
    f = CD / f"{SYM}_{d}.parquet"
    if f.exists(): return d, "cached"
    m, err = day(d)
    if m is not None: m.to_parquet(f)
    print(d, "ok" if m is not None else "empty", "errs", err, flush=True); return d, err
with ThreadPoolExecutor(5) as ex: list(ex.map(one, sample))
print("DONE", flush=True)
