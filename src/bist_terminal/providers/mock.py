from bist_terminal.models import PriceObservation
from bist_terminal.providers.base import BaseProvider, ProviderError

class MockPriceProvider(BaseProvider):
    def __init__(self,provider_id,upstream_vendor,price=100.0,trade_date='2026-10-01',fail=False,volume=1_000_000):
        self.provider_id=provider_id; self.upstream_vendor=upstream_vendor; self.price=price; self.trade_date=trade_date; self.fail=fail; self.volume=volume
    def get_latest_price(self,ticker):
        if self.fail: raise ProviderError(f'{self.provider_id} injected failure')
        return PriceObservation(ticker=ticker,market='BIST',trade_date=self.trade_date,timestamp=self.trade_date+'T18:10:00+03:00',close=self.price,volume=self.volume,provider_id=self.provider_id,upstream_vendor=self.upstream_vendor)
