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


def test_share_class_capital_cannot_value_whole_issuer():
    from bist_terminal.calculations.valuation import multi_class_tickers
    assert multi_class_tickers({'A':{'mkk_member_oid':'same'},'B':{'mkk_member_oid':'same'},'C':{'mkk_member_oid':'other'}})=={'A','B'}
    r=compute_valuation(price_status='VERIFIED_2X',price=10,total_shares=100,net_income_ttm=100,equity=500,issuer_capital_complete=False)
    assert r['share_class_market_cap']==1000 and r['market_cap'] is None
    assert r['pe'] is None and r['pb'] is None and r['valuation_status']=='MULTI_SHARE_CLASS_REVIEW'


def test_unknown_inventory_does_not_become_zero():
    from bist_terminal.calculations.valuation import quick_ratio
    assert quick_ratio(100,None,50) is None
    assert quick_ratio(100,0,50)==2
    assert quick_ratio(100,25,50)==1.5
