from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median
from bist_terminal.models import PriceObservation, PriceConfidence
from bist_terminal.quality.freshness import price_freshness

@dataclass
class VerificationResult:
    ticker: str; status: str; verified_price: float|None; trade_date: str|None; sources: list[str]; upstreams: list[str]; max_diff_pct: float|None; reason: str
    def as_dict(self): return asdict(self)

def verify_prices(observations:list[PriceObservation],expected_trade_date:str,tolerance_pct:float=0.15,official_ids:set[str]|None=None)->VerificationResult:
    if not observations: return VerificationResult('',PriceConfidence.UNVERIFIED,None,None,[],[],None,'no observations')
    ticker=observations[0].ticker
    normalized=[o for o in observations if o.ticker==ticker and o.market=='BIST' and o.currency=='TRY' and not o.adjusted]
    fresh=[o for o in normalized if price_freshness(o.trade_date,expected_trade_date)=='FRESH' and o.close>0]
    if not fresh: return VerificationResult(ticker,PriceConfidence.STALE,None,None,[o.provider_id for o in observations],[],None,'no fresh raw-close observations')
    by_lineage={}
    for o in fresh: by_lineage.setdefault(o.lineage_key(),o)
    independent=list(by_lineage.values())
    official_ids=official_ids or set()
    if len(independent)<2:
        return VerificationResult(ticker,PriceConfidence.SINGLE_SOURCE,None,expected_trade_date,[x.provider_id for x in independent],[x.lineage_key() for x in independent],None,'fewer than 2 independent upstreams')
    prices=[x.close for x in independent]; lo=min(prices); hi=max(prices); mid=median(prices)
    diff=(hi-lo)/mid*100 if mid else 999.0
    if diff>tolerance_pct:
        return VerificationResult(ticker,PriceConfidence.SOURCE_CONFLICT,None,expected_trade_date,[x.provider_id for x in independent],[x.lineage_key() for x in independent],diff,f'price divergence {diff:.4f}% > {tolerance_pct:.4f}%')
    official_present=any(o.provider_id in official_ids for o in independent)
    reason='two or more independent upstreams agree' + ('; official anchor included' if official_present else '')
    return VerificationResult(ticker,PriceConfidence.VERIFIED_2X,mid,expected_trade_date,[x.provider_id for x in independent],[x.lineage_key() for x in independent],diff,reason)
