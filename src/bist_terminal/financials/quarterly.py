from __future__ import annotations

from collections import defaultdict

FLOW_METRICS=(
    'revenue','gross_profit','operating_profit','net_income','cash_from_operations'
)
BALANCE_METRICS=(
    'assets','equity','cash','current_assets','current_liabilities','inventories'
)


def standalone_quarters(records: list[dict]) -> list[dict]:
    """Convert high-confidence KAP cumulative periods into standalone quarters.

    Income/cash-flow metrics are cumulative within each archive year and are
    differenced against the immediately previous archive period. Balance-sheet
    metrics remain point-in-time values from the current period. No missing
    quarter is interpolated or inferred.
    """
    groups=defaultdict(dict)
    for rec in records:
        payload=rec.get('payload') or rec
        if payload.get('status')!='PARSED_HIGH_CONFIDENCE':
            continue
        try:
            year=int(payload.get('archive_year'))
            period=int(payload.get('archive_period'))
        except (TypeError,ValueError):
            continue
        if period not in (1,2,3,4):
            continue
        groups[year][period]={
            'payload':payload,
            'report_period':rec.get('report_period') or payload.get('current_period'),
            'statement_scope':rec.get('statement_scope') or payload.get('statement_scope'),
        }

    out=[]
    for year in sorted(groups):
        by_period=groups[year]
        for period in sorted(by_period):
            item=by_period[period]
            payload=item['payload']
            facts=payload.get('facts') or {}
            qfacts={m:facts.get(m) for m in BALANCE_METRICS}
            if period==1:
                for m in FLOW_METRICS:
                    qfacts[m]=facts.get(m)
                flow_basis='YTD_Q1'
            else:
                prev=by_period.get(period-1)
                prevfacts=(prev['payload'].get('facts') or {}) if prev else {}
                for m in FLOW_METRICS:
                    cur=facts.get(m); old=prevfacts.get(m)
                    qfacts[m]=(cur-old) if cur is not None and old is not None else None
                flow_basis='YTD_DIFFERENCE' if prev else 'MISSING_PREVIOUS_PERIOD'
            out.append({
                'archive_year':year,
                'archive_period':period,
                'report_period':item['report_period'],
                'statement_scope':item['statement_scope'],
                'flow_basis':flow_basis,
                'facts':qfacts,
            })
    return out


def ttm_from_quarters(quarters: list[dict]) -> dict:
    """Return TTM flows + latest balance sheet only for four contiguous quarters."""
    if len(quarters)<4:
        return {}
    q=sorted(quarters,key=lambda x:(x['archive_year'],x['archive_period']))
    last=q[-4:]
    ords=[x['archive_year']*4+(x['archive_period']-1) for x in last]
    if any(b-a!=1 for a,b in zip(ords,ords[1:])):
        return {}
    result={m:last[-1]['facts'].get(m) for m in BALANCE_METRICS}
    for m in FLOW_METRICS:
        vals=[x['facts'].get(m) for x in last]
        result[m]=sum(vals) if all(v is not None for v in vals) else None
    result['quarters_used']=[
        f"{x['archive_year']}Q{x['archive_period']}" for x in last
    ]
    result['report_period']=last[-1].get('report_period')
    return result
