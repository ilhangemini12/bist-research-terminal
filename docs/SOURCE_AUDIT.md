# Source audit

## Rules
- No login-wall bypass, CAPTCHA bypass, proxy/IP rotation, or private API probing.
- HTTP 403/429 triggers circuit-breaker behavior and fallback.
- Real-time Borsa Istanbul redistribution is treated as licensed data; the free-first build does not redistribute it.
- A public page is not automatically permission to scrape. Providers with unresolved terms/robots are disabled or limited to manually reviewed/public-download usage.
- Two domains backed by the same intermediate upstream count as one lineage for price verification.

## Current source decisions (2026-10-01)
- **SPK Web Services**: ACTIVE for broker/bank/activity-permission discovery plus listed-company, financial-report metadata and special-disclosure metadata. The provider preserves published JSON and does not invent statement values.
- **TSPB**: ACTIVE for member/discovery datasets; monthly discovery discovers the current official detailed-member XLSX from the member page instead of hardcoding a dated filename. A TSPB failure is isolated from SPK discovery.
- **KAP**: ACTIVE for public disclosure/financial pages; preserve publication dates and consolidated/solo scope.
- **Borsa Istanbul**: official anchor/reference; real-time redistribution requires license. Historical/DataStore access may not be free. The public `hisse_endeks_ds.csv` reference file is used only for current index membership, with ETag/Last-Modified conditional caching. The public Daily Bulletin UI is not automatically treated as a machine-ingestion license; legacy `/data/thb/` paths remain disabled as a price verifier until current access/terms are explicitly confirmed.
- **Yahoo Finance chart**: secondary/free delayed candidate. Never enough alone for VERIFIED_2X.
- **Investing.com public pages**: automated provider DISABLED until terms/robots review is explicitly safe.
- **TinyFish**: PAID_SOURCE_SKIPPED by user rule; never used.

- **İş Yatırım public analysis**: BLOCKED for automated ingestion. Its `robots.txt` disallows `/_layouts/`, which is where commonly used `HisseTekil`/chart endpoints live. The current usage policy also restricts copying/distributing platform content. Public human-readable pages may still be linked as research references, but the terminal does not crawl the blocked endpoint.
- **TSPB data downloads**: ACTIVE for periodic discovery/reference snapshots. The public data page currently exposes the member factsheet as a downloadable XLSX; this is discovery input, not a price feed.
