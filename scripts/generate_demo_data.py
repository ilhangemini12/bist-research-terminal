from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bist_terminal.providers.mock import MockPriceProvider
from bist_terminal.pipeline.daily import verify_universe
from bist_terminal.exports.static import write_latest

root=Path(__file__).resolve().parents[1]
tickers=['THYAO','ASELS','AKBNK']
providers=[MockPriceProvider('demo_a','demo_upstream_a',100.00),MockPriceProvider('demo_b','demo_upstream_b',100.05)]
verified,_=verify_universe(tickers,providers,'2026-10-01')
base={
'THYAO':dict(sector='Transportation',rsi14=38.4,rsi14_prev=35.0,rsi_recent_low=31.0,pe=4.8,pb=1.1,ev_ebitda=5.3,roe=.31,roic=.19,net_debt_ebitda=1.4,revenue_growth_yoy=.22,ebitda_growth_yoy=.27,net_income_growth_yoy=.18,volume_ratio=1.35,target_upside=.18,quality_score=92,sector_pe_median=8.4,sector_pb_median=1.8,sector_ev_ebitda_median=7.2,sector_roe_median=.20,dividend_yield=.018,fcf_yield=.074,roc20=.06),
'ASELS':dict(sector='Industrial',rsi14=52.1,rsi14_prev=51.0,rsi_recent_low=42.0,pe=31.2,pb=4.9,ev_ebitda=22.0,roe=.29,roic=.17,net_debt_ebitda=.3,revenue_growth_yoy=.33,ebitda_growth_yoy=.36,net_income_growth_yoy=.41,volume_ratio=1.08,target_upside=.07,quality_score=88,sector_pe_median=19.0,sector_pb_median=2.6,sector_ev_ebitda_median=11.5,sector_roe_median=.18,dividend_yield=.004,fcf_yield=.022,roc20=.09),
'AKBNK':dict(sector='Bank',rsi14=33.8,rsi14_prev=30.5,rsi_recent_low=28.0,pe=7.1,pb=1.3,ev_ebitda=None,roe=.21,roic=None,net_debt_ebitda=None,revenue_growth_yoy=.18,ebitda_growth_yoy=None,net_income_growth_yoy=.24,volume_ratio=1.62,target_upside=.22,quality_score=90,sector_pe_median=8.1,sector_pb_median=1.5,sector_ev_ebitda_median=None,sector_roe_median=.19,dividend_yield=.031,fcf_yield=None,roc20=.03)
}
rows=[]
for v in verified:
    t=v['ticker']; r={'ticker':t,**base[t]}
    r.update(price=v['verified_price'],close=v['verified_price'],price_status=v['status'],sma10=98.0,sma20=97.0,sma50=95.0,volume=1_500_000,volume_ma20=1_100_000,market_cap=100_000_000_000)
    rows.append(r)
payload={
'mode':'DEMO_FIXTURE_NOT_LIVE',
'data_as_of':{'prices':'2026-10-01 demo fixture','financials':'synthetic demo','targets':'synthetic demo'},
'summary':{'tracked_stocks':len(rows),'verified_price_count':sum(r['price_status']=='VERIFIED_2X' for r in rows),'unverified_price_count':sum(r['price_status']!='VERIFIED_2X' for r in rows),'financial_coverage_pct':100},
'stocks':rows,
'sources':[{'provider':'demo_a','status':'ACTIVE','last_success':'fixture','last_failure':None,'latency_ms':0,'latest_data_date':'2026-10-01','freshness':'DEMO','fields':['price'],'upstream':'demo_upstream_a'},{'provider':'demo_b','status':'ACTIVE','last_success':'fixture','last_failure':None,'latency_ms':0,'latest_data_date':'2026-10-01','freshness':'DEMO','fields':['price'],'upstream':'demo_upstream_b'}]
}
write_latest(payload,root/'dashboard/data/latest.json')
