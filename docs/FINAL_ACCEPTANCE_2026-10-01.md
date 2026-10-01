# Final Acceptance — 2026-10-01

## Operational status

BIST Research Terminal V2 is operational as a free-first GitHub Actions + GitHub Pages research pipeline.

- Repository: https://github.com/ilhangemini12/bist-research-terminal
- Dashboard: https://ilhangemini12.github.io/bist-research-terminal/
- Accepted Daily run: https://github.com/ilhangemini12/bist-research-terminal/actions/runs/36875958445
- Accepted chained Pages run: https://github.com/ilhangemini12/bist-research-terminal/actions/runs/36876122763
- Daily artifact: BIST-Research-Latest, artifact ID 11168971443
- Artifact SHA-256: e6d94a3d4894b8d8f2bad43b18d374175d3e8b53ae71373da3203759b1330471

## Acceptance evidence

- 72 Python unit/stress tests passed.
- JavaScript safe-formula tests and static syntax checks passed.
- Live BIST index universe loaded from the official reference file.
- 324 unique live tickers tracked across configured indices.
- Current-day prices remain unverified when fewer than two independent fresh upstreams exist.
- Closed-day 2026-09-30 verification matched BIST and Yahoo exactly for THYAO, ASELS and AKBNK and produced VERIFIED_2X.
- Daily Excel snapshot and status report are produced and uploaded as a GitHub Actions artifact.
- Successful Daily Update automatically triggers a separate workflow_run Pages deployment.
- Pages payload validation, artifact upload and deployment passed.
- Point-in-time index-membership history is persisted in Git-tracked Parquet state beginning 2026-10-01.
- Second-run restore proved durability: prices=324, price_verification=324, current membership=406, membership history=406.
- Re-running the same snapshot date remained idempotent: history stayed at 406 rows.

## Data policy

- TinyFish is forbidden and unused.
- No paid scraper, proxy rotation, CAPTCHA bypass, login-wall bypass or mandatory LLM call is used.
- Price conflicts are not averaged.
- Single-source prices do not become VERIFIED_2X.
- Missing structured financial values remain N/A rather than inferred.

## Known external/data-coverage limits

- The zero-cost SPK public financial service exposes report metadata and PDF documents rather than normalized 12–20-quarter line items.
- Structured KAP REST ingestion requires separately authorized/licensed access and is not impersonated by scraping public pages.
- Point-in-time index membership history before 2026-10-01 is not fabricated; affected earlier-period backtests retain BACKTEST BIASED.
- Broker target-price/model-portfolio coverage remains partial where terms, login or licensing prevent compliant automated ingestion.

This document records the accepted operational baseline. Future changes should preserve the VERIFIED_2X provenance contract and the failure/circuit-breaker protections.
