from datetime import date

import pandas as pd
import pytest

pytest.importorskip('duckdb')
pytest.importorskip('pyarrow')

from bist_terminal.pipeline import history_refresh as module
from bist_terminal.pipeline.history_refresh import refresh_history
from bist_terminal.providers.base import Blocked, RateLimited, SchemaChanged, NoData
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.history_files import history_parquet_files


def bar(day='2026-10-05', **changes):
    return {'Date': day, 'Open': 100., 'High': 105., 'Low': 98., 'Close': 102.,
            'Adjusted Close': 101., 'Volume': 1000., 'source_url': 'https://example.invalid/history', **changes}


class FakeYahoo:
    provider_id = 'yahoo_chart'
    upstream_vendor = 'Yahoo market data feed'

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_history_bundle(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        response = self.responses[ticker]
        if isinstance(response, Exception):
            raise response
        history, actions = response
        return pd.DataFrame(history), pd.DataFrame(actions)


@pytest.fixture
def store(tmp_path):
    db = DuckDBStore(tmp_path / 'working.duckdb')
    yield db
    db.close()


def restore(tmp_path, db):
    for table in ('corporate_actions', 'daily_ohlcv'):
        for path in history_parquet_files(tmp_path, table):
            db.import_parquet(table, path)


def seed(store, tmp_path):
    store.upsert_ohlcv(dict(ticker='AAA', trade_date='2026-10-01', open=90., high=95., low=88.,
        close=92., adjusted_close=91., volume=100., provider_id='yahoo_chart',
        upstream_vendor='Yahoo market data feed', source_url='https://example.invalid/old',
        retrieved_at='2026-10-01T18:00:00Z'))
    target = tmp_path / 'data/parquet/daily_ohlcv.parquet'
    store.export_parquet('daily_ohlcv', target)
    return target


def test_incremental_preserves_base_excludes_future_and_is_idempotent(tmp_path, store):
    base = seed(store, tmp_path)
    original = base.read_bytes()
    provider = FakeYahoo({'AAA': ([bar('2026-10-02'), bar(), bar('2026-10-06')], [
        {'date': '2026-10-05', 'action_type': 'dividend', 'amount': 2., 'source_url': 'https://example.invalid/action'},
        {'date': '2026-10-06', 'action_type': 'dividend', 'amount': 3.},
    ])})
    result = refresh_history(tmp_path, store, ['AAA'], date(2026, 10, 5), provider)
    assert provider.calls == [('AAA', '2026-10-02', '2026-10-05')]
    assert result['rows_added'] == 2 and result['actions_added'] == 1
    assert result['current'] == 1 and result['status'] == 'ACTIVE'
    assert result['observations']['AAA'].trade_date == '2026-10-05'
    assert base.read_bytes() == original
    paths = history_parquet_files(tmp_path, 'daily_ohlcv')
    bytes_before = {p.name: p.read_bytes() for p in paths}
    again = refresh_history(tmp_path, store, ['AAA'], '2026-10-05', provider)
    assert again['already_current'] == 1 and again['rows_added'] == 0
    assert len(provider.calls) == 1
    assert bytes_before == {p.name: p.read_bytes() for p in paths}
    assert store.table_count('daily_ohlcv') == 3
    assert store.latest_history_date('AAA', 'yahoo_chart') == date(2026, 10, 5)


def test_successful_ticker_survives_failure_and_restart(tmp_path, store):
    provider = FakeYahoo({'AAA': ([bar()], []), 'BBB': Blocked('403'), 'CCC': ([bar()], [])})
    result = refresh_history(tmp_path, store, ['AAA', 'BBB', 'CCC'], '2026-10-05', provider)
    assert result['status'] == 'BLOCKED' and result['current'] == 1
    assert [call[0] for call in provider.calls] == ['AAA', 'BBB']
    restored = DuckDBStore(tmp_path / 'restart.duckdb')
    try:
        restore(tmp_path, restored)
        second = FakeYahoo({'BBB': ([bar()], []), 'CCC': ([bar()], [])})
        result = refresh_history(tmp_path, restored, ['AAA', 'BBB', 'CCC'], '2026-10-05', second)
        assert [call[0] for call in second.calls] == ['BBB', 'CCC']
        assert result['current'] == 3
    finally:
        restored.close()


def test_incremental_split_review_survives_restart_without_requery(tmp_path, store):
    seed(store, tmp_path)
    provider = FakeYahoo({'AAA': ([bar()], [
        {'date': '2026-10-05', 'action_type': 'split', 'split_ratio': '2:1',
         'source_url': 'https://example.invalid/action'},
    ])})
    first = refresh_history(tmp_path, store, ['AAA'], '2026-10-05', provider)
    assert first['corporate_action_review_tickers'] == ['AAA']
    assert first['status'] == 'PARTIAL' and first['current'] == 1
    restored = DuckDBStore(tmp_path / 'split-restart.duckdb')
    try:
        restore(tmp_path, restored)
        second = FakeYahoo({})
        resumed = refresh_history(tmp_path, restored, ['AAA'], '2026-10-05', second)
        assert second.calls == []
        assert resumed['corporate_action_review_tickers'] == ['AAA']
        assert module.unresolved_split_tickers(tmp_path, '2026-10-04') == []
        assert module.unresolved_split_tickers(tmp_path, '2027-10-07') == []
    finally:
        restored.close()


@pytest.mark.parametrize('failure', [Blocked('403'), RateLimited('429'), SchemaChanged('bad schema')])
def test_provider_errors_open_circuit_immediately(tmp_path, store, failure):
    provider = FakeYahoo({'AAA': failure, 'BBB': ([bar()], [])})
    result = refresh_history(tmp_path, store, ['AAA', 'BBB'], '2026-10-05', provider)
    assert result['circuit_open'] and len(provider.calls) == 1
    assert result['circuit_reason'].startswith(type(failure).__name__)


def test_two_consecutive_failures_stop_without_modifying_old_data(tmp_path, store):
    base = seed(store, tmp_path)
    original = base.read_bytes()
    provider = FakeYahoo({'AAA': ValueError('network'), 'BBB': ValueError('network'), 'CCC': ([bar()], [])})
    result = refresh_history(tmp_path, store, ['AAA', 'BBB', 'CCC'], '2026-10-05', provider)
    assert result['circuit_open'] and len(provider.calls) == 2
    assert store.table_count('daily_ohlcv') == 1
    assert base.read_bytes() == original


@pytest.mark.parametrize('changes', [{'Close': float('inf')}, {'Low': 110}, {'Open': None}, {'Volume': -1}])
def test_invalid_ohlcv_never_persists(tmp_path, store, changes):
    provider = FakeYahoo({'AAA': ([bar(**changes)], [])})
    result = refresh_history(tmp_path, store, ['AAA'], '2026-10-05', provider)
    assert result['status'] == 'PARTIAL' and result['errors']
    assert store.table_count('daily_ohlcv') == 0
    assert not history_parquet_files(tmp_path, 'daily_ohlcv')


def test_empty_or_symbol_missing_does_not_stop_other_tickers(tmp_path, store):
    provider = FakeYahoo({'AAA': ([], []), 'BBB': NoData('not found'), 'CCC': ([bar()], [])})
    result = refresh_history(tmp_path, store, ['AAA', 'BBB', 'CCC'], '2026-10-05', provider)
    assert not result['circuit_open'] and result['current'] == 1
    assert len(result['errors']) == 2 and len(provider.calls) == 3


def test_interrupted_write_cannot_advance_cursor_without_actions(tmp_path, store, monkeypatch):
    real_write = module._write_shard
    def fail_history(root, table, rows, columns):
        if table == 'daily_ohlcv':
            raise OSError('simulated crash before OHLCV persistence')
        return real_write(root, table, rows, columns)
    provider = FakeYahoo({'AAA': ([bar()], [{'date': '2026-10-05', 'action_type': 'dividend', 'amount': 2.}])})
    monkeypatch.setattr(module, '_write_shard', fail_history)
    result = refresh_history(tmp_path, store, ['AAA'], '2026-10-05', provider)
    assert result['current'] == 0
    assert not history_parquet_files(tmp_path, 'daily_ohlcv')
    assert len(history_parquet_files(tmp_path, 'corporate_actions')) == 1
    monkeypatch.setattr(module, '_write_shard', real_write)
    restore(tmp_path, store)
    result = refresh_history(tmp_path, store, ['AAA'], '2026-10-05', provider)
    assert result['current'] == 1
    assert store.table_count('corporate_actions') == 1
    assert len(history_parquet_files(tmp_path, 'corporate_actions')) == 1


def test_source_must_be_yahoo(tmp_path, store):
    provider = FakeYahoo({})
    provider.provider_id = 'bist_daily_bulletin'
    with pytest.raises(ValueError, match='Yahoo lineage'):
        refresh_history(tmp_path, store, [], '2026-10-05', provider)


def test_pacing_between_requests_is_injectable(tmp_path, store):
    provider = FakeYahoo({'AAA': ([bar()], []), 'BBB': ([bar()], [])})
    waits = []
    refresh_history(tmp_path, store, ['AAA', 'BBB'], '2026-10-05', provider, sleep=waits.append)
    assert waits == [0.2]
