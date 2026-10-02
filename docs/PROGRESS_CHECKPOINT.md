# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-02
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~99%.
- Full original specification completion: ~95%.
- Latest verified market date: 2026-10-01.
- Dynamic current universe: 323 tickers.
- TinyFish remains USER_FORBIDDEN / PAID_SOURCE_SKIPPED and must never be used.

## Verified market/history coverage
- Current price verification: 322/323 = 99.7% VERIFIED_2X.
- Five-year OHLCV backfill: 323/323 = 100%.
- Technical RSI14 coverage: 322/323 = 99.7%.
- Historical price state uses frozen base + immutable shards.
- Duplicate shard runs are idempotent/no-op.
- Point-in-time index membership snapshots accumulate from 2026-10-01; earlier membership is not fabricated.

## Verified financial coverage
- Current high-confidence company coverage: 292/323 = 90.4%.
- KAP reporting periods checkpointed: 2022, 2023, 2024 and 2025; each year has 3M/6M/9M/FY.
- Total normalized financial rows after 2022–2025: 4,260.
- High-confidence financial rows: 4,096.
- Median standalone-quarter depth: 16.
- Tickers with >=12 standalone quarters: 230/323 = 71.2%.
- TTM_4Q ready: 276/323 = 85.4%.
- Tickers with >=16 standalone quarters: 205/323 = 63.5%.
- Tickers with >=20 standalone quarters: 0/323 at this checkpoint.
- Financial depth progress versus minimum 12-quarter target: median 16/12 = target exceeded.
- Financial depth progress versus upper 20-quarter target: median 16/20 = 80%.
- Review-required data remains excluded from high-confidence ratios/TTM.

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
5. TTM is emitted only when four contiguous high-confidence standalone quarters exist.
6. Missing prior periods are never interpolated.
7. Publication dates are not fabricated. Fundamental point-in-time backtests remain guarded where publication date is unavailable.
8. TinyFish is never used.

## Current limitations
- Upper financial-depth target of 20 quarters is incomplete.
- Insurance-specific KAP schemas remain review-required for several issuers.
- Several bank interim statements still lack enough high-confidence flow metrics for full quarterly TTM.
- P/E, P/B and EV-based ratios remain N/A without a trustworthy shares/market-cap source.
- Pre-2026-10-01 point-in-time index membership is unavailable; affected historical backtests remain BACKTEST BIASED.
- Broker target-price/model-portfolio/KAP-news discovery is partial and terms-constrained.
- Real-time BIST redistribution is not provided without required licensed rights.
- ISATR remains the current price-verification gap.
- VWAP remains unavailable without genuine intraday trade/volume data.

## Failure/bypass history
- Corrupt GitHub connector binary ZIP bootstrap: abandoned permanently.
- Old mutable history Parquet produced repeated rebase/non-fast-forward failures: bypassed after repeated failures.
- Immutable history shards completed the full current universe and duplicate runs were proven idempotent.
- KAP wrong-route/legacy-XLS assumptions failed repeatedly; documented public bulk ZIP + HTML-formatted XLS parser became production.
- 2024 financial year backfill had a parser failure path; parser was fixed and the retry succeeded.
- Broad SPK PDF extraction was not adopted because PDFs can be image-heavy and title/ticker mapping is insufficient.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and validation succeeds.
- Checkpoint after every successful stage or before changing methods.
- If the same method fails twice consecutively, bypass it rather than trying a third identical run.
- Preferred loop: plan -> edit -> unit test -> live validation -> checkpoint -> next stage.
- Keep data writes small and restartable.

## Immediate next sequence
1. Run Daily Update + Pages and verify the 2022–2025 16-quarter / TTM pipeline is live.
2. Backfill 2021 periods 1/2/3/4 with one commit checkpoint per period.
3. Run Financial Depth Audit; target median >=20 and measure 12/16/20-quarter distributions.
4. Re-run Daily + Pages.
5. Separately improve insurance/bank normalization and trustworthy shares/market-cap / publication-date provenance without weakening confidence gates.
