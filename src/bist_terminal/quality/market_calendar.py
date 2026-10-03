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

def resolve_run_trade_date(today:date,cal:dict,requested:str|None=None)->date|None:
    """Resolve the trade date used by a pipeline run.

    Normal scheduled runs keep the existing behavior: a non-trading current day
    returns None and the pipeline skips. An explicit manual override must be an
    ISO date, must not be in the future, and must itself be a BIST trading day.
    """
    if requested:
        try:
            d=date.fromisoformat(requested)
        except ValueError as exc:
            raise ValueError('BIST_AS_OF_DATE must be YYYY-MM-DD') from exc
        if d>today:
            raise ValueError('BIST_AS_OF_DATE cannot be in the future')
        if not is_trading_day(d,cal):
            raise ValueError('BIST_AS_OF_DATE must be a BIST trading day')
        return d
    return today if is_trading_day(today,cal) else None
