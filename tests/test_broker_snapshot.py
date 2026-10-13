from datetime import datetime, timezone
from scripts.bootstrap_broker_targets import persist_snapshot
from bist_terminal.storage.broker_target_files import load_latest_broker_targets


def test_same_report_date_can_capture_removal_and_same_day_reversion(tmp_path):
    def result(tickers):
        return dict(broker_id='g', portfolio_date='2026-10-01', rows=[dict(
            broker_id='g', ticker=t, target_price=100, portfolio_date='2026-10-01',
            model_portfolio_active=True) for t in tickers])
    a = persist_snapshot(tmp_path, result(['THYAO','AKSA']), datetime(2026,10,13,9,tzinfo=timezone.utc))
    original = a.read_bytes()
    b = persist_snapshot(tmp_path, result(['THYAO']), datetime(2026,10,13,10,tzinfo=timezone.utc))
    assert set(load_latest_broker_targets(tmp_path, '2026-10-13')) == {'THYAO'}
    c = persist_snapshot(tmp_path, result(['THYAO','AKSA']), datetime(2026,10,13,11,tzinfo=timezone.utc))
    assert set(load_latest_broker_targets(tmp_path, '2026-10-13')) == {'THYAO','AKSA'}
    assert a.read_bytes() == original and len({a,b,c}) == 3
