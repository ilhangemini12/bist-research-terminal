from bist_terminal.quality.payload import validate_payload, normalize_bist_timestamp
from bist_terminal.quality.records import dedupe_records, dedupe_kap_disclosures
from bist_terminal.quality.research import target_price_freshness
from bist_terminal.quality.corporate_actions import corporate_action_day_check
from bist_terminal.quality.sanity import validate_market_row, validate_balance_sheet
from bist_terminal.quality.price_verification import verify_prices
from bist_terminal.models import PriceObservation
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.providers.mock import MockPriceProvider
from bist_terminal.providers.base import Blocked, RateLimited


def obs(ticker='THYAO', provider='a', upstream='u1', price=100, date='2026-10-01'):
    return PriceObservation(ticker,'BIST',date,date+'T18:00:00+03:00',price,'TRY',False,100,provider,upstream)


def test_malformed_html_payload_rejected():
    assert validate_payload('<html>captcha</html>', ('ticker','close')) == ['MALFORMED_PAYLOAD']


def test_json_schema_change_flagged():
    errors = validate_payload({'ticker':'THYAO','last':100}, ('ticker','close'))
    assert 'SCHEMA_CHANGED_MISSING_CLOSE' in errors


def test_missing_ticker_schema_change_flagged():
    assert 'SCHEMA_CHANGED_MISSING_TICKER' in validate_payload({'close':100}, ('ticker','close'))


def test_wrong_ticker_isolated_not_verified():
    r=verify_prices([obs('THYAO','a','u1'),obs('GARAN','b','u2')],'2026-10-01')
    assert r.status=='SINGLE_SOURCE' and r.verified_price is None


def test_payload_wrong_ticker_flagged():
    assert 'WRONG_TICKER' in validate_payload({'ticker':'GARAN','close':100}, ('ticker','close'), 'THYAO')


def test_duplicate_market_row_removed():
    rows=[{'ticker':'THYAO','date':'2026-10-01','close':100},{'ticker':'THYAO','date':'2026-10-01','close':100}]
    unique,n=dedupe_records(rows,('ticker','date'))
    assert len(unique)==1 and n==1


def test_duplicate_kap_disclosure_removed():
    rows=[{'disclosure_id':'123','ticker':'THYAO'},{'disclosure_id':'123','ticker':'THYAO'}]
    unique,n=dedupe_kap_disclosures(rows)
    assert len(unique)==1 and n==1


def test_wrong_timezone_is_normalized_to_bist():
    normalized,flags=normalize_bist_timestamp('2026-10-01T19:00:00+04:00')
    assert normalized.endswith('+03:00') and 'TIMEZONE_NORMALIZED' in flags


def test_naive_timestamp_rejected():
    normalized,flags=normalize_bist_timestamp('2026-10-01T18:00:00')
    assert normalized is None and flags==['TIMEZONE_MISSING']


def test_zero_volume_is_warning_not_silent():
    assert 'ZERO_VOLUME_WARNING' in validate_market_row({'price':100,'volume':0})


def test_missing_financial_statement_flagged():
    assert validate_balance_sheet(None,80,20)==['FINANCIAL_MISSING']


def test_old_target_price_archived():
    assert target_price_freshness('2026-06-01','2026-10-01',90)=='ARCHIVE'


def test_recent_target_price_current():
    assert target_price_freshness('2026-09-15','2026-10-01',90)=='CURRENT'


def test_split_day_needs_action_normalization():
    assert corporate_action_day_check(100,50,'SPLIT')==['CORPORATE_ACTION_NORMALIZATION_REQUIRED']


def test_dividend_day_needs_action_normalization():
    assert corporate_action_day_check(100,98,'DIVIDEND')==['CORPORATE_ACTION_NORMALIZATION_REQUIRED']


def test_unexplained_adjusted_raw_mismatch_flagged():
    assert corporate_action_day_check(100,98,None)==['UNEXPLAINED_ADJUSTED_RAW_MISMATCH']


class BlockedProvider(MockPriceProvider):
    def get_latest_price(self,ticker):
        raise Blocked('403 injected')

class TimeoutProvider(MockPriceProvider):
    def get_latest_price(self,ticker):
        raise TimeoutError('timeout injected')


def test_403_circuit_fallback_continues():
    value,attempts=FallbackChain([BlockedProvider('blocked','u1'),MockPriceProvider('ok','u2',101)]).first_success('THYAO')
    assert value.close==101 and attempts[0].ok is False and 'Blocked' in attempts[0].error


def test_timeout_fallback_continues():
    value,attempts=FallbackChain([TimeoutProvider('slow','u1'),MockPriceProvider('ok','u2',102)]).first_success('THYAO')
    assert value.close==102 and 'TimeoutError' in attempts[0].error


def test_429_retry_is_bounded_and_recovers():
    p=MockPriceProvider('p','u')
    calls=[]; sleeps=[]
    def fn():
        calls.append(1)
        if len(calls)<3: raise RateLimited('429')
        return 7
    assert p.with_retry(fn, waits=(0,0,0), sleep=lambda x:sleeps.append(x))==7
    assert len(calls)==3 and len(sleeps)==2
