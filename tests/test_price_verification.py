from bist_terminal.models import PriceObservation
from bist_terminal.quality.price_verification import verify_prices, retain_same_trade_date_verified

def o(p,u,price,date='2026-10-01',adj=False): return PriceObservation('THYAO','BIST',date,date+'T18:00:00+03:00',price,'TRY',adj,100,p,u)
def test_two_independent_sources_verify(): assert verify_prices([o('a','u1',100),o('b','u2',100.05)],'2026-10-01').status=='VERIFIED_2X'
def test_same_upstream_is_single_source(): assert verify_prices([o('a','same',100),o('b','same',100)],'2026-10-01').status=='SINGLE_SOURCE'
def test_conflict_not_averaged():
    r=verify_prices([o('a','u1',100),o('b','u2',102.5)],'2026-10-01'); assert r.status=='SOURCE_CONFLICT' and r.verified_price is None
def test_stale_rejected(): assert verify_prices([o('a','u1',100,'2026-09-29'),o('b','u2',100,'2026-09-29')],'2026-10-01').status=='STALE'
def test_adjusted_raw_mismatch_excluded(): assert verify_prices([o('a','u1',100,adj=True),o('b','u2',100)],'2026-10-01').status=='SINGLE_SOURCE'

def test_single_official_source_is_not_verified():
    r=verify_prices([o('bist_official','Borsa Istanbul',100)],'2026-10-01',official_ids={'bist_official'})
    assert r.status=='SINGLE_SOURCE' and r.verified_price is None

def test_official_plus_independent_source_is_verified_2x():
    r=verify_prices([o('bist_official','Borsa Istanbul',100),o('secondary','independent',100.05)],'2026-10-01',official_ids={'bist_official'})
    assert r.status=='VERIFIED_2X' and 'official anchor included' in r.reason


def test_same_trade_date_verified_result_survives_transient_refresh_failure():
    current=verify_prices([o('secondary','independent',100.05)],'2026-10-01')
    previous={
        'ticker':'THYAO',
        'trade_date':'2026-10-01',
        'verified_price':100.025,
        'status':'VERIFIED_2X',
        'sources':['bist_official','secondary'],
        'upstreams':['Borsa Istanbul','independent'],
        'max_diff_pct':0.05,
    }
    kept=retain_same_trade_date_verified(current,previous,'2026-10-01')
    assert kept.status=='VERIFIED_2X'
    assert kept.verified_price==100.025
    assert 'same trade date' in kept.reason


def test_verification_is_never_carried_across_trade_dates():
    current=verify_prices([o('secondary','independent',100.05,'2026-10-02')],'2026-10-02')
    previous={
        'ticker':'THYAO',
        'trade_date':'2026-10-01',
        'verified_price':100.025,
        'status':'VERIFIED_2X',
        'sources':['bist_official','secondary'],
        'upstreams':['Borsa Istanbul','independent'],
        'max_diff_pct':0.05,
    }
    kept=retain_same_trade_date_verified(current,previous,'2026-10-02')
    assert kept.status!='VERIFIED_2X'
