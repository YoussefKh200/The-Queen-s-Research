# data/
`*_M1_utc.parquet` (HistData M1 converted to UTC, ~1.4 GB) are NOT in git. Rebuild: `python src/load.py` (needs the HistData zips, path set in `src/load.py`).
HistData's raw labels are America/New_York wall-clock (DST-observing), not fixed EST - see REPORT.md section 2.
Tracked here: `duka/days/` (Dukascopy 90-day bid/ask sample), `news/ons_release_dates.csv`, `mt5_GBPUSD_M1.parquet`, `events_*.parquet`.
