"""Discover KAP public company-list/API endpoints from the live client bundles."""
from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup

BASE="https://www.kap.org.tr"
URL=BASE+"/tr/bist-sirketler"
PATTERNS=(
    re.compile(r'["\']([^"\']*/tr/api/[^"\']+)["\']'),
    re.compile(r'["\']([^"\']*/api/[^"\']+)["\']'),
)

def main():
    s=requests.Session()
    h={"User-Agent":"Mozilla/5.0 (compatible; BIST-Research-Terminal/1.0; personal research)"}
    r=s.get(URL,headers=h,timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    scripts=[]
    for tag in soup.find_all("script",src=True):
        src=tag.get("src")
        if not src: continue
        full=src if src.startswith("http") else BASE+src if src.startswith("/") else BASE+"/"+src
        scripts.append(full)
    print(f"KAP_CLIENT_DISCOVERY html_bytes={len(r.content)} scripts={len(scripts)}")
    found=set()
    keywords=("bist-sirketler","sirket-bilgileri","company","member","ticker","mkk")
    for src in scripts[:40]:
        try:
            rr=s.get(src,headers=h,timeout=30)
            if rr.status_code!=200 or len(rr.text)<100:
                continue
            body=rr.text
            low=body.lower()
            if not any(k in low for k in keywords):
                continue
            print(f"KAP_CLIENT_SCRIPT_MATCH url={src} bytes={len(body)}")
            for pat in PATTERNS:
                for m in pat.finditer(body):
                    value=m.group(1)
                    if len(value)<300:
                        found.add(value)
            for kw in ("GET_COMPANY_ITEMS","api/company/items","bist-sirketler","sirket-bilgileri","company-list","company","member"):
                pos=low.find(kw)
                if pos>=0:
                    snippet=body[max(0,pos-500):pos+1200]
                    print("KAP_CLIENT_SNIPPET",kw,snippet[:1700].replace("\n"," "))
        except Exception as exc:
            print(f"KAP_CLIENT_SCRIPT_DEGRADED url={src} err={type(exc).__name__}:{exc}")
    print("KAP_CLIENT_ENDPOINTS",sorted(found)[:200])
    if not found:
        raise SystemExit("KAP_CLIENT_DISCOVERY_NO_ENDPOINTS")

if __name__=="__main__":
    main()
