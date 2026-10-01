from bist_terminal.calculations.fundamental import calc_ratios,ttm

def test_ratios_known_values():
    r=calc_ratios({'price':10,'shares':100,'financial_debt':300,'cash':100,'net_income_ttm':100,'equity':500,'assets':1500,'revenue_ttm':1000,'ebitda_ttm':200,'fcf_ttm':80})
    assert r['market_cap']==1000 and r['ev']==1200 and r['pe']==10 and r['pb']==2 and r['ev_ebitda']==6 and r['roe']==0.2 and r['net_debt']==200 and r['fcf_yield']==0.08
def test_ttm_requires_four_quarters(): assert ttm([1,2,3,4])==10 and ttm([1,2,None,4]) is None


def test_extended_ratios_are_computed_only_from_supplied_inputs():
    from bist_terminal.calculations.fundamental import calc_ratios
    r=calc_ratios({
        'price':10,'shares':100,'financial_debt':200,'cash':50,
        'net_income_ttm':100,'equity':500,'assets':1000,'revenue_ttm':1000,
        'gross_profit_ttm':400,'ebit_ttm':200,'ebitda_ttm':250,'fcf_ttm':80,
        'current_assets':300,'inventories':50,'current_liabilities':150,
        'dividends_ttm':40,'effective_tax_rate':0.25,'invested_capital':600,
    })
    assert r['gross_margin'] == 0.4
    assert r['ebitda_margin'] == 0.25
    assert r['operating_margin'] == 0.2
    assert r['net_margin'] == 0.1
    assert r['current_ratio'] == 2
    assert r['quick_ratio'] == 250/150
    assert r['dividend_yield'] == 0.04
    assert r['payout_ratio'] == 0.4
    assert r['roic'] == 150/600


def test_roic_is_na_without_tax_rate_or_invested_capital():
    from bist_terminal.calculations.fundamental import calc_ratios
    assert calc_ratios({'ebit_ttm':100})['roic'] is None
