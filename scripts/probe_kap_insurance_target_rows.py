"""Targeted insurance statement rows for production mapping."""
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, _clean

def main():
    arc=KapBulkFinancialProvider().download_archive(2025,"4")
    name=arc.entry_for_ticker("AGESA")
    tables=pd.read_html(arc.zip.read(name),header=None)
    for ti,ranges in [(1,[(456,552)]),(279,[(220,277)]),(457,[(60,75)])]:
        df=tables[ti]
        print(f"INS_TARGET_TABLE table={ti} shape={df.shape}")
        for a,b in ranges:
            for ri in range(a,min(b+1,len(df))):
                vals=[_clean(v) for v in df.iloc[ri].tolist()]
                if any(vals):
                    print(f"INS_TARGET_ROW table={ti} row={ri} :: {' | '.join(v for v in vals if v)[:1600]}")
if __name__=="__main__": main()
