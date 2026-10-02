from bist_terminal.calculations.extended_valuation import compute_extended_valuation


def test_extended_valuation_requires_matching_period_and_computes_metrics():
    ext={
        "report_period":"2026-06-30",
        "basis":"2025FY+2026P2-2025P2",
        "financial_debt":500,
        "debt_components_complete":True,
        "depreciation_amortization_ttm":90,
        "capex_spend_ttm":110,
    }
    out=compute_extended_valuation(
        market_cap=2000,
        latest_financial_period="2026-06-30",
        equity=1000,
        cash=200,
        operating_profit_ttm=210,
        revenue_ttm=1500,
        cash_from_operations_ttm=300,
        extended=ext,
    )
    assert out["net_debt"]==300
    assert out["ebitda_ttm"]==300
    assert out["fcf_ttm"]==190
    assert out["ev"]==2300
    assert round(out["ev_ebitda"],6)==round(2300/300,6)
    assert out["net_debt_ebitda"]==1
    assert out["fcf_yield"]==0.095


def test_extended_valuation_rejects_period_mismatch():
    out=compute_extended_valuation(
        market_cap=2000,
        latest_financial_period="2026-06-30",
        equity=1000,
        cash=200,
        operating_profit_ttm=210,
        revenue_ttm=1500,
        cash_from_operations_ttm=300,
        extended={
            "report_period":"2025-12-31",
            "basis":"2025FY_FALLBACK",
            "financial_debt":500,
            "debt_components_complete":True,
            "depreciation_amortization_ttm":90,
            "capex_spend_ttm":110,
        },
    )
    assert out["extended_valuation_status"]=="PERIOD_MISMATCH"
    assert "ev_ebitda" not in out
