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
    'Capital Coverage %':data.get('summary',{}).get('capital_coverage_pct',0),
    'Valuation Active':data.get('summary',{}).get('valuation_active_count',0),
    'P/E Available':data.get('summary',{}).get('pe_count',0),
    'P/B Available':data.get('summary',{}).get('pb_count',0),
    'Extended Valuation Active':data.get('summary',{}).get('extended_valuation_active_count',0),
    'EV/EBITDA Available':data.get('summary',{}).get('ev_ebitda_count',0),
    'Net Debt/EBITDA Available':data.get('summary',{}).get('net_debt_ebitda_count',0),
    'FCF Yield Available':data.get('summary',{}).get('fcf_yield_count',0),
    'ROIC Active':data.get('summary',{}).get('roic_active_count',0),
    'High ROIC >15%':data.get('summary',{}).get('high_roic_gt_15_count',0),
    'Dividend Positive':data.get('summary',{}).get('dividend_positive_count',0),
    'Recent SPK/KAP News':data.get('summary',{}).get('kap_news_count',0),
    'News Mapped to Current Universe':data.get('summary',{}).get('kap_news_mapped_count',0),
    'Target Prices Available':data.get('summary',{}).get('target_price_count',0),
    'Target Consensus 2+':data.get('summary',{}).get('target_consensus_2plus_count',0),
    'Model Portfolio Stocks':data.get('summary',{}).get('model_portfolio_count',0),
}
source_catalog=pd.DataFrame(yaml.safe_load((ROOT/'config/source_catalog.yaml').read_text())['providers'])
source_status=pd.DataFrame(data.get('sources',[]))
kap_news=pd.DataFrame(data.get('kap_news',[]))
broker_models=pd.DataFrame(data.get('broker_model_portfolios',[]))
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
    'High ROIC':filter_expr(presets['HIGH_ROIC']['rules']),
    'Ozkan Filiz':filter_expr(presets['OZKAN_FILIZ_SECTOR_VALUE']['rules']),
    'Volkan Kocabas':filter_expr(presets['VOLKAN_KOCABAS_VALUE_GROWTH']['rules']),
    'Technical':cols(['ticker','price','price_status','rsi14','rsi14_prev','rsi_recent_low','sma10','sma20','sma50','roc20','volume','volume_ma20','volume_ratio']),
    'Fundamentals':cols(['ticker','sector','price','price_status','total_shares','market_cap','pe','pb','ps','earnings_yield','ev','ev_ebitda','ev_sales','financial_debt','financial_debt_basis','net_debt','net_debt_ebitda','debt_equity','ebitda_ttm','ebitda_basis','ebitda_margin','depreciation_amortization_ttm','capex_ttm','fcf_ttm','fcf_basis','fcf_yield','roic','roic_status','roic_basis','roic_report_period','effective_tax_rate','average_invested_capital','extended_valuation_status','extended_metrics_basis','dividend_ttm_per_share','dividend_yield','dividend_payout_ratio','valuation_status','valuation_basis','financial_report_period','financial_quarters_available','roe','roa','gross_margin','operating_margin','current_ratio','quick_ratio','revenue_ttm','net_income_ttm','cash_from_operations_ttm','assets','equity','cash','capital_source_url','financial_source_url']),
    'Growth':cols(['ticker','revenue_growth_yoy','net_income_growth_yoy','revenue_quarter_yoy','net_income_quarter_yoy','revenue_ttm_growth','net_income_ttm_growth']),
    'Target Prices':cols(['ticker','price','price_status','target_price','target_upside','target_status','target_consensus','target_source_count','target_sources','target_latest_date','model_portfolio_active','model_portfolio_brokers']),
    'Model Portfolios':broker_models,
    'KAP News':kap_news,
    'Data Quality':cols(['ticker','price_status','valuation_status','extended_valuation_status','extended_metrics_basis','roic_status','roic_basis','financial_status','financial_quality_score','financial_quarters_available','technical_history_rows','verification_reason','trade_date','source_lineage','capital_method']),
    'Source Status':source_status,
    'Sources':source_catalog,
}
export_excel(tables,ROOT/'artifacts/BIST_Research_Latest.xlsx')
print(ROOT/'artifacts/BIST_Research_Latest.xlsx')
