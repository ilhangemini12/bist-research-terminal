# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-01
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~98%.
- Full original specification completion: ~92%.
- Latest validated Daily run: 36925457529 — SUCCESS.
- Latest validated Pages run: 36925601735 — SUCCESS.
- Python tests collected by latest build report: 87; JS safe-formula tests enabled.

## Verified market/history coverage
- Dynamic current universe: 323 unique tickers from official Borsa Istanbul reference.
- Current live price verification: 322/323 = 99.7% VERIFIED_2X.
- Five-year OHLCV backfill: 323/323 current-universe tickers checkpointed.
- Technical RSI14 coverage: 322/323 = 99.7%.
- Historical OHLCV storage uses frozen base + immutable batch shards; duplicate shard runs are idempotent.
- Point-in-time index membership snapshots accumulate from 2026-10-01. Earlier membership is not fabricated.

## Verified financial coverage
- High-confidence company coverage: 292/323 = 90.4%.
- 2025 KAP reporting periods checkpointed: 3M, 6M, 9M, FY.
- 2024 KAP reporting periods checkpointed: 3M, 6M, 9M, FY.
- Total normalized financial rows after 2024+2025 checkpoints: 2,319.
- Median high-confidence standalone-quarter depth: 8.
- Tickers with >=8 high-confidence standalone quarters: 258/323 = 79.9%.
- Real TTM_4Q available: 276/323 = 85.4%.
- Tickers with >=12 standalone quarters: 0/323 at this checkpoint.
- Financial depth progress versus minimum 12-quarter target: median 8/12 = 66.7%.
- Financial depth progress versus 20-quarter upper target: median 8/20 = 40%.
- Annual fallback remains available where a high-confidence FY statement exists but four contiguous quarters are not available.
- Review-required data stays excluded from high-confidence ratios/TTM.

## Stable architecture decisions
1. Prices require independent Borsa Istanbul official EOD + Yahoo agreement for VERIFIED_2X.
2. KAP public bulk financial downloads are normalized locally; raw bulk files are not republished.
3. History and new financial backfills use immutable checkpoint shards instead of repeatedly rewriting one large binary file.
4. KAP 3M/6M/9M/FY income/cash-flow values are treated as cumulative YTD and normalized conservatively:
   - Q1 = 3M
   - Q2 = 6M - 3M
   - Q3 = 9M - 6M
   - Q4 = FY - 9M
   Balance-sheet values remain period-end stocks.
5. TTM is emitted only when four contiguous high-confidence standalone quarters exist.
6. Missing previous periods are never interpolated.
7. Publication dates are not fabricated. Fundamental point-in-time backtests must remain guarded where publication date is unavailable.
8. TinyFish remains USER_FORBIDDEN / PAID_SOURCE_SKIPPED and must never be used.

## Known partial areas
- Financial depth target: 12–20 quarters is not complete; 2025 currently provides four periods.
- Insurance-specific KAP schemas remain review-required for several issuers.
- P/E, P/B and EV ratios remain N/A without a trustworthy shares/market-cap input.
- Pre-2026-10-01 point-in-time index membership is unavailable; affected historical backtests remain BACKTEST BIASED.
- Broker target-price/model-portfolio/KAP-news discovery is partial and terms-constrained.
- Real-time BIST redistribution is intentionally not provided without licensed rights.
- ISATR remains the one current-price verification gap.
- VWAP remains unavailable without genuine intraday trade/volume data.

## Failure/bypass history
- Corrupt GitHub connector binary ZIP bootstrap: abandoned.
- Old single mutable history Parquet caused repeated rebase/non-fast-forward failures: bypassed after repeated failures.
- Immutable history shards succeeded for the full current universe and duplicate runs were proven no-op/idempotent.
- KAP legacy/wrong-route probes failed repeatedly; documented public bulk ZIP + HTML-formatted XLS parser became the production method.
- Broad SPK PDF extraction was not adopted because PDFs can be image-heavy and title/ticker mapping is insufficient.
- Financial backfill now uses immutable year/period/batch shards for new periods; the original 2025 FY/9M base remains a frozen compatible legacy checkpoint.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and validation succeeds.
- Checkpoint after each successful data stage or before method changes.
- After two consecutive failures of the same method, bypass it rather than retrying indefinitely.
- Preferred loop: plan -> edit -> unit test -> live validation -> checkpoint -> next stage.

## Immediate next sequence
1. Backfill 2023 periods 1/2/3/4 with per-period immutable checkpoint commits.
2. Run Financial Depth Audit; verify median >=12 and count of tickers with >=12 standalone quarters.
3. Run Daily + Pages and validate TTM, quarter YoY and growth outputs on live data.
4. If 2023 is stable, extend 2022 toward 16-quarter depth, then 2021 if needed for the 20-quarter upper target.
5. Separately improve insurance/bank normalization and trustworthy publication-date provenance without weakening confidence gates.
