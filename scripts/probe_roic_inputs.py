"""Bounded ROIC tax-input feasibility probe against KAP 2026 H1."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.financials.roic_inputs import parse_roic_tax_inputs

SAMPLE=("THYAO","ASELS","FROTO","EREGL","SISE","TUPRS","PETKM","ARCLK","KCHOL","BIMAS")


def main():
    arc=KapBulkFinancialProvider().download_archive(2026,"2")
    ok=0; missing=0; partial=0
    for ticker in SAMPLE:
        name=arc.entry_for_ticker(ticker)
        if not name:
            missing+=1
            print(f"ROIC_PROBE_MISSING ticker={ticker}")
            continue
        out=parse_roic_tax_inputs(arc.zip.read(name))
        complete=out.get("pretax_profit_ytd") is not None and out.get("tax_expense_income_ytd") is not None
        ok+=int(complete); partial+=int(not complete)
        print(
            f"ROIC_PROBE ticker={ticker} complete={complete} period={out.get('current_period')} "
            f"pretax={out.get('pretax_profit_ytd')} tax={out.get('tax_expense_income_ytd')} "
            f"observed={out.get('observed_metrics')} source={name}"
        )
    print(f"ROIC_PROBE_DONE sample={len(SAMPLE)} complete={ok} partial={partial} missing={missing}")

if __name__=="__main__":
    main()
