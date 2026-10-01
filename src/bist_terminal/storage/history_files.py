from __future__ import annotations
from pathlib import Path


def history_parquet_files(root: Path, table: str) -> list[Path]:
    """Return frozen base history plus immutable batch shards in deterministic order."""
    base_dir = Path(root) / "data" / "parquet"
    files: list[Path] = []
    base = base_dir / f"{table}.parquet"
    if base.exists():
        files.append(base)
    shard_dir = base_dir / "history"
    if shard_dir.exists():
        files.extend(sorted(shard_dir.glob(f"{table}_*.parquet")))
    return files


def history_shard_path(root: Path, table: str, offset: int, count: int) -> Path:
    if count < 1:
        raise ValueError("count must be >= 1")
    end = offset + count - 1
    return Path(root) / "data" / "parquet" / "history" / f"{table}_{offset:03d}_{end:03d}.parquet"
