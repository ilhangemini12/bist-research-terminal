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


def test_removed_constituent_is_not_resurrected_and_future_snapshot_not_leaked(tmp_path):
    d = tmp_path/'data/parquet/broker_targets'
    d.mkdir(parents=True)
    def save(day, tickers):
        pd.DataFrame([dict(broker_id='g', ticker=t, target_price=100,
            model_portfolio_active=True, portfolio_date='2026-10-01',
            observed_date=day, retrieved_at=day+'T10:00:00Z') for t in tickers]).to_parquet(d/(day+'.parquet'))
    save('2026-10-11', ['THYAO','AKSA'])
    save('2026-10-12', ['THYAO'])
    save('2026-10-14', ['ASTOR'])
    assert set(load_latest_broker_targets(tmp_path, as_of='2026-10-11')) == {'THYAO','AKSA'}
    assert set(load_latest_broker_targets(tmp_path, as_of='2026-10-13')) == {'THYAO'}


def test_nan_report_date_uses_observation_and_stale_new_snapshot_does_not_revive_old(tmp_path):
    d = tmp_path/'data/parquet/broker_targets'
    d.mkdir(parents=True)
    pd.DataFrame([dict(broker_id='g', ticker='THYAO', target_price=100,
        portfolio_date=float('nan'), observed_date='2026-10-12',
        retrieved_at='2026-10-12T10:00:00Z')]).to_parquet(d/'a.parquet')
    assert 'THYAO' in load_latest_broker_targets(tmp_path, as_of='2026-10-13')
    pd.DataFrame([dict(broker_id='g', ticker='THYAO', target_price=200,
        portfolio_date='2026-01-01', observed_date='2026-10-13',
        retrieved_at='2026-10-13T10:00:00Z')]).to_parquet(d/'b.parquet')
    assert load_latest_broker_targets(tmp_path, as_of='2026-10-13') == {}
