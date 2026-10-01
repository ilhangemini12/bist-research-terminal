"""Bounded static-code probe for KAP public financial download UI.

Reads KAP's first-party page and JS bundles, then prints bounded source context
around known public-UI endpoint constants. It does not invoke financial download
endpoints and does not fetch datasets.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests

PAGE="https://www.kap.org.tr/tr"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; bounded endpoint discovery)"}
TARGETS=[
    "api/financialTable/download",
    "api/financialTable/checkFileExist",
    "api/home-financial/download-file",
    "api/financialTable/listCompanyExcelMembers",
]

def main():
    s=requests.Session()
    r=s.get(PAGE,timeout=30,headers=UA); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        u=urljoin(r.url,tag["src"])
        if urlparse(u).netloc.endswith("kap.org.tr") and u not in scripts:
            scripts.append(u)
    found=0
    total=0
    for u in scripts[:20]:
        rr=s.get(u,timeout=30,headers=UA)
        total+=len(rr.content)
        if rr.status_code!=200:
            continue
        txt=rr.text
        for target in TARGETS:
            pos=txt.find(target)
            if pos<0:
                continue
            found+=1
            lo=max(0,pos-2200); hi=min(len(txt),pos+3500)
            ctx=txt[lo:hi].replace("\n"," ")
            print(f"KAP_ENDPOINT_CONTEXT target={target} bundle={u} pos={pos}")
            print("KAP_ENDPOINT_CODE",ctx)
        if found>=len(TARGETS):
            break
        if total>8_000_000:
            break
    print(f"KAP_ENDPOINT_CONTEXT_DONE found={found} total_bytes={total}")
    if found < 2:
        raise RuntimeError("expected KAP endpoint contexts were not found")

if __name__=="__main__":
    main()
