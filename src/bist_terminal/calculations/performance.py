from __future__ import annotations
import pandas as pd

PERIODS={'1D':1,'1W':5,'1M':21,'3M':63,'6M':126,'1Y':252,'3Y':756}

def total_return(close:pd.Series,periods:int):
    if len(close)<=periods: return None
    return close.iloc[-1]/close.iloc[-periods-1]-1

def performance_table(close:pd.Series,benchmark:pd.Series|None=None):
    out={k:total_return(close,n) for k,n in PERIODS.items()}
    if not close.empty:
        y=close[close.index.year==close.index[-1].year] if hasattr(close.index,'year') else close
        out['YTD']=None if len(y)<2 else y.iloc[-1]/y.iloc[0]-1
    if benchmark is not None:
        out.update({f'{k}_vs_XU100':(out[k]-total_return(benchmark,n) if out[k] is not None and total_return(benchmark,n) is not None else None) for k,n in PERIODS.items()})
    return out

def beta(asset:pd.Series,benchmark:pd.Series,window=252):
    a=asset.pct_change(); b=benchmark.pct_change(); z=pd.concat([a,b],axis=1).dropna().tail(window)
    if len(z)<20 or z.iloc[:,1].var()==0: return None
    return z.iloc[:,0].cov(z.iloc[:,1])/z.iloc[:,1].var()
