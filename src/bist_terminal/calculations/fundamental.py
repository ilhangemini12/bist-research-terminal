from __future__ import annotations

from math import isfinite


def safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    try:
        out = a / b
        return out if isfinite(float(out)) else None
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def calc_ratios(d: dict) -> dict:
    price = d.get("price")
    shares = d.get("shares")
    debt = d.get("financial_debt") or 0
    cash = d.get("cash") or 0
    market_cap = price * shares if price is not None and shares is not None else None
    ev = market_cap + debt - cash if market_cap is not None else None
    net_debt = debt - cash

    ni = d.get("net_income_ttm")
    eq = d.get("equity")
    assets = d.get("assets")
    revenue = d.get("revenue_ttm")
    gross_profit = d.get("gross_profit_ttm")
    ebit = d.get("ebit_ttm") or d.get("operating_profit_ttm")
    ebitda = d.get("ebitda_ttm")
    fcf = d.get("fcf_ttm")
    current_assets = d.get("current_assets")
    inventories = d.get("inventories")
    current_liabilities = d.get("current_liabilities")
    dividends = d.get("dividends_ttm")
    tax_rate = d.get("effective_tax_rate")
    invested_capital = d.get("invested_capital")

    # ROIC is only emitted when its required inputs exist. We do not infer a tax
    # rate or invested capital from incomplete balance sheets.
    nopat = None
    if ebit is not None and tax_rate is not None:
        nopat = ebit * (1 - tax_rate)

    quick_assets = None
    if current_assets is not None:
        quick_assets = current_assets - (inventories or 0)

    return {
        "market_cap": market_cap,
        "ev": ev,
        "pe": safe_div(market_cap, ni),
        "pb": safe_div(market_cap, eq),
        "ev_ebitda": safe_div(ev, ebitda),
        "ev_sales": safe_div(ev, revenue),
        "psales": safe_div(market_cap, revenue),
        "eps": safe_div(ni, shares),
        "bvps": safe_div(eq, shares),
        "roe": safe_div(ni, eq),
        "roa": safe_div(ni, assets),
        "roic": safe_div(nopat, invested_capital),
        "gross_margin": safe_div(gross_profit, revenue),
        "ebitda_margin": safe_div(ebitda, revenue),
        "operating_margin": safe_div(ebit, revenue),
        "net_margin": safe_div(ni, revenue),
        "net_debt": net_debt,
        "net_debt_ebitda": safe_div(net_debt, ebitda),
        "debt_equity": safe_div(debt, eq),
        "current_ratio": safe_div(current_assets, current_liabilities),
        "quick_ratio": safe_div(quick_assets, current_liabilities),
        "dividend_yield": safe_div(dividends, market_cap),
        "payout_ratio": safe_div(dividends, ni),
        "fcf_yield": safe_div(fcf, market_cap),
    }


def ttm(values: list[float | None]) -> float | None:
    v = [x for x in values[-4:] if x is not None]
    return sum(v) if len(v) == 4 else None
