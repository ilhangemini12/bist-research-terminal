"""Daily FREE-FIRST pipeline."""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import datetime
import sys
import yaml
from datetime import timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.bist_bulletin import BistDailyBulletinProvider
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.quality.price_verification import verify_prices
from bist_terminal.exports.static import write_latest
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date, is_trading_day
from bist_terminal.storage.duckdb_store import DuckDBStore

def load_runtime():
    return yaml.safe_load((ROOT/'config/runtime.yaml').read_text(encoding='utf-8')) or {}

def build_price_providers(runtime, expected_trade_date):
    cfg=runtime.get('providers',{})
    out=[]
    if cfg.get('bist_daily_bulletin',{}).get('enabled',True):
        out.append(BistDailyBulletinProvider(expected_trade_date))
    if cfg.get('yahoo_chart',{}).get('enabled',True):
        out.append(YahooChartProvider())
    return out

def provider_health(chain, attempts_by_ticker):
    counts={}
    for _, attempts in attempts_by_ticker.items():
        for a in attempts:
            d=asdict(a); pid=d['provider_id']; row=counts.setdefault(pid,Counter())
            row['success'] += int(d['ok'])
            row['failure'] += int(not d['ok'] and not d['skipped'])
            row['skipped'] += int(d['skipped'])
    rows=[]
    for pid,state in chain.circuits.items():
        c=counts.get(pid,Counter())
        status='BLOCKED' if state.open and state.reason and 'Blocked' in state.reason else ('RATE_LIMITED' if state.open and state.reason and 'RateLimited' in state.reason else ('DEGRADED' if state.open or c['failure'] else 'ACTIVE'))
        rows.append({'provider':pid,'status':status,'upstream':next((getattr(p,'upstream_vendor','unknown') for p in chain.providers if getattr(p,'provider_id','')==pid),'unknown'),'successes':c['success'],'failures':c['failure'],'skipped_after_circuit':c['skipped'],'message':state.reason})
    return rows

def main():
    runtime=load_runtime()
    today=datetime.date.today()
    cal=load_calendar(ROOT/'config/bist_calendar_2026.yaml')
    if not is_trading_day(today,cal):
        print(f'SKIP_NON_TRADING_DAY {today.isoformat()}')
        return
    expected=latest_expected_trade_date(today,cal).isoformat()
    index_codes=enabled_indices(ROOT/'config/indices.yaml')
    try:
        universe=BistIndexUniverseProvider(cache_dir=ROOT/'data/cache/bist_universe').get_components(index_codes)
        tickers=universe.tickers
        universe_status='CACHE' if universe.cache_used else 'LIVE_REFERENCE'
    except Exception as exc:
        write_latest({'mode':'LIVE_PIPELINE_UNIVERSE_UNAVAILABLE','data_as_of':{'prices':expected,'financials':'N/A','targets':'N/A'},'stocks':[],'sources':[{'provider':'bist_index_components','status':'DEGRADED','upstream':'Borsa Istanbul','message':f'{type(exc).__name__}: {exc}'}],'summary':{'tracked_stocks':0,'verified_price_count':0,'unverified_price_count':0},'universe':{'indices':index_codes,'status':'UNAVAILABLE'}})
        raise

    providers=build_price_providers(runtime,expected)
    threshold=int(runtime.get('pipeline',{}).get('provider_failure_threshold',3))
    chain=FallbackChain(providers,failure_threshold=threshold)
    tolerance=float(runtime.get('price_verification',{}).get('tolerance_pct',0.15))
    rows=[]; attempts={}; store=None; storage_status='ACTIVE'
    try:
        store=DuckDBStore(ROOT/'data/bist.duckdb')
        stamp=datetime.datetime.now(timezone.utc).isoformat()
        for code,members in universe.members.items():
            store.replace_current_membership(code,[{'ticker':r['symbol'],'company_name':r.get('name')} for r in members],stamp)
    except Exception as exc:
        storage_status=f'DEGRADED: {type(exc).__name__}: {exc}'

    for ticker in tickers:
        obs,att=chain.collect(ticker)
        attempts[ticker]=att
        vr=verify_prices(obs,expected,tolerance_pct=tolerance,official_ids={'bist_daily_bulletin'})
        if store:
            for o in obs:
                store.upsert_price({'ticker':o.ticker,'trade_date':o.trade_date,'close':o.close,'volume':o.volume,'provider_id':o.provider_id,'upstream_vendor':o.upstream_vendor,'status':vr.status,'retrieved_at':o.retrieved_at})
            store.upsert_verification({'ticker':ticker,'trade_date':expected,'verified_price':vr.verified_price,'status':vr.status,'sources':vr.sources,'upstreams':vr.upstreams,'max_diff_pct':vr.max_diff_pct,'reason':vr.reason,'verified_at':datetime.datetime.now(timezone.utc).isoformat()})
        rows.append({'ticker':ticker,'price':vr.verified_price,'price_status':vr.status,'verification_reason':vr.reason,'trade_date':vr.trade_date,'sources':vr.sources,'source_lineage':vr.upstreams,'max_diff_pct':vr.max_diff_pct})

    if store:
        for table in ['prices','price_verification','index_membership_current']:
            store.export_parquet(table,ROOT/f'data/parquet/{table}.parquet')
        store.close()
    verified=sum(r['price_status']=='VERIFIED_2X' for r in rows)
    sources=[{'provider':'bist_index_components','status':'ACTIVE','upstream':'Borsa Istanbul','message':f'{universe_status}; {len(tickers)} unique tickers'},{'provider':'duckdb_store','status':'ACTIVE' if storage_status=='ACTIVE' else 'DEGRADED','upstream':'local','message':storage_status}] + provider_health(chain,attempts)
    write_latest({'mode':'LIVE_PIPELINE','data_as_of':{'prices':expected,'financials':'pending KAP adapter','targets':'pending discovery'},'stocks':rows,'sources':sources,'summary':{'tracked_stocks':len(rows),'verified_price_count':verified,'unverified_price_count':len(rows)-verified},'universe':{'indices':index_codes,'status':universe_status,'members_by_index':{k:len(v) for k,v in universe.members.items()}}})
    print(f'LIVE_PIPELINE_OK expected={expected} tracked={len(rows)} verified={verified} unverified={len(rows)-verified} universe={universe_status}')

if __name__=='__main__':
    main()
