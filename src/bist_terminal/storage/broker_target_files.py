from __future__ import annotations

from pathlib import Path
import pandas as pd


def broker_target_dir(root: Path) -> Path:
    return Path(root)/"data"/"parquet"/"broker_targets"


def broker_target_snapshot_path(root: Path, broker_id: str, portfolio_date: str) -> Path:
    safe_broker="".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in broker_id)
    safe_date=str(portfolio_date).replace("/","-")
    return broker_target_dir(root)/f"{safe_broker}_{safe_date}.parquet"


def broker_target_files(root: Path) -> list[Path]:
    d=broker_target_dir(root)
    return sorted(d.glob("*.parquet")) if d.exists() else []


def load_latest_broker_targets(root: Path, as_of: str | None=None, max_age_days: int=90) -> dict[str,list[dict]]:
    # Each retrieval is a complete model portfolio, not a set of independent
    # recommendations. Mixing snapshots resurrects removed constituents.
    end = pd.Timestamp(as_of or pd.Timestamp.now(tz="UTC").date()).date()
    candidates = {}
    for path in broker_target_files(root):
        frame = pd.read_parquet(path)  # Corruption must not silently revive old data.
        if frame.empty:
            continue
        required = {"broker_id", "ticker", "retrieved_at", "target_price"}
        if not required.issubset(frame.columns):
            raise ValueError("broker snapshot schema unavailable")
        for (broker, retrieved), group in frame.groupby(["broker_id", "retrieved_at"], dropna=False):
            if not isinstance(broker, str) or not broker.strip() or pd.isna(retrieved):
                raise ValueError("broker snapshot identity unavailable")
            stamp = pd.Timestamp(retrieved)
            if pd.isna(stamp):
                raise ValueError("broker retrieval date unavailable")
            stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
            if stamp.date() > end:
                continue  # Do not leak a later observation into a historical view.
            rows = group.to_dict("records")
            if group["ticker"].duplicated().any():
                raise ValueError("duplicate broker snapshot ticker")
            key = broker.strip().casefold()
            rank = (stamp, path.name)
            if key not in candidates or rank > candidates[key][0]:
                candidates[key] = (rank, rows)
    out = {}
    for _, rows in candidates.values():
        for row in rows:
            def present(value):
                return value is not None and not pd.isna(value) and str(value).strip() != ""
            raw = row.get("portfolio_date")
            if not present(raw):
                raw = row.get("observed_date")
            if not present(raw):
                raw = row["retrieved_at"]
            try:
                effective = pd.Timestamp(raw).date()
                age = (end - effective).days
            except (ValueError, TypeError):
                continue
            if not 0 <= age <= max_age_days:
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            row["broker_id"] = str(row["broker_id"]).strip().casefold()
            for field in ("portfolio_date", "observed_date"):
                if not present(row.get(field)):
                    row[field] = None
            out.setdefault(ticker, []).append(row)
    return out
