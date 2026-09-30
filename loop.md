# GBPUSD Midnight Move Research Project

## Objective

I observed that GBPUSD frequently makes a relatively large directional move immediately after
00:00 UTC-4 on the chart.

I want to determine:

1. Whether this phenomenon is statistically real.
2. Exactly which clock time is responsible after accounting for DST.
3. What market mechanism could explain it.
4. Whether the move has predictable direction or only predictable volatility.
5. Whether the phenomenon can be converted into a robust, tradeable strategy.
6. Whether the apparent edge survives realistic spread, slippage and execution costs.
7. Whether the phenomenon is broker/data-feed specific.

Do NOT assume that an edge exists.

The final conclusion can be:
- genuine exploitable edge
- volatility anomaly but not directional edge
- execution/liquidity artifact
- broker/data-feed artifact
- historical anomaly
- no meaningful anomaly

==================================================
1. TIMEZONE INVESTIGATION
==================================================

First determine exactly what "00:00 UTC-4" means.

Investigate:

- UTC
- America/New_York
- EST
- EDT
- MT5 broker server time
- GBPUSD trading-day boundaries
- daily rollover
- Asian session opening
- Sydney/Tokyo market hours

Account explicitly for daylight-saving transitions.

Never hardcode a fixed UTC offset across the entire dataset.

Create a mapping:

Date
Local New York time
UTC time
Broker time
DST state

Determine whether the phenomenon occurs at:

A) 00:00 New York time
B) 00:00 fixed UTC-4
C) 00:00 UTC
D) Asian session opening
E) broker trading-day rollover
F) another institutional/session boundary

==================================================
2. DATA REQUIREMENTS
==================================================

Use high-quality GBPUSD historical data.

Prefer:

- tick data
- bid/ask data
- spread data
- volume/tick volume if available

Minimum:

2015-2026

Preferably:

2005-2026

Use multiple independent data sources if possible.

At minimum compare:

- Dukascopy
- TrueFX / institutional-style source
- OANDA if accessible
- MT5 broker data

Do not trust a single retail broker feed.

==================================================
3. DEFINE THE PHENOMENON PRECISELY
==================================================

Do not use subjective descriptions such as:

"big move"

Define objective measures.

For example:

Return from:
00:00 to 00:01
00:00 to 00:05
00:00 to 00:15
00:00 to 00:30
00:00 to 01:00

Also calculate:

High-Low range
Absolute return
ATR-normalized return
Maximum favorable excursion
Maximum adverse excursion
Spread
Slippage if available

Compare against:

23:00
22:00
01:00
02:00
03:00
04:00
05:00

and all other hours.

==================================================
4. DIRECTIONAL ANALYSIS
==================================================

Determine whether there is a directional edge.

Calculate:

P(return > 0)
P(return < 0)
mean return
median return
mean absolute return
standard deviation
skew
kurtosis

Calculate separately for:

Monday
Tuesday
Wednesday
Thursday
Friday

and:

each month
each year
London DST periods
US DST periods

Also condition on:

previous day's direction
previous day's London direction
previous day's NY direction
Asian range direction
previous day's high/low
previous week's high/low
daily ATR
overnight range

==================================================
5. ASIAN RANGE HYPOTHESIS
==================================================

Test whether the midnight move is actually a breakout of a newly formed
Asian-session range.

Measure:

previous 1h range
previous 30m range
previous 15m range
Asian session high
Asian session low
previous day high
previous day low

Test:

00:00 move relative to:

Asian high
Asian low
previous day high
previous day low

Determine whether price:

- breaks the range and continues
- breaks the range and reverses
- sweeps liquidity then reverses
- simply expands volatility without directional persistence

==================================================
6. LIQUIDITY / MARKET MICROSTRUCTURE
==================================================

Investigate:

- daily rollover
- value-date rollover
- liquidity-provider behavior
- spread widening
- order-book depth
- institutional rebalancing
- fixing mechanisms
- overnight positioning
- stop orders
- pending orders around session boundaries
- Sydney/Tokyo opening
- broker rollover
- swaps
- end-of-day inventory management

IMPORTANT:

Separate genuine underlying-market movement from broker quote behavior.

If possible compare:

mid-price movement
bid movement
ask movement
spread

A large candle caused mostly by spread expansion is NOT a genuine trading edge.

==================================================
7. NEWS ANALYSIS
==================================================

Check whether the phenomenon disappears after excluding days with:

- UK CPI
- UK GDP
- UK employment
- BoE decisions
- US CPI
- US NFP
- FOMC
- major geopolitical events
- unexpected central-bank announcements

Also test:

normal days only

If the anomaly remains on normal days, that is much more interesting.

==================================================
8. CROSS-ASSET ANALYSIS
==================================================

Investigate what happens simultaneously in:

EURUSD
GBPJPY
USDJPY
EURGBP
DXY
US10Y
S&P500 futures
NASDAQ futures

Ask:

Does GBPUSD move alone?

Or does USD broadly move?

Or does GBP broadly move?

For example:

GBPUSD ↑
EURUSD ↑
USDJPY ↓

would suggest USD-driven movement.

Whereas:

GBPUSD ↑
GBPJPY ↑
EURGBP ↓

would suggest GBP-specific flow.

This distinction is critical.

==================================================
9. CONDITIONAL PREDICTION
==================================================

Try to predict the direction of the midnight move using information available
BEFORE the move.

Candidate features:

Asian range width
Asian range position
previous day return
previous day high/low distance
weekly high/low distance
ATR
volatility regime
GBPUSD trend
EURUSD trend
USDJPY trend
DXY trend
EURGBP trend
spread
time/day of week
day-of-month
month
news proximity

Do NOT use future information.

Do NOT use indicators that contain lookahead.

==================================================
10. STRATEGY GENERATION
==================================================

Only after establishing the statistical behavior, design strategies.

Test at least:

Strategy A:
Breakout of pre-midnight range.

Strategy B:
Breakout + volatility filter.

Strategy C:
Liquidity sweep + reversal.

Strategy D:
Momentum continuation after first impulse.

Strategy E:
Mean reversion after abnormal initial move.

Strategy F:
Cross-asset confirmation.

Strategy G:
Machine-learning classifier predicting direction.

Do not optimize dozens of parameters immediately.

==================================================
11. ENTRY MODELS
==================================================

Test entries:

00:00 exactly
00:01
00:02
00:05
after first 1m candle
after first 5m candle
breakout of first 5m range
breakout of pre-midnight range

Compare:

market order
stop order
limit order

==================================================
12. EXIT MODELS
==================================================

Test:

fixed TP/SL
ATR TP/SL
time-based exit
opposite signal
trailing stop
break-even
maximum holding period

Test holding periods:

5m
10m
15m
30m
60m
120m

==================================================
13. COST MODEL
==================================================

This is mandatory.

Include:

spread
commission
slippage
spread widening
execution delay

Use realistic GBPUSD costs.

Run:

optimistic
normal
stress

cost assumptions.

If the strategy only works before costs, classify it as FAILED.

==================================================
14. ROBUSTNESS
==================================================

For every promising strategy perform:

- in-sample / out-of-sample
- walk-forward
- yearly breakdown
- monthly breakdown
- weekday breakdown
- DST breakdown
- volatility-regime breakdown
- spread-regime breakdown

Perform parameter sensitivity.

A real effect should not disappear when:

entry = 00:00 → 00:03

or:

ATR multiplier = 1.5 → 1.7

etc.

==================================================
15. STATISTICAL SIGNIFICANCE
==================================================

Calculate:

sample size
confidence intervals
bootstrap distribution
t-test where appropriate
Mann-Whitney test where appropriate
effect size
probability of positive expectancy
multiple-testing correction

IMPORTANT:

Because many hypotheses will be tested, control for data-mining bias.

Use:

White's Reality Check
Superior Predictive Ability test
Deflated Sharpe Ratio

where appropriate.

==================================================
16. REGIME ANALYSIS
==================================================

Determine whether the phenomenon is stable across:

2005-2010
2011-2015
2016-2020
2021-2026

Also test:

high volatility
low volatility
trending markets
mean-reverting markets
GBP-specific volatility regimes
USD-specific volatility regimes

==================================================
17. BROKER ARTIFACT TEST
==================================================

Compare the exact same timestamp across multiple feeds.

If:

Broker A shows a huge candle
Broker B does not
Broker C does not

then investigate whether the effect is:

- spread
- liquidity
- bad ticks
- broker rollover
- synthetic pricing

Do NOT trade it until this is resolved.

==================================================
18. FINAL OUTPUT
==================================================

Produce a research report with:

1. Executive summary
2. Exact timestamp definition
3. Statistical evidence
4. Hour-of-day comparison
5. Directional statistics
6. Volatility statistics
7. Microstructure explanation
8. Cross-asset analysis
9. News analysis
10. Strategy candidates
11. Backtest results
12. Cost-adjusted results
13. Walk-forward results
14. Robustness tests
15. Data-feed comparison
16. Failure modes
17. Final evidence scorecard

Use this scorecard:

Phenomenon exists:
YES / NO / UNCERTAIN

Directional predictability:
YES / NO / UNCERTAIN

Volatility predictability:
YES / NO / UNCERTAIN

Economic mechanism:
SUPPORTED / WEAK / UNKNOWN

Broker artifact:
YES / NO / UNCERTAIN

Tradeable after costs:
YES / NO / UNCERTAIN

Out-of-sample robustness:
STRONG / MODERATE / WEAK / FAILED

==================================================
19. MOST IMPORTANT RULE
==================================================

Do NOT try to prove my hypothesis.

Try to DESTROY it.

If the effect disappears after:

- DST correction
- spread correction
- realistic costs
- out-of-sample testing
- different data feeds

then report that clearly.

The goal is not to find a strategy.

The goal is to discover whether there is a persistent market mechanism that can
support a strategy.