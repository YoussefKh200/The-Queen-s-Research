"""HistData M1 -> UTC-indexed parquet. EMPIRICAL FINDING (p1): the raw label is America/New_York WALL-CLOCK (DST-observing),
NOT fixed EST as documented: NFP peaks at 08:30 label in summer+winter, Sunday open is 17:00 label year-round."""
import zipfile, io, sys
from pathlib import Path
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

Z = Path(r"C:\Users\youss\OneDrive\Documents\1k eval\le_model_retest\data\histdata_zips")
OUT = Path(__file__).resolve().parent.parent / "data"

def rd(p):
    with zipfile.ZipFile(p) as z:
        n = [x for x in z.namelist() if x.endswith(".csv")][0]
        return pd.read_csv(z.open(n), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"], dtype={"t": str})

def build(sym):
    df = pd.concat(map(rd, sorted(Z.glob(f"DAT_ASCII_{sym}_M1_*.zip"))))
    lab = pd.to_datetime(df.pop("t"), format="%Y%m%d %H%M%S")
    df.index = lab.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.tz_localize(None)
    df = df[df.index.notna()]
    df = df[~df.index.duplicated()].sort_index().drop(columns="v")
    df.to_parquet(OUT / f"{sym}_M1_utc.parquet"); return sym, len(df), df.index[0], df.index[-1]

if __name__ == "__main__":
    with ProcessPoolExecutor(6) as ex:
        for r in ex.map(build, ["GBPUSD", "EURUSD", "USDJPY", "SPXUSD", "NSXUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]): print(r)
    g, e, j = (pd.read_parquet(OUT / f"{s}_M1_utc.parquet") for s in ("GBPUSD", "EURUSD", "USDJPY"))
    ix = g.index.intersection(e.index); (e.loc[ix] / g.loc[ix]).to_parquet(OUT / "EURGBP_M1_utc.parquet")   # synthetic cross (o/h/l are approximate)
    ix = g.index.intersection(j.index); (g.loc[ix] * j.loc[ix]).to_parquet(OUT / "GBPJPY_M1_utc.parquet")
