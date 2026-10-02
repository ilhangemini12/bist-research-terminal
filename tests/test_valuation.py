from bist_terminal.calculations.valuation import compute_valuation


def test_valuation_requires_verified_price():
    out=compute_valuation(
        price_status="SINGLE_SOURCE",price=100,total_shares=10,
        net_income_ttm=100,equity=200,revenue_ttm=500,
    )
    assert out["valuation_status"]=="PRICE_NOT_VERIFIED"
    assert out["market_cap"] is None
    assert out["pe"] is None


def test_valuation_uses_explicit_shares_and_positive_denominators():
    out=compute_valuation(
        price_status="VERIFIED_2X",price=10,total_shares=100,
        net_income_ttm=100,equity=500,revenue_ttm=2000,
    )
    assert out["valuation_status"]=="ACTIVE"
    assert out["market_cap"]==1000
    assert out["pe"]==10
    assert out["pb"]==2
    assert out["ps"]==0.5
    assert out["earnings_yield"]==0.1


def test_negative_earnings_do_not_emit_pe():
    out=compute_valuation(
        price_status="VERIFIED_2X",price=10,total_shares=100,
        net_income_ttm=-50,equity=500,revenue_ttm=2000,
    )
    assert out["market_cap"]==1000
    assert out["pe"] is None
    assert out["earnings_yield"] is None
