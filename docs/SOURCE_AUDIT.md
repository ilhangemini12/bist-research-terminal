# Source audit

## Rules
- No login-wall bypass, CAPTCHA bypass, proxy/IP rotation, or private API probing.
- HTTP 403/429 triggers circuit-breaker behavior and fallback.
- Real-time Borsa Istanbul redistribution is treated as licensed data; the free-first build does not redistribute it.
- A public page is not automatically permission to scrape. Providers with unresolved or restrictive terms are disabled for automated ingestion or limited to manually reviewed/public-download usage.
- Two domains backed by the same intermediate upstream count as one lineage for price verification.
- Missing structured financial values remain N/A; PDFs are not silently converted into guessed taxonomy values.

## Current source decisions (2026-10-01)
- **SPK Web Services**: ACTIVE for broker/bank/activity-permission discovery, listed-company registry, special-disclosure metadata, and financial-report metadata/documents. A live schema probe confirmed 628 listed-company records and 232 financial-report records in the 2026-01-01..2026-10-01 window. Financial-report detail returns a PDF document in base64 `fileData`, not normalized statement line items, so the terminal does not fabricate 12–20 quarter fundamentals from this endpoint.
- **TSPB**: ACTIVE for member/discovery datasets; monthly discovery discovers the current official detailed-member XLSX from the member page instead of hardcoding a dated filename. A TSPB failure is isolated from SPK discovery.
- **KAP public pages**: DISABLED for automated storage/high-volume normalized ingestion. They remain an official human/reference source. The public-site usage terms do not justify treating the website as a free bulk database.
- **KAP public bulk financial-table download**: ACTIVE as a bounded official periodic source using the bulk-download function documented in KAP's own user guidance. Raw ZIP/HTML-XLS payloads are processed transiently and are not republished; the terminal persists normalized statement facts, period/scope/currency metadata and source lineage. The validated 2025 annual archive contained 764 files; 298/323 requested current-universe tickers parsed, 292 at high confidence. Missing/review-required issuers remain N/A.
- **KAP Veri Yayın Servisi REST API**: PAID_SOURCE_SKIPPED in this free-first build. Structured API access requires the applicable Borsa İstanbul data-distribution agreement, MKK/KAP authorization and API credentials/IP authorization; the terminal will use it only if the user later supplies properly licensed access.
- **Borsa Istanbul Daily Bulletin**: ACTIVE as the official EOD price anchor. A closed-day 2026-09-30 smoke test matched Yahoo exactly for THYAO, ASELS and AKBNK and produced `VERIFIED_2X`. A bulletin that is not yet published opens the run-scoped circuit after bounded failures rather than hammering the endpoint.
- **Borsa Istanbul index reference**: ACTIVE. The public `hisse_endeks_ds.csv` file supplies current membership with ETag/Last-Modified conditional caching. Beginning with 2026-10-01, the terminal persists dated membership snapshots so future point-in-time backtests can use accumulated history. Pre-snapshot historical membership is not invented.
- **Yahoo Finance chart**: ACTIVE as a secondary/free delayed price and historical OHLCV lineage. Never enough alone for `VERIFIED_2X`.
- **Investing.com public pages**: automated provider DISABLED until terms/robots review is explicitly safe.
- **TinyFish**: PAID_SOURCE_SKIPPED by user rule; never used.
- **İş Yatırım public analysis**: BLOCKED for automated ingestion. Its `robots.txt` disallows `/_layouts/`, where commonly used chart/data endpoints live. The terminal does not crawl the blocked endpoint.
- **TSPB data downloads**: ACTIVE for periodic discovery/reference snapshots. Public member factsheets are discovery input, not a price feed.

## Data-integrity consequence
The zero-cost build deliberately accepts lower coverage rather than false precision. Current-day prices remain `SINGLE_SOURCE` until an independent official EOD observation exists. Financial coverage uses only successfully normalized permitted sources; missing/review-required periods remain N/A rather than being inferred. Full 12–20-quarter history is still incomplete. This is a feature of the provenance contract, not a silent data gap.
