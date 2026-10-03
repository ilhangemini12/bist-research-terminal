from __future__ import annotations

from io import BytesIO

import pandas as pd

from .kap_bulk import _clean, _fold, _period_columns, parse_tr_number, presentation_scale

EBIT_LABELS={
    "FINANSMAN GELIRI (GIDERI) ONCESI FAALIYET KARI (ZARARI)",
}
PRETAX_LABELS={
    "SURDURULEN FAALIYETLER VERGI ONCESI KARI (ZARARI)",
}
TAX_LABELS={
    "SURDURULEN FAALIYETLER VERGI (GIDERI) GELIRI",
}


def parse_roic_inputs(payload: bytes) -> dict:
    """Parse exact KAP EBIT, pretax-profit and tax expense/income YTD rows.

    Only exact labels validated against live KAP HTML-XLS exports are accepted.
    Values preserve KAP's published sign. Negative tax is treated downstream as
    an expense; tax benefits or implausible effective rates are rejected.
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
    values={
        "ebit_ytd":None,
        "pretax_profit_ytd":None,
        "tax_expense_income_ytd":None,
    }
    observed=[]
    label_map={}
    for label in EBIT_LABELS:
        label_map[label]="ebit_ytd"
    for label in PRETAX_LABELS:
        label_map[label]="pretax_profit_ytd"
    for label in TAX_LABELS:
        label_map[label]="tax_expense_income_ytd"

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
            metric=label_map.get(label)
            if not metric or metric in observed:
                continue
            raw=vals[cur] if cur<len(vals) else None
            v=parse_tr_number(raw)
            values[metric]=v*scale if v is not None else None
            observed.append(metric)
            current_period=current_period or cols.get("current_period")

    return {
        "currency":currency,
        "scale":scale,
        "current_period":current_period,
        **values,
        "observed_metrics":sorted(observed),
    }


# Backwards-compatible name used by the earlier bounded probe/tests.
def parse_roic_tax_inputs(payload: bytes) -> dict:
    return parse_roic_inputs(payload)


def ttm_from_ytd_bridge(fy: float|None, current_ytd: float|None, prior_ytd: float|None) -> float|None:
    if fy is None or current_ytd is None or prior_ytd is None:
        return None
    return fy+current_ytd-prior_ytd


def effective_tax_rate(pretax_profit_ttm: float|None, tax_expense_income_ttm: float|None) -> float|None:
    if pretax_profit_ttm is None or tax_expense_income_ttm is None or pretax_profit_ttm<=0:
        return None
    rate=-tax_expense_income_ttm/pretax_profit_ttm
    return rate if 0 <= rate <= 1 else None


def derive_roic_ttm(records: list[dict], current_year: int) -> dict:
    """Derive exact-label EBIT/pretax/tax TTM from immutable KAP checkpoints."""
    by={}
    for rec in records:
        try:
            key=(int(rec.get("archive_year")),int(rec.get("archive_period")))
        except (TypeError,ValueError):
            continue
        by[key]=rec

    current_periods=sorted(p for (y,p) in by if y==int(current_year))
    if not current_periods:
        return {"status":"UNAVAILABLE"}
    p=current_periods[-1]
    cur=by[(int(current_year),p)]
    if p==4:
        ebit=cur.get("ebit_ytd")
        pretax=cur.get("pretax_profit_ytd")
        tax=cur.get("tax_expense_income_ytd")
        basis=f"{current_year}FY"
    else:
        prev_fy=by.get((int(current_year)-1,4),{})
        prev_ytd=by.get((int(current_year)-1,p),{})
        ebit=ttm_from_ytd_bridge(prev_fy.get("ebit_ytd"),cur.get("ebit_ytd"),prev_ytd.get("ebit_ytd"))
        pretax=ttm_from_ytd_bridge(prev_fy.get("pretax_profit_ytd"),cur.get("pretax_profit_ytd"),prev_ytd.get("pretax_profit_ytd"))
        tax=ttm_from_ytd_bridge(prev_fy.get("tax_expense_income_ytd"),cur.get("tax_expense_income_ytd"),prev_ytd.get("tax_expense_income_ytd"))
        basis=f"{current_year-1}FY+{current_year}P{p}-{current_year-1}P{p}"

    rate=effective_tax_rate(pretax,tax)
    complete=ebit is not None and pretax is not None and tax is not None and rate is not None
    return {
        "status":"ACTIVE" if complete else "INSUFFICIENT_INPUTS",
        "archive_year":int(current_year),
        "archive_period":p,
        "report_period":cur.get("report_period") or cur.get("current_period"),
        "ebit_ttm":ebit,
        "pretax_profit_ttm":pretax,
        "tax_expense_income_ttm":tax,
        "effective_tax_rate":rate,
        "basis":basis,
    }


def invested_capital(equity: float|None, financial_debt: float|None, cash: float|None) -> float|None:
    if equity is None or financial_debt is None or cash is None:
        return None
    value=equity+financial_debt-cash
    return value if value>0 else None


def derive_average_invested_capital(
    financial_records: list[dict],
    extended_records: list[dict],
    current_year: int,
    current_period: int,
) -> dict:
    """Average current/prior-year same-period invested capital.

    Requires high-confidence KAP equity/cash and complete exact-label borrowing
    totals for both periods. No missing component is inferred.
    """
    fin_by={}
    for rec in financial_records:
        payload=rec.get("payload") or {}
        if payload.get("status")!="PARSED_HIGH_CONFIDENCE":
            continue
        try:
            key=(int(payload.get("archive_year")),int(payload.get("archive_period")))
        except (TypeError,ValueError):
            continue
        fin_by[key]=rec

    ext_by={}
    for rec in extended_records:
        try:
            key=(int(rec.get("archive_year")),int(rec.get("archive_period")))
        except (TypeError,ValueError):
            continue
        if rec.get("debt_components_complete") and rec.get("financial_debt") is not None:
            ext_by[key]=rec

    capitals=[]
    periods=[]
    for year in (int(current_year)-1,int(current_year)):
        key=(year,int(current_period))
        fin=fin_by.get(key)
        ext=ext_by.get(key)
        if not fin or not ext:
            return {"status":"INSUFFICIENT_INPUTS","missing_period":f"{year}P{current_period}"}
        payload=fin.get("payload") or {}
        facts=payload.get("facts") or {}
        fin_period=rec_period=fin.get("report_period") or payload.get("current_period")
        ext_period=ext.get("report_period") or ext.get("current_period")
        if fin_period and ext_period and fin_period!=ext_period:
            return {"status":"PERIOD_MISMATCH","financial_period":fin_period,"extended_period":ext_period}
        cap=invested_capital(facts.get("equity"),ext.get("financial_debt"),facts.get("cash"))
        if cap is None:
            return {"status":"INSUFFICIENT_INPUTS","missing_period":f"{year}P{current_period}"}
        capitals.append(cap)
        periods.append(fin_period)

    avg=sum(capitals)/2
    return {
        "status":"ACTIVE",
        "average_invested_capital":avg,
        "prior_invested_capital":capitals[0],
        "current_invested_capital":capitals[1],
        "periods":periods,
        "basis":f"AVG_{current_year-1}P{current_period}_{current_year}P{current_period}",
    }


def compute_roic(
    ebit_ttm: float|None,
    effective_tax_rate_value: float|None,
    average_invested_capital: float|None,
) -> float|None:
    if ebit_ttm is None or effective_tax_rate_value is None:
        return None
    if average_invested_capital is None or average_invested_capital<=0:
        return None
    nopat=ebit_ttm*(1-effective_tax_rate_value)
    return nopat/average_invested_capital
