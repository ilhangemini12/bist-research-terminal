from __future__ import annotations

from pathlib import Path

import pandas as pd


def roic_input_dir(root: Path) -> Path:
    return Path(root)/"data"/"parquet"/"roic_inputs"


def roic_input_files(root: Path) -> list[Path]:
    d=roic_input_dir(root)
    return sorted(d.glob("roic_inputs_*.parquet")) if d.exists() else []


def roic_input_shard_path(root: Path, year: int, period: str|int) -> Path:
    p=int(period)
    if p not in (1,2,3,4):
        raise ValueError("period must be 1..4")
    return roic_input_dir(root)/f"roic_inputs_{int(year)}_{p}.parquet"


def load_roic_input_records(root: Path) -> dict[str,list[dict]]:
    out: dict[str,list[dict]]={}
    for path in roic_input_files(root):
        df=pd.read_parquet(path)
        for row in df.to_dict("records"):
            clean={}
            for k,v in row.items():
                try:
                    if pd.isna(v):
                        v=None
                except (TypeError,ValueError):
                    pass
                clean[k]=v
            ticker=str(clean.get("ticker") or "").upper()
            if ticker:
                out.setdefault(ticker,[]).append(clean)
    for rows in out.values():
        rows.sort(key=lambda r:(int(r.get("archive_year") or 0),int(r.get("archive_period") or 0)))
    return out
