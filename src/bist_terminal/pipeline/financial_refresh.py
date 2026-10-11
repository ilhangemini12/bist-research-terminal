"""Bounded daily KAP refresh; immutable normalized facts, never raw archives.

The caller restores financial_parquet_files before calling and commits both the
new shards and data/state/financial_refresh receipts after a successful build.
One pipeline writer is required, as for all existing canonical checkpoint files.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from uuid import uuid4

import pandas as pd

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider
from bist_terminal.financials.extended_metrics import parse_extended_metrics
from bist_terminal.financials.roic_inputs import parse_roic_inputs
from bist_terminal.storage.extended_financial_files import load_extended_metric_records
from bist_terminal.storage.roic_input_files import load_roic_input_records

_COLUMNS = ['ticker', 'report_period', 'publication_date', 'statement_scope', 'payload', 'source_url']


def completed_quarters(expected_date: str | date) -> list[tuple[int, str, str]]:
    """Most recent two calendar quarter ends no later than the closed market day."""
    day = date.fromisoformat(str(expected_date))
    ends = [(date(y, m, monthrange(y, m)[1]), str(m // 3))
            for y in (day.year - 1, day.year) for m in (3, 6, 9, 12)]
    return [(d.year, q, d.isoformat()) for d, q in sorted(ends, reverse=True) if d <= day][:2]


def _stable(value):
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in {'retrieved_at', 'checked_at'}}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def _digest(value) -> str:
    raw = json.dumps(_stable(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _acceptable(result: dict, ticker: str, period_end: str) -> bool:
    facts = result.get('facts') or {}
    return (result.get('status') == 'PARSED_HIGH_CONFIDENCE'
            and result.get('ticker') == ticker
            and result.get('current_period') == period_end
            and result.get('currency') == 'TRY'
            and result.get('statement_scope') not in (None, '', 'UNKNOWN')
            and all(k in facts for k in ('assets', 'equity', 'net_income'))
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                    for v in facts.values()))



def _write_shard(root, prefix, rows):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    shard = root / 'data/parquet' / prefix / f'{prefix}_zzrefresh_{stamp}_{_digest(rows)[:16]}.parquet'
    shard.parent.mkdir(parents=True, exist_ok=True)
    tmp = shard.with_suffix('.tmp')
    try:
        pd.DataFrame(rows).to_parquet(tmp, index=False)
        with tmp.open('rb') as stream:
            os.fsync(stream.fileno())
        os.link(tmp, shard)
    finally:
        tmp.unlink(missing_ok=True)
    return shard


def _supplement_rows(archive, result, stamp, provider):
    # Parse the same selected statement; never download twice or combine scopes.
    raw = archive.zip.read(result['source_file'])
    common = dict(ticker=result['ticker'], archive_year=result['archive_year'],
                  archive_period=int(result['archive_period']), report_period=result['current_period'],
                  currency=result['currency'], scale=result.get('scale'),
                  statement_scope=result['statement_scope'], source_file=result['source_file'],
                  source_url=archive.source_url, retrieved_at=stamp,
                  provider_id=provider.provider_id, upstream_vendor=provider.upstream_vendor)
    out = {}
    specs = [
        ('extended_financials', parse_extended_metrics,
         ('short_term_borrowings', 'current_portion_long_term_borrowings', 'long_term_borrowings',
          'financial_debt', 'depreciation_amortization_ytd', 'capex_cash_outflow_ytd', 'capex_spend_ytd')),
        ('roic_inputs', parse_roic_inputs, ('ebit_ytd', 'pretax_profit_ytd', 'tax_expense_income_ytd')),
    ]
    for prefix, parser, fields in specs:
        metrics = parser(raw)
        # Missing statement metrics stay explicit N/A and replace stale same-period
        # facts when a newer KAP notification no longer exposes that metric.
        if metrics.get('current_period') not in (None, result['current_period']):
            raise ValueError('supplementary financial period mismatch')
        row = {**common, **{key: metrics.get(key) for key in fields},
               'observed_metrics_json': json.dumps(metrics.get('observed_metrics') or [], ensure_ascii=False)}
        if prefix == 'extended_financials':
            row['debt_components_complete'] = bool(metrics.get('debt_components_complete'))
        out[prefix] = row
    return out

def refresh_financials(root, store, tickers, expected_date, provider=None) -> dict:
    """Check <=2 archives, persist only changed high-confidence rows, return evidence.

    A successful same-market-day check is reused only if all its shards still
    exist. Failed checks have a two-attempt daily cap. A transport failure opens
    the circuit immediately; there is no hidden retry or paid fallback.
    """
    root = Path(root)
    expected_date = date.fromisoformat(str(expected_date)).isoformat()
    tickers = sorted({str(t).upper().removesuffix('.IS') for t in tickers})
    check_day = datetime.now(timezone.utc).date().isoformat()
    receipt = root / 'data/state/financial_refresh' / f'{check_day}_{expected_date}_{_digest(tickers)[:16]}.json'
    prior = {}
    if receipt.exists():
        try:
            prior = json.loads(receipt.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    if prior.get('status') == 'ACTIVE/TESTED' and all((root / p).exists() for p in prior.get('shards', [])):
        return {**prior, 'cached': True}
    if prior.get('attempts', 0) >= 2:
        return {**prior, 'status': 'BLOCKED', 'cached': True, 'circuit_reason': 'daily_attempt_limit'}

    report = dict(status='PARTIAL', expected_market_date=expected_date,
                  checked_at=datetime.now(timezone.utc).isoformat(), attempts=prior.get('attempts', 0) + 1,
                  requested=len(tickers), archives_checked=0, parsed=0, changed=0,
                  unchanged=0, review_rejected=0, missing=0, stale_rejected=0,
                  errors=[], shards=list(prior.get('shards', [])), cached=False,
                  extended_financials_changed=0, roic_inputs_changed=0)
    provider = provider or KapBulkFinancialProvider()
    report['provider_id'] = provider.provider_id
    report['upstream_vendor'] = provider.upstream_vendor
    if not tickers:
        report['status'] = 'NOT CONFIGURED'
        return report

    existing = {}
    for ticker, records in store.financial_payload_history().items():
        if ticker in tickers:
            for row in records:
                existing[(ticker, row['report_period'], row['statement_scope'])] = row

    supplements = {}
    for prefix, loader in [('extended_financials', load_extended_metric_records), ('roic_inputs', load_roic_input_records)]:
        supplements[prefix] = {(t, row['report_period']): row for t, rows in loader(root).items() for row in rows}

    for year, period, period_end in completed_quarters(expected_date):
        try:
            archive = provider.download_archive(year, period)
        except Exception as exc:
            report['errors'].append({'year': year, 'period': period, 'stage': 'download', 'error': type(exc).__name__, 'http_status': getattr(getattr(exc, 'response', None), 'status_code', None)})
            if getattr(getattr(exc, 'response', None), 'status_code', None) == 404:
                continue  # A not-yet-published quarter does not suppress the prior quarter.
            # Timeout/access/rate-limit failures stop all calls to this host.
            break
        report['archives_checked'] += 1
        new_rows = []
        supplemental_rows = {'extended_financials': [], 'roic_inputs': []}
        try:
            for ticker in tickers:
                try:
                    result = archive.parse_ticker(ticker)
                    if result is None:
                        report['missing'] += 1
                        continue
                    if not _acceptable(result, ticker, period_end):
                        report['review_rejected'] += 1
                        continue
                    report['parsed'] += 1
                    payload = {**result, 'provider_id': provider.provider_id,
                               'upstream_vendor': provider.upstream_vendor, 'retrieved_at': report['checked_at']}
                    row = dict(ticker=ticker, report_period=period_end, publication_date=None,
                               statement_scope=result['statement_scope'], payload=payload, source_url=archive.source_url)
                    key = (ticker, period_end, row['statement_scope'])
                    old = existing.get(key)
                    old_payload = (old or {}).get('payload', {})
                    old_id = old_payload.get('notification_id')
                    new_id = payload.get('notification_id')
                    if old_id and (not new_id or int(new_id) < int(old_id)):
                        report['stale_rejected'] += 1
                        continue
                    for prefix, supplement in _supplement_rows(archive, result, report['checked_at'], provider).items():
                        previous = supplements[prefix].get((ticker, period_end))
                        if previous is None or _digest(previous) != _digest(supplement):
                            supplemental_rows[prefix].append(supplement)
                    if old and _digest(old_payload) == _digest(payload) and old.get('source_url') == row['source_url']:
                        report['unchanged'] += 1
                        continue
                    new_rows.append(row)
                except Exception as exc:
                    report['errors'].append({'ticker': ticker, 'period': period_end, 'stage': 'parse', 'error': type(exc).__name__})
                    if len(report['errors']) >= max(5, len(tickers) // 10):
                        break
        finally:
            if hasattr(archive, 'zip'):
                archive.zip.close()
        # Avoid accepting a partial archive after systemic parser failure.
        if len(report['errors']) >= max(5, len(tickers) // 10):
            break
        if new_rows:
            shard = _write_shard(root, 'financials', [{**r, 'payload': json.dumps(r['payload'], ensure_ascii=False, allow_nan=False)} for r in new_rows])
            store.import_parquet('financials', shard)
            report['changed'] += len(new_rows)
            report['shards'].append(str(shard.relative_to(root)))
        for prefix, rows in supplemental_rows.items():
            if rows:
                shard = _write_shard(root, prefix, rows)
                report[prefix + '_changed'] += len(rows)
                report['shards'].append(str(shard.relative_to(root)))
    report['status'] = 'ACTIVE/TESTED' if not report['errors'] else 'PARTIAL'
    _atomic_json(receipt, report)
    return report
