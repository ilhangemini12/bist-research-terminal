from datetime import date
from bist_terminal.quality.market_calendar import is_trading_day,latest_expected_trade_date

def test_holiday_and_weekend():
    cal={'closed':['2026-10-29']}
    assert not is_trading_day(date(2026,10,29),cal)
    assert latest_expected_trade_date(date(2026,11,1),cal)==date(2026,10,30)
