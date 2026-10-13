"""Publication acceptance: structural integrity, truthful freshness, no invented data."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT/'dashboard/data/latest.json').read_text())
rows = data['stocks']
assert rows and len({r['ticker'] for r in rows}) == len(rows), 'empty/duplicate universe'
expected = data['data_as_of']['prices']
verified = [r for r in rows if r['price_status']=='VERIFIED_2X']
assert len(verified) == data['summary']['verified_price_count']
for row in rows:
    if row['price_status']=='VERIFIED_2X':
        assert row['trade_date']==expected and row['price']>0
        assert len(set(row['source_lineage']))>=2
    else:
        assert row.get('price') is None, 'unverified price was promoted'
    details = row.get('target_details', [])
    broker_ids = [str(d.get('broker_id') or '').strip().casefold() for d in details]
    assert len(broker_ids) == len(set(broker_ids)) and all(broker_ids), 'duplicate/unknown broker lineage'
    assert row.get('target_source_count', 0) == len(broker_ids), 'broker count mismatch'
    assert all(math.isfinite(d['target_price']) and d['target_price'] > 0 for d in details), 'invalid target'
    if row.get('target_status') == 'CONSENSUS_2PLUS':
        assert len(broker_ids) >= 2 and row.get('target_consensus') is not None, 'false consensus'
    elif len(broker_ids) < 2:
        assert row.get('target_consensus') is None, 'single broker consensus'
    if row.get('target_upside') is not None:
        assert row['price_status'] == 'VERIFIED_2X' and math.isfinite(row['target_upside']), 'invalid target upside'
    if row.get('rsi14') is not None:
        assert row.get('technical_data_date')==expected and row.get('technical_freshness')=='FRESH', 'stale technical published'
assert data['health']['fresh_history'] == sum(r.get('technical_data_date')==expected for r in rows)
print('PRODUCTION_ACCEPTANCE_PASS',data['health']['status'],len(rows),len(verified))
state=ROOT/'data/state';state.mkdir(parents=True,exist_ok=True)
(state/'production_checkpoint.json').write_text(json.dumps({
    'schema_version':1,'generated_at':data['generated_at'],'market_date':expected,
    'health':data['health'],'next_action':'Resolve explicit gaps; never rescan committed history or lower verification.',
    'resume_document':'docs/CONTINUE.md'
},ensure_ascii=False,indent=2))
