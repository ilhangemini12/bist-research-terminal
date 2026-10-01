"""Probe Borsa Istanbul's publicly linked DataFilePaths archive.

Discovery-only: this does not ingest, republish, or enable market prices.
It discovers official file/path patterns without guessing URLs.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import json
import zipfile

import pandas as pd
import requests

URL="https://www.borsaistanbul.com/files/DataFilePaths.zip"
ROOT=Path(__file__).resolve().parents[1]

def decode_text(raw: bytes) -> str | None:
    if b"\x00" in raw[:2048]:
        return None
    for enc in ("utf-8-sig","cp1254","latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None

def xlsx_rows(raw: bytes) -> list[dict]:
    out=[]
    book=pd.ExcelFile(BytesIO(raw),engine="openpyxl")
    for sheet in book.sheet_names:
        frame=pd.read_excel(book,sheet_name=sheet,header=None,dtype=str).fillna("")
        for idx,row in frame.iterrows():
            vals=[str(v).strip() for v in row.tolist()]
            if not any(vals):
                continue
            joined=" | ".join(v for v in vals if v)
            out.append({"sheet":sheet,"row":int(idx)+1,"values":vals,"joined":joined})
    return out

def main():
    r=requests.get(URL,timeout=30,headers={"User-Agent":"BIST-Research-Terminal/1.0 source-discovery"})
    print(f"BIST_PATHS_HTTP status={r.status_code} content_type={r.headers.get('content-type')} bytes={len(r.content)}")
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise RuntimeError("official DataFilePaths response is not a ZIP archive")
    digest=hashlib.sha256(r.content).hexdigest()
    extracts=[]
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        names=zf.namelist()
        print(f"BIST_PATHS_ZIP_OK sha256={digest} entries={len(names)} names={names}")
        for name in names:
            if name.endswith("/") or name.startswith("__MACOSX/"):
                continue
            raw=zf.read(name)
            if name.lower().endswith(".xlsx"):
                rows=xlsx_rows(raw)
                extracts.append({"name":name,"bytes":len(raw),"xlsx_rows":rows})
                print(f"BIST_PATHS_XLSX name={name} bytes={len(raw)} rows={len(rows)}")
                keywords=("bülten","bulten","bullet","thb","pay piyas","equity","http","zip","csv","data/")
                interesting=[x for x in rows if any(k in x["joined"].lower() for k in keywords)]
                print(f"BIST_PATHS_XLSX_INTERESTING count={len(interesting)}")
                for item in interesting[:200]:
                    print(f"BIST_PATH_ROW sheet={item['sheet']} row={item['row']} :: {item['joined'][:1000]}")
                continue
            text=decode_text(raw)
            if text is None:
                extracts.append({"name":name,"bytes":len(raw),"text":None})
                print(f"BIST_PATHS_BINARY name={name} bytes={len(raw)}")
                continue
            interesting=[
                line.strip() for line in text.splitlines()
                if any(k in line.lower() for k in ("thb","bult","bullet","pay","equity","http","zip","csv","data/"))
            ][:250]
            extracts.append({"name":name,"bytes":len(raw),"interesting_lines":interesting})
            for line in interesting[:80]:
                print("BIST_PATH_PATTERN",line[:500])
    out={
        "source_url":URL,
        "http_status":r.status_code,
        "content_type":r.headers.get("content-type"),
        "sha256":digest,
        "entries":extracts,
        "purpose":"discovery_only_no_market_data_ingestion",
    }
    (ROOT/"artifacts").mkdir(exist_ok=True)
    (ROOT/"artifacts/bist_file_paths_probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("BIST_PATHS_PROBE_OK")

if __name__=="__main__":
    main()
