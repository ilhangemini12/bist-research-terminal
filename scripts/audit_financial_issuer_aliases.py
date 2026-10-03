"""Audit missing financial tickers for exact same-issuer sibling matches."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json, sys, unicodedata, re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.storage.capital_files import load_capital_records
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files


def norm(s):
    t=str(s or "").upper().replace("İ","I")
    t=unicodedata.normalize("NFKD",t)
    t="".join(ch for ch in t if not unicodedata.combining(ch))
    t=re.sub(r"[^A-Z0-9]+"," ",t)
    return re.sub(r"\s+"," ",t).strip()


def main():
    caps=load_capital_records(ROOT)
    store=DuckDBStore(ROOT/'data/bist.duckdb')
    try:
        for p in financial_parquet_files(ROOT):
            store.import_parquet('financials',p)
        latest=store.latest_financial_payloads()
        by_title=defaultdict(list)
        for ticker,rec in caps.items():
            key=norm(rec.get('company_title'))
            if key:
                by_title[key].append(ticker)

        rows=[]
        for ticker,rec in sorted(caps.items()):
            fin=latest.get(ticker) or {}
            payload=fin.get('payload') or {}
            if payload.get('status')=='PARSED_HIGH_CONFIDENCE':
                continue
            title=norm(rec.get('company_title'))
            siblings=[t for t in by_title.get(title,[]) if t!=ticker]
            donors=[]
            for sib in siblings:
                sfin=latest.get(sib) or {}
                sp=(sfin.get('payload') or {})
                if sp.get('status')=='PARSED_HIGH_CONFIDENCE':
                    donors.append({
                        'ticker':sib,
                        'report_period':sfin.get('report_period'),
                        'quality_score':sp.get('quality_score'),
                        'source_file':sp.get('source_file'),
                    })
            rows.append({
                'ticker':ticker,
                'company_title':rec.get('company_title'),
                'current_financial_status':payload.get('status'),
                'exact_title_siblings':siblings,
                'high_confidence_donors':donors,
            })
        out={'missing_or_review_count':len(rows),'rows':rows}
        (ROOT/'artifacts').mkdir(exist_ok=True)
        (ROOT/'artifacts/financial_issuer_alias_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(out,ensure_ascii=False,indent=2))
    finally:
        store.close()

if __name__=='__main__':
    main()
