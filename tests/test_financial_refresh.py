from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest
import requests

from bist_terminal.pipeline import financial_refresh as refresh
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.financial_files import financial_parquet_files
from bist_terminal.storage.extended_financial_files import load_extended_metric_records


class Provider:
    provider_id = 'kap_bulk_financials'
    upstream_vendor = 'KAP / MKK'

    def __init__(self, status='PARSED_HIGH_CONFIDENCE', value=100.0, notification=12, fail=False):
        self.status, self.value, self.notification, self.fail = status, value, notification, fail
        self.calls = []

    def download_archive(self, year, period):
        self.calls.append((year, period))
        if self.fail:
            raise requests.Timeout('provider unavailable')
        end = dict(refresh.completed_quarters('2026-10-09')) if False else {'3': '2026-09-30', '2': '2026-06-30'}
        def parse(ticker):
            if ticker == 'MISSING':
                return None
            return dict(ticker=ticker, status=self.status, current_period=end[period], quality_score=95,
                        statement_scope='Konsolide', currency='TRY', scale=1.0, archive_year=year,
                        archive_period=period, source_file=f'{ticker}_{self.notification}_{year}_{period}.xls',
                        notification_id=self.notification, facts=dict(assets=self.value, equity=10.0, net_income=1.0))
        return SimpleNamespace(source_url=f'https://www.kap.org.tr/{year}/{period}', parse_ticker=parse,
                               zip=SimpleNamespace(read=lambda name: b'fixture', close=lambda: None))


@pytest.fixture
def store(tmp_path):
    s = DuckDBStore(tmp_path / 'test.duckdb')
    yield s
    s.close()


@pytest.fixture(autouse=True)
def supplemental_parsers(monkeypatch):
    monkeypatch.setattr(refresh, 'parse_extended_metrics', lambda raw: dict(financial_debt=5.0, observed_metrics=['financial_debt']))
    monkeypatch.setattr(refresh, 'parse_roic_inputs', lambda raw: dict(ebit_ytd=2.0, observed_metrics=['ebit_ytd']))


def invalidate_receipts(root):
    for p in (root / 'data/state/financial_refresh').glob('*.json'):
        p.unlink()


def test_two_completed_quarters_and_year_boundary():
    assert refresh.completed_quarters('2026-01-02') == [(2025, '4', '2025-12-31'), (2025, '3', '2025-09-30')]
    assert refresh.completed_quarters('2026-09-29') == [(2026, '2', '2026-06-30'), (2026, '1', '2026-03-31')]


def test_bounded_refresh_daily_receipt_and_supplements(tmp_path, store):
    provider = Provider()
    report = refresh.refresh_financials(tmp_path, store, ['TEST', 'MISSING'], '2026-10-09', provider)
    assert report['status'] == 'PARTIAL'
    assert report['changed'] == 2 and report['missing'] == 2
    assert len(provider.calls) == 2
    assert report['extended_financials_changed'] == report['roic_inputs_changed'] == 2
    assert len(load_extended_metric_records(tmp_path)['TEST']) == 2
    again = refresh.refresh_financials(tmp_path, store, ['TEST', 'MISSING'], '2026-10-09', provider)
    assert again['cached'] and len(provider.calls) == 2
    assert datetime.now(timezone.utc).date().isoformat() in next((tmp_path / 'data/state/financial_refresh').glob('*.json')).name


def test_unchanged_facts_dont_create_shards_and_old_files_immutable(tmp_path, store):
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider())
    files = {p: p.read_bytes() for p in (tmp_path / 'data/parquet').rglob('*.parquet')}
    invalidate_receipts(tmp_path)
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider())
    assert result['changed'] == result['extended_financials_changed'] == result['roic_inputs_changed'] == 0
    assert result['unchanged'] == 2
    assert files == {p: p.read_bytes() for p in (tmp_path / 'data/parquet').rglob('*.parquet')}


def test_latest_overlay_wins_after_restore_and_preserves_old_shards(tmp_path, store):
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider())
    files = {p: p.read_bytes() for p in financial_parquet_files(tmp_path)}
    invalidate_receipts(tmp_path)
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider(value=200.0, notification=13))
    assert result['changed'] == 2
    assert all(p.read_bytes() == data for p, data in files.items())
    restored = DuckDBStore(tmp_path / 'restored.duckdb')
    try:
        for p in financial_parquet_files(tmp_path):
            restored.import_parquet('financials', p)
        assert restored.latest_financial_payloads()['TEST']['payload']['facts']['assets'] == 200.0
    finally:
        restored.close()


def test_review_cannot_replace_high_confidence(tmp_path, store):
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider())
    invalidate_receipts(tmp_path)
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider(status='PARSED_REVIEW_REQUIRED', value=0))
    assert result['changed'] == 0 and result['review_rejected'] == 2
    assert store.latest_financial_payloads()['TEST']['payload']['facts']['assets'] == 100.0


def test_stale_notification_does_not_replace_newer_filing(tmp_path, store):
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider(notification=20))
    invalidate_receipts(tmp_path)
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', Provider(notification=19, value=0))
    assert result['changed'] == 0 and result['stale_rejected'] == 2
    assert store.latest_financial_payloads()['TEST']['payload']['notification_id'] == 20


def test_transport_failure_opens_circuit_and_daily_attempt_cap(tmp_path, store):
    provider = Provider(fail=True)
    one = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    two = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    three = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert one['status'] == two['status'] == 'BLOCKED'
    assert three['status'] == 'BLOCKED'
    assert len(provider.calls) == 1 and store.table_count('financials') == 0
    assert not financial_parquet_files(tmp_path)


def test_digest_ignores_only_retrieval_metadata():
    assert refresh._digest({'facts': {'a': 1}, 'retrieved_at': 'yesterday'}) == refresh._digest({'facts': {'a': 1}, 'retrieved_at': 'today'})
    assert refresh._digest({'facts': {'a': 1}}) != refresh._digest({'facts': {'a': 2}})


def http_error(code, stage='archive'):
    response = requests.Response()
    response.status_code = code
    exc = requests.HTTPError('fixture HTTP failure', response=response)
    if stage is not None:
        exc.kap_request_stage = stage
    return exc


class QuarterFailureProvider(Provider):
    def __init__(self, code=500, stage='archive'):
        super().__init__()
        self.code, self.stage = code, stage

    def download_archive(self, year, period):
        if period == '3':
            self.calls.append((year, period))
            raise http_error(self.code, self.stage)
        return super().download_archive(year, period)


def legacy_receipt(root, code=500, attempts=2, suffix='market_universe', request_stage='archive'):
    day = datetime.now(timezone.utc).date().isoformat()
    path = root / 'data/state/financial_refresh' / f'{day}_{suffix}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'status': 'PARTIAL', 'attempts': attempts,
        'errors': [{'year': 2026, 'period': '3', 'stage': 'download',
                    'error': 'HTTPError', 'http_status': code, 'request_stage': request_stage}]}))
    return path


def test_migrate_exhausted_legacy_q3_allows_unattempted_q2(tmp_path, store):
    path = legacy_receipt(tmp_path)
    original = path.read_bytes()
    provider = Provider()
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert provider.calls == [(2026, '2')]
    assert result['status'] == 'PARTIAL'
    assert result['periods']['2026Q3']['reason'] == 'daily_period_failure_limit'
    assert result['periods']['2026Q2']['status'] == 'ACTIVE/TESTED'
    assert path.read_bytes() == original
    again = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-12', provider)
    assert again['cached'] and len(provider.calls) == 1
    # A different universe can check Q2, but must never resurrect exhausted Q3.
    refresh.refresh_financials(tmp_path, store, ['OTHER'], '2026-10-12', provider)
    assert provider.calls == [(2026, '2'), (2026, '2')]


@pytest.mark.parametrize('code', [404, 500])
def test_archive_failure_cap_survives_date_and_ticker_changes(tmp_path, store, code):
    provider = QuarterFailureProvider(code)
    first = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    second = refresh.refresh_financials(tmp_path, store, ['OTHER'], '2026-10-12', provider)
    third = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-13', provider)
    assert first['status'] == second['status'] == third['status'] == 'PARTIAL'
    assert first['downloads_attempted'] == second['downloads_attempted'] == 2
    assert third['downloads_attempted'] == 0
    assert provider.calls.count((2026, '3')) == 2
    assert all(not result['host_circuit'] for result in (first, second, third))


@pytest.mark.parametrize(('code', 'stage'), [(401, 'archive'), (403, 'archive'),
    (429, 'archive'), (503, 'archive'), (500, 'homepage'), (404, 'homepage'), (500, None)])
def test_host_circuit_persists_across_universe_and_market_date(tmp_path, store, code, stage):
    provider = QuarterFailureProvider(code, stage)
    first = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    second = refresh.refresh_financials(tmp_path, store, ['OTHER'], '2026-10-12', provider)
    assert first['status'] == second['status'] == 'BLOCKED'
    assert first['host_circuit']['http_status'] == code
    assert provider.calls == [(2026, '3')]


def test_legacy_access_denial_cannot_be_reset_by_migration(tmp_path, store):
    legacy_receipt(tmp_path, code=403, attempts=1)
    provider = Provider()
    result = refresh.refresh_financials(tmp_path, store, ['OTHER'], '2026-10-12', provider)
    assert result['status'] == 'BLOCKED' and not provider.calls


def test_unknown_stage_legacy_500_does_not_invent_period_scope(tmp_path, store):
    legacy_receipt(tmp_path, request_stage=None)
    provider = Provider()
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert result['status'] == 'BLOCKED' and not provider.calls


def test_missing_only_archive_does_not_download_repeatedly(tmp_path, store):
    provider = Provider()
    first = refresh.refresh_financials(tmp_path, store, ['MISSING'], '2026-10-09', provider)
    second = refresh.refresh_financials(tmp_path, store, ['MISSING'], '2026-10-09', provider)
    assert first['status'] == second['status'] == 'PARTIAL'
    assert second['cached'] and len(provider.calls) == 2


def test_success_cache_requires_exact_ticker_coverage(tmp_path, store):
    provider = Provider()
    one = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    two = refresh.refresh_financials(tmp_path, store, ['TEST', 'OTHER'], '2026-10-09', provider)
    assert one['status'] == two['status'] == 'ACTIVE/TESTED'
    assert len(provider.calls) == 4 and not two['cached']
    assert set(store.latest_financial_payloads()) == {'TEST', 'OTHER'}
    refresh.refresh_financials(tmp_path, store, ['other.IS', 'TEST'], '2026-10-12', provider)
    assert len(provider.calls) == 4


def test_deleted_shard_rebuilds_even_when_duckdb_still_has_rows(tmp_path, store):
    provider = Provider()
    first = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    removed = next(tmp_path / p for p in first['shards'] if '/financials/' in p)
    removed.unlink()
    recovered = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert recovered['status'] == 'ACTIVE/TESTED'
    assert recovered['changed'] > 0 and len(provider.calls) == 4
    restored = DuckDBStore(tmp_path / 'recovered.duckdb')
    try:
        for p in financial_parquet_files(tmp_path):
            restored.import_parquet('financials', p)
        history = restored.financial_payload_history()['TEST']
        assert {row['report_period'] for row in history} == {'2026-09-30', '2026-06-30'}
    finally:
        restored.close()
    cached = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert cached['cached'] and len(provider.calls) == 4


def test_download_cap_is_enforced_even_if_more_periods_requested(tmp_path, store, monkeypatch):
    monkeypatch.setattr(refresh, 'completed_quarters', lambda day:
        [(2026, '3', '2026-09-30'), (2026, '2', '2026-06-30'), (2026, '1', '2026-03-31')])
    provider = Provider()
    report = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert len(provider.calls) == report['downloads_attempted'] == 2
    assert report['periods']['2026Q1']['reason'] == 'call_download_limit'
    assert report['status'] == 'PARTIAL'


def test_corrupt_ledger_fails_closed(tmp_path, store):
    day = datetime.now(timezone.utc).date().isoformat()
    receipt = tmp_path / 'data/state/financial_refresh' / f'{day}_kap_periods_v2.json'
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{truncated')
    provider = Provider()
    report = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert report['status'] == 'BLOCKED' and not provider.calls
    assert receipt.read_text() == '{truncated'


@pytest.mark.parametrize('payload', [{'reason': 'HTTP_429'}, ['malformed']])
def test_capital_host_circuit_stops_financial_downloads(tmp_path, store, payload):
    day = datetime.now(timezone.utc).date().isoformat()
    circuit = tmp_path / 'data/state/capital_refresh' / day / '_circuit.json'
    circuit.parent.mkdir(parents=True)
    circuit.write_text(json.dumps(payload))
    provider = Provider()
    result = refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert result['status'] == 'BLOCKED' and provider.calls == []


def test_utc_day_reset_independent_of_market_date(tmp_path, store, monkeypatch):
    provider = Provider(fail=True)
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    current = datetime.now(timezone.utc)
    from datetime import timedelta
    class NextDay(datetime):
        @classmethod
        def now(cls, tz=None):
            return current + timedelta(days=1)
    monkeypatch.setattr(refresh, 'datetime', NextDay)
    refresh.refresh_financials(tmp_path, store, ['TEST'], '2026-10-09', provider)
    assert len(provider.calls) == 2
