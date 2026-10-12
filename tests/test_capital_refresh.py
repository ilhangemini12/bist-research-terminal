from datetime import datetime, timezone

import pandas as pd
import pytest
import requests

from bist_terminal.pipeline import capital_refresh as module
from bist_terminal.storage.capital_files import load_capital_records


class Provider:
    def __init__(self, values=None):
        self.values = values or {}
        self.calls = []
        self.mapping_calls = 0

    def company_mapping(self):
        self.mapping_calls += 1
        return {t: {'mkk_member_oid': t} for t in ('AAA', 'BBB', 'CCC')}

    def capital_for_ticker(self, ticker, mapping):
        self.calls.append(ticker)
        result = self.values.get(ticker, 100)
        if isinstance(result, Exception):
            raise result
        if isinstance(result, dict):
            return result
        return dict(ticker=ticker, total_shares=result, status='ACTIVE', method='EXPLICIT_TOTAL_SHARE_COUNT',
                    source_url='https://www.kap.org.tr/tr/sirket-bilgileri/genel/' + ticker)


def refresh(root, tickers, provider):
    return module.refresh_capital(root, tickers, provider, pause_seconds=0)


def test_daily_refresh_resume_and_next_day(tmp_path, monkeypatch):
    clock = [datetime(2026, 10, 9, 12, tzinfo=timezone.utc)]
    monkeypatch.setattr(module, '_utc_now', lambda: clock[0])
    p = Provider()
    first = refresh(tmp_path, ['AAA', 'BBB'], p)
    assert first['status'] == 'ACTIVE/TESTED'
    assert first['refreshed'] == 2
    assert load_capital_records(tmp_path)['AAA']['total_shares'] == 100
    again = refresh(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert again['skipped'] == 2 and again['refreshed'] == 1
    assert p.calls == ['AAA', 'BBB', 'CCC']
    assert p.mapping_calls == 2
    clock[0] = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    p.values['AAA'] = 200
    next_day = refresh(tmp_path, ['AAA'], p)
    assert next_day['refreshed'] == 1
    assert load_capital_records(tmp_path)['AAA']['total_shares'] == 200
    assert len(list((tmp_path / 'data/parquet/capital').glob('*.parquet'))) == 4


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, 0, None, True,
                               dict(ticker='AAA', total_shares=100, status='ACTIVE', method='SHARE_GROUP_NOMINAL_RATIO')])
def test_bad_values_preserve_good_snapshot(tmp_path, bad):
    d = tmp_path / 'data/parquet/capital'
    d.mkdir(parents=True)
    pd.DataFrame([dict(ticker='AAA', total_shares=90, method='EXPLICIT_TOTAL_SHARE_COUNT')]).to_parquet(d / 'capital_000.parquet')
    p = Provider({'AAA': bad})
    report = refresh(tmp_path, ['AAA'], p)
    assert report['status'] == 'PARTIAL' and report['stale'] == 1
    assert load_capital_records(tmp_path)['AAA']['total_shares'] == 90
    refresh(tmp_path, ['AAA'], p)
    assert p.calls == ['AAA']


@pytest.mark.parametrize('code', [401, 403, 429])
def test_access_circuit_is_persistent(tmp_path, code):
    response = requests.Response()
    response.status_code = code
    p = Provider({'AAA': requests.HTTPError(response=response)})
    report = refresh(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert report['status'] == 'BLOCKED'
    assert report['stale'] == 3 and p.calls == ['AAA']
    assert refresh(tmp_path, ['BBB'], p)['status'] == 'BLOCKED'
    assert p.mapping_calls == 1


def test_two_errors_stop_and_valid_record_resets_counter(tmp_path):
    p = Provider({'AAA': RuntimeError(), 'BBB': RuntimeError()})
    report = refresh(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert report['circuit_reason'] == 'two_consecutive_errors'
    assert p.calls == ['AAA', 'BBB']
    other = tmp_path / 'other'
    p = Provider({'AAA': RuntimeError(), 'CCC': RuntimeError()})
    report = refresh(other, ['AAA', 'BBB', 'CCC'], p)
    assert report['status'] == 'PARTIAL' and report['refreshed'] == 1


def test_invalid_mapping_stops_all_requests(tmp_path):
    p = Provider()
    p.company_mapping = lambda: {}
    report = refresh(tmp_path, ['AAA', 'BBB'], p)
    assert report['status'] == 'BLOCKED' and p.calls == []


def test_missing_success_shard_is_not_false_cache_hit(tmp_path):
    p = Provider()
    first = refresh(tmp_path, ['AAA'], p)
    (tmp_path / first['shards'][0]).unlink()
    assert refresh(tmp_path, ['AAA'], p)['refreshed'] == 1
    assert p.calls == ['AAA', 'AAA']


def test_write_failure_preserves_prior_snapshot(tmp_path, monkeypatch):
    p = Provider()
    monkeypatch.setattr(module.os, 'link', lambda *a: (_ for _ in ()).throw(OSError()))
    report = refresh(tmp_path, ['AAA'], p)
    assert report['stale'] == 1
    assert not list((tmp_path / 'data/parquet/capital').glob('*.parquet'))
    assert not list((tmp_path / 'data/parquet/capital').glob('*.tmp'))


def test_oldest_first_after_day_boundary_preserves_daily_circuit(tmp_path, monkeypatch):
    clock = [datetime(2026, 10, 11, 12, tzinfo=timezone.utc)]
    monkeypatch.setattr(module, '_utc_now', lambda: clock[0])
    response = requests.Response()
    response.status_code = 429
    p = Provider({'BBB': requests.HTTPError(response=response)})
    first = refresh(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert first['refreshed'] == 1 and p.calls == ['AAA', 'BBB']
    # Sorting is not a way around the existing provider circuit.
    assert refresh(tmp_path, ['CCC'], p)['status'] == 'BLOCKED'
    assert p.calls == ['AAA', 'BBB']
    clock[0] = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
    p.values = {}
    second = refresh(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert p.calls[2:] == ['BBB', 'CCC', 'AAA']
    assert second['refreshed'] == 3


def test_oldest_first_uses_timestamp_not_ticker_and_retains_pacing(tmp_path, monkeypatch):
    folder = tmp_path / 'data/parquet/capital'
    folder.mkdir(parents=True)
    pd.DataFrame([
        dict(ticker=t, total_shares=100, method='EXPLICIT_TOTAL_SHARE_COUNT', retrieved_at=stamp)
        for t, stamp in [('AAA', '2026-10-10T12:00:00+00:00'),
                         ('BBB', '2026-10-09T16:00:00+04:00'), ('CCC', None)]
    ]).to_parquet(folder / 'capital_000.parquet')
    pauses = []
    monkeypatch.setattr(module.time, 'sleep', pauses.append)
    p = Provider()
    result = module.refresh_capital(tmp_path, ['AAA', 'BBB', 'CCC'], p)
    assert p.calls == ['CCC', 'BBB', 'AAA']
    assert pauses == [2.0, 2.0, 2.0]
    assert result['scheduling'] == 'oldest_successful_check_first'
