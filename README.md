# BIST Research Terminal V2

![Daily Update](https://img.shields.io/badge/Daily%20Update-GitHub%20Actions%20ready-2563eb)
![Data Quality](https://img.shields.io/badge/Data%20Quality-VERIFIED__2X%20default-0f766e)
![Tests](https://img.shields.io/badge/Tests-unit%20%2B%20stress-7c3aed)
![Cost](https://img.shields.io/badge/Default%20cost-%240%2Fmonth-16a34a)

**FREE-FIRST · MULTI-SOURCE · VERIFIED · CUSTOMIZABLE · STRESS-TESTED**

A personal BIST research terminal built around one non-negotiable rule: **provenance first, calculations local, stale/conflicting/single-source prices never masquerade as verified data**.

> Current build: the research core, static dashboard, Excel exporter, dynamic BIST universe loader, source catalog, strategy engine and CI workflows are implemented and locally tested. The bundled browser data is explicitly labelled `DEMO_FIXTURE_NOT_LIVE`. A live price is promoted to `VERIFIED_2X` only when at least two independent upstream lineages agree for the same normalized trade date/state.

## Implemented core

- Official Borsa İstanbul index-universe loader from `hisse_endeks_ds.csv`; enabled indices live in `config/indices.yaml`, not hard-coded constituents.
- SPK public-service adapter for intermediary/bank registries, activity permissions, listed-company metadata, financial-report metadata and special disclosures.
- Source catalog with official/secondary, free/login/delay, lineage, robots/TOS and operational status metadata.
- Provider interface, fallback chain, bounded retry, run-scoped circuit breaker and failure isolation.
- Strict price lineage and `VERIFIED_2X / SINGLE_SOURCE / SOURCE_CONFLICT / STALE / UNVERIFIED` handling. There is **no one-source official exception**.
- Freshness and sanity guards; malformed payload/schema change, bad ticker, duplicate rows, zero/negative values, balance-sheet equation and target-age checks.
- Technical engine: RSI 7/14/21; SMA 5/10/20/50/100/200; EMA 12/20/26/50/200; MACD; ATR14; Bollinger; ADX/+DI/-DI; ROC 5/20; OBV; volume MA/ratio; historical volatility; beta/performance helpers; 52-week distances.
- Fundamental engine: market cap, EV, P/E, P/B, EV/EBITDA, EV/Sales, P/Sales, EPS, BVPS, ROE, ROA, ROIC, margins, net debt/leverage, liquidity, dividend/payout and FCF yield. Missing inputs remain N/A.
- Growth and sector normalization helpers: YoY/TTM/CAGR, sector mean/median, percentile, z-score and discount-to-median.
- Safe Strategy Lab expression interpreter using Python AST walking; **no Python `eval()`**, imports, attribute access or function calls.
- Built-in Özkan Filiz and Volkan Kocabaş public-methodology reconstructions plus Value/Quality/Growth/Dividend/Momentum/Oversold/Trend/Low Debt/High ROIC/High FCF Yield combinations.
- Backtest metrics with publication-date look-ahead guard and explicit `BACKTEST BIASED` warning when point-in-time universe is unavailable.
- DuckDB + Parquet storage layer with incremental architecture; CSV/JSON reserved for exports/snapshots.
- Static GitHub Pages dashboard: Light/Dark/System, accent color, density, verified-only filter, watch-style scanner, custom formulas, settings JSON import/export, widget visibility/reordering/sizing, table column visibility/order/width, multi-sort and configurable tabs.
- Excel snapshot with every requested sheet name, including Data Quality, Source Status and Sources.
- GitHub Actions definitions for weekday post-close update, monthly source discovery and Pages deployment.

## Zero-cost policy

Default operating budget is **$0/month**. TinyFish is explicitly forbidden. The project uses no paid scraping service, paid proxy, CAPTCHA bypass, paywall/login bypass or mandatory daily LLM call. A paid-only source is catalogued as `PAID_SOURCE_SKIPPED` rather than silently substituted.

## Price verification contract

A price may be displayed as `VERIFIED_2X` only when all of the following hold:

1. ticker, market, trade date, timestamp, adjusted/raw state and currency are normalized;
2. the observation is fresh for the expected BIST trading date;
3. candidate records resolve to **at least two independent upstream lineages**;
4. their prices agree within configured tolerance;
5. sanity and corporate-action context checks pass.

Two websites using the same upstream count as one lineage. A single official EOD observation is still `SINGLE_SOURCE` until independently confirmed. Conflicting prices become `SOURCE_CONFLICT`; the system never averages them into a synthetic close.

## Source policy

SPK, TSPB, KAP and Borsa İstanbul are preferred for official registries, company/report/disclosure metadata, index membership, calendars and reference data. Free display access is **not** treated as permission for automated ingestion. Login walls, CAPTCHA, 403/429 and disallowed paths trip the provider circuit breaker rather than triggering bypass attempts.

The current price candidate is Yahoo Finance. Because a second current, free, terms-compatible independent price lineage has not yet been approved, a real live run can legitimately report zero `VERIFIED_2X` prices. That is preferable to false verification.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
python scripts/generate_demo_data.py
python scripts/build_excel_snapshot.py
python -m http.server 8000 -d dashboard
```

Open `http://localhost:8000`.

For a live update:

```bash
python scripts/run_daily.py
python scripts/build_excel_snapshot.py
```

The live pipeline first validates the BIST trading day, refreshes the configured index universe, executes the provider fallback tree, verifies lineages, applies freshness/quality gates, writes the static dashboard dataset and then builds exports.

## Repository layout

```text
src/bist_terminal/
  providers/ quality/ calculations/ strategies/ backtesting/ storage/ pipeline/ exports/
config/ tests/ stress_tests/ dashboard/ docs/ scripts/ data/ artifacts/ .github/workflows/
```

## GitHub deployment

The workflows are ready, but the connected GitHub integration cannot create a repository. After an empty `ilhangemini12/bist-research-terminal` repository exists, the project can be pushed there and `pages.yml` can publish `dashboard/` through GitHub Pages. Until that repository exists, neither a repository URL nor a Pages URL should be represented as live.

## Known limitations

- A second approved, independent, zero-cost live/EOD price lineage is intentionally not faked; live `VERIFIED_2X` coverage can therefore be zero.
- Full KAP financial-statement taxonomy normalization across issuer types is not complete yet; SPK/KAP report metadata are preserved without inventing missing line items.
- Historical point-in-time index universes are not fully populated. Backtests that rely on today’s universe must retain the survivorship-bias warning.
- Broker target/model-portfolio PDF discovery and normalization remain partial and must respect each source’s access/usage terms.
- The included browser fixture is synthetic and exists only to exercise UI behavior; it is not market data.

## Transparency rule

Every critical record should preserve `source`, `source_url`, `retrieved_at`, `data_date` and lineage. Strategy results must be explainable rule by rule—e.g. “P/E below sector median ✓, ROE above sector median ✓, RSI14 threshold ✓, verified price ✓”—rather than issuing an opaque buy/sell verdict.
