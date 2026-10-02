"""Audit checkpointed KAP debt/D&A/capex coverage against latest financial periods."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.extended_metrics import derive_extended_ttm
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.extended_financial_files import load_extended_metric_records
from bist_terminal.storage.financial_files import financial_parquet_files


def pct(n,d):
    return round(n/d*100,1) if d else 0.0


def main():
    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=universe.tickers
    ext=load_extended_metric_records(ROOT)

    store=DuckDBStore(ROOT/'data/bist.duckdb')
    try:
        for p in financial_parquet_files(ROOT):
            store.import_parquet('financials',p)
        latest=store.latest_financial_payloads()
    finally:
        store.close()

    current_year=max(
        [int((row.get('report_period') or '0000')[:4]) for row in latest.values() if row.get('report_period')] or [2026]
    )
    rows=[]
    matched=debt=da=capex=all_core=0
    for ticker in tickers:
        latest_period=latest.get(ticker,{}).get('report_period')
        derived=derive_extended_ttm(ext.get(ticker,[]),current_year)
        period_match=bool(derived and latest_period and derived.get('report_period')==latest_period)
        debt_ok=period_match and derived.get('financial_debt') is not None and bool(derived.get('debt_components_complete'))
        da_ok=period_match and derived.get('depreciation_amortization_ttm') is not None
        capex_ok=period_match and derived.get('capex_spend_ttm') is not None
        matched+=int(period_match); debt+=int(debt_ok); da+=int(da_ok); capex+=int(capex_ok)
        all_core+=int(debt_ok and da_ok and capex_ok)
        rows.append({
            'ticker':ticker,
            'latest_financial_period':latest_period,
            'extended_report_period':derived.get('report_period') if derived else None,
            'basis':derived.get('basis') if derived else None,
            'period_match':period_match,
            'debt_ready':debt_ok,
            'da_ttm_ready':da_ok,
            'capex_ttm_ready':capex_ok,
        })
    report={
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'current_year':current_year,
        'tracked_tickers':len(tickers),
        'tickers_with_any_extended_checkpoint':len(ext),
        'period_matched_count':matched,
        'period_matched_pct':pct(matched,len(tickers)),
        'debt_ready_count':debt,
        'debt_ready_pct':pct(debt,len(tickers)),
        'da_ttm_ready_count':da,
        'da_ttm_ready_pct':pct(da,len(tickers)),
        'capex_ttm_ready_count':capex,
        'capex_ttm_ready_pct':pct(capex,len(tickers)),
        'all_core_extended_ready_count':all_core,
        'all_core_extended_ready_pct':pct(all_core,len(tickers)),
        'unready_sample':[r for r in rows if not (r['debt_ready'] and r['da_ttm_ready'] and r['capex_ttm_ready'])][:80],
    }
    out=ROOT/'artifacts/extended_financial_coverage.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
