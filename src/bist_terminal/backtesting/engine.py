from __future__ import annotations
import numpy as np, pandas as pd

def metrics(returns:pd.Series,rf=0.0):
    r=returns.dropna();
    if r.empty: return {}
    wealth=(1+r).cumprod(); years=max(len(r)/252,1/252); cagr=wealth.iloc[-1]**(1/years)-1
    vol=r.std(ddof=0)*np.sqrt(252); downside=r[r<0].std(ddof=0)*np.sqrt(252) if (r<0).any() else 0
    sharpe=(r.mean()*252-rf)/vol if vol else None; sortino=(r.mean()*252-rf)/downside if downside else None
    dd=wealth/wealth.cummax()-1
    return {'cagr':cagr,'total_return':wealth.iloc[-1]-1,'annualized_volatility':vol,'sharpe':sharpe,'sortino':sortino,'max_drawdown':dd.min(),'win_rate':float((r>0).mean())}

def point_in_time_guard(financial_publication_date,decision_date):
    if pd.Timestamp(financial_publication_date)>pd.Timestamp(decision_date): raise ValueError('LOOK_AHEAD_BIAS_BLOCKED')

def universe_guard(has_point_in_time_membership:bool):
    return None if has_point_in_time_membership else 'BACKTEST BIASED: point-in-time universe unavailable'


def turnover(weights: pd.DataFrame) -> float | None:
    """Average one-way portfolio turnover from periodic target weights."""
    if weights is None or weights.empty or len(weights) < 2:
        return None
    w = weights.fillna(0.0)
    return float(w.diff().abs().sum(axis=1).iloc[1:].mean() / 2.0)
