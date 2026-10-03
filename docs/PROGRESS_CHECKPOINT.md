# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-03
Purpose: evidence-based restart point. Only GitHub-committed and workflow/test-verified progress is counted.

## Current operational state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~99.9%.
- Full original specification completion within free/legal constraints: ~99.0%.
- Latest final ROIC validation Daily run: 37119448627 — SUCCESS.
- Latest Pages run after that publish: 37119533016 — SUCCESS.
- Final validation: 128 Python tests PASS + JS formula tests PASS + Excel artifact upload SUCCESS.

## Verified live coverage (as-of 2026-10-02)
- Current universe: 323 tickers.
- VERIFIED_2X prices: 322/323 = 99.7%.
- Five-year OHLCV backfill: 323/323 = 100%.
- RSI14/technical coverage: 322/323 = 99.7%.
- Explicit KAP total-share coverage: 323/323 = 100%.
- High-confidence latest financial coverage: 311/323 = 96.3%.
- Financial depth median: 22 standalone quarters.
- >=12 high-confidence standalone quarters: 259/323 = 80.2%.
- >=20 high-confidence standalone quarters: 207/323 = 64.1%.
- TTM 4Q ready: 294/323 = 91.0%.
- Valuation active: 322/323.
- P/E available: 160; P/B available: 310.
- Extended valuation active: 294/323.
- EV/EBITDA: 234; Net Debt/EBITDA: 234; FCF Yield: 262.
- Guarded ROIC active: 107 tickers; High ROIC >15%: 44.
- Dividend-positive: 104.
- Point-in-time membership history: 811 rows, accumulating from 2026-10-01.

## ROIC completion checkpoint
- Exact KAP EBIT label validated on a 10-ticker live sample: FİNANSMAN GELİRİ (GİDERİ) ÖNCESİ FAALİYET KARI (ZARARI).
- Exact pretax and tax rows are used; effective tax rate is accepted only in [0,1].
- Immutable input checkpoints persisted separately for 2025 H1, 2025 FY and 2026 H1.
- TTM EBIT/pretax/tax uses FY + current YTD - prior comparable YTD.
- Invested capital = equity + complete financial debt - cash.
- Average invested capital requires current and prior-year same-period inputs.
- Bank, Insurance and Brokerage sectors are excluded from this ROIC definition.
- Period mismatch, missing inputs, tax benefits/invalid rates or non-positive invested capital remain N/A.
- Coverage audit: 107/296 eligible non-financial tickers ACTIVE = 36.1%; 44 >15%.
- HIGH_ROIC preset is active only after live pipeline validation.

## Stable architecture decisions
1. Price verification uses independent Borsa Istanbul official EOD + Yahoo lineage. One source alone never becomes VERIFIED_2X.
2. KAP public bulk financial downloads are normalized locally; raw bulk files are not republished.
3. Historical OHLCV uses a frozen legacy base plus immutable batch shards.
4. Financial history, extended metrics and ROIC inputs use immutable checkpoint shards.
5. Duplicate shard runs are idempotent/no-op.
6. Manual weekend validation can use guarded BIST_AS_OF_DATE; normal scheduled weekend behavior still skips.
7. TinyFish remains USER_FORBIDDEN / PAID_SOURCE_SKIPPED and must never be used.

## Remaining partial or structural limits
1. Broker target-price / model-portfolio ingestion remains partial and must pass public-access + terms/robots review before automation.
2. ISATR remains the single current price verification gap; no price is manufactured.
3. Twelve current-universe names still lack latest high-confidence normalized financials.
4. Pre-2026-10-01 point-in-time index membership is unavailable; affected historical backtests retain BACKTEST BIASED.
5. Genuine intraday/VWAP and licensed real-time BIST redistribution are not provided without required market-data rights.
6. SPK recent disclosure metadata may have zero exact current-universe title mappings; approximate name matching is not forced.

## Failure history and bypass rules
- GitHub connector binary ZIP bootstrap repeatedly produced corrupt archives: permanently abandoned.
- Mutable shared history Parquet caused binary rebase conflicts: bypassed with immutable history shards.
- Initial financial mutable state was replaced for new backfills by immutable period shards.
- Share-class exact issuer repair failed twice: third identical retry forbidden; missing rows remain N/A.
- HIGH_ROIC final validation initially failed only because an old acceptance test still expected ROIC to be unavailable. Production ROIC had already passed live validation; the stale contract test was updated, and the next full validation passed 128/128.
- If the same method fails twice consecutively, do not make a third identical attempt.

## Method discipline
- No speculative progress.
- A stage counts only after code/data is committed and its validation workflow succeeds.
- Checkpoint after every successful stage or before changing methods.
- Smallest sequence: analyze -> edit -> unit test -> live validation -> checkpoint -> continue.
- Prefer immutable period/batch shards so failures require only the smallest failed piece to be retried.

## Next highest-value work
1. Determine whether any public, free, terms-compatible broker target/model-portfolio source can be automated. If terms are unclear, keep discovery manual/disabled.
2. Investigate ISATR only with existing approved free sources; do not weaken VERIFIED_2X.
3. Improve the 12 missing latest-financial issuers only through exact KAP mappings/labels; no fuzzy issuer repair after repeated failures.
4. Keep accumulating point-in-time index snapshots prospectively.
