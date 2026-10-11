from bist_terminal.providers.yahoo import YahooChartProvider

class Resp:
    status_code=200
    def raise_for_status(self): pass
    def json(self):
        return {'chart':{'result':[{'timestamp':[1760000000,1760086400],'meta':{'currency':'TRY','symbol':'TEST.IS'},'indicators':{'quote':[{'open':[10,11],'high':[12,13],'low':[9,10],'close':[11,12],'volume':[100,200]}],'adjclose':[{'adjclose':[10.5,11.5]}]},'events':{'dividends':{'x':{'date':1760086400,'amount':.5}},'splits':{'y':{'date':1760000000,'splitRatio':'2:1'}}}}]}}
class S:
    def get(self,*a,**k): return Resp()

def test_yahoo_history_has_raw_and_adjusted_separate():
    p=YahooChartProvider(session=S()); df=p.get_history('TEST','2025-10-01','2025-10-10')
    assert list(df[['Close','Adjusted Close']].iloc[0])==[11,10.5]
    assert list(df.columns[:7])==['Date','Open','High','Low','Close','Adjusted Close','Volume']

def test_yahoo_corporate_actions_are_typed():
    p=YahooChartProvider(session=S()); df=p.get_corporate_actions('TEST','2025-10-01','2025-10-10')
    assert set(df['action_type'])=={'dividend','split'}


def test_history_rejects_wrong_currency_and_symbol():
    import pytest
    from bist_terminal.providers.base import SchemaChanged
    p=YahooChartProvider()
    for key,value in [('currency','USD'),('symbol','OTHER.IS')]:
        data=Resp().json()
        data['chart']['result'][0]['meta'][key]=value
        with pytest.raises(SchemaChanged):
            p._parse_history_bundle('TEST','https://example.test',data)


def test_empty_history_is_symbol_specific_no_data():
    import pytest
    from bist_terminal.providers.base import NoData
    p=YahooChartProvider()
    data={'chart':{'result':[{'meta':{'currency':'TRY','symbol':'TEST.IS'},'indicators':{'quote':[{}]}}]}}
    with pytest.raises(NoData):
        p._parse_history_bundle('TEST','https://example.test',data)
