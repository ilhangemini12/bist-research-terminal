"""Persist normalized KAP financial statements using immutable checkpoint shards."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files, financial_shard_path


def restore_financial_state(store):
    restored=0
    for parquet in financial_parquet_files(ROOT):
        added=store.import_parquet('financials',parquet)
        restored+=added
        print(
            f'FINANCIAL_STATE_RESTORED file={parquet.name} '
            f'rows_added={added} total={store.table_count("financials")}'
        )
    return restored


def main():
    ap=ArgumentParser()
    ap.add_argument('--year',type=int,required=True)
    ap.add_argument('--period',choices=['1','2','3','4'],required=True)
    ap.add_argument('--tickers',default='')
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--force',action='store_true')
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

    if not tickers:
        print(f'KAP_FIN_BOOTSTRAP_DONE requested=0 parsed=0 review=0 missing=0 failed=0 year={args.year} period={args.period}')
        return

    shard=financial_shard_path(ROOT,args.year,args.period,args.offset,len(tickers))
    if shard.exists() and not args.force:
        print(f'FINANCIAL_SHARD_EXISTS file={shard.name}; immutable checkpoint kept, no rewrite')
        return

    store=DuckDBStore(ROOT/'data/bist.duckdb')
    restore_financial_state(store)

    provider=KapBulkFinancialProvider()
    archive=provider.download_archive(args.year,args.period)
    print(f'KAP_FIN_ARCHIVE_OK year={args.year} period={args.period} files={len(archive.names)} bytes={len(archive.raw)}')

    parsed=0; missing=0; review=0; failed=0
    stamp=datetime.now(timezone.utc).isoformat()
    new_rows=[]
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
                row={
                    'ticker':ticker,
                    'report_period':result['current_period'],
                    'publication_date':None,
                    'statement_scope':result.get('statement_scope') or 'UNKNOWN',
                    'payload':json.dumps(payload,ensure_ascii=False),
                    'source_url':archive.source_url,
                }
                store.upsert_financial({**row,'payload':payload})
                new_rows.append(row)
                parsed+=1
                keys=sorted(result.get('facts',{}))
                print(
                    f'KAP_FIN_OK ticker={ticker} period={result["current_period"]} '
                    f'status={result["status"]} quality={result["quality_score"]} metrics={keys}'
                )
            except Exception as exc:
                failed+=1
                print(f'KAP_FIN_DEGRADED ticker={ticker} {type(exc).__name__}: {exc}')

        if new_rows:
            shard.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(
                new_rows,
                columns=['ticker','report_period','publication_date','statement_scope','payload','source_url'],
            ).to_parquet(shard,index=False)
            print(f'FINANCIAL_SHARD_WRITTEN file={shard.name} rows={len(new_rows)}')
        else:
            print('FINANCIAL_STATE_UNCHANGED no shard write')
        print(
            f'KAP_FIN_BOOTSTRAP_DONE requested={len(tickers)} parsed={parsed} '
            f'review={review} missing={missing} failed={failed} total_rows={store.table_count("financials")} '
            f'year={args.year} period={args.period}'
        )
    finally:
        store.close()


if __name__=='__main__':
    main()
