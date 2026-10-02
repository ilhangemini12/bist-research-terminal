"""Checkpoint verified KAP debt/D&A/capex metrics into immutable period shards."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.extended_metrics import parse_extended_metrics
from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.extended_financial_files import extended_metric_shard_path


def main():
    ap=ArgumentParser()
    ap.add_argument('--year',type=int,required=True)
    ap.add_argument('--period',choices=['1','2','3','4'],required=True)
    args=ap.parse_args()

    out=extended_metric_shard_path(ROOT,args.year,args.period)
    if out.exists():
        print(f'EXT_FIN_SHARD_EXISTS file={out.name}; immutable checkpoint kept')
        return

    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=universe.tickers
    provider=KapBulkFinancialProvider()
    archive=provider.download_archive(args.year,args.period)
    print(f'EXT_FIN_ARCHIVE_OK year={args.year} period={args.period} files={len(archive.names)} bytes={len(archive.raw)}')

    rows=[]
    missing=0; parsed=0; debt=0; da=0; capex=0; failed=0
    stamp=datetime.now(timezone.utc).isoformat()
    for ticker in tickers:
        try:
            name=archive.entry_for_ticker(ticker)
            if not name:
                missing+=1
                continue
            metrics=parse_extended_metrics(archive.zip.read(name))
            if not metrics.get('observed_metrics'):
                continue
            row={
                'ticker':ticker,
                'archive_year':int(args.year),
                'archive_period':int(args.period),
                'report_period':metrics.get('current_period'),
                'currency':metrics.get('currency'),
                'scale':metrics.get('scale'),
                'debt_components_complete':bool(metrics.get('debt_components_complete')),
                'short_term_borrowings':metrics.get('short_term_borrowings'),
                'current_portion_long_term_borrowings':metrics.get('current_portion_long_term_borrowings'),
                'long_term_borrowings':metrics.get('long_term_borrowings'),
                'financial_debt':metrics.get('financial_debt'),
                'depreciation_amortization_ytd':metrics.get('depreciation_amortization_ytd'),
                'capex_cash_outflow_ytd':metrics.get('capex_cash_outflow_ytd'),
                'capex_spend_ytd':metrics.get('capex_spend_ytd'),
                'observed_metrics_json':json.dumps(metrics.get('observed_metrics') or [],ensure_ascii=False),
                'source_file':name,
                'source_url':archive.source_url,
                'retrieved_at':stamp,
            }
            rows.append(row); parsed+=1
            debt+=int(row['financial_debt'] is not None and row['debt_components_complete'])
            da+=int(row['depreciation_amortization_ytd'] is not None)
            capex+=int(row['capex_spend_ytd'] is not None)
        except Exception as exc:
            failed+=1
            print(f'EXT_FIN_DEGRADED ticker={ticker} {type(exc).__name__}: {exc}')

    out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_parquet(out,index=False)
    print(
        f'EXT_FIN_SHARD_WRITTEN file={out.name} rows={len(rows)} debt_complete={debt} '
        f'da={da} capex={capex} missing={missing} failed={failed}'
    )
    print(f'EXT_FIN_DONE year={args.year} period={args.period} parsed={parsed}/{len(tickers)}')


if __name__=='__main__':
    main()
