"""Probe KAP bank financial table labels for interim net-income aliases."""
from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, _fold, _clean

TICKERS=["AKBNK","GARAN","HALKB","ISCTR","SKBNK","TSKB","VAKBN","YKBNK","ALBRK","ICBCT"]
KEYWORDS=("DONEM KARI","NET DONEM","NET KAR","KAR VE ZARAR","KAR ZARAR","SURDURULEN","ANA ORTAKLIK","OZKAYNAK","AKTIF TOPLAMI")


def main():
    arc=KapBulkFinancialProvider().download_archive(2025,"3")
    print(f"BANK_PROBE_ARCHIVE files={len(arc.names)}")
    for ticker in TICKERS:
        name=arc.entry_for_ticker(ticker)
        print(f"BANK_PROBE_TICKER ticker={ticker} file={name}")
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
            if hits:
                print(f"BANK_TABLE ticker={ticker} table={ti} shape={df.shape} hits={len(hits)}")
                for ri,vals in hits[:160]:
                    print(f"BANK_ROW ticker={ticker} table={ti} row={ri} :: {' | '.join(v for v in vals if v)[:1200]}")

if __name__=="__main__":
    main()
