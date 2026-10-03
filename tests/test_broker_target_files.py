from bist_terminal.storage.broker_target_files import (
    broker_target_snapshot_path,
    load_latest_broker_targets,
)
import pandas as pd


def test_snapshot_path_is_deterministic(tmp_path):
    p=broker_target_snapshot_path(tmp_path,"gedik_model_portfolio","2026-09-22")
    assert p.name=="gedik_model_portfolio_2026-09-22.parquet"


def test_loader_keeps_latest_per_broker_and_filters_age(tmp_path):
    d=tmp_path/"data"/"parquet"/"broker_targets"
    d.mkdir(parents=True)
    pd.DataFrame([
        {"broker_id":"g","broker_name":"G","ticker":"THYAO","target_price":400.0,"model_portfolio_active":True,"portfolio_date":"2026-07-01","source_url":"u","retrieved_at":"2026-07-01T00:00:00Z"},
        {"broker_id":"g","broker_name":"G","ticker":"THYAO","target_price":483.0,"model_portfolio_active":True,"portfolio_date":"2026-09-22","source_url":"u","retrieved_at":"2026-09-22T00:00:00Z"},
    ]).to_parquet(d/"g.parquet",index=False)
    out=load_latest_broker_targets(tmp_path,as_of="2026-10-02",max_age_days=90)
    assert out["THYAO"][0]["target_price"]==483.0
    assert out["THYAO"][0]["portfolio_date"]=="2026-09-22"
