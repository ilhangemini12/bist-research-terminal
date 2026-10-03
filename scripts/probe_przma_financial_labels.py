"""Bounded PRZMA income-label probe for KAP 2026 H1."""
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, _clean, _fold

KEYWORDS=("KAR","ZARAR","GELIR","SATIS","HASILAT","FAALIYET","VERGI")


def main():
    arc=KapBulkFinancialProvider().download_archive(2026,"2")
    name=arc.entry_for_ticker("PRZMA")
    print(f"PRZMA_PROBE_FILE {name}")
    if not name:
        raise SystemExit("PRZMA file missing")
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
        if hits:
            print(f"PRZMA_TABLE table={ti} shape={df.shape} hits={len(hits)}")
            for ri,vals in hits[:220]:
                print(f"PRZMA_ROW table={ti} row={ri} :: {' | '.join(v for v in vals if v)[:1400]}")

if __name__=="__main__":
    main()
