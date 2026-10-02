"""Validate insurance parser against live KAP archive without mutating state."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider

TICKERS=["AGESA","AKGRT","ANHYT","ANSGR","RAYSG","TURSG"]

def main():
    arc=KapBulkFinancialProvider().download_archive(2025,"4")
    failed=[]
    for t in TICKERS:
        out=arc.parse_ticker(t)
        status=out.get("status") if out else "MISSING"
        facts=sorted((out or {}).get("facts",{}))
        print(f"INSURANCE_VALIDATE ticker={t} status={status} quality={(out or {}).get('quality_score')} facts={facts}")
        for required in ("assets","equity","net_income"):
            if not out or out.get("facts",{}).get(required) is None:
                failed.append(f"{t}:{required}")
        if status!="PARSED_HIGH_CONFIDENCE":
            failed.append(f"{t}:status={status}")
    if failed:
        raise SystemExit("INSURANCE_VALIDATE_FAILED "+",".join(failed))
    print("INSURANCE_VALIDATE_OK count=6")

if __name__=="__main__": main()
