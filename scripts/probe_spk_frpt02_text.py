"""One-off coverage probe: map SPK FRPT02 report metadata to the current BIST universe.

No PDFs are downloaded. Matching is deliberately conservative; ambiguous or
low-score company-name matches are reported as unmatched.
"""
from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from bist_terminal.providers.spk import SPKRegistryProvider
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices

LEGAL_TERMS={
    "ANONIM","SIRKETI","SIRKET","A","S","AS","AŞ","AO","ORTAKLIGI","ORTAKLIGI",
    "VE","TICARET","SANAYI","SAN","TIC","YATIRIM","HOLDING",
}

def fold(s:str)->str:
    s=(s or "").upper().replace("İ","I").replace("İ","I")
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=re.sub(r"[^A-Z0-9 ]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def compact_company(s:str)->str:
    toks=[t for t in fold(s).split() if t not in LEGAL_TERMS]
    return " ".join(toks)

def score(a:str,b:str)->float:
    a=compact_company(a); b=compact_company(b)
    if not a or not b:
        return 0.0
    seq=SequenceMatcher(None,a,b).ratio()
    at=set(a.split()); bt=set(b.split())
    jac=len(at&bt)/max(1,len(at|bt))
    contain=0.98 if (len(a)>=6 and len(b)>=6 and (a in b or b in a)) else 0.0
    return max(seq, jac, contain)

def main():
    indices=enabled_indices(ROOT/"config/indices.yaml")
    universe=BistIndexUniverseProvider(cache_dir=ROOT/"data/cache/bist_universe").get_components(indices)
    companies={}
    for members in universe.members.values():
        for row in members:
            companies[row["symbol"]]=row.get("name") or row["symbol"]
    spk=SPKRegistryProvider()
    reports=spk.financial_reports(
        subject="FRPT02",
        dateBegin="2024-01-01",
        dateEnd=date.today().isoformat(),
    )
    if not isinstance(reports,list):
        raise RuntimeError(f"unexpected SPK financial_reports type {type(reports).__name__}")
    unique_titles=sorted({(r.get("companyTitle") or "").strip() for r in reports if r.get("companyTitle")})
    matched=[]
    ambiguous=[]
    unmatched=[]
    for title in unique_titles:
        ranked=sorted(
            ((score(title,name),ticker,name) for ticker,name in companies.items()),
            reverse=True,
        )
        best=ranked[0] if ranked else (0.0,"","")
        second=ranked[1] if len(ranked)>1 else (0.0,"","")
        margin=best[0]-second[0]
        row=(title,best[1],best[2],round(best[0],4),round(margin,4))
        if best[0]>=0.90 and margin>=0.05:
            matched.append(row)
        elif best[0]>=0.82:
            ambiguous.append(row)
        else:
            unmatched.append(row)
    report_rows=sum(1 for r in reports if any(m[0]==(r.get("companyTitle") or "").strip() for m in matched))
    print("SPK_BIST_COVERAGE_PROBE_OK")
    print(f"SPK_BIST_COVERAGE reports={len(reports)} unique_titles={len(unique_titles)} bist_tickers={len(companies)}")
    print(f"SPK_BIST_COVERAGE matched_titles={len(matched)} ambiguous_titles={len(ambiguous)} unmatched_titles={len(unmatched)} matched_report_rows={report_rows}")
    for row in matched[:60]:
        print(f"SPK_BIST_MATCH title={row[0]} ticker={row[1]} bist_name={row[2]} score={row[3]} margin={row[4]}")
    for row in ambiguous[:25]:
        print(f"SPK_BIST_AMBIGUOUS title={row[0]} ticker={row[1]} bist_name={row[2]} score={row[3]} margin={row[4]}")

if __name__=="__main__":
    main()
