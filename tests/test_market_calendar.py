from datetime import date
import pytest

from bist_terminal.quality.market_calendar import (
    is_trading_day,
    latest_expected_trade_date,
    resolve_run_trade_date,
)


def test_holiday_and_weekend():
    cal={'closed':['2026-10-29']}
    assert not is_trading_day(date(2026,10,29),cal)
    assert latest_expected_trade_date(date(2026,11,1),cal)==date(2026,10,30)


def test_normal_weekend_run_skips_but_manual_prior_trade_date_is_allowed():
    cal={'closed':[]}
    today=date(2026,10,3)  # Saturday
    assert resolve_run_trade_date(today,cal) is None
    assert resolve_run_trade_date(today,cal,'2026-10-02')==date(2026,10,2)


def test_manual_as_of_rejects_future_weekend_and_bad_format():
    cal={'closed':[]}
    today=date(2026,10,3)
    with pytest.raises(ValueError):
        resolve_run_trade_date(today,cal,'2026-10-04')
    with pytest.raises(ValueError):
        resolve_run_trade_date(today,cal,'2026-09-27')
    with pytest.raises(ValueError):
        resolve_run_trade_date(today,cal,'2026/10/02')
