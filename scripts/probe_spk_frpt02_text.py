"""One-off SPK FRPT02 PDF text-layer probe.

Fetches one documented public SPK financial-statement PDF into memory, measures
whether a usable text layer exists, prints only structural/text-quality metadata,
and never writes or commits the PDF bytes.
"""
from __future__ import annotations

import base64
from io import BytesIO
import re

from pypdf import PdfReader

from src.bist_terminal.providers.spk import SPKRegistryProvider

REPORT_ID = 1986  # FRPT02 sample observed from documented public metadata endpoint

def main():
    detail=SPKRegistryProvider().financial_report(REPORT_ID)
    assert detail.get("mimeType") == "application/pdf"
    raw=base64.b64decode(detail["fileData"],validate=True)
    if not raw.startswith(b"%PDF"):
        raise RuntimeError("SPK financial report is not a PDF")
    reader=PdfReader(BytesIO(raw))
    texts=[]
    image_pages=0
    for page in reader.pages:
        txt=(page.extract_text() or "").strip()
        texts.append(txt)
        try:
            if getattr(page,"images",None) and len(page.images):
                image_pages += 1
        except Exception:
            pass
    joined="\n".join(texts)
    normalized=re.sub(r"\s+"," ",joined).strip()
    finance_terms=[
        term for term in [
            "finansal durum","kar veya zarar","nakit akış","özkaynak","hasılat",
            "dönen varlık","toplam varlık","toplam yükümlülük","net dönem"
        ] if term.casefold() in normalized.casefold()
    ]
    nonempty=sum(bool(t) for t in texts)
    print("SPK_FRPT02_PROBE_OK")
    print(f"SPK_FRPT02_META id={detail.get('id')} companyCode={detail.get('companyCode')} subject={detail.get('subject')} date={detail.get('date')}")
    print(f"SPK_FRPT02_PDF bytes={len(raw)} pages={len(reader.pages)} nonempty_text_pages={nonempty} image_pages={image_pages}")
    print(f"SPK_FRPT02_TEXT chars={len(normalized)} finance_terms={finance_terms}")
    print("SPK_FRPT02_SAMPLE", normalized[:1200].replace("\n"," "))

if __name__=="__main__":
    main()
