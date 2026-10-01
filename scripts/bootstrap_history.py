"""Incremental 5-year daily OHLCV bootstrap using immutable Git-friendly shards."""
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
import argparse, sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.base import Blocked, RateLimited
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.history_files import history_parquet_files, history_shard_path
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date

OHLCV_COLUMNS=[
    'ticker','trade_date','open','high','low','close','adjusted_close','volume',
    'provider_id','upstream_vendor','source_url','retrieved_at'
]
ACTION_COLUMNS=[
    'ticker','action_date','action_type','amount','split_ratio','provider_id','source_url','retrieved_at'
]


def restore_history(store):
    for table in ['daily_ohlcv','corporate_actions']:
        files=history_parquet_files(ROOT,table)
        for parquet in files:
            added=store.import_parquet(table,parquet)
            print(
                f'HISTORY_STATE_RESTORED table={table} file={parquet.name} '
                f'rows_added={added} total={store.table_count(table)}'
            )


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--limit',type=int,default=25)
    args=ap.parse_args()

    cal=load_calendar(ROOT/'config/bist_calendar_2026.yaml')
    end=latest_expected_trade_date(date.today(),cal)
    u=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=u.tickers[args.offset:args.offset+args.limit]
    if not tickers:
        print(f'BOOTSTRAP_DONE processed=0/0 offset={args.offset} limit={args.limit}')
        return

    store=DuckDBStore(ROOT/'data/bist.duckdb')
    provider=YahooChartProvider()
    retrieved=datetime.now(timezone.utc).isoformat()
    done=0
    new_ohlcv=[]
    new_actions=[]
    try:
        restore_history(store)
        for ticker in tickers:
            last=store.latest_history_date(ticker,provider.provider_id)
            start=(last+timedelta(days=1)) if last else (end-timedelta(days=365*5+5))
            if start>end:
                print(f'HISTORY_UP_TO_DATE {ticker} last={last}')
                continue
            try:
                df,acts=provider.get_history_bundle(ticker,start.isoformat(),end.isoformat())
                for r in df.to_dict('records'):
                    row={
                        'ticker':ticker,'trade_date':r['Date'],'open':r['Open'],'high':r['High'],
                        'low':r['Low'],'close':r['Close'],'adjusted_close':r['Adjusted Close'],
                        'volume':r['Volume'],'provider_id':r['provider_id'],
                        'upstream_vendor':r['upstream_vendor'],'source_url':r['source_url'],
                        'retrieved_at':retrieved,
                    }
                    store.upsert_ohlcv(row)
                    new_ohlcv.append(row)
                for r in acts.to_dict('records'):
                    row={
                        'ticker':ticker,'action_date':r['date'],'action_type':r['action_type'],
                        'amount':r.get('amount'),'split_ratio':r.get('split_ratio'),
                        'provider_id':r['provider_id'],'source_url':r['source_url'],
                        'retrieved_at':retrieved,
                    }
                    store.upsert_corporate_action(row)
                    new_actions.append(row)
                done+=1
                print(f'HISTORY_OK {ticker} rows={len(df)} actions={len(acts)}')
            except (Blocked,RateLimited) as exc:
                print(f'HISTORY_PROVIDER_CIRCUIT_OPEN {type(exc).__name__}: {exc}')
                break
            except Exception as exc:
                print(f'HISTORY_DEGRADED {ticker} {type(exc).__name__}: {exc}')

        shard_count=len(tickers)
        if new_ohlcv:
            p=history_shard_path(ROOT,'daily_ohlcv',args.offset,shard_count)
            p.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(new_ohlcv,columns=OHLCV_COLUMNS).to_parquet(p,index=False)
            print(f'HISTORY_SHARD_WRITTEN table=daily_ohlcv file={p.name} rows={len(new_ohlcv)}')
        if new_actions:
            p=history_shard_path(ROOT,'corporate_actions',args.offset,shard_count)
            p.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(new_actions,columns=ACTION_COLUMNS).to_parquet(p,index=False)
            print(f'HISTORY_SHARD_WRITTEN table=corporate_actions file={p.name} rows={len(new_actions)}')
        if not new_ohlcv and not new_actions:
            print('HISTORY_STATE_UNCHANGED no shard write')
        print(f'BOOTSTRAP_DONE processed={done}/{len(tickers)} offset={args.offset} limit={args.limit}')
    finally:
        store.close()


if __name__=='__main__':
    main()
