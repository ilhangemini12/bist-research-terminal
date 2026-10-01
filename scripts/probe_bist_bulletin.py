"""Probe Borsa Istanbul's publicly linked DataFilePaths archive.

This is discovery-only. It does not ingest, republish, or enable market prices.
The probe exists to discover official file path patterns without guessing URLs.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import json
import zipfile

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

def main():
    r=requests.get(URL,timeout=30,headers={"User-Agent":"BIST-Research-Terminal/1.0 source-discovery"})
    print(f"BIST_PATHS_HTTP status={r.status_code} content_type={r.headers.get('content-type')} bytes={len(r.content)}")
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise RuntimeError("official DataFilePaths response is not a ZIP archive")
    digest=hashlib.sha256(r.content).hexdigest()
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        names=zf.namelist()
        print(f"BIST_PATHS_ZIP_OK sha256={digest} entries={len(names)} names={names}")
        extracts=[]
        for name in names:
            if name.endswith("/"):
                continue
            raw=zf.read(name)
            text=decode_text(raw)
            if text is None:
                extracts.append({"name":name,"bytes":len(raw),"text":None})
                print(f"BIST_PATHS_BINARY name={name} bytes={len(raw)}")
                continue
            # Keep discovery bounded; only lines useful for path/pattern discovery.
            interesting=[
                line.strip() for line in text.splitlines()
                if any(k in line.lower() for k in ("thb","bult","bullet","pay","equity","http","zip","csv","data/"))
            ][:250]
            extracts.append({"name":name,"bytes":len(raw),"interesting_lines":interesting})
            print(f"BIST_PATHS_TEXT name={name} bytes={len(raw)} interesting={len(interesting)}")
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
