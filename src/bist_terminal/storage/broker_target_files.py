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
    frames=[]
    for path in broker_target_files(root):
        try:
            frame=pd.read_parquet(path)
        except Exception:
            continue
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return {}
    frame=pd.concat(frames,ignore_index=True)
    if as_of:
        end=pd.Timestamp(as_of).date()
        def effective_date(row):
            raw=row.get("portfolio_date") or row.get("observed_date")
            try:
                return pd.Timestamp(raw).date()
            except Exception:
                return None
        def fresh_row(row):
            d=effective_date(row)
            if d is None:
                return False
            age=(end-d).days
            return 0<=age<=max_age_days
        frame=frame[frame.apply(fresh_row,axis=1)]
    if frame.empty:
        return {}
    # Latest snapshot wins within each broker/ticker; different brokers remain independent.
    frame["_effective_date"]=frame.apply(
        lambda r: r.get("portfolio_date") or r.get("observed_date"),axis=1
    )
    frame=frame.sort_values(["broker_id","ticker","_effective_date","retrieved_at"],na_position="first")
    frame=frame.drop_duplicates(["broker_id","ticker"],keep="last")
    out={}
    for row in frame.to_dict("records"):
        ticker=str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        out.setdefault(ticker,[]).append(row)
    return out
