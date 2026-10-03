"""Checkpoint exact-label KAP ROIC inputs into immutable period shards."""
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
from bist_terminal.financials.roic_inputs import parse_roic_inputs
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.roic_input_files import roic_input_shard_path


def main():
    ap=ArgumentParser()
    ap.add_argument('--year',type=int,required=True)
    ap.add_argument('--period',choices=['1','2','3','4'],required=True)
    args=ap.parse_args()

    out=roic_input_shard_path(ROOT,args.year,args.period)
    if out.exists():
        print(f'ROIC_INPUT_SHARD_EXISTS file={out.name}; immutable checkpoint kept')
        return

    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=universe.tickers
    provider=KapBulkFinancialProvider()
    archive=provider.download_archive(args.year,args.period)
    print(f'ROIC_INPUT_ARCHIVE_OK year={args.year} period={args.period} files={len(archive.names)} bytes={len(archive.raw)}')

    rows=[]
    missing=0; parsed=0; complete=0; failed=0
    stamp=datetime.now(timezone.utc).isoformat()
    for ticker in tickers:
        try:
            name=archive.entry_for_ticker(ticker)
            if not name:
                missing+=1
                continue
            metrics=parse_roic_inputs(archive.zip.read(name))
            if not metrics.get('observed_metrics'):
                continue
            row={
                'ticker':ticker,
                'archive_year':int(args.year),
                'archive_period':int(args.period),
                'report_period':metrics.get('current_period'),
                'currency':metrics.get('currency'),
                'scale':metrics.get('scale'),
                'ebit_ytd':metrics.get('ebit_ytd'),
                'pretax_profit_ytd':metrics.get('pretax_profit_ytd'),
                'tax_expense_income_ytd':metrics.get('tax_expense_income_ytd'),
                'observed_metrics_json':json.dumps(metrics.get('observed_metrics') or [],ensure_ascii=False),
                'source_file':name,
                'source_url':archive.source_url,
                'retrieved_at':stamp,
            }
            rows.append(row); parsed+=1
            complete+=int(
                row['ebit_ytd'] is not None
                and row['pretax_profit_ytd'] is not None
                and row['tax_expense_income_ytd'] is not None
            )
        except Exception as exc:
            failed+=1
            print(f'ROIC_INPUT_DEGRADED ticker={ticker} {type(exc).__name__}: {exc}')

    out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_parquet(out,index=False)
    print(
        f'ROIC_INPUT_SHARD_WRITTEN file={out.name} rows={len(rows)} '
        f'complete={complete} missing={missing} failed={failed}'
    )
    print(f'ROIC_INPUT_DONE year={args.year} period={args.period} parsed={parsed}/{len(tickers)}')


if __name__=='__main__':
    main()
