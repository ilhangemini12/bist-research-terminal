"""Compact PRZMA header/parse probe for KAP 2026 H1."""
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider, parse_html_xls, _period_columns


def main():
    arc=KapBulkFinancialProvider().download_archive(2026,"2")
    name=arc.entry_for_ticker("PRZMA")
    print(f"PRZMA_PROBE_FILE {name}")
    if not name:
        raise SystemExit("PRZMA file missing")
    raw=arc.zip.read(name)
    tables=pd.read_html(raw,header=None)
    df=tables[300]
    print(f"PRZMA_TABLE300_SHAPE {df.shape}")
    for i in range(min(8,len(df))):
        print(f"PRZMA_HEADER_ROW row={i} :: {df.iloc[i].tolist()}")
    print(f"PRZMA_PERIOD_COLUMNS {_period_columns(df)}")
    parsed=parse_html_xls(raw,name)
    print(f"PRZMA_PARSED status={parsed.get('status')} quality={parsed.get('quality_score')} current={parsed.get('current_period')} facts={parsed.get('facts')} matched={parsed.get('matched_statement_tables')}")

if __name__=="__main__":
    main()
