from __future__ import annotations

import math
from statistics import mean, median, pstdev


def sector_stats(values: list[float | None]) -> dict:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"mean": None, "median": None, "count": 0}
    return {"mean": mean(clean), "median": median(clean), "count": len(clean)}


def percentile_rank(value: float | None, peers: list[float | None]) -> float | None:
    if value is None:
        return None
    clean = sorted(float(v) for v in peers if v is not None and math.isfinite(float(v)))
    if not clean:
        return None
    below = sum(v < value for v in clean)
    equal = sum(v == value for v in clean)
    return (below + 0.5 * equal) / len(clean)


def zscore(value: float | None, peers: list[float | None]) -> float | None:
    if value is None:
        return None
    clean = [float(v) for v in peers if v is not None and math.isfinite(float(v))]
    if len(clean) < 2:
        return None
    sd = pstdev(clean)
    return None if sd == 0 else (value - mean(clean)) / sd


def discount_to_median(value: float | None, sector_median: float | None) -> float | None:
    """Positive means cheaper/lower than sector median for valuation multiples."""
    if value is None or sector_median in (None, 0):
        return None
    return 1 - value / sector_median
