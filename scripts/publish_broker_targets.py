"""Publish current broker target/model-portfolio overlay without refreshing market prices."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.calculations.broker_targets import apply_broker_targets
from bist_terminal.exports.static import write_latest
from bist_terminal.storage.broker_target_files import load_latest_broker_targets


def main():
    latest_path=ROOT/'dashboard/data/latest.json'
    data=json.loads(latest_path.read_text(encoding='utf-8'))
    today=date.today().isoformat()
    targets=load_latest_broker_targets(ROOT,as_of=today,max_age_days=90)
    stocks=apply_broker_targets(data.get('stocks',[]),targets)
    data['stocks']=stocks

    active=[r for r in stocks if r.get('target_source_count',0)>0]
    model=[r for r in stocks if r.get('model_portfolio_active')]
    dates=[r.get('target_latest_date') for r in active if r.get('target_latest_date')]
    latest_date=max(dates) if dates else 'N/A'
    details=[]
    for r in active:
        for d in r.get('target_details',[]):
            details.append({
                'ticker':r.get('ticker'),
                **d,
            })
    data['broker_model_portfolios']=details
    data.setdefault('data_as_of',{})['targets']=latest_date
    data['data_as_of']['targets_basis']='BROKER_UPDATE_DATE_OR_OBSERVED_CURRENT_PUBLIC_PAGE'
    summary=data.setdefault('summary',{})
    summary['target_price_count']=len(active)
    summary['target_consensus_2plus_count']=sum(r.get('target_status')=='CONSENSUS_2PLUS' for r in stocks)
    summary['model_portfolio_count']=len(model)
    summary['broker_target_source_count']=len({d.get('broker_id') for d in details if d.get('broker_id')})

    sources=[s for s in data.get('sources',[]) if s.get('provider')!='gedik_model_portfolio']
    sources.append({
        'provider':'gedik_model_portfolio',
        'status':'ACTIVE' if details else 'DEGRADED',
        'upstream':'Gedik Yatirim',
        'successes':len(details),
        'failures':0 if details else 1,
        'skipped_after_circuit':0,
        'latest_data_date':latest_date,
        'freshness':'OBSERVED_CURRENT_PUBLIC_PAGE' if details and all(not d.get('portfolio_date') for d in details) else 'BROKER_UPDATE_DATE',
        'fields':['ticker','target_price','model_portfolio_membership'],
        'message':(
            f'Facts-only public model portfolio: {len(details)} rows; '
            'single broker is not labeled consensus; BIST page market data not republished'
        ),
    })
    data['sources']=sources
    write_latest(data)
    print(
        f'BROKER_TARGET_PUBLISH_OK targets={len(active)} model={len(model)} '
        f'sources={summary["broker_target_source_count"]} as_of={latest_date}'
    )


if __name__=='__main__':
    main()
