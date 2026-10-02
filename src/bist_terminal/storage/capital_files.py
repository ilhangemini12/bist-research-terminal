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


def load_capital_records(root: Path) -> dict[str, dict]:
    """Load only explicit KAP total-share checkpoints, keyed by ticker."""
    import pandas as pd

    out: dict[str, dict] = {}
    for path in capital_parquet_files(root):
        frame = pd.read_parquet(path)
        for row in frame.to_dict("records"):
            ticker = str(row.get("ticker") or "").upper()
            shares = row.get("total_shares")
            method = row.get("method")
            try:
                shares = float(shares)
            except (TypeError, ValueError):
                continue
            if not ticker or shares <= 0 or method != "EXPLICIT_TOTAL_SHARE_COUNT":
                continue
            out[ticker] = {
                "ticker": ticker,
                "total_shares": shares,
                "method": method,
                "source_url": row.get("source_url"),
                "mkk_member_oid": row.get("mkk_member_oid"),
                "company_title": row.get("company_title"),
                "retrieved_at": row.get("retrieved_at"),
            }
    return out
