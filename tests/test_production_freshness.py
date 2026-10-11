from datetime import datetime, timezone
import pytest
from bist_terminal.quality.production import completed_trade_date
from bist_terminal.providers.base import NoData, SchemaChanged
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.providers.yahoo import YahooChartProvider


def test_preclose_and_weekend_use_last_closed_session():
    cal={'year':2026,'closed':[]}
    assert str(completed_trade_date(datetime(2026,10,9,12,tzinfo=timezone.utc),cal))=='2026-10-08'
    assert str(completed_trade_date(datetime(2026,10,9,18,tzinfo=timezone.utc),cal))=='2026-10-09'
    assert str(completed_trade_date(datetime(2026,10,11,1,tzinfo=timezone.utc),cal))=='2026-10-09'
    with pytest.raises(ValueError):completed_trade_date(datetime(2026,10,9,12,tzinfo=timezone.utc),cal,'2026-10-09')
    with pytest.raises(ValueError):completed_trade_date(datetime(2027,1,4,18,tzinfo=timezone.utc),cal)


def test_symbol_no_data_never_shuts_remaining_universe():
    class Provider:
        provider_id='test'
        def get_latest_price(self,ticker):
            if ticker=='ISATR':raise NoData('no trades')
            return ticker
    chain=FallbackChain([Provider()])
    assert chain.collect('ISATR')[0]==[]
    assert chain.collect('ISCTR')[0]==['ISCTR']
    assert not chain.circuits['test'].open


def test_empty_valid_yahoo_series_is_no_data_not_schema_failure():
    p=YahooChartProvider()
    p._request_json=lambda _: {'chart':{'result':[{'meta':{'symbol':'ISATR.IS'},'indicators':{'quote':[{}]}}]}}
    with pytest.raises(NoData):p.get_latest_price('ISATR')
    p._request_json=lambda _: {'chart':{'result':[{}]}}
    with pytest.raises(SchemaChanged):p.get_latest_price('ISATR')
