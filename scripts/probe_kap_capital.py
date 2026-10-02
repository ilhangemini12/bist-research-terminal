"""Probe public KAP company pages for capital/share-count structure."""
from __future__ import annotations
from pathlib import Path
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

BASE="https://www.kap.org.tr"
LIST_URL=BASE+"/tr/bist-sirketler"
TARGETS={"THYAO","INFO","MARTI"}

def main():
    s=requests.Session()
    h={"User-Agent":"Mozilla/5.0 (compatible; BIST-Research-Terminal/1.0; personal research)"}
    r=s.get(LIST_URL,headers=h,timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    links={}
    for a in soup.select('a[href*="/tr/sirket-bilgileri/genel/"]'):
        code=" ".join(a.get_text(" ",strip=True).split())
        if code in TARGETS:
            links[code]=BASE+a.get("href") if a.get("href","").startswith("/") else a.get("href")
    print("KAP_CAPITAL_LIST_FOUND",links)

    # Next.js can keep the company rows in serialized server state rather than
    # literal anchor tags. Inspect bounded snippets for target stock codes.
    raw=r.text
    for ticker in sorted(TARGETS):
        patterns=[f'"stockCode":"{ticker}"',f'\\\"stockCode\\\":\\\"{ticker}\\\"']
        for pat in patterns:
            pos=raw.find(pat)
            if pos>=0:
                print("KAP_CAPITAL_STATE_SNIPPET",ticker,raw[max(0,pos-700):pos+1400].replace("\n"," "))
                break
    for ticker,url in sorted(links.items()):
        rr=s.get(url,headers=h,timeout=30); rr.raise_for_status()
        text=" ".join(BeautifulSoup(rr.text,"html.parser").stripped_strings)
        print(f"KAP_CAPITAL_PAGE ticker={ticker} url={url} chars={len(text)}")
        tables=pd.read_html(rr.text)
        for i,df in enumerate(tables):
            cols=" | ".join(str(x) for x in df.columns)
            body=" ".join(str(x) for x in df.head(8).astype(str).to_numpy().ravel())
            blob=(cols+" "+body).upper()
            if any(k in blob for k in ("TOPLAM PAY ADED","BEHER PAYIN NOMINAL","PAYLARIN NOMINAL","FIILI DOLASIM")):
                print(f"KAP_CAPITAL_TABLE ticker={ticker} table={i} shape={df.shape} cols={cols}")
                print(df.head(12).to_string(index=False))
        idx=text.find("Ödenmiş/Çıkarılmış Sermaye")
        if idx>=0:
            print("KAP_CAPITAL_TEXT",ticker,text[idx:idx+1000])

if __name__=="__main__":
    main()
