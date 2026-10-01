"""Single low-impact availability check for KAP's public bulk financial download.

Uses the exact GET route and period code exposed by KAP's own public frontend.
This probe checks one closed period (2025 annual) and does NOT download the file.
"""
from __future__ import annotations
import json
import requests

BASE="https://kapsitebackend.mkk.com.tr"
LANG="tr"
YEAR="2025"
PERIOD="4"  # KAP public UI: 4 = Yıllık
URL=f"{BASE}/{LANG}/api/financialTable/checkFileExist/{YEAR}/{PERIOD}"
UA={"User-Agent":"bist-research-terminal/0.4 (+research; one-shot public UI availability check)",
    "Accept-Language":"tr","Content-Type":"application/json"}

def main():
    r=requests.get(URL,timeout=30,headers=UA)
    print(f"KAP_CHECK_HTTP status={r.status_code} content_type={r.headers.get('content-type')} bytes={len(r.content)} url={URL}")
    body=r.text[:4000]
    try:
        data=r.json()
        if isinstance(data,list):
            print(f"KAP_CHECK_JSON type=list count={len(data)} sample={json.dumps(data[:3],ensure_ascii=False)[:2500]}")
        elif isinstance(data,dict):
            print(f"KAP_CHECK_JSON type=dict keys={list(data)[:40]} sample={json.dumps(data,ensure_ascii=False)[:2500]}")
        else:
            print(f"KAP_CHECK_JSON type={type(data).__name__} sample={str(data)[:1200]}")
    except Exception:
        print("KAP_CHECK_BODY",body.replace("\n"," ")[:2500])
    if r.status_code != 200:
        raise RuntimeError(f"KAP checkFileExist returned HTTP {r.status_code}")
    print("KAP_CHECK_DONE")

if __name__=="__main__":
    main()
