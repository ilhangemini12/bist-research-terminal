"""Bounded public broker model-portfolio access probe.

Checks robots.txt and visible public HTML only. It does not call private APIs,
does not log in, and does not persist broker target prices.
"""
from __future__ import annotations

from io import StringIO
from pathlib import Path
import json
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
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
    try:
        tables=pd.read_html(StringIO(r.text),header=None)
    except ValueError:
        tables=[]
    result["table_count"]=len(tables)
    for i,df in enumerate(tables):
        blob=" ".join(str(x) for x in df.astype(str).to_numpy().ravel()).upper()
        if "HEDEF" not in blob and "MODEL PORTF" not in blob:
            continue
        result["candidate_tables"].append({
            "index":i,
            "shape":[int(df.shape[0]),int(df.shape[1])],
            "first_rows":[
                [str(x)[:140] for x in row]
                for row in df.head(8).fillna("").astype(str).values.tolist()
            ],
        })
    # Text-only signals for server-rendered card layouts.
    upper=r.text.upper()
    result["signals"]={
        "hedef_fiyat":("HEDEF F" in upper),
        "model_portfoy":("MODEL PORTF" in upper),
        "known_ticker_count":sum(upper.count(t) for t in ["ANHYT","GARAN","THYAO","YKBNK","AKSA","ASTOR","DOHOL"]),
    }
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
