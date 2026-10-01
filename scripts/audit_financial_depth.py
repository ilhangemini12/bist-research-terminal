"""Audit normalized financial-statement depth without mutating financial state."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files


def main():
    store=DuckDBStore(ROOT/'data/bist.duckdb')
    try:
        for parquet in financial_parquet_files(ROOT):
            store.import_parquet('financials',parquet)
        rows=store.con.execute(
            'select ticker, report_period, statement_scope, payload from financials order by ticker, report_period'
        ).fetchall()
        universe=BistIndexUniverseProvider(
            cache_dir=ROOT/'data/cache/bist_universe'
        ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
        tickers=universe.tickers

        periods_by={t:set() for t in tickers}
        high_by={t:set() for t in tickers}
        status_counts=Counter()
        period_counts=Counter()
        source_period_counts=Counter()
        for ticker,period,scope,payload in rows:
            if ticker not in periods_by:
                continue
            periods_by[ticker].add(str(period))
            try:
                p=json.loads(payload) if isinstance(payload,str) else (payload or {})
            except Exception:
                p={}
            status=p.get('status') or 'UNKNOWN'
            status_counts[status]+=1
            period_counts[str(period)]+=1
            key=f"{p.get('archive_year','?')}-{p.get('archive_period','?')}"
            source_period_counts[key]+=1
            if status=='PARSED_HIGH_CONFIDENCE':
                high_by[ticker].add(str(period))

        all_counts=[len(periods_by[t]) for t in tickers]
        high_counts=[len(high_by[t]) for t in tickers]
        def pct(n,d): return round(n/d*100,1) if d else 0
        thresholds={str(n):sum(c>=n for c in high_counts) for n in (1,4,8,12,16,20)}
        report={
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'tracked_tickers':len(tickers),
            'financial_rows':len(rows),
            'status_counts':dict(status_counts),
            'distinct_report_periods':sorted(period_counts),
            'report_period_company_counts':dict(sorted(period_counts.items())),
            'archive_period_row_counts':dict(sorted(source_period_counts.items())),
            'period_depth':{
                'all_min':min(all_counts) if all_counts else 0,
                'all_median':statistics.median(all_counts) if all_counts else 0,
                'all_max':max(all_counts) if all_counts else 0,
                'high_conf_min':min(high_counts) if high_counts else 0,
                'high_conf_median':statistics.median(high_counts) if high_counts else 0,
                'high_conf_max':max(high_counts) if high_counts else 0,
                'tickers_with_at_least':thresholds,
                'pct_with_at_least_12_high_conf':pct(thresholds['12'],len(tickers)),
                'pct_with_at_least_20_high_conf':pct(thresholds['20'],len(tickers)),
            },
            'lowest_depth':[
                {'ticker':t,'all_periods':len(periods_by[t]),'high_conf_periods':len(high_by[t])}
                for t in sorted(tickers,key=lambda x:(len(high_by[x]),len(periods_by[x]),x))[:60]
            ],
        }
        out=ROOT/'artifacts/financial_depth_report.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        store.close()


if __name__=='__main__':
    main()
