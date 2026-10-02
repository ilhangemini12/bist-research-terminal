from __future__ import annotations

from io import BytesIO

import pandas as pd

from .kap_bulk import _clean, _fold, _period_columns, parse_tr_number, presentation_scale

DEBT_LABELS = {
    "short_term_borrowings": "KISA VADELI BORCLANMALAR",
    "current_portion_long_term_borrowings": "UZUN VADELI BORCLANMALARIN KISA VADELI KISIMLARI",
    "long_term_borrowings": "UZUN VADELI BORCLANMALAR",
}
FLOW_LABELS = {
    "depreciation_amortization_ytd": "AMORTISMAN VE ITFA GIDERI ILE ILGILI DUZELTMELER",
    "capex_cash_outflow_ytd": "MADDI VE MADDI OLMAYAN DURAN VARLIKLARIN ALIMINDAN KAYNAKLANAN NAKIT CIKISLARI",
}
ALL_LABELS = {**DEBT_LABELS, **FLOW_LABELS}


def parse_extended_metrics(payload: bytes) -> dict:
    """Parse narrowly verified KAP debt/D&A/capex rows from one HTML-XLS statement.

    Only exact parent-total labels observed in live KAP probes are accepted.
    Child borrowings are intentionally ignored to avoid double counting.
    """
    tables = pd.read_html(BytesIO(payload), header=None)
    if not tables:
        raise ValueError("KAP workbook contains no HTML tables")

    currency = "UNKNOWN"
    scale = 1.0
    if tables[0].shape[1] >= 2:
        for _, row in tables[0].iterrows():
            if _fold(row.iloc[0]) == "SUNUM PARA BIRIMI":
                currency, scale = presentation_scale(_clean(row.iloc[1]))

    facts: dict[str, float | None] = {}
    observed: set[str] = set()
    current_period = None
    label_to_metric = {label: metric for metric, label in ALL_LABELS.items()}

    for df in tables:
        cols = _period_columns(df)
        if not cols or cols["current_col"] is None:
            continue
        cur = cols["current_col"]
        current_period = current_period or cols.get("current_period")
        for _, row in df.iterrows():
            vals = row.tolist()
            label = ""
            if len(vals) > 1 and _clean(vals[1]):
                label = _fold(vals[1])
            elif vals:
                label = _fold(vals[0])
            metric = label_to_metric.get(label)
            if not metric or metric in observed:
                continue
            observed.add(metric)
            raw = vals[cur] if cur < len(vals) else None
            value = parse_tr_number(raw)
            facts[metric] = value * scale if value is not None else None

    debt_complete = all(metric in observed for metric in DEBT_LABELS)
    financial_debt = None
    if debt_complete:
        financial_debt = sum((facts.get(metric) or 0.0) for metric in DEBT_LABELS)

    capex_raw = facts.get("capex_cash_outflow_ytd")
    capex_spend = abs(capex_raw) if capex_raw is not None else None

    return {
        "currency": currency,
        "scale": scale,
        "current_period": current_period,
        "observed_metrics": sorted(observed),
        "debt_components_complete": debt_complete,
        "short_term_borrowings": facts.get("short_term_borrowings"),
        "current_portion_long_term_borrowings": facts.get("current_portion_long_term_borrowings"),
        "long_term_borrowings": facts.get("long_term_borrowings"),
        "financial_debt": financial_debt,
        "depreciation_amortization_ytd": facts.get("depreciation_amortization_ytd"),
        "capex_cash_outflow_ytd": capex_raw,
        "capex_spend_ytd": capex_spend,
    }


def ttm_from_ytd_bridge(fy: float | None, current_ytd: float | None, prior_ytd: float | None) -> float | None:
    """TTM = prior FY + current YTD - prior-year comparable YTD."""
    if fy is None or current_ytd is None or prior_ytd is None:
        return None
    return fy + current_ytd - prior_ytd
