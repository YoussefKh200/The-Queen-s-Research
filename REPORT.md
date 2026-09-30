# GBPUSD "Midnight Move" — Falsification Report

**Verdict: no meaningful anomaly at 00:00 UTC-4 / New York midnight.** The move you saw is most plausibly the **17:00 New York daily-rollover candle** (a spread-blowout artifact) or 00:00 UTC (Tokyo open), plus selection/recall bias. Nothing at NY midnight is tradeable.

Charts: `out/fig1_hour_of_day.png`, `out/fig2_minute_profile.png`, `out/fig3_broker_spread.png`. Code: `src/` (p1…p11, `engine.py` + `test_engine.py`). Raw tables: `out/*.csv`.

## 1. Executive summary

| Question (loop.md §Objective) | Answer |
|---|---|
| 1. Statistically real? | **No.** 5/15-min move after NY 00:00 ranks **24th of 24 hours** (0.57× the all-day baseline); 60-min ranks 21st. |
| 2. Which clock time? | Candidates A–F all tested. NY 00:00 and fixed 04:00 UTC: quiet. **00:00 UTC** and **17:00 NY** are the real volatility events. |
| 3. Mechanism | 17:00 NY: liquidity vacuum (ticks/min 9 vs 45–190) + spread 1 → 6.6–7 pips. 00:00 UTC: Tokyo open. NY midnight: none found. |
| 4. Direction or volatility? | Neither at midnight. P(up) 0.47–0.50, every mean \|t\| < 1 (n = 4,105 days). |
| 5. Tradeable strategy? | **No.** 60 strategy variants at NY 00:00: White RC p = 1.00, Hansen SPA p = 0.75, Deflated Sharpe = 0.000. |
| 6. Survives costs? | Moot at midnight (no gross edge). The only gross "edge" (17:00 rollover) is **+3.10 pips on bid, −3.85 pips at the real ask**. |
| 7. Broker/feed specific? | Midnight is feed-consistent (Dukascopy 1.62 vs HistData 1.66 pips, same 90 days). The rollover candle is a quote artifact. |

Final class: **execution/liquidity artifact (rollover) + no meaningful anomaly (midnight).**

## 2. Exact timestamp definition (critical data finding)

- **HistData M1 labels are America/New_York wall-clock (DST-observing), not fixed EST as documented.** Proof: NFP peaks at 08:30 label in both summer and winter; the Sunday open is 17:00 label year-round. A naive +5 h shift puts every summer bar 1 h off. Loader fixed (`src/load.py`); revalidated: NFP peaks at 08:30 NY across 2006–2026.
- Mapping: "00:00 UTC-4" is **00:00 EDT = 04:00 UTC** in summer, but a fixed UTC-4 chart is 23:00 EST (= 04:00 UTC) in winter. Frames tested with DST handled per date: A NY 00:00; B fixed 04:00 UTC; B2 fixed 05:00 UTC; C 00:00 UTC; E NY 17:00 (= MT5 00:00 on NY-close GMT+2/+3 brokers).
- Your BrightFunded MT5 server clock equals UTC (live tick 10:51:23 vs UTC 10:51:24), so its "00:00" is 00:00 UTC, not UTC-4.

## 3. Statistical evidence / 4. Hour-of-day comparison (weekdays 2012–26, `p2_hour_abs_moves.csv`)

Mean \|move\| in pips from each NY hour boundary (S/W averaged):

| NY hour | 00 | 01 | 03 | 08 | 10 | 17 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|
| 5 min | **1.57** | 2.01 | 4.93 | 3.77 | 5.77 | 3.05 | 1.91 | 1.69 |
| 15 min | **2.60** | 3.29 | 7.96 | 6.44 | 8.96 | 3.26 | 3.11 | 2.69 |
| 60 min | **5.09** | 6.71 | 13.81 | 15.27 | 17.16 | 4.27 | 5.57 | 4.88 |

Vol-jump scan of all 1,440 anchor minutes (post-5 m / pre-5 m): NY 00:00 rank 94/1440 (summer), 208/1440 (winter), ratio 1.07–1.15. Top anchors are 08:30 NY, 16:55–17:00 NY, 02:00 NY. **00:00 UTC ranks 12th–31st** (ratio 1.46–1.71).

## 5. Directional statistics (anchor A, n = 4,105)

| Horizon | P(up) | mean (pips) | t | mean \|r\| | skew | kurt |
|---|---|---|---|---|---|---|
| 5 m | 0.466 | −0.04 | −0.83 | 1.62 | 9.7 | 263 |
| 15 m | 0.477 | −0.01 | −0.08 | 2.65 | 5.1 | 121 |
| 60 m | 0.499 | −0.01 | −0.09 | 5.21 | −0.2 | 7.6 |

198 slice-tests (weekday, month, year, DST states, terciles of 15 known-before features, Spearman): 20 raw p<0.05 (chance ≈ 10), **5 survive BH-FDR, all are one effect**: the pre-midnight 15/60-min move mildly mean-reverts (ρ ≈ −0.08 to −0.10 vs 15-min return). Economically tiny and it did not survive the strategy layer. MFE/MAE 60 m: 5.4/5.4 pips, P(MFE>MAE) = 0.503 (symmetric).

## 6. Volatility statistics

Midnight \|r15\| is 0.40–0.64× the all-day 15-min move in **every year 2010–2026**; era means 2.63 / 2.73 / 2.59 pips (2010-15 / 16-20 / 21-26). Volatility is predictable only via ordinary vol clustering (ATR/range terciles: 1.9 → 3.5 pips).

## 7. Microstructure (Dukascopy real bid/ask, 90 random weekdays 2018–26; MT5 broker, 7 weeks)

| | NY 23:59 | **NY 00:00** | NY 17:00 | NY 17:05 |
|---|---|---|---|---|
| Dukascopy spread (pips) | 0.98 | **0.97** | **6.60** | 6.94 |
| ticks / min | 45 | 51 | **9** | 19 |
| MT5 broker spread mean/max | 0.13 | 0.15 / 0.3 | **1.10 / 22.4** | 0.12 / 1.1 |
| MT5 1-min candle range | 0.83 | 1.18 | **10.1** | – |

- At NY 00:00: bid move ≈ mid move, ΔSpread ≈ 0 → genuine price movement, but small (1.62 pips in 5 min).
- At 17:00: ΔSpread +1.9 to +3.2 pips inside 1–5 min; mean bid −1.1 to −1.3 vs mean mid −0.2 to +0.3. **The big candle is quote behavior**, exactly the case loop.md warns about.

## 8. Cross-asset (USD factor built from EUR/AUD/NZD/JPY/CAD/CHF — no GBP pair)

USD factor explains 38% (15 m) / 44% (60 m) of midnight GBPUSD variance, in line with other hours (32–57%). Top-decile midnight moves are ~46% USD-driven, the rest GBP-specific. **Correction to my own first pass:** regressions using synthetic EURGBP/GBPJPY (built from GBPUSD) gave R² = 1.00 — circular and discarded.

## 9. News

No tier-1 release is scheduled 00:00–01:00 NY. Excluding first-Friday (NFP), Christmas–New Year and top-2% days leaves mean\|r15\| 2.36–2.65 and mean r15 ≈ 0 (\|t\| < 0.12). **Limitation:** no offline economic calendar (CPI/GDP/BoE/FOMC dates) was available, so this used proxies.

## 10–13. Strategies, backtest and cost-adjusted results

Strategies A (pre-range breakout), B (+vol filter), C (sweep-reversal), D (momentum after 5 m), E (fade abnormal 5 m), E2 (fade pre-15 m), F (cross-asset confirm) + naive entries at 00:00/01/02/05; holds 15/30/60/120; 4 anchors; costs gross / 0.6 / 1.5 / 3.0 pips RT. 240 cells; fills at bar open, SL priority on ties, entry-bar stops honoured (`test_engine.py` passes).

- Anchor A: **naive entry gross mean = 0.00 across all 32 cells** (range ±0.21). Only 1/60 cells positive at normal cost (+0.009 pips/day).
- Best anchor-A cell: fade abnormal first 5 m, hold 120: +1.65 gross (t 2.7), +1.05 at 0.6-pip cost (t 1.7). One of 60 cells → Bonferroni-equivalent p ≈ 0.4.
- Strategy G (walk-forward logit/GBM, 2016–26, yearly refit): anchor A AUC 0.50–0.51, net **−1.36 / −1.71 pips/trade** (t −4.3 / −7.5).

## 14. Robustness / 15. Significance

| Test (normal cost) | Anchor A | Anchor E (17:00) |
|---|---|---|
| White Reality Check p | **1.000** | 0.036 |
| Hansen SPA p | **0.750** | 0.010 |
| Deflated Sharpe, best of 60 | **0.000** (SR 0.03 vs null max 2.16) | 0.000 pooled (SR 0.46 vs 2.60, 240 trials) |

Entry-time sensitivity (00:00→00:01/02/05) and hold sensitivity are flat at zero for A. Pooled 240-cell SPA p = 0.022 is driven entirely by the rollover anchor.

## 16. Regime

Stable null across 2010-15 / 2016-20 / 2021-26 and across ATR/range terciles (see §6). 2005-2010 appears only in the candidate scoreboard (`p3_candidates.csv`): wider moves everywhere (all hours), same conclusion.

## 17. Data-feed comparison

- Dukascopy vs HistData at NY 00:00 first-5-min: **1.62 vs 1.66 pips** (n = 90); mean \|close diff\| at NY hour 0 = 0.16 pips (p99 3.8), the *most* feed-consistent hour. Feeds diverge in fast markets (NY 02–04, p99 21–36 pips on 1-min closes).
- MT5 vs HistData: 1-min return correlation 0.92, mean \|diff\| 0.33 pips.
- Rollover: HistData first-5-min \|move\| 2.52 vs Dukascopy 2.33 (n = 20). Its "edge" reverses sign with real asks.

## 18. Failure modes of this study (read before relying on it)

1. Dukascopy is a **90-day random sample**, not 2005–2026 ticks (server throttling: HTTPS resets, HTTP 429). MT5 gives only ~7 weeks (50k-bar cap). OANDA/TrueFX not accessed.
2. HistData is **bid-only M1**; spread costs before the samples are assumed (0.6/1.5/3.0), not measured. Measured midnight spread: Dukascopy 0.97, MT5 raw 0.15.
3. News tests use proxies (no calendar). Event tables start 2010-11 (SPX/NSX data start there).
4. Rollover strategy results at anchor E are bid-artifact results, not tradeable ones.
5. Your chart's actual timezone/broker is unknown; if it differs from the frames tested (e.g., a broker on NY-close GMT+2/+3, where server 00:00 = 17:00 NY), the answer is the rollover candle.

## Final evidence scorecard

| | |
|---|---|
| Phenomenon exists | **NO** (at NY 00:00 / 04:00 UTC); YES at 17:00 NY and 00:00 UTC |
| Directional predictability | **NO** |
| Volatility predictability | **NO** (only generic vol clustering) |
| Economic mechanism | **UNKNOWN** at midnight; **SUPPORTED** for rollover (spread/liquidity) |
| Broker artifact | **YES** for the 17:00 candle; **NO** for midnight |
| Tradeable after costs | **NO** |
| Out-of-sample robustness | **FAILED** |

## What to check next (one action)

Open your chart, hover the "00:00" candle that looks big, and read its true timestamp in UTC. If it is 21:00/22:00 UTC (or 17:00 NY), it is the rollover spread candle; if 00:00 UTC, it is the Tokyo open. Either way, do not trade it.

---

## Addendum — the 00:00–05:00 NY (UTC-4) window on H1 (`src/p12_window.py`, `out/p12_window_strategies.csv`)

Follow-up to the user's clarification: the observed move is anywhere between 00:00 and 05:00 UTC-4, not at the 00:00 minute.

- **The window is genuinely active.** H1 bar range (NY clock): 00h 10.9 → 02h 24.1 → 03h 28.6 → 04h 30.4 pips. Window (00:00–05:00) H-L: mean 52.8 pips, median 47; **64% of days ≥ 40 pips**. Share of the window's range by hour: 00h 10%, 01h 13%, 02h 22%, 03h 26%, 04h 28%. So it is the **London open (02:00–05:00 NY)**, not midnight, that produces the move.
- **It is average, not special.** The 00–05 window ranks 11th of 20 five-hour windows (1.09× the average); 06:00–11:00 NY windows are larger (~68 pips).
- **Direction is a coin flip.** Net 00→05 return: P(up) 0.490, mean −0.91 pips (t −1.63). corr(00–03 return, 03–05 return) = −0.027; same sign 49.0%.
- **Strategies anchored at NY 03:00 (signals from the 00:00–03:00 H1/M1 range; 18 variants, holds to 05:00/06:00):** gross best is fade of the 00–03 move (+0.93 pips, t 2.0 — 1 of 18, no cost survives: −0.57 at normal, ~+0.3 at 0.6-pip cost, not significant). Range breakout gross +0.55 (t 1.4), net −0.22 to −0.85. Trend-continuation loses even gross (−0.93, t −2.0). **Reality Check p = 1.000, SPA p = 0.999.**
- Bug caught and fixed while doing this: my first run silently truncated holds to ~41 minutes (bar-array cap); all numbers above are from the corrected rerun. The earlier anchor grid (`p6`) used holds ≤120 min inside its window and was not affected.

**Conclusion for this window:** large, symmetric, unpredictable London-open volatility. It is a *volatility* phenomenon, not a directional edge; useful for sizing/stops, not for a signal.

---

## Addendum 2 — News inside the 00:00–05:00 NY window (`src/p13_news.py`, `data/news/ons_release_dates.csv`, `out/p13_news_continuation.csv`)

**Source coverage (honest):** ForexFactory/Investing.com blocked (Cloudflare 403), Trading Economics guest API discontinued, FairEconomy JSON is current-week only. **Only UK ONS release history was retrievable** (official release-version dates, Dec 2015–Sep 2026): CPI 130, Unemployment 125, Retail Sales 129 = 384 events (GDP series URL 404, skipped). No Eurozone/German (PMI, Ifo, ZEW), BoJ/RBA or BoE data. Release clock inferred from price reaction: **09:30 London (04:30 NY) through ~2019, 07:00 London (02:00 NY) from ~2020**, i.e. always inside the window.

- **News moves price, a lot:** mean |first 5 min| 11.4 pips vs 4.75 at the same clock on non-event days (2.4×; CPI 2.8×), MWU p < 1e-15.
- **But news does not explain the window:** UK-release days are 14% of days; window range 58.4 pips (75% ≥ 40) on release days vs 49.7 (59% ≥ 40) otherwise. Removing them only moves the window mean 50.9 → 49.7. **The big moves on ordinary days are London-open flow, not news.**
- **Direction after the release is not reliably tradeable:** continuation of the first-5-min move (enter +5 min, hold 30/60/120): P(continue) 0.51, gross ≈ 0 for all-releases; sign of the result flips between 2016-20 (−3.6 pips) and 2021-26 (+4.2). Only lead: **CPI, 60-min hold, +4.6 pips gross (t 2.5, raw p 0.015, Bonferroni 0.18 over 12 tests, n = 106)**, positive in both halves (+2.6 / +6.1) and +3.1 after 1.5-pip cost. Suggestive, not significant; would need an out-of-sample forward test on new CPI releases before trusting it.

---

## Addendum 3 — What happens after the big 00:00–05:00 NY move (`src/p14_after.py`, `out/p14_after_big_move.csv`)

Signal known at 05:00 NY; outcomes from 05:00 to 06:00 / 08:00 / 12:00 / 17:00 NY, measured in the direction of the window's net move. n = 3,854 days (2010-11 → 2026-09). "Big" = |net move| ≥ its expanding 75th percentile (no lookahead; ≈ 36 pips; n = 740).

- Window net move: mean |26| pips, median 20, p75 36, p90 55.
- **Continuation vs reversal is a coin flip:** P(continue) 0.45–0.53 at every horizon; only marginal item is big DOWN moves partly bouncing in the next hour (P(cont) 0.41, −2.3 pips, t −2.5; 1 of ~32 cells, not corrected).
- **The volatility does not stop:** on big-move days price exceeds the window's high/low again by 12:00 NY 81% of the time; median further 05:00–12:00 range 75 pips vs 69 on all days. The window extreme is the 00–17 day high only 38% of the time (low 37%).
- **Giveback:** ≥50% of the window move is retraced by noon on 56% of big-move days (78% on average days; small moves are easy to give back).
- **Unstable:** signed 05→12 drift on big-move days −2.2 pips (2010–17) vs +3.7 (2018–26).

---

## Addendum 4 — What precedes / causes the big 00:00–05:00 NY move (`src/p15_causes.py`, `out/p15_day_table.parquet`)

n = 3,564 days. "Big" = expanding-75th-percentile (no lookahead) of window range (base P = 17.5%) or of |net move| (base 20.4%).

- **Volatility regime is the dominant precursor.** P(big range) by ATR14 quartile: 5.5% / 11% / 17% / **36%**; by prior-day range: 9% / 11% / 19% / **30%**. Prior-evening (19:00–00:00 NY) range Q4 vs Q1: 30% vs 7%, but *relative to ATR* the effect is weak (22% vs 15%), so it is regime carry-over, **not** "quiet Asia compression then explosion" (compression does not predict).
- **Walk-forward logit 2016–26:** known at 00:00 NY → AUC **0.77** for a big 00–05 range (top predicted quintile: 43% vs 18% base); known at 02:00 → AUC 0.79 for big 02–05 (46% vs 17%). Largest coefficients: ATR14 +0.65, prior-day range +0.45, evening range/ATR +0.43, UK-data day +0.19.
- **UK data day:** P(big range) 25% vs 17%, window 57.8 vs 50.5 pips (355 days).
- **Timeline:** on big days 50% of the move is done by hour 2 (31%), 3 (36%), 4 (23%) — the **London open**; on normal days it is done early (61% by hour 1, i.e. Asia-tail noise). Big days are already ~1.4× busier before London (00–02 range 22.7 vs 16.1 pips).
- **Mechanism:** the USD factor (non-GBP pairs) explains **44%** of GBPUSD variance on big days vs **20%** on normal days → big overnight moves are more broad-USD/macro, less GBP-idiosyncratic.
- **Not a stop-run pattern:** big days sweep *both* sides of the 00–02 range less often (36% vs 58%), i.e. they are one-way trends. (Caveat: partly definitional, since "big" is conditioned on the outcome. The 75% "first break goes with the final direction" stat is therefore not a usable signal.)
- **No direction precursor** (consistent with §5 and Addendum 3): the features predict *size*, not sign.

---

## Addendum 5 — Frozen "big-night" score, out-of-sample (`src/p16_score.py`, `out/p16_*.csv`, `out/fig4_score_stop_sizing.png`)

Logistic score from 4 inputs known at 00:00 NY (ATR14, prior-day range, prior-evening range/ATR, UK-data day), **trained only on 2010-15 (964 days), cutoffs frozen, never refit**; tested on 2016-26 (2,600 days).

- **Forecasts size, out of sample:** AUC 0.777 (big 00–05 range), 0.779 (big 02–05). P(big) by quintile Q1→Q5: 4% / 8% / 15% / 21% / **39%**. Mean 00–05 range 35 → 70 pips (p90 52 → 111). Sub-periods hold: Q5 P(big) 0.40 (2016-19), 0.40 (2020-22), 0.29 (2023-26).
- **Caveat:** the score uses absolute-pip ATR, so in the calmer 2023-26 regime Q5 fires much less (n = 56 days). Re-derive the cutoffs if volatility regime shifts persist.
- **It creates no trading edge:** conditioning 3 entry rules × 2 holds on the score changes nothing usable. Q5-only nights: best +0.07 pips/day at 1.5-pip cost, **Reality Check / SPA p = 0.988**. Q-by-Q results are noise (signs flip quintile to quintile).
- **It does size risk.** 03:00→08:00 NY high-low range by quintile (median / p75 / p90): Q1 37/48/61 · Q2 47/62/79 · Q3 50/66/85 · Q4 57/75/95 · **Q5 74/99/130 pips**. Worst excursion from the 03:00 open, either side (median / p90): Q1 28/57 · Q5 56/109. Practical use: stop distance and position size scale with the score.

---

## Addendum 6 — Forward test on unseen nights (`src/score_forward.py`, `out/forward_log.csv`)

Frozen score (Addendum 5) applied to MT5 GBPUSD nights **2026-09-21 → 09-30**, which post-date all HistData used in every earlier analysis (ends 09-18). Model rebuilt from 2010-15 only; nothing refit.

- All 8 nights scored **Q1 (calm)**: ATR14 ≈ 56–62 pips is below the 2010-15-calibrated cutoffs (the regime caveat from Addendum 5 in action).
- Realized 00:00–05:00 range: mean **35.5 pips** vs the historical Q1 mean of 34.7 (median 36.8); 2 of 8 nights exceeded 55 pips (61.3, 55.7), inside the Q1 p90 of 61.5. Calibration consistent at the calm end.
- **Not a real test yet:** n = 8, one quintile only, so no discrimination between score levels can be assessed (score/range rank corr 0.06). Needs weeks of nights including a volatility expansion.
- Next UK releases on the calendar: Unemployment 2026-10-20, CPI 2026-10-21, Retail Sales 2026-10-23 (flagged in the score).
- To keep accumulating: run `python src/score_forward.py` once after 00:00 NY each night (scores the night, fills earlier nights' realized ranges). Scoring a night needs its 19:00–00:00 NY evening complete.

---

## Addendum 7 — Triggers, calendar proxies, adaptive score, exit models (`src/p18_triggers_adaptive.py`, `src/p19_exits.py`, `out/p19_exit_grid.csv`)

- **Which clock times drive the window** (mean |5-min move| starting each minute, 01:30–05:30 NY, 2016–26, median minute 2.6 pips): **03:00 = 5.0 pips on UK-release AND ordinary days (5.1 / 5.0) → structural London-open flow, not news.** **04:30 NY (09:30 London) = 5.2 pips overall, 7.9 on UK-release days vs 4.8 otherwise** (UK PMIs / legacy ONS slot). 02:00 (UK 07:00 prints) is only 4.2 (3.8 on non-UK days) — weaker than assumed.
- **Calendar proxies (stand-in for the missing EU calendar) do nothing:** last week of month P(big) 14% vs 19%, month-turn 13% vs 18% (both *lower*), mid-month Tuesday n.s.; UK-data flag remains +0.49 logit (p = 0.001). Adding the flags *lowers* OOS AUC (0.734).
- **Regime-adaptive score is worse than the absolute-pip score** (ATR relative to its 250-d median): OOS AUC 0.745 vs **0.777**; 2023–26 AUC 0.67 vs 0.71. The Addendum-5/6 suggestion to re-derive cutoffs is **withdrawn** — keep the frozen absolute score; the calm-regime reading is real (Q5 fires on 6% of 2023–26 nights), not a calibration bug.
- **Exit models (Sec 12 completed):** 72 entry × exit cells (fixed SL 10/20/30 × TP none/10/20/40, trailing 10/20, break-even 10/20; entries: 00–03 range breakout, trend, naive long/short at 03:00; hold cap 5 h). Gross best = naive *short* SL20 +1.32 pips (t 2.7) — its mirror (naive long) is negative, i.e. it is GBPUSD's 2010–26 downtrend, not an exit edge. **Net at 1.5 pips: 0/72 cells positive; at 0.6 pips 17/72 marginally; Reality Check p = 1.000, SPA p = 0.987.** No exit rule creates an edge.
- **Infrastructure:** nightly scheduled task `QueenForwardScore` (Mon–Fri 06:30 local, needs MT5 open; runs `src/run_forward.bat` → `out/forward_run.log`, `out/forward_log.csv`).

## Not done / open (so the record is honest)

Limit-order entry models (skipped: known fill-rigging trap on directionless nulls); DST and spread-regime breakdowns for a "promising" strategy (none survived to need them); OANDA/TrueFX feeds and full-history tick bid/ask (only Dukascopy 90-day sample + 7 weeks MT5); Eurozone/German/BoE/BoJ event dates (no source retrievable); 2005–2009 in the event studies (event tables start 2010-11).
