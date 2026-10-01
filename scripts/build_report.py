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
report={
  'project':'bist-research-terminal',
  'generated_at':datetime.now(timezone.utc).isoformat(),
  'mode':latest.get('mode'),
  'repository_url':None,
  'dashboard_url':None,
  'live_market_status':{
    'last_verified_market_date': None if is_demo else latest.get('data_as_of',{}).get('prices'),
    'tracked_live_tickers': 0 if is_demo else latest.get('summary',{}).get('tracked_stocks',0),
    'verified_price_count': 0 if is_demo else latest.get('summary',{}).get('verified_price_count',0),
    'unverified_price_count': 0 if is_demo else latest.get('summary',{}).get('unverified_price_count',0),
    'reason':'Bundled dataset is synthetic demo fixture; no live market date is claimed.' if is_demo else 'Live pipeline output.'
  },
  'demo_fixture':{'tracked_stocks':latest.get('summary',{}).get('tracked_stocks',0),'verified_fixture_rows':latest.get('summary',{}).get('verified_price_count',0)} if is_demo else None,
  'financial_coverage_percent_live':0 if is_demo else latest.get('summary',{}).get('financial_coverage_pct',0),
  'source_catalog':{'discovered_or_catalogued':len(providers),'status_counts':dict(sorted(statuses.items()))},
  'python_tests_collected':collected,
  'js_formula_tests':'dashboard/tests/formula.test.js',
  'presets':list(yaml.safe_load((ROOT/'config/presets.yaml').read_text())['presets']),
  'known_limitations':[
    'Connected GitHub tool can write to an existing repository but cannot create the new repository in this session.',
    'GitHub Pages is not live until ilhangemini12/bist-research-terminal exists and this build is pushed.',
    'Live VERIFIED_2X coverage remains zero until a second current, free, terms-compatible independent price lineage is approved.',
    'Full KAP financial-statement taxonomy normalization and 12–20-quarter population across all issuer types is not complete.',
    'Historical point-in-time index universes are not fully populated; affected backtests must retain BACKTEST BIASED.',
    'Broker target-price/model-portfolio discovery is partial and must respect each public source terms/access boundaries.',
    'Local sandbox lacks duckdb/pyarrow; the storage module is compiled/tested structurally and GitHub Actions installs declared dependencies.'
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
