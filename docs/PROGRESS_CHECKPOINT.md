# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-03
Rule: only GitHub-committed and workflow/test-verified work counts as progress.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~99.7%
- Full original specification completion within free/legal constraints: ~98%
- Latest validated Daily run: 37094255618 — SUCCESS
- Latest validated Pages run: 37094284447 — SUCCESS
- Python tests: 114 passed
- JS safe-formula tests: PASS
- TinyFish: USER_FORBIDDEN / never use

## Verified coverage
- Configured universe: 323 tickers
- VERIFIED_2X current price: 322/323 = 99.7%
- Five-year OHLCV history: 323/323 = 100%
- RSI14 / technical coverage: 322/323 = 99.7%
- Explicit KAP total-share coverage: 323/323 = 100%
- High-confidence financial coverage: 310/323 = 96.0%
- Median standalone-quarter depth: 22
- >=12 standalone quarters: 259/323 = 80.2%
- >=20 standalone quarters: 207/323 = 64.1%
- TTM 4Q ready: 293/323 = 90.7%
- Extended period-matched valuation inputs active: 293/323 = 90.7%
- Core extended debt + D&A + capex ready: 262/323 = 81.1%
- EV/EBITDA available: 234 tickers
- Net-debt/EBITDA available: 234 tickers
- FCF yield available: 261 tickers
- Positive trailing dividend yield: 104 tickers
- KAP/SPK recent disclosure metadata: 9 rows in latest live dataset
- Point-in-time universe snapshots: accumulating from 2026-10-01; pre-2026-10-01 membership is not fabricated

## Stable architecture
1. VERIFIED_2X requires independent Borsa Istanbul official EOD + Yahoo lineage.
2. Same-day verification can retain only same-trade-date durable verified evidence; stale dates do not qualify.
3. Five-year OHLCV is durable via immutable shards and duplicate runs are idempotent.
4. KAP financial history is durable via immutable period/year shards.
5. Cumulative KAP flows are normalized conservatively: Q1=3M, Q2=6M-3M, Q3=9M-6M, Q4=FY-9M.
6. TTM is emitted only from four contiguous high-confidence quarters.
7. KAP explicit total-share count is the only production share-count path.
8. Market cap / P-E / P-B / P-S require VERIFIED_2X price where applicable; missing values remain N/A.
9. Extended EV/debt/FCF metrics require period-matched exact-label KAP checkpoints.
10. LOW_DEBT and HIGH_FCF_YIELD presets are active because their verified inputs now exist. HIGH_ROIC remains disabled until verified inputs are complete.
11. Raw KAP archives are not republished.
12. Missing licensed/intraday/historical point-in-time inputs are not fabricated.

## Latest failure / bypass decisions
- 2026-10-03 preset regression: fixed; current Daily run passes 114/114 tests and Pages deploy passes.
- Same-issuer share-class audit proved KRDMA/KRDMB share the exact KAP company title with KRDMD and donor filenames name all three tickers.
- Experimental same-issuer repair method failed twice:
  1. test import path error;
  2. stale helper cleanup left an undefined unicodedata reference.
- Per the two-failure rule, that repair method is BYPASSED. No third retry. KRDMA/KRDMB remain N/A unless a different, independently validated ingestion path is introduced.
- İş Bankası A/B/C classes have exact-title siblings but no high-confidence donor; no financial values are copied.
- Recent SPK disclosure rows currently have zero current-universe exact-title matches; no forced ticker mapping is performed.

## Remaining material gaps
1. Pre-2026-10-01 historical point-in-time index membership is unavailable.
2. Genuine intraday data / VWAP and licensed real-time BIST redistribution are unavailable in the free-first build.
3. Broker target-price/model-portfolio coverage is partial because current candidates are login-gated, blocked by terms/robots, or paid.
4. ISATR remains the current price verification gap.
5. 13 current-universe tickers are not high-confidence financials; unsupported repairs remain N/A.
6. ROIC remains disabled until verified EBIT/effective-tax/invested-capital inputs are available.
7. Recent SPK disclosure metadata is useful but may contain zero current-universe matches in a given 7-day window.

## Method discipline
Plan -> smallest edit -> unit test -> live validation -> checkpoint -> continue.
Never count speculative progress.
Save partial successes immediately.
If the same method fails twice, bypass it and use a different method.
Do not weaken quality gates to increase coverage.
