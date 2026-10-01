import pandas as pd, numpy as np
from bist_terminal.calculations.technical import sma,ema,rsi,macd,atr,bollinger

def sample():
    c=pd.Series(np.arange(1,61,dtype=float)); return pd.DataFrame({'High':c+1,'Low':c-1,'Close':c,'Volume':1000})
def test_sma(): assert sma(sample().Close,5).iloc[-1]==58.0
def test_ema_monotonic(): assert ema(sample().Close,12).iloc[-1] > ema(sample().Close,26).iloc[-1]
def test_rsi_uptrend_near_100(): assert rsi(sample().Close,14).iloc[-1] == 100.0
def test_macd_positive(): assert macd(sample().Close)[0].iloc[-1] > 0
def test_atr_positive(): assert atr(sample(),14).iloc[-1] > 0
def test_bollinger_order():
    mid,up,lo=bollinger(sample().Close); assert lo.iloc[-1] < mid.iloc[-1] < up.iloc[-1]

def test_vwap_requires_intraday_price_and_volume():
    from bist_terminal.calculations.technical import vwap
    assert vwap(pd.DataFrame({'Close':[1,2],'Volume':[10,20]})) is None
    assert vwap(pd.DataFrame({'Price':[10,20],'Volume':[1,3]})) == 17.5

def test_adx_outputs_nonnegative_when_available():
    from bist_terminal.calculations.technical import adx
    a,p,m=adx(sample(),14)
    assert (a.dropna()>=0).all() and (p.dropna()>=0).all() and (m.dropna()>=0).all()
