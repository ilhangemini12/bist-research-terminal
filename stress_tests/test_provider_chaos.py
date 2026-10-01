from bist_terminal.providers.mock import MockPriceProvider
from bist_terminal.providers.registry import FallbackChain

def test_primary_down_secondary_works():
    c=FallbackChain([MockPriceProvider('primary','u1',fail=True),MockPriceProvider('secondary','u2',price=101)])
    v,a=c.first_success('THYAO'); assert v.close==101 and [x.ok for x in a]==[False,True]
def test_primary_secondary_down_third_works():
    c=FallbackChain([MockPriceProvider('p1','u1',fail=True),MockPriceProvider('p2','u2',fail=True),MockPriceProvider('p3','u3',price=99)])
    v,a=c.first_success('THYAO'); assert v.provider_id=='p3' and len(a)==3

def test_blocked_provider_circuit_stays_open_for_rest_of_run():
    class CountBlocked(MockPriceProvider):
        def __init__(self): super().__init__('blocked','u1'); self.calls=0
        def get_latest_price(self,ticker): self.calls+=1; raise __import__('bist_terminal.providers.base',fromlist=['Blocked']).Blocked('403')
    bad=CountBlocked(); ok=MockPriceProvider('ok','u2',price=101)
    c=FallbackChain([bad,ok])
    c.collect('THYAO'); _,attempts=c.collect('GARAN')
    assert bad.calls==1 and attempts[0].skipped and 'CIRCUIT_OPEN' in attempts[0].error

def test_timeout_opens_after_threshold_not_forever_polled():
    class CountTimeout(MockPriceProvider):
        def __init__(self): super().__init__('slow','u1'); self.calls=0
        def get_latest_price(self,ticker): self.calls+=1; raise TimeoutError('timeout')
    bad=CountTimeout(); ok=MockPriceProvider('ok','u2',price=101)
    c=FallbackChain([bad,ok], failure_threshold=2)
    c.collect('A'); c.collect('B'); _,att=c.collect('C')
    assert bad.calls==2 and att[0].skipped
