"""Bounded public broker model-portfolio access probe.

Checks robots.txt and visible public HTML only. It does not call private APIs,
does not log in, and does not persist broker target prices.
"""
from __future__ import annotations

from pathlib import Path
import json
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import requests

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
    {
        "id":"ak_yatirim_model_portfolio",
        "url":"https://www.akyatirim.com.tr/tr/raporlarimiz/model-portfoy",
    },
    {
        "id":"gedik_model_portfolio",
        "url":"https://gedik.com/analiz/model-portfoy/hisse-model-portfoy",
    },
]


def probe(source):
    url=source["url"]
    parsed=urlparse(url)
    robots=f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    headers={"User-Agent":"BIST-Research-Terminal/1.0 public-source-audit"}
    rr=requests.get(robots,headers=headers,timeout=20)
    robots_text=rr.text if rr.status_code==200 else ""
    rp=RobotFileParser()
    rp.set_url(robots)
    if robots_text:
        rp.parse(robots_text.splitlines())
        can_fetch=rp.can_fetch(headers["User-Agent"],url)
    else:
        can_fetch=None

    result={
        "provider_id":source["id"],
        "url":url,
        "robots_url":robots,
        "robots_status":rr.status_code,
        "robots_can_fetch":can_fetch,
        "page_status":None,
        "page_bytes":0,
        "table_count":0,
        "candidate_tables":[],
    }
    if can_fetch is False:
        return result

    r=requests.get(url,headers=headers,timeout=30)
    result["page_status"]=r.status_code
    result["page_bytes"]=len(r.content)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    tables=soup.find_all("table")
    result["table_count"]=len(tables)
    for i,table in enumerate(tables):
        rows=[]
        for tr in table.find_all("tr")[:10]:
            cells=[x.get_text(" ",strip=True)[:140] for x in tr.find_all(["th","td"])]
            if cells:
                rows.append(cells)
        blob=" ".join(" ".join(row) for row in rows).upper()
        if "HEDEF" not in blob and "MODEL PORTF" not in blob:
            continue
        result["candidate_tables"].append({
            "index":i,
            "first_rows":rows,
        })
    # Text-only signals for server-rendered card layouts.
    visible=soup.get_text(" ",strip=True)
    upper=visible.upper()
    result["signals"]={
        "hedef_fiyat":("HEDEF F" in upper),
        "model_portfoy":("MODEL PORTF" in upper),
        "known_ticker_count":sum(upper.count(t) for t in ["ANHYT","GARAN","THYAO","YKBNK","AKSA","ASTOR","DOHOL"]),
    }
    snippets=[]
    for ticker in ["ANHYT","GARAN","THYAO","YKBNK","AKSA","ASTOR","DOHOL"]:
        pos=upper.find(ticker)
        if pos>=0:
            snippets.append({"ticker":ticker,"snippet":visible[max(0,pos-120):pos+420]})
    result["ticker_snippets"]=snippets[:10]
    dates_visible=sorted(set(re.findall(r"\\b\\d{2}\\.\\d{2}\\.\\d{4}\\b",visible)))
    dates_raw=sorted(set(re.findall(r"\\b\\d{2}\\.\\d{2}\\.\\d{4}\\b",r.text)))
    result["dates_visible"]=dates_visible[-30:]
    result["dates_raw"]=dates_raw[-30:]
    raw_contexts=[]
    for d in dates_raw[-10:]:
        pos=r.text.find(d)
        raw_contexts.append({"date":d,"context":re.sub(r"\\s+"," ",r.text[max(0,pos-250):pos+350])[:700]})
    result["date_contexts_raw"]=raw_contexts
    return result


def main():
    rows=[]
    for source in SOURCES:
        try:
            row=probe(source)
        except Exception as exc:
            row={
                "provider_id":source["id"],
                "url":source["url"],
                "error":f"{type(exc).__name__}: {exc}",
            }
        rows.append(row)
        print("BROKER_PUBLIC_PROBE",json.dumps(row,ensure_ascii=False))
    out=ROOT/"artifacts/broker_public_probe.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"sources":rows},ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
