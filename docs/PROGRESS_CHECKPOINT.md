# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-01
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~94%
- Full original specification completion: ~82%

## Verified coverage
- Current live price verification: 322/323 = 99.7% VERIFIED_2X.
- Current high-confidence financial company coverage: 292/323 = 90.4%.
- Current financial depth: materially below the requested 12–20 quarters; annual/high-confidence normalization works, historical quarter backfill remains.
- Committed 5-year OHLCV universe coverage: first 105 tickers of the current sorted universe have been successfully processed/committed through offsets 5 and 55 plus the original five-ticker bootstrap. Remaining batches begin at offset 105.
- Dynamic current index universe: ACTIVE from official Borsa Istanbul reference.
- Point-in-time membership history: accumulating from 2026-10-01; pre-2026-10-01 history is not fabricated.
- GitHub Pages: LIVE.
- Daily -> Pages chain: SUCCESS.
- Python test collection: 79 at last build report; JS safe-formula tests enabled.

## Current blockers / partial areas
1. Historical OHLCV backfill:
   - Data fetch itself succeeds.
   - Offset 105 fetched successfully but commit failed because multiple history jobs had been queued from older commits and binary Parquet conflicted during git rebase.
   - Do not queue multiple history trigger commits at once.
   - New rule: run one batch, wait for SUCCESS and pushed commit, then trigger next batch from latest main.
2. Financial statements:
   - KAP bulk parser is productionized.
   - High-confidence company coverage is 90.4%.
   - Requested 12–20-quarter depth is not complete.
3. Backtesting:
   - Metrics, look-ahead guard and survivorship warning exist.
   - Pre-2026-10-01 point-in-time index membership is unavailable.
4. Broker targets/model portfolios/KAP news:
   - Partial discovery only; must remain within public/terms-compatible boundaries.
5. Real-time market data:
   - No licensed real-time BIST redistribution. This is intentional.
6. TinyFish:
   - USER_FORBIDDEN / PAID_SOURCE_SKIPPED. Never use.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and its validation workflow succeeds.
- Save a checkpoint after every successful stage or before changing methods.
- If the same method fails twice consecutively, bypass it and use another path.
- Prefer the simplest sequence: edit -> test -> validate live -> commit -> continue.
- Never run multiple binary-Parquet history writers from stale trigger commits in parallel.

## Immediate next sequence
1. Re-run history offset 105, limit 50 from latest main; wait for complete SUCCESS.
2. Then sequentially run offsets 155, 205, 255 and 305 (last batch bounded by remaining tickers).
3. Trigger Daily Update once history is complete so RSI/SMA/etc. are published from durable history.
4. Rebuild report and verify live dashboard/Excel.
5. Only then continue quarter-depth financial backfill and partial broker-target/news work.
