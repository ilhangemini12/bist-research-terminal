from __future__ import annotations
import numpy as np
import pandas as pd

def sma(s,n): return s.rolling(n,min_periods=n).mean()
def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean(); ad=dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    rs=au/ad.replace(0,np.nan); out=100-(100/(1+rs))
    return out.where(ad!=0,100.0)
def macd(s,fast=12,slow=26,signal=9):
    m=ema(s,fast)-ema(s,slow); sig=m.ewm(span=signal,adjust=False,min_periods=signal).mean(); return m,sig,m-sig
def true_range(df):
    prev=df['Close'].shift(1); return pd.concat([(df['High']-df['Low']).abs(),(df['High']-prev).abs(),(df['Low']-prev).abs()],axis=1).max(axis=1)
def atr(df,n=14): return true_range(df).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
def bollinger(s,n=20,k=2):
    mid=sma(s,n); std=s.rolling(n,min_periods=n).std(ddof=0); return mid,mid+k*std,mid-k*std
def roc(s,n): return (s/s.shift(n)-1)*100
def obv(close,volume): return (np.sign(close.diff()).fillna(0)*volume).cumsum()
def historical_volatility(s,n): return s.pct_change().rolling(n).std(ddof=0)*np.sqrt(252)
def max_drawdown(s):
    wealth=s/s.iloc[0]; dd=wealth/wealth.cummax()-1; return dd.cummin()
def adx(df,n=14):
    up=df['High'].diff(); down=-df['Low'].diff()
    plus_dm=up.where((up>down)&(up>0),0.0); minus_dm=down.where((down>up)&(down>0),0.0)
    tr=true_range(df); atrn=tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    plus_di=100*plus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/atrn
    minus_di=100*minus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/atrn
    denom=(plus_di+minus_di).replace(0,np.nan); dx=100*(plus_di-minus_di).abs()/denom
    adxv=dx.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    return adxv,plus_di,minus_di

def vwap(intraday:pd.DataFrame):
    required={'Price','Volume'}
    if not required.issubset(intraday.columns) or intraday.empty: return None
    vol=intraday['Volume'].sum()
    if vol<=0: return None
    return float((intraday['Price']*intraday['Volume']).sum()/vol)

def add_indicators(df:pd.DataFrame)->pd.DataFrame:
    x=df.copy(); c=x['Close']
    for n in (7,14,21): x[f'RSI{n}']=rsi(c,n)
    for n in (5,10,20,50,100,200): x[f'SMA{n}']=sma(c,n)
    for n in (12,20,26,50,200): x[f'EMA{n}']=ema(c,n)
    x['MACD'],x['MACD_SIGNAL'],x['MACD_HIST']=macd(c); x['ATR14']=atr(x)
    x['BB_MID'],x['BB_UPPER'],x['BB_LOWER']=bollinger(c)
    x['ADX'],x['PLUS_DI'],x['MINUS_DI']=adx(x)
    x['ROC5']=roc(c,5); x['ROC20']=roc(c,20); x['OBV']=obv(c,x['Volume'])
    x['VOLUME_MA20']=x['Volume'].rolling(20).mean(); x['VOLUME_RATIO']=x['Volume']/x['VOLUME_MA20']
    for n in (20,60,252): x[f'HVOL{n}']=historical_volatility(c,n)
    x['DIST_52W_HIGH']=(c/c.rolling(252).max()-1)*100; x['DIST_52W_LOW']=(c/c.rolling(252).min()-1)*100
    return x
