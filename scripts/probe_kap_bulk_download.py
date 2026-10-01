"""Discover KAP public financial-table period codes from first-party UI config.

This probe fetches only the public KAP page and its own static JS. It does not call
financial data/download endpoints.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import html,re,requests

PAGE="https://www.kap.org.tr/tr"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; bounded endpoint discovery)"}

def snippets(text, needles, before=1200, after=2200, max_hits=30):
    out=[]; seen=set()
    for needle in needles:
        start=0
        while len(out)<max_hits:
            pos=text.lower().find(needle.lower(),start)
            if pos<0: break
            ctx=text[max(0,pos-before):min(len(text),pos+after)].replace("\n"," ")
            key=ctx[:500]
            if key not in seen:
                seen.add(key); out.append((needle,pos,ctx))
            start=pos+len(needle)
    return out

def main():
    s=requests.Session(); r=s.get(PAGE,timeout=30,headers=UA); r.raise_for_status()
    page=r.text
    print(f"KAP_PERIOD_PAGE status={r.status_code} bytes={len(r.content)}")
    page_hits=snippets(page,[
        "homeFinancialConstants","financialReport","period","periods",
        "3 Aylık","6 Aylık","9 Aylık","Yıllık","Tüm"
    ],before=700,after=1400,max_hits=15)
    for needle,pos,ctx in page_hits:
        print(f"KAP_PERIOD_PAGE_HIT needle={needle} pos={pos}")
        print("KAP_PERIOD_PAGE_CODE",html.unescape(ctx))

    soup=BeautifulSoup(page,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        u=urljoin(r.url,tag["src"])
        if urlparse(u).netloc.endswith("kap.org.tr") and u not in scripts:
            scripts.append(u)
    emitted=0; total=0
    for u in scripts[:25]:
        rr=s.get(u,timeout=30,headers=UA); total+=len(rr.content)
        if rr.status_code!=200: continue
        txt=rr.text
        # Focus on the home-financial component/config only.
        if not any(n in txt for n in ("homeFinancialConstants","DOWNLOAD_FINANCIAL_TABLE","warnCompanyChoiseForAllPeriod")):
            continue
        for needle,pos,ctx in snippets(txt,[
            "homeFinancialConstants","defaults?.period","defaults:{",
            "periods","periodList","M?.code","warnCompanyChoiseForAllPeriod"
        ],before=1800,after=4200,max_hits=20):
            emitted+=1
            print(f"KAP_PERIOD_JS_HIT hit={emitted} needle={needle} bundle={u} pos={pos}")
            print("KAP_PERIOD_JS_CODE",ctx)
            if emitted>=20: break
        if emitted>=20: break
    print(f"KAP_PERIOD_DONE page_hits={len(page_hits)} js_hits={emitted} total_bytes={total}")
    if not page_hits and not emitted:
        raise RuntimeError("period configuration not found")

if __name__=="__main__":
    main()
