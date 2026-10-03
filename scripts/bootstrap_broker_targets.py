"""Checkpoint the public Gedik stock model portfolio as a facts-only immutable snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.gedik_model import GedikModelPortfolioProvider
from bist_terminal.storage.broker_target_files import broker_target_snapshot_path


def main():
    provider=GedikModelPortfolioProvider(timeout=30)
    result=provider.fetch()
    portfolio_date=result.get("portfolio_date")
    rows=result.get("rows") or []
    if not portfolio_date or not rows:
        raise SystemExit("GEDIK_TARGET_BOOTSTRAP_FAILED missing date/rows")
    out=broker_target_snapshot_path(ROOT,result["broker_id"],portfolio_date)
    if out.exists():
        print(f"GEDIK_TARGET_SNAPSHOT_EXISTS file={out.name}; immutable checkpoint kept")
        return
    stamp=datetime.now(timezone.utc).isoformat()
    frame=pd.DataFrame([
        {
            **row,
            "retrieved_at":stamp,
        }
        for row in rows
    ],columns=[
        "broker_id","broker_name","ticker","company_name","target_price",
        "model_portfolio_active","portfolio_date","source_url","retrieved_at"
    ])
    if frame["ticker"].duplicated().any():
        raise SystemExit("GEDIK_TARGET_BOOTSTRAP_FAILED duplicate tickers")
    out.parent.mkdir(parents=True,exist_ok=True)
    frame.to_parquet(out,index=False)
    print(
        f"GEDIK_TARGET_SNAPSHOT_WRITTEN file={out.name} rows={len(frame)} "
        f"portfolio_date={portfolio_date} tickers={frame['ticker'].tolist()}"
    )


if __name__=="__main__":
    main()
