"""Bounded static-code probe for KAP public financial-download UI call sites.

Fetches only first-party static JS bundles and searches for *usages* of the exported
financial-download route constants and related parameter names. No KAP data endpoint
is invoked here.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import requests

PAGE="https://www.kap.org.tr/tr"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; bounded endpoint discovery)"}
NEEDLES=[
    "DOWNLOAD_FINANCIAL_TABLE",
    "GET_HOME_FINANCIAL_CHECK_FILE_EXIST",
    "GET_HOME_FINANCIAL_DOWNLOAD",
    "GET_HOME_FINANCIAL_LIST_EXCEL_MEMBERS",
    "checkFileExist",
    "download-file",
    "listCompanyExcelMembers",
    "financialTable/download",
]
PARAM_NEEDLES=[
    "year","period","periodType","term","member","memberIds","company","companyId",
    "language","lang","consolidated","financialTable"
]
MAX_TOTAL=8_000_000

def bounded_context(text:str,pos:int,before:int=2600,after:int=4200)->str:
    return text[max(0,pos-before):min(len(text),pos+after)].replace("\n"," ")

def main():
    s=requests.Session()
    r=s.get(PAGE,timeout=30,headers=UA); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        u=urljoin(r.url,tag["src"])
        if urlparse(u).netloc.endswith("kap.org.tr") and u not in scripts:
            scripts.append(u)
    print(f"KAP_CALLSITE_SCRIPTS count={len(scripts)}")
    total=0
    emitted=0
    declaration_bundle=None
    for u in scripts[:25]:
        rr=s.get(u,timeout=30,headers=UA)
        total+=len(rr.content)
        if rr.status_code!=200:
            continue
        txt=rr.text
        if '"DOWNLOAD_FINANCIAL_TABLE"' in txt and '"api/financialTable/download"' in txt:
            declaration_bundle=u
        positions=[]
        for needle in NEEDLES:
            start=0
            while True:
                pos=txt.find(needle,start)
                if pos<0: break
                positions.append((pos,needle))
                start=pos+len(needle)
        # Emit only likely call sites; skip the pure route-declaration module unless
        # the same bundle has additional references away from the declaration.
        for pos,needle in sorted(set(positions)):
            ctx=bounded_context(txt,pos)
            low=ctx.lower()
            score=sum(1 for k in ("fetch(","axios","method:","params:","body:","post(","get(","request","query") if k in low)
            param_hits=[p for p in PARAM_NEEDLES if p.lower() in low]
            is_decl = '"api/financialtable/download"' in low and 'e.s(["download_financial_table"' in low
            if is_decl and score==0:
                continue
            if score==0 and len(param_hits)<2:
                continue
            emitted+=1
            print(f"KAP_CALLSITE hit={emitted} needle={needle} bundle={u} pos={pos} score={score} params={param_hits}")
            print("KAP_CALLSITE_CODE",ctx)
            if emitted>=24:
                break
        if emitted>=24 or total>=MAX_TOTAL:
            break
    print(f"KAP_CALLSITE_DONE emitted={emitted} total_bytes={total} declaration_bundle={declaration_bundle}")
    if emitted==0:
        raise RuntimeError("no likely KAP financial download call sites found")

if __name__=="__main__":
    main()
