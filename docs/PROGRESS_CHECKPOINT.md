# BIST Research Terminal — Progress Checkpoint

Updated: 2026-10-02
Rule: only GitHub-committed and workflow/test-verified work counts as progress.

## Current state
- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Live dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Core operational maturity: ~99.5%
- Full original specification completion: ~97%
- Latest validated Daily run: 37040350593 — SUCCESS
- Latest Pages run: 37040531056 — SUCCESS
- Python tests: 99 passed
- JS safe-formula tests: PASS
- TinyFish: USER_FORBIDDEN / never use

## Verified current coverage
- Dynamic configured universe: 323 tickers
- Current VERIFIED_2X price coverage: 322/323 = 99.7%
- Five-year OHLCV backfill: 323/323 = 100%
- RSI14 / technical coverage: 322/323 = 99.7%
- Explicit KAP total-share coverage: 323/323 = 100%
- Active verified market-cap coverage: 322/323
- P/E available: 163 tickers; negative/non-positive earnings deliberately remain N/A
- P/B available: 298 tickers
- Current high-confidence financial coverage: 298/323 = 92.3%
- Normalized financial rows: 5,087
- Median standalone-quarter depth: 20
- >=12 standalone quarters: 243/323 = 75.2%
- >=20 standalone quarters: 191/323 = 59.1%
- TTM 4Q ready: 288/323 = 89.2%
- Point-in-time universe snapshots: accumulating from 2026-10-01; pre-2026-10-01 history is not fabricated

## Stable architecture
1. Price VERIFIED_2X requires independent Borsa Istanbul official EOD + Yahoo agreement.
2. Current-day verification stays unverified until official BIST EOD is actually published.
3. Historical OHLCV uses immutable checkpoint shards; duplicate runs are idempotent.
4. KAP bulk financial archives use immutable year/period shards.
5. 3M/6M/9M/FY cumulative flows are converted conservatively:
   Q1=3M; Q2=6M-3M; Q3=9M-6M; Q4=FY-9M.
6. TTM is emitted only from four contiguous high-confidence quarters.
7. KAP explicit total-share count is the only production share-count path.
   Experimental nominal-ratio inference is excluded from valuation.
8. Market cap / P-E / P-B / P-S are emitted only when price is VERIFIED_2X.
9. Sector-relative P/E, P/B, P/S and ROE medians are produced from live rows.
10. Missing values are not estimated.
11. Publication dates and pre-2026 universe history are never fabricated.

## Remaining partial areas
- EV/EBITDA, net-debt ratios, ROIC and FCF yield need trustworthy debt/tax/capex inputs.
- Several strategy presets still reference those unavailable fields and are being converted to clearly labelled available-input approximations rather than fake values.
- Some issuers still have missing/review-required KAP statements.
- Historical point-in-time index membership before 2026-10-01 remains unavailable.
- Broker target-price/model-portfolio/KAP-news coverage is partial and terms-constrained.
- Real-time BIST redistribution is not provided without licensed rights.
- ISATR is the remaining current price verification gap.
- VWAP is unavailable without genuine intraday trade/volume data.

## Failure / bypass history
- Corrupt GitHub connector binary ZIP upload: abandoned permanently.
- Mutable large history Parquet caused repeated rebase conflicts: bypassed; immutable shards completed 323/323.
- KAP wrong-route / legacy XLS assumptions failed: bypassed; documented public bulk ZIP + HTML-XLS parser is production.
- Initial Pages enablement failed via integration token: repo-level Pages was enabled and deploy is now stable.
- Capital bootstrap fallback path failed twice; production was isolated to explicit KAP total-share rows only.
- First valuation Daily run exposed a Turkish decimal parsing regression in the experimental fallback test. Root cause fixed with Turkish decimal/thousands handling; second and final Daily runs passed.
- No failed method is retried a third identical time.

## Method discipline
Plan -> small edit -> unit test -> live validation -> checkpoint -> next stage.
Save successful partial work immediately.
If the same method fails twice, bypass it.
Do not count speculative or unvalidated progress.

## Next sequence
1. Make preset library functional with currently verified inputs; label partial reconstructions explicitly.
2. Add trailing-dividend metrics from already checkpointed corporate actions, with conservative guards.
3. Improve remaining financial review-required issuers where schema evidence supports it.
4. Expand terms-compatible target-price/model-portfolio/KAP-news discovery.
5. Keep unavailable licensed/intraday/point-in-time historical inputs as N/A rather than fabricating them.
