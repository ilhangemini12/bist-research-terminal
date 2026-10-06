from datetime import datetime
import pytest
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.base import ProviderError
from bist_terminal.quality.price_verification import verify_prices, retain_same_trade_date_verified
from bist_terminal.models import PriceObservation

class Response:
    status_code = 200
    def __init__(self, bars): self.bars = bars
    def raise_for_status(self): pass
    def json(self):
        return {'chart': {'result': [{'timestamp': [int(datetime.fromisoformat(t).timestamp()) for t, _ in self.bars],
            'meta': {'currency': 'TRY'}, 'indicators': {'quote': [{'close': [v for _, v in self.bars], 'volume': [1]*len(self.bars)}]}}]}}

class Session:
    def __init__(self, bars): self.bars = bars; self.urls = []
    def get(self, url, **kwargs): self.urls.append(url); return Response(self.bars)

def test_exact_target_selected_even_when_response_has_newer_bar():
    s = Session([('2026-10-05T10:00:00+03:00', 100), ('2026-10-06T10:00:00+03:00', 110)])
    obs = YahooChartProvider(session=s, target_trade_date='2026-10-05').get_latest_price('THYAO')
    assert obs.trade_date == '2026-10-05' and obs.close == 100
    assert 'period1=' in s.urls[0] and 'range=5d' not in s.urls[0]
    official = PriceObservation('THYAO','BIST','2026-10-05','2026-10-05T18:10:00+03:00',100,provider_id='bist',upstream_vendor='Borsa Istanbul')
    assert verify_prices([official, obs], '2026-10-05').status == 'VERIFIED_2X'

def test_missing_target_does_not_relabel_old_or_new_price():
    s = Session([('2026-10-02T10:00:00+03:00', 100), ('2026-10-06T10:00:00+03:00', 110)])
    with pytest.raises(ProviderError, match='no raw close'):
        YahooChartProvider(session=s, target_trade_date='2026-10-05').get_latest_price('THYAO')
    assert len(s.urls) == 1

def test_exchange_date_used_instead_of_utc_date():
    s = Session([('2026-10-04T22:30:00+00:00', 100)])
    assert YahooChartProvider(session=s, target_trade_date='2026-10-05').get_latest_price('THYAO').trade_date == '2026-10-05'

def test_prior_verification_cannot_hide_current_source_conflict():
    a = PriceObservation('THYAO','BIST','2026-10-05','',100,provider_id='a',upstream_vendor='a')
    b = PriceObservation('THYAO','BIST','2026-10-05','',110,provider_id='b',upstream_vendor='b')
    current = verify_prices([a,b], '2026-10-05')
    previous = {'ticker':'THYAO','trade_date':'2026-10-05','status':'VERIFIED_2X','verified_price':100,'upstreams':['a','b']}
    assert retain_same_trade_date_verified(current, previous, '2026-10-05').status == 'SOURCE_CONFLICT'
