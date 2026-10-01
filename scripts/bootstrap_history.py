"""Incremental 5-year daily OHLCV bootstrap.

Use in bounded batches from GitHub Actions. The script stops a provider for the run
on Blocked/RateLimited instead of hammering it across the remaining tickers.
"""
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
import argparse, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.base import Blocked, RateLimited
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--offset',type=int,default=0); ap.add_argument('--limit',type=int,default=25); args=ap.parse_args()
    cal=load_calendar(ROOT/'config/bist_calendar_2026.yaml'); end=latest_expected_trade_date(date.today(),cal)
    u=BistIndexUniverseProvider(cache_dir=ROOT/'data/cache/bist_universe').get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=u.tickers[args.offset:args.offset+args.limit]; store=DuckDBStore(ROOT/'data/bist.duckdb'); p=YahooChartProvider(); retrieved=datetime.now(timezone.utc).isoformat()
    done=0
    try:
        # GitHub runners are ephemeral. Restore committed Parquet state into the
        # transient DuckDB before calculating each ticker's incremental start date.
        for table in ['daily_ohlcv','corporate_actions']:
            parquet=ROOT/f'data/parquet/{table}.parquet'
            restored=store.import_parquet(table,parquet)
            if parquet.exists():
                print(f'HISTORY_STATE_RESTORED table={table} rows_added={restored} total={store.table_count(table)}')
        for t in tickers:
            last=store.latest_history_date(t,p.provider_id); start=(last+timedelta(days=1)) if last else (end-timedelta(days=365*5+5))
            if start>end: continue
            try:
                df=p.get_history(t,start.isoformat(),end.isoformat())
                for r in df.to_dict('records'):
                    store.upsert_ohlcv({'ticker':t,'trade_date':r['Date'],'open':r['Open'],'high':r['High'],'low':r['Low'],'close':r['Close'],'adjusted_close':r['Adjusted Close'],'volume':r['Volume'],'provider_id':r['provider_id'],'upstream_vendor':r['upstream_vendor'],'source_url':r['source_url'],'retrieved_at':retrieved})
                acts=p.get_corporate_actions(t,start.isoformat(),end.isoformat())
                for r in acts.to_dict('records'):
                    store.upsert_corporate_action({'ticker':t,'action_date':r['date'],'action_type':r['action_type'],'amount':r.get('amount'),'split_ratio':r.get('split_ratio'),'provider_id':r['provider_id'],'source_url':r['source_url'],'retrieved_at':retrieved})
                done+=1; print(f'HISTORY_OK {t} rows={len(df)}')
            except (Blocked,RateLimited) as exc:
                print(f'HISTORY_PROVIDER_CIRCUIT_OPEN {type(exc).__name__}: {exc}'); break
            except Exception as exc:
                print(f'HISTORY_DEGRADED {t} {type(exc).__name__}: {exc}')
        for table in ['daily_ohlcv','corporate_actions']:
            store.export_parquet(table,ROOT/f'data/parquet/{table}.parquet')
        print(f'BOOTSTRAP_DONE processed={done}/{len(tickers)} offset={args.offset} limit={args.limit}')
    finally: store.close()
if __name__=='__main__': main()
