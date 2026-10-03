"""Create conservative same-issuer financial overlays for share classes.

Only copies high-confidence donor rows when:
1) recipient and donor have the exact same normalized KAP company title, and
2) the donor KAP source filename explicitly contains the recipient ticker token.
This prevents generic title-based inference.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, re, sys, unicodedata
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.storage.capital_files import load_capital_records
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files

RECIPIENTS={"KRDMA":"KRDMD","KRDMB":"KRDMD"}

def norm(s):
    t=str(s or "").upper().replace("İ","I")
    t=unicodedata.normalize("NFKD",t)
    t="".join(ch for ch in t if not unicodedata.combining(ch))
    t=re.sub(r"[^A-Z0-9]+"," ",t)
    return re.sub(r"\s+"," ",t).strip()

def source_names_recipient(source_file:str|None, recipient:str)->bool:
    base=Path(str(source_file or "")).name.upper()
    return bool(re.search(rf"(^|[-_]){re.escape(recipient)}([-_]|$)",base))

def main():
    out=ROOT/'data/parquet/financials/financials_repair_share_classes_v001.parquet'
    if out.exists():
        print(f"SHARE_CLASS_REPAIR_EXISTS file={out.name}")
        return

    caps=load_capital_records(ROOT)
    store=DuckDBStore(ROOT/'data/bist.duckdb')
    try:
        for p in financial_parquet_files(ROOT):
            store.import_parquet('financials',p)
        rows=[]
        stamp=datetime.now(timezone.utc).isoformat()
        for recipient,donor in RECIPIENTS.items():
            rcap=caps.get(recipient) or {}
            dcap=caps.get(donor) or {}
            if not rcap or not dcap or norm(rcap.get('company_title'))!=norm(dcap.get('company_title')):
                raise RuntimeError(f"issuer-title mismatch {recipient} <- {donor}")
            donor_rows=store.con.execute(
                "select report_period, publication_date, statement_scope, payload, source_url from financials where ticker=? order by report_period",
                [donor],
            ).fetchall()
            copied=0
            for report_period,publication_date,scope,payload,source_url in donor_rows:
                p=json.loads(payload) if isinstance(payload,str) else (payload or {})
                if p.get('status')!='PARSED_HIGH_CONFIDENCE':
                    continue
                source_file=p.get('source_file')
                if not source_names_recipient(source_file,recipient):
                    continue
                newp=dict(p)
                newp.update({
                    'ticker':recipient,
                    'repair_overlay':'same_issuer_share_class',
                    'repair_donor_ticker':donor,
                    'repair_evidence':'exact_company_title_and_source_filename_contains_recipient',
                    'repair_retrieved_at':stamp,
                })
                rows.append({
                    'ticker':recipient,
                    'report_period':str(report_period),
                    'publication_date':str(publication_date) if publication_date else None,
                    'statement_scope':scope,
                    'payload':json.dumps(newp,ensure_ascii=False),
                    'source_url':source_url,
                })
                copied+=1
            print(f"SHARE_CLASS_REPAIR ticker={recipient} donor={donor} copied={copied}")
            if copied<4:
                raise RuntimeError(f"insufficient evidence rows for {recipient}: {copied}")
        out.parent.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(rows,columns=['ticker','report_period','publication_date','statement_scope','payload','source_url']).to_parquet(out,index=False)
        print(f"SHARE_CLASS_REPAIR_SHARD_WRITTEN file={out.name} rows={len(rows)}")
    finally:
        store.close()

if __name__=='__main__':
    main()
