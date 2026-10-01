"""Bounded probe for the official Borsa Istanbul Equity Market daily bulletin.

Discovery/validation only. It makes at most three requests for the previous
BIST trading day, using the official path pattern discovered from
DataFilePaths.zip. It does not persist or redistribute raw market data.
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path
import csv
import sys
import zipfile

import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date

BASE="https://www.borsaistanbul.com"

def previous_trade_date() -> date:
    cal=load_calendar(ROOT/"config/bist_calendar_2026.yaml")
    latest=latest_expected_trade_date(date.today(),cal)
    return latest_expected_trade_date(latest-timedelta(days=1),cal)

def decode(raw: bytes) -> str:
    for enc in ("utf-8-sig","cp1254","latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("unable to decode bulletin")

def main():
    d=previous_trade_date()
    print(f"BIST_BULLETIN_TARGET trade_date={d.isoformat()}")
    successes=[]
    for suffix in ("1","2","3"):
        url=f"{BASE}/data/thb/{d:%Y}/{d:%m}/thb{d:%Y%m%d}{suffix}.zip"
        r=requests.get(url,timeout=30,headers={"User-Agent":"BIST-Research-Terminal/1.0 source-discovery"})
        print(f"BIST_BULLETIN_HTTP suffix={suffix} status={r.status_code} bytes={len(r.content)} content_type={r.headers.get('content-type')} url={url}")
        if r.status_code != 200 or not r.content.startswith(b"PK"):
            continue
        with zipfile.ZipFile(BytesIO(r.content)) as zf:
            names=[n for n in zf.namelist() if not n.endswith("/")]
            print(f"BIST_BULLETIN_ZIP_OK suffix={suffix} entries={names}")
            parsed=[]
            for name in names:
                raw=zf.read(name)
                if not name.lower().endswith((".csv",".txt")):
                    print(f"BIST_BULLETIN_ENTRY_BINARY name={name} bytes={len(raw)}")
                    continue
                text=decode(raw)
                rows=list(csv.reader(StringIO(text),delimiter=";"))
                nonempty=[row for row in rows if any(str(v).strip() for v in row)]
                widths=sorted({len(row) for row in nonempty})
                header=[str(x).strip() for x in nonempty[0]] if nonempty else []
                print(f"BIST_BULLETIN_CSV name={name} rows={len(nonempty)} widths={widths[:12]}")
                print("BIST_BULLETIN_HEADERS "+ " | ".join(f"{i}:{v}" for i,v in enumerate(header)))
                if header:
                    h={name:i for i,name in enumerate(header)}
                    code_i=h.get("ISLEM  KODU",h.get("ISLEM KODU",1))
                    selected=[
                        "TARIH","ISLEM  KODU","BULTEN ADI","ENSTRUMAN GRUBU","ENSTRUMAN TIPI",
                        "ONCEKI KAPANIS FIYATI","ACILIS FIYATI","EN DUSUK FIYAT","EN YUKSEK FIYAT",
                        "KAPANIS FIYATI","KAPANIS SEANSI FIYATI","DEGISIM (%)",
                        "AGIRLIKLI ORTALAMA FIYAT","ISLEM MIKTARI","ISLEM HACMI"
                    ]
                    thy=[row for row in nonempty[1:] if len(row)>code_i and str(row[code_i]).upper().startswith("THYAO")]
                    print(f"BIST_BULLETIN_THYAO_ROWS count={len(thy)} codes={[row[code_i] for row in thy]}")
                    for row in thy[:20]:
                        vals={}
                        for key in selected:
                            i=h.get(key)
                            if i is not None and i < len(row):
                                vals[key]=row[i]
                        print(f"BIST_BULLETIN_THYAO_DETAIL {vals}")
                parsed.append((name,len(nonempty)))
            successes.append((suffix,url,names,parsed))
    print(f"BIST_BULLETIN_PROBE_DONE successes={len(successes)}")
    if not successes:
        raise RuntimeError("No official previous-trading-day bulletin ZIP found for bounded suffixes 1..3")

if __name__=="__main__":
    main()
