"""Build an immutable bank financial repair overlay for one KAP year."""
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
from bist_terminal.providers.bist_universe import BistIndexUniverseProvider
from bist_terminal.storage.financial_files import financial_repair_shard_path


def main():
    ap=ArgumentParser()
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--version",type=int,default=1)
    args=ap.parse_args()

    out=financial_repair_shard_path(ROOT,"banks",args.year,args.version)
    if out.exists():
        print(f"BANK_REPAIR_EXISTS file={out.name}; immutable checkpoint kept")
        return

    universe=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(["XBANK"])
    tickers=universe.tickers
    print(f"BANK_REPAIR_UNIVERSE tickers={tickers}")

    provider=KapBulkFinancialProvider()
    stamp=datetime.now(timezone.utc).isoformat()
    rows=[]
    rejected=[]
    missing_files=[]
    for period in ("1","2","3","4"):
        arc=provider.download_archive(args.year,period)
        print(f"BANK_REPAIR_ARCHIVE_OK year={args.year} period={period} files={len(arc.names)}")
        for ticker in tickers:
            result=arc.parse_ticker(ticker)
            if not result:
                missing_files.append(f"{ticker}:{period}")
                print(f"BANK_REPAIR_MISSING ticker={ticker} year={args.year} period={period}")
                continue
            status=result.get("status")
            facts=result.get("facts") or {}
            required=("assets","equity","net_income")
            missing=[k for k in required if facts.get(k) is None]
            if status!="PARSED_HIGH_CONFIDENCE" or missing:
                rejected.append(f"{ticker}:{period}:{status}:missing={missing}")
                print(f"BANK_REPAIR_REJECT ticker={ticker} year={args.year} period={period} status={status} missing={missing}")
                continue
            payload={
                **result,
                "provider_id":provider.provider_id,
                "upstream_vendor":provider.upstream_vendor,
                "retrieved_at":stamp,
                "repair_overlay":"banks",
                "repair_version":args.version,
            }
            rows.append({
                "ticker":ticker,
                "report_period":result["current_period"],
                "publication_date":None,
                "statement_scope":result.get("statement_scope") or "UNKNOWN",
                "payload":json.dumps(payload,ensure_ascii=False),
                "source_url":arc.source_url,
            })
            print(
                f"BANK_REPAIR_OK ticker={ticker} year={args.year} period={period} "
                f"report_period={result['current_period']} quality={result.get('quality_score')} facts={sorted(facts)}"
            )

    if not rows:
        raise SystemExit("BANK_REPAIR_FAILED no high-confidence rows produced")
    out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(
        rows,
        columns=["ticker","report_period","publication_date","statement_scope","payload","source_url"],
    ).to_parquet(out,index=False)
    print(
        f"BANK_REPAIR_SHARD_WRITTEN file={out.name} rows={len(rows)} "
        f"rejected={len(rejected)} missing_files={len(missing_files)}"
    )


if __name__=="__main__":
    main()
