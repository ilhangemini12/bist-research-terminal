"""Persist normalized KAP bulk financial statements for the configured BIST universe."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.duckdb_store import DuckDBStore


def main():
    ap=ArgumentParser()
    ap.add_argument('--year',type=int,required=True)
    ap.add_argument('--period',choices=['1','2','3','4'],required=True)
    ap.add_argument('--tickers',default='')
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--limit',type=int,default=0)
    args=ap.parse_args()

    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    if args.tickers.strip():
        wanted=[x.strip().upper().replace('.IS','') for x in args.tickers.split(',') if x.strip()]
        allowed=set(universe.tickers)
        tickers=[x for x in wanted if x in allowed]
    else:
        tickers=universe.tickers[args.offset:]
        if args.limit>0:
            tickers=tickers[:args.limit]

    store=DuckDBStore(ROOT/'data/bist.duckdb')
    parquet=ROOT/'data/parquet/financials.parquet'
    restored=store.import_parquet('financials',parquet)
    print(f'FINANCIAL_STATE_RESTORED rows_added={restored} total={store.table_count("financials")}')

    provider=KapBulkFinancialProvider()
    archive=provider.download_archive(args.year,args.period)
    print(f'KAP_FIN_ARCHIVE_OK year={args.year} period={args.period} files={len(archive.names)} bytes={len(archive.raw)}')

    parsed=0; missing=0; review=0; failed=0
    stamp=datetime.now(timezone.utc).isoformat()
    try:
        for ticker in tickers:
            try:
                result=archive.parse_ticker(ticker)
                if result is None:
                    missing+=1
                    print(f'KAP_FIN_MISSING ticker={ticker}')
                    continue
                if not result.get('current_period') or not result.get('facts'):
                    failed+=1
                    print(f'KAP_FIN_UNPARSEABLE ticker={ticker} status={result.get("status")}')
                    continue
                if result.get('status') != 'PARSED_HIGH_CONFIDENCE':
                    review+=1
                payload={
                    **result,
                    'provider_id':provider.provider_id,
                    'upstream_vendor':provider.upstream_vendor,
                    'retrieved_at':stamp,
                }
                store.upsert_financial({
                    'ticker':ticker,
                    'report_period':result['current_period'],
                    'publication_date':None,
                    'statement_scope':result.get('statement_scope') or 'UNKNOWN',
                    'payload':payload,
                    'source_url':archive.source_url,
                })
                parsed+=1
                keys=sorted(result.get('facts',{}))
                print(
                    f'KAP_FIN_OK ticker={ticker} period={result["current_period"]} '
                    f'status={result["status"]} quality={result["quality_score"]} metrics={keys}'
                )
            except Exception as exc:
                failed+=1
                print(f'KAP_FIN_DEGRADED ticker={ticker} {type(exc).__name__}: {exc}')
        store.export_parquet('financials',parquet)
        print(
            f'KAP_FIN_BOOTSTRAP_DONE requested={len(tickers)} parsed={parsed} '
            f'review={review} missing={missing} failed={failed} total_rows={store.table_count("financials")}'
        )
    finally:
        store.close()


if __name__=='__main__':
    main()
