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

_COUNTERS = ('archives_checked', 'parsed', 'changed', 'unchanged', 'review_rejected',
             'missing', 'stale_rejected', 'extended_financials_changed', 'roic_inputs_changed')


def _valid_shards(root: Path, paths) -> bool:
    if not isinstance(paths, list):
        return False
    for name in paths:
        if not isinstance(name, str):
            return False
        path = (root / name).resolve()
        if not path.is_relative_to((root / 'data/parquet').resolve()) or not path.is_file():
            return False
        try:
            # Existence alone is insufficient after a truncated restore.
            import pyarrow.parquet as pq
            pq.read_metadata(path)
        except Exception:
            return False
    return True


def _shard_dependencies(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for prefix in ('financials', 'extended_financials', 'roic_inputs')
                  for p in (root / 'data/parquet' / prefix).glob('*.parquet'))


def _daily_ledger(root: Path, day: str) -> tuple[Path, dict]:
    directory = root / 'data/state/financial_refresh'
    receipt = directory / f'{day}_kap_periods_v2.json'
    if receipt.exists():
        # A corrupt canonical ledger fails closed; never silently reset limits.
        ledger = json.loads(receipt.read_text(encoding='utf-8'))
        if ledger.get('schema_version') != 2 or ledger.get('utc_day') != day or not isinstance(ledger.get('periods'), dict):
            raise ValueError('Invalid KAP daily receipt')
        return receipt, ledger
    ledger = {'schema_version': 2, 'utc_day': day, 'periods': {}, 'host_circuit': None}
    # Legacy receipts were scoped to market day + ticker set, and attempts were
    # cumulative per receipt. Preserve every scope's used budget, bounded at 2.
    for path in sorted(directory.glob(f'{day}_*.json')):
        prior = json.loads(path.read_text(encoding='utf-8'))
        for error in prior.get('errors', []):
            if error.get('stage') != 'download' or not error.get('year') or not error.get('period'):
                continue
            key = f"{error['year']}Q{error['period']}"
            state = ledger['periods'].setdefault(key, {'attempts': 0, 'failures': 0, 'checks': {}})
            consumed = max(1, int(prior.get('attempts', 1)))
            state['attempts'] += consumed
            state['failures'] = min(2, state['failures'] + consumed)
            state['last_error'] = error
            # Unknown-stage legacy errors could be from HOME, not the archive.
            # Never infer period-scoped failure from a status code alone.
            if not (error.get('request_stage') == 'archive' and error.get('http_status') in (404, 500)):
                ledger['host_circuit'] = error
    _atomic_json(receipt, ledger)
    return receipt, ledger


def refresh_financials(root, store, tickers, expected_date, provider=None) -> dict:
    """Two downloads per call, with UTC-day per-period failures and host circuit.

    Market-date and ticker-set changes never reset budgets. Cached checks must
    match the ticker set and have readable financial shard dependencies.
    """
    root = Path(root)
    expected_date = date.fromisoformat(str(expected_date)).isoformat()
    tickers = sorted({str(t).upper().removesuffix('.IS') for t in tickers})
    check_day = datetime.now(timezone.utc).date().isoformat()
    provider = provider or KapBulkFinancialProvider()
    report = dict(status='PARTIAL', expected_market_date=expected_date,
                  checked_at=datetime.now(timezone.utc).isoformat(), requested=len(tickers),
                  errors=[], shards=[], cached=True, periods={}, downloads_attempted=0,
                  provider_id=provider.provider_id, upstream_vendor=provider.upstream_vendor,
                  **{key: 0 for key in _COUNTERS})
    if not tickers:
        report['status'] = 'NOT CONFIGURED'
        return report
    try:
        receipt, ledger = _daily_ledger(root, check_day)
        capital_circuit = root / 'data/state/capital_refresh' / check_day / '_circuit.json'
        if capital_circuit.exists():
            blocked = json.loads(capital_circuit.read_text(encoding='utf-8'))
            if not isinstance(blocked, dict):
                raise ValueError('invalid capital circuit')
            if blocked:
                ledger['host_circuit'] = {'stage': 'capital_refresh',
                    'reason': blocked.get('reason', 'capital_host_circuit')}
                _atomic_json(receipt, ledger)
    except (ValueError, OSError, TypeError):
        return {**report, 'status': 'BLOCKED', 'circuit_reason': 'invalid_daily_receipt'}
    ticker_key = _digest(tickers)
    existing = {}
    for ticker, records in store.financial_payload_history().items():
        if ticker in tickers:
            for row in records:
                existing[(ticker, row['report_period'], row['statement_scope'])] = row

    supplements = {}
    for prefix, loader in [('extended_financials', load_extended_metric_records), ('roic_inputs', load_roic_input_records)]:
        supplements[prefix] = {(t, row['report_period']): row for t, rows in loader(root).items() for row in rows}

    for year, period, period_end in completed_quarters(expected_date):
        key = f'{year}Q{period}'
        state = ledger['periods'].setdefault(key, {'attempts': 0, 'failures': 0, 'checks': {}})
        check = state.get('checks', {}).get(ticker_key)
        if check and check.get('tickers') == tickers and _valid_shards(root, check.get('shards')):
            report['periods'][key] = {**check, 'cached': True}
            report['shards'].extend(check['shards'])
            report['errors'].extend(check.get('errors', []))
            continue
        force_rebuild = bool(check)
        if ledger.get('host_circuit') or state.get('failures', 0) >= 2:
            reason = 'host_circuit' if ledger.get('host_circuit') else 'daily_period_failure_limit'
            report['periods'][key] = {'status': 'BLOCKED', 'reason': reason, 'cached': True,
                                      'last_error': state.get('last_error')}
            continue
        if report['downloads_attempted'] >= 2:
            report['periods'][key] = {'status': 'BLOCKED', 'reason': 'call_download_limit'}
            continue
        # Reserve a failure before I/O: interruption cannot reset the daily cap.
        state['attempts'] += 1
        state['failures'] += 1
        _atomic_json(receipt, ledger)
        report['downloads_attempted'] += 1
        report['cached'] = False
        try:
            archive = provider.download_archive(year, period)
        except Exception as exc:
            error = {'year': year, 'period': period, 'stage': 'download',
                     'error': type(exc).__name__,
                     'http_status': getattr(getattr(exc, 'response', None), 'status_code', None),
                     'request_stage': getattr(exc, 'kap_request_stage', 'unknown')}
            report['errors'].append(error)
            state['last_error'] = error
            if not (error['request_stage'] == 'archive' and error['http_status'] in (404, 500)):
                ledger['host_circuit'] = error
            report['periods'][key] = {'status': 'BLOCKED', 'last_error': error, 'cached': False}
            _atomic_json(receipt, ledger)
            continue
        before = {k: report[k] for k in _COUNTERS}
        errors_before = len(report['errors'])
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
                    fact_key = (ticker, period_end, row['statement_scope'])
                    old = existing.get(fact_key)
                    old_payload = (old or {}).get('payload', {})
                    old_id = old_payload.get('notification_id')
                    new_id = payload.get('notification_id')
                    if old_id and (not new_id or int(new_id) < int(old_id)):
                        report['stale_rejected'] += 1
                        continue
                    for prefix, supplement in _supplement_rows(archive, result, report['checked_at'], provider).items():
                        previous = supplements[prefix].get((ticker, period_end))
                        if force_rebuild or previous is None or _digest(previous) != _digest(supplement):
                            supplemental_rows[prefix].append(supplement)
                    if not force_rebuild and old and _digest(old_payload) == _digest(payload) and old.get('source_url') == row['source_url']:
                        report['unchanged'] += 1
                        continue
                    new_rows.append(row)
                except Exception as exc:
                    report['errors'].append({'ticker': ticker, 'period': period_end, 'stage': 'parse', 'error': type(exc).__name__})
                    if len(report['errors']) - errors_before >= max(5, len(tickers) // 10):
                        break
        finally:
            if hasattr(archive, 'zip'):
                archive.zip.close()
        # Avoid accepting a partial archive after systemic parser failure.
        if len(report['errors']) - errors_before >= max(5, len(tickers) // 10):
            report['periods'][key] = {'status': 'PARTIAL', 'reason': 'systemic_parse_failure'}
            _atomic_json(receipt, ledger)
            continue
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
        state['failures'] -= 1
        stats = {k: report[k] - before[k] for k in _COUNTERS}
        period_errors = report['errors'][errors_before:]
        healthy = not period_errors and not any(stats[k] for k in ('missing', 'review_rejected', 'stale_rejected'))
        check = {'status': 'ACTIVE/TESTED' if healthy else 'PARTIAL', 'tickers': tickers,
                 'shards': _shard_dependencies(root), 'stats': stats, 'errors': period_errors,
                 'checked_at': report['checked_at']}
        state.setdefault('checks', {})[ticker_key] = check
        report['periods'][key] = {**check, 'cached': False}
        _atomic_json(receipt, ledger)
    outcomes = [p['status'] for p in report['periods'].values()]
    report['status'] = ('ACTIVE/TESTED' if outcomes and all(s == 'ACTIVE/TESTED' for s in outcomes)
                        else 'BLOCKED' if outcomes and all(s == 'BLOCKED' for s in outcomes) else 'PARTIAL')
    report['shards'] = sorted(set(report['shards']))
    report['attempts'] = sum(p.get('attempts', 0) for p in ledger['periods'].values())
    report['host_circuit'] = ledger.get('host_circuit')
    return report
