"""Live validation for the public KAP capital/share-count provider."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.kap_capital import KapCapitalProvider

TARGETS=["THYAO","INFO","MARTI"]


def main():
    p=KapCapitalProvider()
    mapping=p.company_mapping()
    print(f"KAP_CAPITAL_MAPPING_OK count={len(mapping)}")
    failed=[]
    for ticker in TARGETS:
        out=p.capital_for_ticker(ticker,mapping)
        print("KAP_CAPITAL_RESULT",out)
        if out.get("status")!="ACTIVE" or not out.get("total_shares"):
            failed.append(ticker)
    if failed:
        raise SystemExit("KAP_CAPITAL_VALIDATION_FAILED "+",".join(failed))
    print("KAP_CAPITAL_VALIDATION_OK")


if __name__=="__main__":
    main()
