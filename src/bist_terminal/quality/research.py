from __future__ import annotations
from datetime import date


def target_price_freshness(report_date: str, as_of: str, threshold_days: int = 90) -> str:
    report = date.fromisoformat(report_date); current = date.fromisoformat(as_of)
    age = (current - report).days
    if age < 0:
        return "FUTURE_DATE_ERROR"
    return "CURRENT" if age <= threshold_days else "ARCHIVE"
