from __future__ import annotations
from datetime import date,timedelta
import yaml

def load_calendar(path='config/bist_calendar_2026.yaml'):
    with open(path,encoding='utf-8') as f: return yaml.safe_load(f)

def is_trading_day(day:date,cal:dict)->bool:
    return day.weekday()<5 and day.isoformat() not in set(map(str,cal.get('closed',[])))

def latest_expected_trade_date(day:date,cal:dict)->date:
    d=day
    while not is_trading_day(d,cal): d-=timedelta(days=1)
    return d
