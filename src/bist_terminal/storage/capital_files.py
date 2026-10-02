from __future__ import annotations
from pathlib import Path


def capital_parquet_files(root: Path) -> list[Path]:
    d=Path(root)/"data"/"parquet"/"capital"
    return sorted(d.glob("capital_*.parquet")) if d.exists() else []


def capital_shard_path(root: Path, offset: int, count: int) -> Path:
    if count < 1:
        raise ValueError("count must be >= 1")
    end=offset+count-1
    return Path(root)/"data"/"parquet"/"capital"/f"capital_{offset:03d}_{end:03d}.parquet"
