"""Schema probe for KAP's HTML-disguised-as-.xls financial workbooks.

Exactly one public bulk ZIP request is made after a normal KAP browser session.
Selected company files stay in memory and are parsed as HTML tables with pandas/lxml.
"""
from __future__ import annotations

from io import BytesIO
import json,re,zipfile
import pandas as pd
import requests

HOME="https://www.kap.org.tr/tr"
DOWNLOAD="https://www.kap.org.tr/tr/api/financialTable/download/2025/4"
TARGET_TICKERS=("THYAO","ASELS","AKBNK","PETKM")
MAX_BYTES=120_000_000
KEYWORDS=(
    "TOPLAM VARLIKLAR","ÖZKAYNAK","OZKAYNAK","HASILAT","DÖNEM KARI","DÖNEM KÂRI","NET DÖNEM","NAKİT","NAKIT",
    "BORÇLANMA","BORCLANMA","FİNANSAL BORÇ","FINANSAL BORC","KİRALAMA YÜKÜMLÜLÜ","KIRALAMA YUKUMLULU",
    "AMORTİSMAN","AMORTISMAN","İTFA","ITFA","MADDİ DURAN VARLIK","MADDI DURAN VARLIK",
    "MADDİ OLMAYAN DURAN VARLIK","MADDI OLMAYAN DURAN VARLIK","YATIRIM HARCAMA","YATIRIM HARCAM",
    "VERGİ GİDER","VERGI GIDER","VERGİ GELİR","VERGI GELIR"
)


EXACT_PROBE_TERMS=(
    "Kısa Vadeli Borçlanmalar",
    "Uzun Vadeli Borçlanmaların Kısa Vadeli Kısımları",
    "Uzun Vadeli Borçlanmalar",
    "Amortisman ve İtfa Gideri İle İlgili Düzeltmeler",
    "Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları",
)

BROWSER_HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
API_HEADERS={**BROWSER_HEADERS,"Accept":"*/*","Content-Type":"application/json","Referer":HOME,"Origin":"https://www.kap.org.tr"}

def clean(v):
    if pd.isna(v): return ""
    return re.sub(r"\s+"," ",str(v)).strip()

def parse_html_xls(payload:bytes,name:str):
    print(f"KAP_HTML_XLS_MAGIC name={name} first48={payload[:48].hex()} bytes={len(payload)}")
    # pandas/lxml handles the Office HTML tables despite the .xls suffix.
    tables=pd.read_html(BytesIO(payload),header=None)
    print(f"KAP_HTML_XLS_TABLES name={name} count={len(tables)} shapes={[list(t.shape) for t in tables[:20]]}")
    hits=0
    for idx,df in enumerate(tables):
        rows=[]
        for _,row in df.iterrows():
            vals=[clean(v) for v in row.tolist()]
            joined=" | ".join(v for v in vals if v)
            upper=joined.upper()
            if any(k in upper for k in KEYWORDS):
                rows.append(vals[:16])
        if rows:
            hits+=len(rows)
            print(f"KAP_HTML_XLS_METRICS name={name} table={idx} shape={df.shape} rows={json.dumps(rows[:30],ensure_ascii=False)[:9000]}")
    # Also emit bounded samples from the first few non-empty tables.
    emitted=0
    for idx,df in enumerate(tables):
        sample=[]
        for _,row in df.head(40).iterrows():
            vals=[clean(v) for v in row.tolist()]
            if any(vals):
                sample.append(vals[:14])
                if len(sample)>=8: break
        if sample:
            print(f"KAP_HTML_XLS_SAMPLE name={name} table={idx} shape={df.shape} rows={json.dumps(sample,ensure_ascii=False)[:5000]}")
            emitted+=1
            if emitted>=5: break

    # Emit exact, value-bearing rows for debt / D&A / capex and any tax-expense labels.
    exact_hits=[]
    for idx,df in enumerate(tables):
        for _,row in df.iterrows():
            vals=[clean(v) for v in row.tolist()]
            label=next((v for v in vals[:2] if v), "")
            folded=label.upper()
            wanted=label in EXACT_PROBE_TERMS or ("VERGİ" in folded and ("GİDER" in folded or "GELİR" in folded))
            if wanted and any(v for v in vals[2:]):
                exact_hits.append({"table":idx,"row":vals[:16]})
    print(f"KAP_EXACT_FINANCIAL_ROWS name={name} rows={json.dumps(exact_hits,ensure_ascii=False)[:18000]}")

    print(f"KAP_HTML_XLS_PARSED name={name} metric_rows={hits}")

def main():
    s=requests.Session(); s.get(HOME,timeout=30,headers=BROWSER_HEADERS).raise_for_status()
    with s.get(DOWNLOAD,timeout=90,headers=API_HEADERS,stream=True) as r:
        print(f"KAP_HTML_XLS_HTTP status={r.status_code} type={r.headers.get('content-type')} disposition={r.headers.get('content-disposition')}")
        r.raise_for_status()
        buf=bytearray()
        for chunk in r.iter_content(1024*1024):
            if chunk:
                buf.extend(chunk)
                if len(buf)>MAX_BYTES: raise RuntimeError("bounded byte limit exceeded")
    raw=bytes(buf)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names=[i.filename for i in zf.infolist() if not i.is_dir()]
        picked=[]
        for ticker in TARGET_TICKERS:
            hits=[n for n in names if n.upper().startswith(ticker+"_") and n.lower().endswith(".xls")]
            if hits: picked.append(hits[0])
            else: print(f"KAP_HTML_XLS_TARGET_MISSING ticker={ticker}")
        print(f"KAP_HTML_XLS_PICKED {picked}")
        for name in picked:
            parse_html_xls(zf.read(name),name)
    print("KAP_HTML_XLS_SCHEMA_DONE")

if __name__=="__main__":
    main()
