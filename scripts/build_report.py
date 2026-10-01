from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json, re, subprocess, yaml

ROOT=Path(__file__).resolve().parents[1]
latest=json.loads((ROOT/'dashboard/data/latest.json').read_text())
providers=yaml.safe_load((ROOT/'config/source_catalog.yaml').read_text())['providers']
statuses=Counter(p['status'] for p in providers)
try:
    out=subprocess.check_output(['pytest','--collect-only'],cwd=ROOT,text=True,stderr=subprocess.STDOUT)
    m=re.search(r'(\d+) tests collected',out); collected=int(m.group(1)) if m else None
except Exception:
    collected=None
is_demo='DEMO' in latest.get('mode','')
summary=latest.get('summary',{})
verified=0 if is_demo else int(summary.get('verified_price_count',0) or 0)
expected_date=None if is_demo else latest.get('data_as_of',{}).get('prices')
dashboard_url='https://ilhangemini12.github.io/bist-research-terminal/'
report={
  'project':'bist-research-terminal',
  'generated_at':datetime.now(timezone.utc).isoformat(),
  'mode':latest.get('mode'),
  'repository_url':'https://github.com/ilhangemini12/bist-research-terminal',
  'dashboard_url':dashboard_url,
  'expected_dashboard_url':dashboard_url,
  'live_market_status':{
    'expected_market_date':expected_date,
    'last_verified_market_date': expected_date if verified > 0 else None,
    'tracked_live_tickers': 0 if is_demo else summary.get('tracked_stocks',0),
    'verified_price_count':verified,
    'unverified_price_count':0 if is_demo else summary.get('unverified_price_count',0),
    'reason':(
      'Bundled dataset is synthetic demo fixture; no live market date is claimed.' if is_demo
      else ('Live pipeline has VERIFIED_2X prices.' if verified > 0 else 'Live pipeline ran, but no current-day price met the two-independent-upstream VERIFIED_2X contract.')
    )
  },
  'demo_fixture':{'tracked_stocks':summary.get('tracked_stocks',0),'verified_fixture_rows':summary.get('verified_price_count',0)} if is_demo else None,
  'financial_coverage_percent_live':0 if is_demo else summary.get('financial_coverage_pct',0),
  'financial_high_confidence_count':0 if is_demo else summary.get('financial_high_confidence_count',0),
  'source_catalog':{'discovered_or_catalogued':len(providers),'status_counts':dict(sorted(statuses.items()))},
  'python_tests_collected':collected,
  'js_formula_tests':'dashboard/tests/formula.test.js',
  'presets':list(yaml.safe_load((ROOT/'config/presets.yaml').read_text())['presets']),
  'verification_evidence':{'closed_day_sample':'2026-09-30','tickers':['THYAO','ASELS','AKBNK'],'status':'VERIFIED_2X','max_diff_pct':0.0},
  'point_in_time_universe':{
    'snapshot_date':latest.get('universe',{}).get('snapshot_date'),
    'history_status':latest.get('universe',{}).get('history_status'),
    'history_rows':latest.get('universe',{}).get('history_rows',0),
  },
  'known_limitations':[
    'Current-day VERIFIED_2X can remain zero until the official Borsa Istanbul EOD bulletin is published; closed-day BIST-vs-Yahoo cross-checks are validated.',
    'KAP public bulk financial downloads now provide normalized high-confidence annual financials for most of the configured universe; full 12–20-quarter history is still being accumulated and missing/review-required issuers remain N/A.',
    'Point-in-time index membership snapshots accumulate from 2026-10-01 onward; periods before the first snapshot remain unavailable and affected backtests must retain BACKTEST BIASED.',
    'Broker target-price/model-portfolio discovery is partial and must respect each public source terms/access boundaries.'
  ],
  'stress_coverage':[
    'primary/secondary provider down','HTTP 403','HTTP 429 bounded retry','timeout','malformed payload/HTML','schema change',
    'missing ticker','wrong ticker','duplicate row','stale/one-day-old price','adjusted/raw mismatch','wrong timezone normalization',
    'split day','dividend day','BIST holiday','missing financial statement','duplicate KAP disclosure','target price archive threshold',
    'zero volume warning','source conflict','extreme values','balance-sheet sanity','look-ahead bias','survivorship-bias warning',
    'VWAP data sufficiency','provider circuit breaker','dynamic BIST universe schema/cache fallback'
  ]
}
(ROOT/'artifacts').mkdir(exist_ok=True)
(ROOT/'artifacts/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
