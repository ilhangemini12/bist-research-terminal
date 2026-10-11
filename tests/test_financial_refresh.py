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
    assert report['status'] == 'ACTIVE/TESTED'
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
    assert one['status'] == two['status'] == 'PARTIAL'
    assert three['status'] == 'BLOCKED'
    assert len(provider.calls) == 2 and store.table_count('financials') == 0
    assert not financial_parquet_files(tmp_path)


def test_digest_ignores_only_retrieval_metadata():
    assert refresh._digest({'facts': {'a': 1}, 'retrieved_at': 'yesterday'}) == refresh._digest({'facts': {'a': 1}, 'retrieved_at': 'today'})
    assert refresh._digest({'facts': {'a': 1}}) != refresh._digest({'facts': {'a': 2}})
