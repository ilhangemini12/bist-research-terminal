"""Checkpoint the public Gedik stock model portfolio as a facts-only immutable snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import hashlib
import json

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.gedik_model import GedikModelPortfolioProvider
from bist_terminal.storage.broker_target_files import broker_target_snapshot_path


def persist_snapshot(root, result, now=None):
    now = now or datetime.now(timezone.utc)
    portfolio_date=result.get("portfolio_date")
    rows=result.get("rows") or []
    if not rows:
        raise SystemExit("GEDIK_TARGET_BOOTSTRAP_FAILED missing rows")
    observed_date=now.date().isoformat()
    # Public page contents may change without a new displayed report date.
    # Preserve both observations, including same-day corrections, immutably.
    facts = sorted(rows, key=lambda row: row["ticker"])
    digest = hashlib.sha256(json.dumps(facts, sort_keys=True, allow_nan=False).encode()).hexdigest()[:16]
    out=broker_target_snapshot_path(root,result["broker_id"],observed_date + "_" + now.strftime("%H%M%S%fZ") + "_" + digest)
    if out.exists():
        print(f"GEDIK_TARGET_SNAPSHOT_EXISTS file={out.name}; immutable checkpoint kept")
        return out
    stamp=now.isoformat()
    frame=pd.DataFrame([
        {
            **row,
            "observed_date":observed_date,
            "date_basis":"BROKER_UPDATE_DATE" if portfolio_date else "OBSERVED_CURRENT_PUBLIC_PAGE",
            "retrieved_at":stamp,
        }
        for row in rows
    ],columns=[
        "broker_id","broker_name","ticker","company_name","target_price",
        "model_portfolio_active","portfolio_date","observed_date","date_basis","source_url","retrieved_at"
    ])
    if frame["ticker"].duplicated().any():
        raise SystemExit("GEDIK_TARGET_BOOTSTRAP_FAILED duplicate tickers")
    out.parent.mkdir(parents=True,exist_ok=True)
    frame.to_parquet(out,index=False)
    print(
        f"GEDIK_TARGET_SNAPSHOT_WRITTEN file={out.name} rows={len(frame)} "
        f"portfolio_date={portfolio_date} observed_date={observed_date} tickers={frame['ticker'].tolist()}"
    )

    return out


def main():
    result = GedikModelPortfolioProvider(timeout=30).fetch()
    persist_snapshot(ROOT, result)


if __name__=="__main__":
    main()
