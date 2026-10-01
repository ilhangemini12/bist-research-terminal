from __future__ import annotations
from pathlib import Path


def financial_parquet_files(root: Path) -> list[Path]:
    """Return frozen base financials plus immutable financial shards."""
    base_dir=Path(root)/"data"/"parquet"
    files=[]
    base=base_dir/"financials.parquet"
    if base.exists():
        files.append(base)
    shard_dir=base_dir/"financials"
    if shard_dir.exists():
        files.extend(sorted(shard_dir.glob("financials_*.parquet")))
    return files


def financial_shard_path(root: Path, year: int, period: str|int, offset: int, count: int) -> Path:
    if count < 1:
        raise ValueError("count must be >= 1")
    end=offset+count-1
    return Path(root)/"data"/"parquet"/"financials"/f"financials_{int(year)}_{period}_{offset:03d}_{end:03d}.parquet"
