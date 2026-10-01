import pytest
from bist_terminal.calculations.growth import cagr, growth_rate, ttm_growth, yoy_from_quarters
from bist_terminal.calculations.sector import discount_to_median, percentile_rank, sector_stats, zscore


def test_growth_helpers():
    assert growth_rate(120, 100) == pytest.approx(0.2)
    assert round(cagr(121, 100, 2), 4) == 0.1
    assert yoy_from_quarters([100, 1, 1, 1, 120]) == pytest.approx(0.2)
    assert ttm_growth([10,10,10,10,12,12,12,12]) == pytest.approx(0.2)
    assert cagr(-1, 100, 3) is None


def test_sector_normalisation():
    s=sector_stats([10,20,30,None])
    assert s['median'] == 20 and s['mean'] == 20
    assert percentile_rank(20,[10,20,30]) == 0.5
    assert zscore(20,[10,20,30]) == 0
    assert discount_to_median(8,10) == pytest.approx(0.2)
