"""Closed-session dates and evidence-based production health."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .market_calendar import latest_expected_trade_date, resolve_run_trade_date


def completed_trade_date(now, calendar, requested=None):
    local = now.astimezone(ZoneInfo('Europe/Istanbul'))
    if calendar.get('year') and int(calendar['year']) != local.year:
        raise ValueError('CALENDAR_YEAR_UNREVIEWED')
    candidate = local.date() if local.hour >= 19 else local.date() - timedelta(days=1)
    completed = latest_expected_trade_date(candidate, calendar)
    if requested:
        chosen = resolve_run_trade_date(local.date(), calendar, requested)
        if chosen > completed:
            raise ValueError('REQUESTED_SESSION_NOT_CLOSED')
        return chosen
    return completed


def production_health(stocks, expected, history_status, financial_status, capital_status):
    total = len(stocks)
    verified = sum(s.get('price_status') == 'VERIFIED_2X' for s in stocks)
    fresh = sum(s.get('technical_data_date') == expected for s in stocks)
    missing = [s['ticker'] for s in stocks if s.get('price_status') != 'VERIFIED_2X']
    stale = [s['ticker'] for s in stocks if s.get('technical_data_date') != expected]
    return {
        'status': 'HEALTHY' if total and verified == total and fresh == total and all(x in ('ACTIVE','ACTIVE/TESTED','UP_TO_DATE') for x in (history_status,financial_status,capital_status)) else 'PARTIAL',
        'expected_market_date': expected, 'tracked': total,
        'verified_prices': verified, 'fresh_history': fresh,
        'unverified_tickers': missing, 'stale_history_tickers': stale,
        'history_refresh_status': history_status,
        'financial_refresh_status': financial_status,
        'capital_refresh_status': capital_status,
        'policy': 'Missing or stale inputs remain unavailable; no relaxed verification.'
    }
