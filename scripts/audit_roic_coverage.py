"""Audit guarded ROIC coverage from checkpointed KAP inputs."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files
from bist_terminal.storage.extended_financial_files import load_extended_metric_records
from bist_terminal.storage.roic_input_files import load_roic_input_records
from bist_terminal.financials.roic_inputs import (
    compute_roic,
    derive_average_invested_capital,
    derive_roic_ttm,
)


def main():
    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=universe.tickers
    ticker_indices={}
    for code,members in universe.members.items():
        for member in members:
            ticker_indices.setdefault(member['symbol'],set()).add(code)

    def sector(ticker):
        m=ticker_indices.get(ticker,set())
        if 'XBANK' in m: return 'Bank'
        if 'XSGRT' in m: return 'Insurance'
        if 'XAKUR' in m: return 'Brokerage'
        if 'XUSIN' in m: return 'Industrials'
        return 'Other'

    store=DuckDBStore(ROOT/'data/bist.duckdb')
    try:
        for path in financial_parquet_files(ROOT):
            store.import_parquet('financials',path)
        histories=store.financial_payload_history()
        latest=store.latest_financial_payloads()
    finally:
        store.close()

    extended=load_extended_metric_records(ROOT)
    roic_inputs=load_roic_input_records(ROOT)
    current_year=2026

    rows=[]
    for ticker in tickers:
        sec=sector(ticker)
        excluded=sec in {'Bank','Insurance','Brokerage'}
        rttm=derive_roic_ttm(roic_inputs.get(ticker,[]),current_year)
        period=rttm.get('archive_period')
        cap={'status':'EXCLUDED_FINANCIAL_SECTOR'} if excluded or not period else derive_average_invested_capital(
            histories.get(ticker,[]),extended.get(ticker,[]),current_year,int(period)
        )
        latest_fin=latest.get(ticker,{})
        latest_period=latest_fin.get('report_period')
        period_match=bool(
            rttm.get('report_period')
            and latest_period
            and rttm.get('report_period')==latest_period
        )
        roic=None
        status='EXCLUDED_FINANCIAL_SECTOR' if excluded else 'INSUFFICIENT_INPUTS'
        if not excluded and rttm.get('status')=='ACTIVE' and cap.get('status')=='ACTIVE' and period_match:
            roic=compute_roic(
                rttm.get('ebit_ttm'),
                rttm.get('effective_tax_rate'),
                cap.get('average_invested_capital'),
            )
            status='ACTIVE' if roic is not None else 'INSUFFICIENT_INPUTS'
        rows.append({
            'ticker':ticker,
            'sector':sec,
            'status':status,
            'period_match':period_match,
            'latest_financial_period':latest_period,
            'roic_report_period':rttm.get('report_period'),
            'roic_input_status':rttm.get('status'),
            'capital_status':cap.get('status'),
            'ebit_ttm':rttm.get('ebit_ttm'),
            'effective_tax_rate':rttm.get('effective_tax_rate'),
            'average_invested_capital':cap.get('average_invested_capital'),
            'roic':roic,
            'high_roic':bool(roic is not None and roic>0.15),
            'roic_basis':rttm.get('basis'),
            'capital_basis':cap.get('basis'),
        })

    eligible=[r for r in rows if r['sector'] not in {'Bank','Insurance','Brokerage'}]
    def count(pred): return sum(1 for r in eligible if pred(r))
    report={
        'tracked_tickers':len(rows),
        'eligible_non_financial_tickers':len(eligible),
        'roic_input_ttm_active_count':count(lambda r:r['roic_input_status']=='ACTIVE'),
        'average_invested_capital_active_count':count(lambda r:r['capital_status']=='ACTIVE'),
        'period_match_count':count(lambda r:r['period_match']),
        'roic_active_count':count(lambda r:r['status']=='ACTIVE'),
        'roic_active_pct_eligible':round(count(lambda r:r['status']=='ACTIVE')/len(eligible)*100,1) if eligible else 0,
        'high_roic_gt_15_count':count(lambda r:r['high_roic']),
        'active_sample':[r for r in rows if r['status']=='ACTIVE'][:40],
        'unavailable_sample':[r for r in rows if r['sector'] not in {'Bank','Insurance','Brokerage'} and r['status']!='ACTIVE'][:60],
    }
    out=ROOT/'artifacts/roic_coverage_report.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
