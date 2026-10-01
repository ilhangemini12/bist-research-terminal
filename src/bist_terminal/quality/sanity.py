from __future__ import annotations

def validate_market_row(row:dict)->list[str]:
    e=[]
    if row.get('price') is not None and row['price']<=0: e.append('INVALID_PRICE')
    if row.get('volume') is not None and row['volume']<0: e.append('INVALID_VOLUME')
    if row.get('volume') == 0: e.append('ZERO_VOLUME_WARNING')
    if row.get('pb') == 0: e.append('INVALID_PB_ZERO')
    if row.get('pe') is not None and row['pe'] < -100: e.append('EXTREME_PE')
    if row.get('ev_ebitda') is not None and row['ev_ebitda'] < -20: e.append('EXTREME_EV_EBITDA')
    return e

def validate_balance_sheet(assets,liabilities,equity,tolerance=0.02)->list[str]:
    if assets is None or liabilities is None or equity is None: return ['FINANCIAL_MISSING']
    denom=max(abs(assets),1.0); gap=abs(assets-(liabilities+equity))/denom
    return ['FINANCIAL_VALIDATION_WARNING'] if gap>tolerance else []
