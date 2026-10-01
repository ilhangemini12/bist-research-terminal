from __future__ import annotations
from dataclasses import asdict
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.quality.price_verification import verify_prices

def verify_universe(tickers,providers,expected_trade_date,tolerance_pct=0.15):
    chain=FallbackChain(providers); rows=[]; attempts={}
    for t in tickers:
        obs,att=chain.collect(t); attempts[t]=[asdict(a) for a in att]
        vr=verify_prices(obs,expected_trade_date,tolerance_pct=tolerance_pct); rows.append(vr.as_dict())
    return rows,attempts
