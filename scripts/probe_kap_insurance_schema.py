"""Probe KAP insurance financial table labels without changing production data."""
from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, _fold, _clean

TICKERS=["AGESA","AKGRT","ANHYT","ANSGR","RAYSG","TURSG"]
KEYWORDS=("OZKAYNAK","OZSERMAYE","SERMAYE","KAR","ZARAR","PRIM","TEKNIK","YUKUMLULUK","VARLIK","NAKIT","HASILAT","GELIR","GIDER")


def main():
    arc=KapBulkFinancialProvider().download_archive(2025,"4")
    print(f"INSURANCE_PROBE_ARCHIVE files={len(arc.names)}")
    for ticker in TICKERS:
        name=arc.entry_for_ticker(ticker)
        print(f"INSURANCE_PROBE_TICKER ticker={ticker} file={name}")
        if not name:
            continue
        tables=pd.read_html(arc.zip.read(name),header=None)
        for ti,df in enumerate(tables):
            if len(df)<3:
                continue
            hits=[]
            for ri,row in df.iterrows():
                vals=[_clean(v) for v in row.tolist()]
                folded=" | ".join(_fold(v) for v in vals if v)
                if any(k in folded for k in KEYWORDS):
                    hits.append((int(ri),vals))
            if not hits:
                continue
            print(f"INSURANCE_TABLE ticker={ticker} table={ti} shape={df.shape} hits={len(hits)}")
            for ri,vals in hits[:140]:
                print(f"INSURANCE_ROW ticker={ticker} table={ti} row={ri} :: {' | '.join(v for v in vals if v)[:1200]}")

if __name__=="__main__":
    main()
