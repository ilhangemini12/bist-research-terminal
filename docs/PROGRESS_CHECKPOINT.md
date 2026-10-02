# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-02
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~99%.
- Full original specification completion: ~96%.
- Dynamic current universe: 323 tickers.
- Latest completed 20-quarter Daily run: 37011569409 (SUCCESS).
- Latest Pages deployment: 37011748399 (SUCCESS).
- Python tests collected in the latest build report: 88.
- TinyFish remains USER_FORBIDDEN / PAID_SOURCE_SKIPPED and must never be used.

## Verified market/history coverage
- Five-year OHLCV backfill: 323/323 = 100%.
- Technical RSI14 coverage: 322/323 = 99.7%.
- Historical price state uses frozen base + immutable shards.
- Duplicate shard runs are idempotent/no-op.
- Point-in-time index membership snapshots accumulate from 2026-10-01; earlier membership is not fabricated.
- Current-day price verification is intentionally freshness-aware:
  - During the trading session, official BIST EOD may not yet exist.
  - In that state, current-day VERIFIED_2X remains zero rather than silently using a stale close.
  - Closed-day BIST official EOD + Yahoo two-lineage verification has already been validated.

## Verified financial coverage
- KAP financial years checkpointed: 2021, 2022, 2023, 2024, 2025.
- Each year has 3M / 6M / 9M / FY checkpoints.
- Normalized financial rows after 2021–2025: 5,087.
- High-confidence rows: 4,878.
- High-confidence current company coverage: 292/323 = 90.4%.
- Median standalone-quarter depth: 20.
- Tickers with >=12 standalone quarters: 232/323 = 71.8%.
- Tickers with >=16 standalone quarters: 208/323 = 64.4%.
- Tickers with >=20 standalone quarters: 179/323 = 55.4%.
- TTM_4Q ready: 276/323 = 85.4%.
- TTM is emitted only from four contiguous high-confidence standalone quarters.
- Current TTM status counts in live payload:
  - TTM_4Q: 276
  - ANNUAL_FALLBACK: 16
  - INSUFFICIENT_QUARTERS: 31
- Review-required records remain excluded from high-confidence ratios/TTM.

## Stable architecture decisions
1. Prices require independent Borsa Istanbul official EOD + Yahoo agreement for VERIFIED_2X.
2. KAP public bulk financial downloads are normalized locally; raw bulk files are not republished.
3. History and financial backfills use immutable checkpoint shards instead of repeatedly rewriting one large binary file.
4. KAP 3M/6M/9M/FY flow values are treated as cumulative YTD and normalized conservatively:
   - Q1 = 3M
   - Q2 = 6M - 3M
   - Q3 = 9M - 6M
   - Q4 = FY - 9M
   Balance-sheet values remain period-end stocks.
5. Missing prior periods are never interpolated.
6. Publication dates are not fabricated. Fundamental point-in-time backtests remain guarded where publication date is unavailable.
7. No valuation multiple is enabled without trustworthy shares / market-cap inputs.
8. TinyFish is never used.

## Remaining partial areas
1. Insurance-specific KAP schemas remain review-required for several issuers.
2. Some bank interim statements lack enough high-confidence flow metrics for full quarterly TTM.
3. P/E, P/B and EV-based ratios remain N/A without a trustworthy shares/market-cap source.
4. Pre-2026-10-01 point-in-time index membership is unavailable; affected historical backtests remain BACKTEST BIASED.
5. Broker target-price/model-portfolio/KAP-news discovery is partial and terms-constrained.
6. Real-time BIST redistribution is not provided without licensed market-data rights.
7. ISATR remains a price-verification gap.
8. VWAP remains unavailable without genuine intraday trade/volume data.

## Failure/bypass history
- Corrupt GitHub connector binary ZIP bootstrap: abandoned permanently.
- Old mutable history Parquet produced repeated rebase/non-fast-forward failures: bypassed after repeated failures.
- Immutable history shards completed the full current universe and duplicate runs were proven idempotent.
- KAP wrong-route/legacy-XLS assumptions failed repeatedly; documented public bulk ZIP + HTML-formatted XLS parser became production.
- 2024 financial backfill had a parser failure path; parser was fixed and retry succeeded.
- A 12-quarter Daily publish failed once on a missing KAP source filename; null guard + regression test fixed it and retry succeeded.
- Broad SPK PDF extraction was not adopted because PDFs can be image-heavy and title/ticker mapping is insufficient.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and validation succeeds.
- Checkpoint after every successful stage or before changing methods.
- If the same method fails twice consecutively, bypass it rather than trying a third identical run.
- Preferred loop: plan -> edit -> unit test -> live validation -> checkpoint -> next stage.
- Keep data writes small and restartable.

## Immediate next sequence
1. Improve insurance-specific KAP normalization without lowering confidence gates.
2. Improve bank interim-flow normalization where the KAP schema supports it.
3. Search for a trustworthy, free, terms-compatible shares/market-cap source before enabling valuation multiples.
4. Expand public/terms-compatible broker target-price/model-portfolio/KAP-news discovery.
5. Preserve BACKTEST BIASED wherever historical point-in-time universe or publication-date provenance is unavailable.
