from __future__ import annotations


def _positive(value):
    try:
        value=float(value)
    except (TypeError,ValueError):
        return None
    return value if value>0 else None


def compute_valuation(
    *,
    price_status: str,
    price,
    total_shares,
    net_income_ttm=None,
    equity=None,
    revenue_ttm=None,
) -> dict:
    """Compute conservative equity valuation metrics.

    Market cap is emitted only from a VERIFIED_2X price and an explicit positive
    KAP total-share count. Ratios with non-positive denominators remain N/A.
    """
    p=_positive(price)
    shares=_positive(total_shares)
    if price_status!="VERIFIED_2X" or p is None:
        return {
            "valuation_status":"PRICE_NOT_VERIFIED",
            "market_cap":None,"pe":None,"pb":None,"ps":None,"earnings_yield":None,
        }
    if shares is None:
        return {
            "valuation_status":"CAPITAL_UNAVAILABLE",
            "market_cap":None,"pe":None,"pb":None,"ps":None,"earnings_yield":None,
        }

    market_cap=p*shares
    ni=_positive(net_income_ttm)
    eq=_positive(equity)
    rev=_positive(revenue_ttm)
    return {
        "valuation_status":"ACTIVE",
        "market_cap":market_cap,
        "pe":market_cap/ni if ni is not None else None,
        "pb":market_cap/eq if eq is not None else None,
        "ps":market_cap/rev if rev is not None else None,
        "earnings_yield":ni/market_cap if ni is not None and market_cap>0 else None,
    }
