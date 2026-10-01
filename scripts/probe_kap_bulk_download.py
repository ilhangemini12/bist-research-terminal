"""Final bounded KAP bulk-download availability probe.

This mirrors a normal public browser session: first GET the KAP home page to receive
first-party cookies, then make exactly one GET to the public UI checkFileExist route.
No retries, no proxy, no CAPTCHA bypass, no download.
"""
from __future__ import annotations
import json
import requests

HOME="https://www.kap.org.tr/tr"
CHECK="https://www.kap.org.tr/tr/api/financialTable/checkFileExist/2025/4"

BROWSER_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
API_HEADERS={
    **BROWSER_HEADERS,
    "Accept":"*/*",
    "Content-Type":"application/json",
    "Referer":HOME,
    "Origin":"https://www.kap.org.tr",
}

def main():
    s=requests.Session()
    home=s.get(HOME,timeout=30,headers=BROWSER_HEADERS)
    print(f"KAP_SESSION_HOME status={home.status_code} bytes={len(home.content)} cookies={list(s.cookies.keys())}")
    home.raise_for_status()

    r=s.get(CHECK,timeout=30,headers=API_HEADERS,allow_redirects=True)
    print(f"KAP_SESSION_CHECK status={r.status_code} content_type={r.headers.get('content-type')} bytes={len(r.content)} final_url={r.url}")
    try:
        data=r.json()
        if isinstance(data,list):
            print(f"KAP_SESSION_JSON type=list count={len(data)} sample={json.dumps(data[:3],ensure_ascii=False)[:2500]}")
        elif isinstance(data,dict):
            print(f"KAP_SESSION_JSON type=dict keys={list(data)[:40]} sample={json.dumps(data,ensure_ascii=False)[:2500]}")
        else:
            print(f"KAP_SESSION_JSON type={type(data).__name__} sample={str(data)[:1200]}")
    except Exception:
        print("KAP_SESSION_BODY",r.text.replace("\n"," ")[:2500])
    if r.status_code != 200:
        raise RuntimeError(f"KAP public UI availability check blocked HTTP {r.status_code}")
    print("KAP_SESSION_CHECK_DONE")

if __name__=="__main__":
    main()
