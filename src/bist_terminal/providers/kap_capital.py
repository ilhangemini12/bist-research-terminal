from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import html as html_lib
import re
import unicodedata

import pandas as pd
import requests

BASE="https://www.kap.org.tr"
LIST_URL=BASE+"/tr/bist-sirketler"


def _fold(value):
    text=str(value or "").strip().upper().replace("İ","I")
    text=unicodedata.normalize("NFKD",text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _tr_num(value):
    if value is None:
        return None
    s=str(value).strip()
    if not s or s.lower()=="nan" or s in {"-","—"}:
        return None
    s=s.replace(" "," ").replace(" ","")
    # Turkish formatting: dot thousands, comma decimal.
    if "," in s:
        s=s.replace(".","").replace(",",".")
    else:
        parts=s.split(".")
        if len(parts)>1 and all(len(p)==3 for p in parts[1:]):
            s="".join(parts)
    s=re.sub(r"[^0-9.-]","",s)
    if not s or s in {"-","."}:
        return None
    return float(s)


def parse_company_mapping(page_html:str)->dict[str,dict]:
    # Next.js embeds company rows in escaped server-state strings.
    text=html_lib.unescape(page_html).replace('\\"','"')
    pat=re.compile(
        r'\{"mkkMemberOid":"(?P<oid>[^"]+)","kapMemberTitle":"(?P<title>[^"]*)".*?"stockCode":"(?P<code>[^"]*)"',
        re.S,
    )
    out={}
    for m in pat.finditer(text):
        codes=re.findall(r'\b[A-Z0-9]{4,6}\b',m.group("code").upper())
        for code in codes:
            out[code]={"mkk_member_oid":m.group("oid"),"company_title":m.group("title"),"stock_code_raw":m.group("code")}
    return out


def parse_total_shares(page_html:str,ticker:str|None=None)->dict:
    tables=pd.read_html(StringIO(page_html), decimal=',', thousands='.')
    # Prefer explicit current KAP float table total-share field when present.
    for df in tables:
        cols=[str(c).strip() for c in df.columns]
        norm=[_fold(c) for c in cols]
        if any("TOPLAM PAY ADED" in c for c in norm):
            idx=next(i for i,c in enumerate(norm) if "TOPLAM PAY ADED" in c)
            for _,row in df.iterrows():
                if ticker:
                    blob=" ".join(str(x) for x in row.tolist()).upper()
                    if ticker.upper() not in blob:
                        continue
                val=_tr_num(row.iloc[idx])
                if val is not None and val>0:
                    return {"total_shares":val,"method":"EXPLICIT_TOTAL_SHARE_COUNT","table_columns":cols}

    # Fallback: sum each share group's nominal amount divided by that group's
    # nominal value per share. Never assume nominal value is 1 TRY.
    for df in tables:
        cols=[str(c).strip() for c in df.columns]
        norm=[_fold(c) for c in cols]
        nominal_per=None; nominal_total=None
        for i,c in enumerate(norm):
            if "BEHER PAYIN NOMINAL DEGERI" in c:
                nominal_per=i
            if "PAYLARIN NOMINAL DEGERI" in c:
                nominal_total=i
        if nominal_per is None or nominal_total is None:
            continue
        total=0.0; groups=0
        for _,row in df.iterrows():
            per=_tr_num(row.iloc[nominal_per]); amount=_tr_num(row.iloc[nominal_total])
            if per is None or amount is None or per<=0 or amount<0:
                continue
            total += amount/per
            groups += 1
        if groups and total>0:
            return {"total_shares":total,"method":"SHARE_GROUP_NOMINAL_RATIO","share_groups":groups,"table_columns":cols}
    return {"total_shares":None,"method":"UNAVAILABLE"}


@dataclass
class KapCapitalProvider:
    session: requests.Session|None=None
    timeout:int=30

    def __post_init__(self):
        if self.session is None:
            self.session=requests.Session()
        self.headers={"User-Agent":"Mozilla/5.0 (compatible; BIST-Research-Terminal/1.0; personal research)"}

    def company_mapping(self)->dict[str,dict]:
        r=self.session.get(LIST_URL,headers=self.headers,timeout=self.timeout)
        r.raise_for_status()
        mapping=parse_company_mapping(r.text)
        if not mapping:
            raise RuntimeError("KAP company mapping schema unavailable")
        return mapping

    def capital_for_ticker(self,ticker:str,mapping:dict[str,dict]|None=None)->dict:
        ticker=ticker.upper().replace(".IS","")
        mapping=mapping or self.company_mapping()
        meta=mapping.get(ticker)
        if not meta:
            return {"ticker":ticker,"status":"MAPPING_MISSING","total_shares":None}
        oid=meta["mkk_member_oid"]
        url=f"{BASE}/tr/sirket-bilgileri/genel/{oid}"
        r=self.session.get(url,headers=self.headers,timeout=self.timeout)
        r.raise_for_status()
        parsed=parse_total_shares(r.text,ticker)
        production_ok = parsed.get("method") == "EXPLICIT_TOTAL_SHARE_COUNT" and bool(parsed.get("total_shares"))
        return {
            "ticker":ticker,
            "status":"ACTIVE" if production_ok else ("EXPERIMENTAL_FALLBACK_ONLY" if parsed.get("total_shares") else "DATA_UNAVAILABLE"),
            "source_url":url,
            **meta,
            **parsed,
        }
