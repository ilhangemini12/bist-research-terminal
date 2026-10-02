from __future__ import annotations

from .fundamental import safe_div


def compute_extended_valuation(
    *,
    market_cap: float | None,
    latest_financial_period: str | None,
    equity: float | None,
    cash: float | None,
    operating_profit_ttm: float | None,
    revenue_ttm: float | None,
    cash_from_operations_ttm: float | None,
    extended: dict | None,
) -> dict:
    ext=extended or {}
    if not ext:
        return {"extended_valuation_status":"UNAVAILABLE"}
    if not latest_financial_period or ext.get("report_period") != latest_financial_period:
        return {
            "extended_valuation_status":"PERIOD_MISMATCH",
            "extended_metrics_basis":ext.get("basis"),
        }

    debt=ext.get("financial_debt") if ext.get("debt_components_complete") else None
    da=ext.get("depreciation_amortization_ttm")
    capex=ext.get("capex_spend_ttm")

    net_debt=(debt-cash) if debt is not None and cash is not None else None
    ebitda=(operating_profit_ttm+da) if operating_profit_ttm is not None and da is not None else None
    fcf=(cash_from_operations_ttm-capex) if cash_from_operations_ttm is not None and capex is not None else None
    ev=(market_cap+net_debt) if market_cap is not None and net_debt is not None else None

    positive_ebitda=ebitda if ebitda is not None and ebitda>0 else None
    return {
        "extended_valuation_status":"ACTIVE" if any(v is not None for v in (net_debt,ebitda,fcf,ev)) else "INSUFFICIENT_INPUTS",
        "extended_metrics_basis":ext.get("basis"),
        "financial_debt":debt,
        "financial_debt_basis":"KAP_BORROWINGS_PARENT_TOTALS_EXCL_SEPARATE_LEASE_LIABILITIES" if debt is not None else None,
        "net_debt":net_debt,
        "depreciation_amortization_ttm":da,
        "capex_ttm":capex,
        "ebitda_ttm":ebitda,
        "ebitda_basis":"OPERATING_PROFIT_PLUS_KAP_CASH_FLOW_DA_ADJUSTMENT" if ebitda is not None else None,
        "fcf_ttm":fcf,
        "fcf_basis":"CASH_FROM_OPERATIONS_MINUS_KAP_CAPEX_CASH_OUTFLOW" if fcf is not None else None,
        "ev":ev,
        "ev_ebitda":safe_div(ev,positive_ebitda),
        "ev_sales":safe_div(ev,revenue_ttm),
        "net_debt_ebitda":safe_div(net_debt,positive_ebitda),
        "debt_equity":safe_div(debt,equity),
        "ebitda_margin":safe_div(ebitda,revenue_ttm),
        "fcf_yield":safe_div(fcf,market_cap),
    }
