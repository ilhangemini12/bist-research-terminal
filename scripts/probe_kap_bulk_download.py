"""Schema probe for a handful of legacy .xls workbooks inside KAP's public
2025 annual bulk financial archive.

Exactly one bulk ZIP request is made after a normal first-party browser session.
Bytes stay in memory. Only bounded workbook metadata and sample rows are logged.
"""
from __future__ import annotations

from io import BytesIO
import json
import zipfile

import requests
import xlrd

HOME="https://www.kap.org.tr/tr"
DOWNLOAD="https://www.kap.org.tr/tr/api/financialTable/download/2025/4"
TARGET_TICKERS=("THYAO","ASELS","AKBNK","PETKM")
MAX_BYTES=120_000_000

BROWSER_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
API_HEADERS={**BROWSER_HEADERS,"Accept":"*/*","Content-Type":"application/json","Referer":HOME,"Origin":"https://www.kap.org.tr"}

def workbook_samples(payload:bytes,name:str):
    print(f"KAP_XLS_MAGIC name={name} first32={payload[:32].hex()} bytes={len(payload)}")
    book=xlrd.open_workbook(file_contents=payload,on_demand=True)
    print(f"KAP_XLS_WORKBOOK name={name} sheets={book.sheet_names()}")
    for sname in book.sheet_names()[:8]:
        sh=book.sheet_by_name(sname)
        rows=[]
        for r in range(min(sh.nrows,80)):
            vals=[sh.cell_value(r,c) for c in range(min(sh.ncols,18))]
            if any(v not in ("",None) for v in vals):
                rows.append(vals)
                if len(rows)>=12: break
        print(f"KAP_XLS_SHEET workbook={name} sheet={sname} nrows={sh.nrows} ncols={sh.ncols} sample={json.dumps(rows,ensure_ascii=False,default=str)[:7000]}")
    book.release_resources()

def main():
    s=requests.Session(); s.get(HOME,timeout=30,headers=BROWSER_HEADERS).raise_for_status()
    with s.get(DOWNLOAD,timeout=90,headers=API_HEADERS,stream=True) as r:
        print(f"KAP_XLS_HTTP status={r.status_code} type={r.headers.get('content-type')} disposition={r.headers.get('content-disposition')}")
        r.raise_for_status()
        buf=bytearray()
        for chunk in r.iter_content(1024*1024):
            if chunk:
                buf.extend(chunk)
                if len(buf)>MAX_BYTES: raise RuntimeError("bounded byte limit exceeded")
    raw=bytes(buf)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        infos=[i for i in zf.infolist() if not i.is_dir()]
        names=[i.filename for i in infos]
        print(f"KAP_XLS_ARCHIVE files={len(names)} bytes={len(raw)}")
        picked=[]
        for ticker in TARGET_TICKERS:
            hits=[n for n in names if n.upper().startswith(ticker+"_") and n.lower().endswith(".xls")]
            if hits: picked.append(hits[0])
            else: print(f"KAP_XLS_TARGET_MISSING ticker={ticker}")
        if len(picked)<2:
            picked += [n for n in names if n.lower().endswith(".xls") and n not in picked][:4-len(picked)]
        print(f"KAP_XLS_PICKED {picked}")
        for name in picked[:4]:
            workbook_samples(zf.read(name),name)
    print("KAP_XLS_SCHEMA_DONE")

if __name__=="__main__":
    main()
