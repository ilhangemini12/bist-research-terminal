"""Audit SPK 7-day disclosure-to-current-BIST title mapping without fuzzy matching."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import date
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.spk import SPKRegistryProvider
from bist_terminal.providers.spk_news import normalize_company_title
from bist_terminal.storage.capital_files import load_capital_records


LEGAL_SUFFIXES=(
    " ANONIM SIRKETI",
    " ANONIM SIRKET",
    " A S",
    " LIMITED SIRKETI",
    " LTD STI",
)


def canonical_legal_title(value: str|None) -> str:
    text=normalize_company_title(value)
    changed=True
    while changed and text:
        changed=False
        for suffix in LEGAL_SUFFIXES:
            if text.endswith(suffix):
                text=text[:-len(suffix)].strip()
                changed=True
                break
    return re.sub(r"\s+"," ",text).strip()


def unique_map(records: dict[str,dict], key_fn) -> tuple[dict[str,str],set[str]]:
    out={}; collisions=set()
    for ticker,rec in records.items():
        key=key_fn(rec.get("company_title"))
        if not key:
            continue
        if key in out and out[key]!=ticker:
            collisions.add(key)
        else:
            out[key]=ticker
    for key in collisions:
        out.pop(key,None)
    return out,collisions


def main():
    ap=ArgumentParser()
    ap.add_argument("--end-date",default="2026-10-02")
    ap.add_argument("--days",type=int,default=7)
    args=ap.parse_args()
    end=date.fromisoformat(args.end_date)
    capital=load_capital_records(ROOT)
    exact,_=unique_map(capital,normalize_company_title)
    legal,legal_collisions=unique_map(capital,canonical_legal_title)

    p=SPKRegistryProvider(timeout=30)
    start=end.fromordinal(end.toordinal()-args.days+1)
    raw=p.special_disclosures(dateBegin=start.isoformat(),dateEnd=end.isoformat())
    if not isinstance(raw,list):
        raise RuntimeError("SPK schema changed: expected list")

    rows=[]; exact_count=0; legal_count=0
    for r in raw:
        title=str(r.get("companyTitle") or "").strip()
        ex=exact.get(normalize_company_title(title))
        lc=legal.get(canonical_legal_title(title))
        exact_count += bool(ex)
        legal_count += bool(lc)
        rows.append({
            "id":r.get("id"),
            "date":str(r.get("date") or "")[:10] or None,
            "company_code":r.get("companyCode"),
            "company_title":title or None,
            "subject":r.get("subject"),
            "exact_ticker":ex,
            "legal_suffix_ticker":lc,
            "legal_canonical_title":canonical_legal_title(title),
        })

    report={
        "end_date":args.end_date,
        "days":args.days,
        "spk_rows":len(rows),
        "capital_titles":len(capital),
        "exact_matches":exact_count,
        "legal_suffix_unique_matches":legal_count,
        "legal_suffix_collision_count":len(legal_collisions),
        "rows":rows,
    }
    out=ROOT/"artifacts/spk_news_mapping_audit.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
