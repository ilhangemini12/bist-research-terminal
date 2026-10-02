from __future__ import annotations

from datetime import date, timedelta
import re
import unicodedata


def normalize_company_title(value: str | None) -> str:
    text=str(value or "").strip().upper().replace("İ","I")
    text=unicodedata.normalize("NFKD",text)
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    text=re.sub(r"[^A-Z0-9]+"," ",text)
    return re.sub(r"\s+"," ",text).strip()


def title_to_ticker_map(capital_records: dict[str,dict]) -> dict[str,str]:
    out={}
    collisions=set()
    for ticker,rec in (capital_records or {}).items():
        key=normalize_company_title(rec.get("company_title"))
        if not key:
            continue
        if key in out and out[key] != ticker:
            collisions.add(key)
        else:
            out[key]=ticker
    for key in collisions:
        out.pop(key,None)
    return out


def recent_spk_disclosures(provider, capital_records: dict[str,dict], end_date: date, days: int=7) -> list[dict]:
    if days < 1:
        raise ValueError("days must be >= 1")
    start=end_date-timedelta(days=days-1)
    mapping=title_to_ticker_map(capital_records)
    raw=provider.special_disclosures(dateBegin=start.isoformat(),dateEnd=end_date.isoformat())
    if not isinstance(raw,list):
        raise RuntimeError("SPK disclosure response schema changed: expected list")
    out=[]
    seen=set()
    for row in raw:
        if not isinstance(row,dict):
            continue
        rid=row.get("id")
        if rid in seen:
            continue
        seen.add(rid)
        title=str(row.get("companyTitle") or "").strip()
        ticker=mapping.get(normalize_company_title(title))
        dt=str(row.get("date") or "")[:10] or None
        out.append({
            "id":rid,
            "date":dt,
            "ticker":ticker,
            "company_title":title or None,
            "subject":str(row.get("subject") or "").strip() or None,
            "mime_type":row.get("mimeType"),
            "company_code":row.get("companyCode"),
            "mapped_current_universe":bool(ticker),
            "source_url":f"https://ws.spk.gov.tr/CompanyData/api/OzelDurumAciklamalari/{rid}" if rid is not None else None,
            "provider_id":"spk_ws",
            "upstream_vendor":"SPK",
        })
    out.sort(key=lambda x:((x.get("date") or ""),int(x.get("id") or 0)),reverse=True)
    return out
