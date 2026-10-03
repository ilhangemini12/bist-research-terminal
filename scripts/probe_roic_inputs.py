"""Bounded ROIC input feasibility probe against KAP 2026 H1."""
from pathlib import Path
from io import BytesIO
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, _clean, _fold
from bist_terminal.financials.roic_inputs import parse_roic_tax_inputs

SAMPLE=("THYAO","ASELS","FROTO","EREGL","SISE","TUPRS","PETKM","ARCLK","KCHOL","BIMAS")


def candidate_ebit_labels(payload: bytes) -> list[str]:
    labels=set()
    for df in pd.read_html(BytesIO(payload),header=None):
        for _,row in df.iterrows():
            vals=row.tolist()
            label=""
            if len(vals)>1 and _clean(vals[1]):
                label=_clean(vals[1])
            elif vals:
                label=_clean(vals[0])
            folded=_fold(label)
            if "FINANSMAN" in folded and "FAALIYET" in folded and "KAR" in folded:
                labels.add(label)
    return sorted(labels)


def main():
    arc=KapBulkFinancialProvider().download_archive(2026,"2")
    ok=0; missing=0; partial=0
    label_counts={}
    for ticker in SAMPLE:
        name=arc.entry_for_ticker(ticker)
        if not name:
            missing+=1
            print(f"ROIC_PROBE_MISSING ticker={ticker}")
            continue
        raw=arc.zip.read(name)
        out=parse_roic_tax_inputs(raw)
        labels=candidate_ebit_labels(raw)
        for label in labels:
            label_counts[label]=label_counts.get(label,0)+1
        complete=out.get("pretax_profit_ytd") is not None and out.get("tax_expense_income_ytd") is not None
        ok+=int(complete); partial+=int(not complete)
        print(
            f"ROIC_PROBE ticker={ticker} complete={complete} period={out.get('current_period')} "
            f"pretax={out.get('pretax_profit_ytd')} tax={out.get('tax_expense_income_ytd')} "
            f"ebit_candidates={labels} observed={out.get('observed_metrics')} source={name}"
        )
    print(f"ROIC_EBIT_LABEL_COUNTS {label_counts}")
    print(f"ROIC_PROBE_DONE sample={len(SAMPLE)} complete={ok} partial={partial} missing={missing}")

if __name__=="__main__":
    main()
