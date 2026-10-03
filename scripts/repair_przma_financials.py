"""Build an immutable PRZMA financial repair overlay using the validated YTD parser."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.storage.financial_files import financial_repair_shard_path


def main():
    ap=ArgumentParser()
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--periods",default="1 2 3 4")
    ap.add_argument("--version",type=int,default=1)
    args=ap.parse_args()
    periods=[p for p in args.periods.split() if p in {"1","2","3","4"}]
    if not periods:
        raise SystemExit("PRZMA_REPAIR_FAILED no valid periods")
    out=financial_repair_shard_path(ROOT,"przma",args.year,args.version)
    if out.exists():
        print(f"PRZMA_REPAIR_EXISTS file={out.name}; immutable checkpoint kept")
        return

    provider=KapBulkFinancialProvider()
    stamp=datetime.now(timezone.utc).isoformat()
    rows=[]
    missing=[]
    rejected=[]
    for period in periods:
        arc=provider.download_archive(args.year,period)
        print(f"PRZMA_REPAIR_ARCHIVE_OK year={args.year} period={period} files={len(arc.names)}")
        result=arc.parse_ticker("PRZMA")
        if result is None:
            missing.append(period)
            print(f"PRZMA_REPAIR_MISSING year={args.year} period={period}")
            continue
        facts=result.get("facts") or {}
        required=("assets","equity","revenue","operating_profit","net_income")
        absent=[k for k in required if facts.get(k) is None]
        if result.get("status")!="PARSED_HIGH_CONFIDENCE" or absent:
            rejected.append({"period":period,"status":result.get("status"),"missing":absent})
            print(f"PRZMA_REPAIR_REJECT year={args.year} period={period} status={result.get('status')} missing={absent}")
            continue
        payload={
            **result,
            "provider_id":provider.provider_id,
            "upstream_vendor":provider.upstream_vendor,
            "retrieved_at":stamp,
            "repair_overlay":"przma_ytd_period_columns",
            "repair_version":args.version,
        }
        rows.append({
            "ticker":"PRZMA",
            "report_period":result["current_period"],
            "publication_date":None,
            "statement_scope":result.get("statement_scope") or "UNKNOWN",
            "payload":json.dumps(payload,ensure_ascii=False),
            "source_url":arc.source_url,
        })
        print(f"PRZMA_REPAIR_OK year={args.year} period={period} report_period={result['current_period']} quality={result.get('quality_score')}")
    if rejected:
        raise SystemExit(f"PRZMA_REPAIR_FAILED rejected={rejected}")
    if not rows:
        raise SystemExit(f"PRZMA_REPAIR_FAILED no high-confidence rows; missing={missing}")
    out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(
        rows,
        columns=["ticker","report_period","publication_date","statement_scope","payload","source_url"],
    ).to_parquet(out,index=False)
    print(f"PRZMA_REPAIR_SHARD_WRITTEN file={out.name} rows={len(rows)} missing={missing} periods={periods}")

if __name__=="__main__":
    main()
