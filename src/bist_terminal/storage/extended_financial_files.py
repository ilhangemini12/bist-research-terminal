from __future__ import annotations

from pathlib import Path
import math

import pandas as pd


def extended_metric_dir(root: Path) -> Path:
    return Path(root)/"data"/"parquet"/"extended_financials"


def extended_metric_files(root: Path) -> list[Path]:
    d=extended_metric_dir(root)
    return sorted(d.glob("extended_financials_*.parquet")) if d.exists() else []


def extended_metric_shard_path(root: Path, year: int, period: str|int) -> Path:
    p=int(period)
    if p not in (1,2,3,4):
        raise ValueError("period must be 1..4")
    return extended_metric_dir(root)/f"extended_financials_{int(year)}_{p}.parquet"


def load_extended_metric_records(root: Path) -> dict[str,list[dict]]:
    out: dict[str,list[dict]]={}
    for path in extended_metric_files(root):
        df=pd.read_parquet(path)
        for row in df.to_dict("records"):
            clean={}
            for k,v in row.items():
                if isinstance(v,float) and math.isnan(v):
                    v=None
                clean[k]=v
            ticker=str(clean.get("ticker") or "").upper()
            if ticker:
                out.setdefault(ticker,[]).append(clean)
    for rows in out.values():
        rows.sort(key=lambda r:(int(r.get("archive_year") or 0),int(r.get("archive_period") or 0)))
    return out
