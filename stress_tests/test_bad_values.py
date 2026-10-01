from bist_terminal.quality.sanity import validate_market_row,validate_balance_sheet

def test_extremes_flagged():
    e=validate_market_row({'price':0,'volume':-10,'pe':-999,'pb':0,'ev_ebitda':-50}); assert {'INVALID_PRICE','INVALID_VOLUME','EXTREME_PE','INVALID_PB_ZERO','EXTREME_EV_EBITDA'} <= set(e)
def test_balance_sheet_warning(): assert validate_balance_sheet(100,80,10)==['FINANCIAL_VALIDATION_WARNING']
