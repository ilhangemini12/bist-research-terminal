"""Bounded discovery probe for KAP public bulk financial-download UI.

Fetches KAP's public page and a limited number of first-party JS bundles to locate
the endpoint used by the user-facing Download button. It does not call the
download endpoint and does not request financial datasets.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import requests

PAGE="https://www.kap.org.tr/tr"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; bounded endpoint discovery)"}
MAX_JS=12
MAX_BYTES=12_000_000

def main():
    s=requests.Session()
    r=s.get(PAGE,timeout=30,headers=UA)
    print(f"KAP_DISCOVERY_PAGE status={r.status_code} bytes={len(r.content)} url={r.url}")
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        u=urljoin(r.url,tag["src"])
        if urlparse(u).netloc.endswith("kap.org.tr") and u not in scripts:
            scripts.append(u)
    print(f"KAP_DISCOVERY_SCRIPTS count={len(scripts)}")
    total=0
    hits=[]
    needles=("finansal","financial","download","kalem","statement","excel","xlsx","rar")
    endpoint_re=re.compile(r'["\']([^"\']*(?:api|download|financial|finansal|kalem)[^"\']*)["\']',re.I)
    for u in scripts[:MAX_JS]:
        rr=s.get(u,timeout=30,headers=UA)
        total += len(rr.content)
        print(f"KAP_DISCOVERY_JS status={rr.status_code} bytes={len(rr.content)} url={u}")
        if rr.status_code!=200:
            continue
        text=rr.text
        low=text.lower()
        if any(n in low for n in needles):
            for m in endpoint_re.finditer(text):
                val=m.group(1)
                if len(val)<=500 and any(n in val.lower() for n in needles):
                    hits.append((u,val))
        if total>=MAX_BYTES:
            print(f"KAP_DISCOVERY_BUDGET_STOP total_bytes={total}")
            break
    dedup=[]
    seen=set()
    for u,val in hits:
        key=val.strip()
        if key and key not in seen:
            seen.add(key); dedup.append((u,key))
    print(f"KAP_DISCOVERY_HITS count={len(dedup)} total_js_bytes={total}")
    for u,val in dedup[:200]:
        print(f"KAP_DISCOVERY_HIT bundle={u} value={val[:700]}")
    print("KAP_DISCOVERY_DONE")

if __name__=="__main__":
    main()
