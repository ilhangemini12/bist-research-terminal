from pathlib import Path
import json, sys, yaml
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bist_terminal.exports.excel import export_excel
from bist_terminal.strategies.expression import compile_expression

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'dashboard/data/latest.json').read_text())
stocks=pd.DataFrame(data.get('stocks',[]))
summary={
    'Mode':data.get('mode'),'Prices as of':data.get('data_as_of',{}).get('prices'),'Financials as of':data.get('data_as_of',{}).get('financials'),
    'Targets as of':data.get('data_as_of',{}).get('targets'),'Tracked Stocks':data.get('summary',{}).get('tracked_stocks',0),
    'Verified Prices':data.get('summary',{}).get('verified_price_count',0),'Unverified Prices':data.get('summary',{}).get('unverified_price_count',0),
    'Financial Coverage %':data.get('summary',{}).get('financial_coverage_pct',0),
}
source_catalog=pd.DataFrame(yaml.safe_load((ROOT/'config/source_catalog.yaml').read_text())['providers'])
source_status=pd.DataFrame(data.get('sources',[]))
presets=yaml.safe_load((ROOT/'config/presets.yaml').read_text())['presets']

def cols(names):
    return stocks[[c for c in names if c in stocks.columns]].copy() if not stocks.empty else pd.DataFrame()

def filter_expr(expr):
    if stocks.empty: return stocks.copy()
    fn=compile_expression(expr)
    mask=[]
    for r in stocks.to_dict('records'):
        try: mask.append(bool(fn(r)))
        except Exception: mask.append(False)
    return stocks.loc[mask].copy()

def sector_contains(*parts):
    if stocks.empty or 'sector' not in stocks: return stocks.iloc[0:0].copy()
    pat='|'.join(parts); return stocks[stocks['sector'].fillna('').str.contains(pat,case=False,regex=True)].copy()

tables={
    'Dashboard':pd.DataFrame([summary]),
    'All Stocks':stocks,
    'BIST30':stocks[stocks.get('indices',pd.Series([[]]*len(stocks))).apply(lambda x:isinstance(x,list) and 'XU030' in x)] if 'indices' in stocks else pd.DataFrame(),
    'BIST100':stocks[stocks.get('indices',pd.Series([[]]*len(stocks))).apply(lambda x:isinstance(x,list) and 'XU100' in x)] if 'indices' in stocks else pd.DataFrame(),
    'Banks':sector_contains('bank'),
    'Insurance':sector_contains('insurance','sigorta'),
    'Brokerage':sector_contains('broker','aracı','araci'),
    'Industrials':sector_contains('industrial','sanayi'),
    'RSI Scanner':stocks.sort_values('rsi14') if 'rsi14' in stocks else stocks,
    'Value Scanner':filter_expr(presets['VALUE']['rules']),
    'Quality Scanner':filter_expr(presets['QUALITY']['rules']),
    'Growth Scanner':filter_expr(presets['GROWTH']['rules']),
    'Ozkan Filiz':filter_expr(presets['OZKAN_FILIZ_SECTOR_VALUE']['rules']),
    'Volkan Kocabas':filter_expr(presets['VOLKAN_KOCABAS_VALUE_GROWTH']['rules']),
    'Technical':cols(['ticker','price','price_status','rsi14','sma10','sma20','sma50','roc20','volume','volume_ma20','volume_ratio']),
    'Fundamentals':cols(['ticker','sector','price','pe','pb','ev_ebitda','roe','roic','net_debt_ebitda','dividend_yield','fcf_yield']),
    'Growth':cols(['ticker','revenue_growth_yoy','ebitda_growth_yoy','net_income_growth_yoy']),
    'Target Prices':cols(['ticker','target_upside']),
    'Model Portfolios':pd.DataFrame(),
    'KAP News':pd.DataFrame(),
    'Data Quality':cols(['ticker','price_status','quality_score','verification_reason','trade_date','source_lineage']),
    'Source Status':source_status,
    'Sources':source_catalog,
}
export_excel(tables,ROOT/'artifacts/BIST_Research_Latest.xlsx')
print(ROOT/'artifacts/BIST_Research_Latest.xlsx')
