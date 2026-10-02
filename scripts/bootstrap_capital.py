"""Checkpoint current KAP total-share data in immutable bounded shards."""
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.providers.kap_capital import KapCapitalProvider
from bist_terminal.storage.capital_files import capital_shard_path


def main():
    ap=ArgumentParser()
    ap.add_argument("--offset",type=int,default=0)
    ap.add_argument("--limit",type=int,default=50)
    args=ap.parse_args()

    u=BistIndexUniverseProvider(
        cache_dir=ROOT/'data/cache/bist_universe'
    ).get_components(enabled_indices(ROOT/'config/indices.yaml'))
    tickers=u.tickers[args.offset:args.offset+args.limit]
    if not tickers:
        print(f"CAPITAL_BOOTSTRAP_DONE requested=0 active=0 degraded=0 offset={args.offset}")
        return
    out=capital_shard_path(ROOT,args.offset,len(tickers))
    if out.exists():
        print(f"CAPITAL_SHARD_EXISTS file={out.name}; immutable checkpoint kept")
        return

    p=KapCapitalProvider()
    mapping=p.company_mapping()
    print(f"CAPITAL_MAPPING_OK count={len(mapping)}")
    stamp=datetime.now(timezone.utc).isoformat()
    rows=[]; degraded=[]
    for ticker in tickers:
        try:
            rec=p.capital_for_ticker(ticker,mapping)
            shares=rec.get("total_shares")
            if rec.get("status")!="ACTIVE" or shares is None or shares<=0:
                degraded.append(ticker)
                print(f"CAPITAL_DEGRADED ticker={ticker} status={rec.get('status')} method={rec.get('method')}")
                continue
            rows.append({
                "ticker":ticker,
                "total_shares":float(shares),
                "method":rec.get("method"),
                "source_url":rec.get("source_url"),
                "mkk_member_oid":rec.get("mkk_member_oid"),
                "company_title":rec.get("company_title"),
                "retrieved_at":stamp,
            })
            print(f"CAPITAL_OK ticker={ticker} shares={shares} method={rec.get('method')}")
        except Exception as exc:
            degraded.append(ticker)
            print(f"CAPITAL_DEGRADED ticker={ticker} err={type(exc).__name__}:{exc}")

    if not rows:
        raise SystemExit("CAPITAL_BOOTSTRAP_FAILED no confirmed rows")
    out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows,columns=[
        "ticker","total_shares","method","source_url","mkk_member_oid","company_title","retrieved_at"
    ]).to_parquet(out,index=False)
    print(
        f"CAPITAL_SHARD_WRITTEN file={out.name} rows={len(rows)} "
        f"degraded={len(degraded)} degraded_tickers={degraded}"
    )
    print(
        f"CAPITAL_BOOTSTRAP_DONE requested={len(tickers)} active={len(rows)} "
        f"degraded={len(degraded)} offset={args.offset} limit={args.limit}"
    )


if __name__=="__main__":
    main()
