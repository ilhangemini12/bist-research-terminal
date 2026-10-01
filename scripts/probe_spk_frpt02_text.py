"""One-off SPK FRPT02 PDF structure probe.

Fetches one documented public SPK financial-statement PDF into memory, checks
text-layer quality, and prints only bounded line contexts needed to design a safe
normalizer. No PDF bytes are persisted or committed.
"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
import re
import sys

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from bist_terminal.providers.spk import SPKRegistryProvider

REPORT_ID = 1986
TERMS = [
    "TOPLAM VARLIKLAR",
    "TOPLAM KAYNAKLAR",
    "TOPLAM ÖZKAYNAKLAR",
    "ÖZKAYNAKLAR",
    "HASILAT",
    "BRÜT KAR",
    "BRÜT KÂR",
    "FAALİYET KARI",
    "FAALİYET KÂRI",
    "DÖNEM KARI",
    "DÖNEM KÂRI",
    "NET DÖNEM KARI",
    "NET DÖNEM KÂRI",
    "NAKİT VE NAKİT BENZERLERİ",
]

def clean(s: str) -> str:
    return re.sub(r"\s+"," ",s or "").strip()

def main():
    detail=SPKRegistryProvider().financial_report(REPORT_ID)
    raw=base64.b64decode(detail["fileData"],validate=True)
    if not raw.startswith(b"%PDF"):
        raise RuntimeError("SPK financial report is not a PDF")
    reader=PdfReader(BytesIO(raw))
    contexts=[]
    all_text=[]
    image_pages=0
    for pno,page in enumerate(reader.pages,1):
        txt=page.extract_text() or ""
        all_text.append(txt)
        try:
            if getattr(page,"images",None) and len(page.images):
                image_pages += 1
        except Exception:
            pass
        lines=[clean(x) for x in txt.splitlines() if clean(x)]
        for i,line in enumerate(lines):
            up=line.upper()
            if any(term in up for term in TERMS):
                before=lines[max(0,i-1)] if i else ""
                after=lines[i+1] if i+1 < len(lines) else ""
                contexts.append((pno,before,line,after))
    normalized=clean("\n".join(all_text))
    print("SPK_FRPT02_STRUCTURE_PROBE_OK")
    print(f"SPK_FRPT02_META id={detail.get('id')} companyCode={detail.get('companyCode')} subject={detail.get('subject')} date={detail.get('date')}")
    print(f"SPK_FRPT02_PDF bytes={len(raw)} pages={len(reader.pages)} nonempty_text_pages={sum(bool(clean(x)) for x in all_text)} image_pages={image_pages} chars={len(normalized)}")
    print(f"SPK_FRPT02_CONTEXT_COUNT {len(contexts)}")
    for pno,before,line,after in contexts[:60]:
        print(f"SPK_FRPT02_CONTEXT page={pno} :: PRE={before[:300]} || HIT={line[:700]} || POST={after[:300]}")

if __name__=="__main__":
    main()
