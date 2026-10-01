from __future__ import annotations
from datetime import date, datetime

def price_freshness(trade_date:str, expected_trade_date:str)->str:
    if not trade_date: return 'UNVERIFIED'
    if trade_date == expected_trade_date: return 'FRESH'
    return 'STALE' if trade_date < expected_trade_date else 'FUTURE_DATE_ERROR'

def age_hours(retrieved_at:str, now:datetime|None=None)->float:
    dt=datetime.fromisoformat(retrieved_at.replace('Z','+00:00')); now=now or datetime.now(dt.tzinfo)
    return max(0.0,(now-dt).total_seconds()/3600)
