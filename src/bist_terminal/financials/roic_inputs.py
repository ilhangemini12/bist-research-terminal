from __future__ import annotations

from io import BytesIO

import pandas as pd

from .kap_bulk import _clean, _fold, _period_columns, parse_tr_number, presentation_scale

PRETAX_LABELS={
    "SURDURULEN FAALIYETLER VERGI ONCESI KARI (ZARARI)",
}
TAX_LABELS={
    "SURDURULEN FAALIYETLER VERGI (GIDERI) GELIRI",
}


def parse_roic_tax_inputs(payload: bytes) -> dict:
    """Parse exact KAP pretax-profit and tax expense/income YTD rows.

    Values are signed exactly as published. A tax expense is generally negative
    in KAP statements; conversion to a positive effective-tax rate is done
    downstream with explicit guards.
    """
    tables=pd.read_html(BytesIO(payload),header=None)
    if not tables:
        raise ValueError("KAP workbook contains no HTML tables")

    currency="UNKNOWN"; scale=1.0
    if tables[0].shape[1]>=2:
        for _,row in tables[0].iterrows():
            if _fold(row.iloc[0])=="SUNUM PARA BIRIMI":
                currency,scale=presentation_scale(_clean(row.iloc[1]))

    current_period=None
    pretax=None; tax=None
    observed=[]
    for df in tables:
        cols=_period_columns(df)
        if not cols or cols.get("current_col") is None:
            continue
        cur=cols["current_col"]
        for _,row in df.iterrows():
            vals=row.tolist()
            label=""
            if len(vals)>1 and _clean(vals[1]):
                label=_fold(vals[1])
            elif vals:
                label=_fold(vals[0])
            if label in PRETAX_LABELS and "pretax_profit_ytd" not in observed:
                raw=vals[cur] if cur<len(vals) else None
                v=parse_tr_number(raw)
                pretax=v*scale if v is not None else None
                observed.append("pretax_profit_ytd")
                current_period=current_period or cols.get("current_period")
            elif label in TAX_LABELS and "tax_expense_income_ytd" not in observed:
                raw=vals[cur] if cur<len(vals) else None
                v=parse_tr_number(raw)
                tax=v*scale if v is not None else None
                observed.append("tax_expense_income_ytd")
                current_period=current_period or cols.get("current_period")
    return {
        "currency":currency,
        "scale":scale,
        "current_period":current_period,
        "pretax_profit_ytd":pretax,
        "tax_expense_income_ytd":tax,
        "observed_metrics":sorted(observed),
    }


def effective_tax_rate(pretax_profit_ttm: float|None, tax_expense_income_ttm: float|None) -> float|None:
    if pretax_profit_ttm is None or tax_expense_income_ttm is None or pretax_profit_ttm<=0:
        return None
    rate=-tax_expense_income_ttm/pretax_profit_ttm
    return rate if 0 <= rate <= 1 else None


def compute_roic(
    operating_profit_ttm: float|None,
    effective_tax_rate_value: float|None,
    average_invested_capital: float|None,
) -> float|None:
    if operating_profit_ttm is None or effective_tax_rate_value is None:
        return None
    if average_invested_capital is None or average_invested_capital<=0:
        return None
    nopat=operating_profit_ttm*(1-effective_tax_rate_value)
    return nopat/average_invested_capital
