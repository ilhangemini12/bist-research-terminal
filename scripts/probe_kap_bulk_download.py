"""Static discovery of KAP's actual client base URL.

Fetches only KAP's public HTML/first-party JS and prints bounded contexts around
CLIENT_BASE_URL / SERVER_BASE_URL and component invocations. No data endpoint calls.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import re,requests

PAGE="https://www.kap.org.tr/tr"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; bounded endpoint discovery)"}

def emit(label,text,needle,before=1200,after=2200,limit=10):
    start=0; count=0
    while count<limit:
        pos=text.find(needle,start)
        if pos<0: break
        ctx=text[max(0,pos-before):min(len(text),pos+after)].replace("\n"," ")
        print(f"KAP_BASE_CONTEXT label={label} needle={needle} pos={pos}")
        print("KAP_BASE_CODE",ctx)
        count+=1; start=pos+len(needle)
    return count

def main():
    s=requests.Session(); r=s.get(PAGE,timeout=30,headers=UA); r.raise_for_status()
    page=r.text
    print(f"KAP_BASE_PAGE status={r.status_code} bytes={len(r.content)}")
    found=0
    for needle in ("CLIENT_BASE_URL","SERVER_BASE_URL","kapsitebackend","https://www.kap.org.tr"):
        found+=emit("page",page,needle,700,1500,8)
    soup=BeautifulSoup(page,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        u=urljoin(r.url,tag["src"])
        if urlparse(u).netloc.endswith("kap.org.tr") and u not in scripts:
            scripts.append(u)
    total=0
    for u in scripts[:25]:
        rr=s.get(u,timeout=30,headers=UA); total+=len(rr.content)
        if rr.status_code!=200: continue
        txt=rr.text
        if not any(n in txt for n in ("CLIENT_BASE_URL","SERVER_BASE_URL","60304","homeFinancialConstants")):
            continue
        local=0
        for needle in ("CLIENT_BASE_URL","SERVER_BASE_URL","60304","homeFinancialConstants"):
            local+=emit(u,txt,needle,1400,2600,5)
        found+=local
        if found>=25: break
    urls=sorted(set(re.findall(r'https://[A-Za-z0-9._:-]+',page)))
    print(f"KAP_BASE_URLS {urls[:40]}")
    print(f"KAP_BASE_DONE found={found} total_js_bytes={total}")
    if found==0: raise RuntimeError("KAP client base context not found")

if __name__=="__main__":
    main()
