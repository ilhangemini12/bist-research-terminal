# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-01
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~97%.
- Full original specification completion: ~87%.
- Daily Update -> artifact build -> commit -> GitHub Pages deployment: SUCCESS.
- Latest validated Daily run: 36911075664.
- Latest validated Pages run: 36911254847.

## Verified coverage
- Current live price verification: 322/323 = 99.7% VERIFIED_2X.
- Five-year OHLCV backfill for the current 323-ticker universe: 323/323 = 100%.
- Durable OHLCV rows: approximately 347,075.
- Durable corporate-action rows: approximately 860.
- Live RSI14/technical coverage after full history restore: 322/323 = 99.7%.
- Current high-confidence financial company coverage: 292/323 = 90.4%.
- Financial depth versus the requested 12–20 quarters: still materially incomplete; current company coverage must not be confused with quarter-depth completion.
- Dynamic current index universe: ACTIVE from official Borsa Istanbul reference.
- Point-in-time membership history: accumulating from 2026-10-01; pre-2026-10-01 membership is not fabricated.
- Python tests collected in the latest build report: 81; JS safe-formula tests are also enabled.
- GitHub Pages: LIVE and latest deployment SUCCESS.

## Stable architecture decisions
1. Price verification uses independent Borsa Istanbul official EOD + Yahoo lineage. One source alone never becomes VERIFIED_2X.
2. KAP public bulk financial downloads are normalized locally; raw bulk files are not republished.
3. Historical OHLCV uses a frozen legacy base plus immutable batch shards. The old single mutable binary-Parquet writer is retired for new batches.
4. History shard runs are idempotent: a duplicate offset restores the existing shard and produces no new commit.
5. TinyFish remains USER_FORBIDDEN / PAID_SOURCE_SKIPPED and must never be used.

## Remaining partial areas
1. Financial depth: 12–20-quarter high-confidence normalized history is not complete.
2. Valuation multiples: P/E, P/B and EV-based ratios must remain N/A where trusted shares/market-cap inputs are unavailable. Do not infer share count from paid-in capital without a validated source/rule.
3. Point-in-time backtesting: pre-2026-10-01 index membership is unavailable, so affected historical backtests retain BACKTEST BIASED.
4. Broker targets/model portfolios/KAP News: only partial, terms-compatible discovery exists.
5. Real-time BIST redistribution: not provided without the required licensed market-data rights.
6. ISATR: current verified-price coverage remains unavailable/stale; do not manufacture a current price.
7. VWAP remains unavailable without real intraday trade/volume data.

## Failure history and bypass rules
- GitHub connector binary ZIP bootstrap repeatedly produced corrupt archives. Abandoned permanently.
- Initial Pages deployments failed before repository-level Pages enablement. Pages was subsequently enabled and the current workflow is successful.
- Monthly discovery once failed on a concurrent non-fast-forward push. Data-writer serialization/rebase handling fixed it.
- Early history runs wrote ephemeral DuckDB state or one mutable large Parquet. Persistence was fixed, but concurrent mutable-Parquet jobs later produced repeated binary rebase/non-fast-forward failures.
- After repeated mutable-Parquet failures, the method was bypassed. Immutable offset shards succeeded for 105–154, 155–204, 205–254, 255–304 and 305–322, and a duplicate run was confirmed idempotent.
- KAP bulk discovery had wrong-route/legacy-XLS assumptions. Final production path is the documented public bulk ZIP with HTML-formatted .xls tables parsed using pandas/lxml.
- SPK PDF reports were not adopted as the broad fundamentals source because the public endpoint returns PDF/base64 documents and current-BIST title mapping was insufficient.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and its validation workflow succeeds.
- Save a checkpoint after every successful stage or before changing methods.
- If the same method fails twice consecutively, bypass it and use another path.
- Prefer the simplest sequence: edit -> test -> validate live -> commit -> continue.
- Do not run competing mutable binary writers from stale commits.

## Next highest-value work
1. Expand KAP financial history by bounded period/year backfills while preserving period/publication-date provenance.
2. Add a trustworthy shares/market-cap source before enabling P/E, P/B and EV multiples.
3. Improve insurance-specific KAP normalization without lowering confidence gates.
4. Expand public/terms-compatible broker target-price/model-portfolio/KAP-news discovery.
5. Preserve BACKTEST BIASED for any period lacking a true point-in-time universe.
