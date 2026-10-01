from __future__ import annotations

from math import isfinite


def growth_rate(current: float | None, prior: float | None) -> float | None:
    if current is None or prior in (None, 0):
        return None
    try:
        out = current / prior - 1
        return out if isfinite(float(out)) else None
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def cagr(end: float | None, start: float | None, years: float) -> float | None:
    """CAGR only for positive endpoints; avoids complex/meaningless growth values."""
    if end is None or start is None or years <= 0 or end <= 0 or start <= 0:
        return None
    out = (end / start) ** (1 / years) - 1
    return out if isfinite(float(out)) else None


def yoy_from_quarters(values: list[float | None]) -> float | None:
    """Compare latest quarter with the same quarter a year earlier."""
    if len(values) < 5:
        return None
    return growth_rate(values[-1], values[-5])


def ttm_growth(values: list[float | None]) -> float | None:
    """Latest four-quarter sum versus preceding four-quarter sum."""
    if len(values) < 8 or any(v is None for v in values[-8:]):
        return None
    return growth_rate(sum(values[-4:]), sum(values[-8:-4]))
