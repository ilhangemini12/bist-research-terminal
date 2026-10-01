"""One-shot schema probe of KAP's public 2025 annual bulk financial download.

Mirrors the normal browser session, performs exactly one bulk download after the
known-positive availability check, keeps bytes in memory only, and prints bounded
archive/workbook schema metadata. Raw financial files are not written or committed.
"""
from __future__ import annotations
from io import BytesIO
import json, zipfile
import requests
from openpyxl import load_workbook

HOME="https://www.kap.org.tr/tr"
CHECK="https://www.kap.org.tr/tr/api/financialTable/checkFileExist/2025/4"
DOWNLOAD="https://www.kap.org.tr/tr/api/financialTable/download/2025/4"
MAX_BYTES=120_000_000

BROWSER_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
API_HEADERS={**BROWSER_HEADERS,"Accept":"*/*","Content-Type":"application/json","Referer":HOME,"Origin":"https://www.kap.org.tr"}

def nonempty_rows(ws, limit=10):
    out=[]
    for row in ws.iter_rows(values_only=True):
        vals=[v for v in row]
        if any(v not in (None,"") for v in vals):
            out.append(vals[:18])
            if len(out)>=limit: break
    return out

def main():
    s=requests.Session()
    home=s.get(HOME,timeout=30,headers=BROWSER_HEADERS); home.raise_for_status()
    chk=s.get(CHECK,timeout=30,headers=API_HEADERS); chk.raise_for_status()
    available=chk.json()
    print(f"KAP_BULK_CHECK count={len(available) if isinstance(available,list) else 'n/a'} body={json.dumps(available,ensure_ascii=False)[:600]}")
    if not isinstance(available,list) or not available:
        raise RuntimeError("KAP 2025 annual bulk file is not available")

    with s.get(DOWNLOAD,timeout=90,headers=API_HEADERS,stream=True) as r:
        print(f"KAP_BULK_HTTP status={r.status_code} content_type={r.headers.get('content-type')} disposition={r.headers.get('content-disposition')} content_length={r.headers.get('content-length')}")
        r.raise_for_status()
        declared=int(r.headers.get("content-length") or 0)
        if declared and declared>MAX_BYTES:
            raise RuntimeError(f"bulk file too large for bounded probe: {declared}")
        buf=bytearray()
        for chunk in r.iter_content(1024*1024):
            if not chunk: continue
            buf.extend(chunk)
            if len(buf)>MAX_BYTES:
                raise RuntimeError("bulk file exceeded bounded probe byte limit")
    raw=bytes(buf)
    print(f"KAP_BULK_BYTES bytes={len(raw)} magic={raw[:12].hex()}")
    if not raw.startswith(b"PK"):
        raise RuntimeError("KAP bulk financial download is not a ZIP archive")

    with zipfile.ZipFile(BytesIO(raw)) as zf:
        infos=[i for i in zf.infolist() if not i.is_dir()]
        print(f"KAP_BULK_ZIP files={len(infos)} compressed={sum(i.compress_size for i in infos)} uncompressed={sum(i.file_size for i in infos)}")
        for i in infos[:40]:
            print(f"KAP_BULK_ENTRY name={i.filename} bytes={i.file_size}")
        excel=[i for i in infos if i.filename.lower().endswith((".xlsx",".xlsm"))]
        print(f"KAP_BULK_EXCEL count={len(excel)}")
        for info in excel[:3]:
            payload=zf.read(info)
            wb=load_workbook(BytesIO(payload),read_only=True,data_only=True)
            print(f"KAP_BULK_WORKBOOK name={info.filename} sheets={wb.sheetnames}")
            for ws in wb.worksheets[:4]:
                rows=nonempty_rows(ws,8)
                print(f"KAP_BULK_SHEET workbook={info.filename} sheet={ws.title} max_row={ws.max_row} max_col={ws.max_column} sample={json.dumps(rows,ensure_ascii=False,default=str)[:5000]}")
            wb.close()
    print("KAP_BULK_SCHEMA_PROBE_DONE")

if __name__=="__main__":
    main()
