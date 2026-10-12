"""Daily explicit KAP share-count checks with resumable per-ticker receipts.

One canonical pipeline writer is required. Failed requests never overwrite good
capital snapshots. A provider-wide daily circuit prevents subsequent runs from
hammering an unavailable or access-restricted upstream.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from uuid import uuid4

import pandas as pd

from bist_terminal.providers.kap_capital import KapCapitalProvider
from bist_terminal.storage.capital_files import load_capital_records


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc)


def _access_code(exc):
    return getattr(getattr(exc, 'response', None), 'status_code', None)


def _acceptable(record, ticker):
    try:
        shares = float(record.get('total_shares'))
    except (TypeError, ValueError, OverflowError):
        return False
    return (record.get('ticker') == ticker and record.get('status') == 'ACTIVE'
            and record.get('method') == 'EXPLICIT_TOTAL_SHARE_COUNT'
            and not isinstance(record.get('total_shares'), bool)
            and math.isfinite(shares) and shares > 0)


def refresh_capital(root, tickers, provider=None, *, pause_seconds=2.0) -> dict:
    """Fetch mapping once and check each ticker at most once per UTC day.

    Successful receipts are reusable only while their shard exists. Access/rate
    restrictions, malformed mapping and two consecutive generic errors open a
    persistent daily circuit. All failure details are bounded and omit raw
    exception strings, which can contain sensitive request metadata.
    """
    root = Path(root)
    tickers = sorted({str(t).upper().removesuffix('.IS') for t in tickers})
    if any(not re.fullmatch(r'[A-Z0-9]{1,12}', t) for t in tickers):
        raise ValueError('Invalid capital ticker')
    if not math.isfinite(pause_seconds) or pause_seconds < 0:
        raise ValueError('pause_seconds must be finite and non-negative')
    now = _utc_now()
    day = now.date().isoformat()
    state = root / 'data/state/capital_refresh' / day
    circuit = state / '_circuit.json'
    report = dict(status='PARTIAL', provider_id='kap_capital', upstream_vendor='KAP',
                  checked_at=now.isoformat(), check_date=day, requested=len(tickers),
                  refreshed=0, skipped=0, stale=0, attempted=0, errors=[], shards=[],
                  circuit_reason=None)
    if not tickers:
        report['status'] = 'NOT CONFIGURED'
        return report
    pending = []
    for ticker in tickers:
        receipt = _read(state / f'{ticker}.json')
        if receipt.get('status') == 'ACTIVE/TESTED' and receipt.get('shard') and (root / receipt['shard']).is_file():
            report['skipped'] += 1
            report['shards'].append(receipt['shard'])
        elif receipt.get('status') == 'STALE':
            report['stale'] += 1
            report['errors'].append({'ticker': ticker, 'reason': receipt.get('reason', 'prior_failed_check'), 'cached': True})
        else:
            pending.append(ticker)
    prior_circuit = _read(circuit)
    if pending and prior_circuit:
        report['stale'] += len(pending)
        report.update(status='BLOCKED', circuit_reason=prior_circuit.get('reason'))
        return report
    if not pending:
        report['status'] = 'ACTIVE/TESTED' if not report['stale'] else 'PARTIAL'
        return report

    # A daily rate limit must not permanently starve the alphabetic tail. Only
    # reorder after honoring today's receipts/circuit; never reopen a blocked day.
    snapshots = load_capital_records(root)
    def last_checked(ticker):
        value = snapshots.get(ticker, {}).get('retrieved_at')
        try:
            parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp(), ticker
        except (TypeError, ValueError, OverflowError):
            return float('-inf'), ticker
    pending.sort(key=last_checked)
    report['scheduling'] = 'oldest_successful_check_first'
    report['pause_seconds'] = pause_seconds

    def open_circuit(reason):
        report['circuit_reason'] = reason
        _atomic_json(circuit, {'checked_at': _utc_now().isoformat(), 'reason': reason})

    provider = provider or KapCapitalProvider()
    try:
        mapping = provider.company_mapping()
        if (not isinstance(mapping, dict) or not mapping
                or any(not isinstance(v, dict) or not v.get('mkk_member_oid') for v in mapping.values())):
            raise ValueError('mapping_schema_unavailable')
    except Exception as exc:
        code = _access_code(exc)
        reason = f'HTTP_{code}' if code in (401, 403, 429) else 'mapping_unavailable'
        report['errors'].append({'stage': 'mapping', 'reason': reason, 'error': type(exc).__name__})
        open_circuit(reason)
        report.update(status='BLOCKED', stale=report['stale'] + len(pending))
        return report

    consecutive_errors = 0
    for i, ticker in enumerate(pending):
        if pause_seconds:
            time.sleep(pause_seconds)
        report['attempted'] += 1
        reason = None
        try:
            record = provider.capital_for_ticker(ticker, mapping)
            if not isinstance(record, dict) or not _acceptable(record, ticker):
                reason = 'explicit_finite_shares_unavailable'
                consecutive_errors = 0
            else:
                checked_at = _utc_now()
                stamp = checked_at.strftime('%Y%m%dT%H%M%S%fZ')
                shard = root / 'data/parquet/capital' / f'capital_zzrefresh_{stamp}_{ticker}.parquet'
                shard.parent.mkdir(parents=True, exist_ok=True)
                tmp = shard.with_name(shard.name + '.' + uuid4().hex + '.tmp')
                row = {k: record.get(k) for k in ('ticker', 'method', 'source_url', 'mkk_member_oid', 'company_title')}
                row.update(total_shares=float(record['total_shares']), retrieved_at=checked_at.isoformat(),
                           checked_at=checked_at.isoformat(), provider_id='kap_capital', upstream_vendor='KAP')
                try:
                    pd.DataFrame([row]).to_parquet(tmp, index=False)
                    # Link publishes a complete file and cannot replace an existing snapshot.
                    os.link(tmp, shard)
                finally:
                    tmp.unlink(missing_ok=True)
                relative = str(shard.relative_to(root))
                _atomic_json(state / f'{ticker}.json', dict(status='ACTIVE/TESTED', ticker=ticker,
                             checked_at=checked_at.isoformat(), shard=relative, total_shares=row['total_shares']))
                report['shards'].append(relative)
                report['refreshed'] += 1
                consecutive_errors = 0
        except Exception as exc:
            consecutive_errors += 1
            code = _access_code(exc)
            reason = f'HTTP_{code}' if code in (401, 403, 429) else type(exc).__name__
            if code in (401, 403, 429):
                open_circuit(reason)
            elif consecutive_errors >= 2:
                open_circuit('two_consecutive_errors')
        if reason:
            report['stale'] += 1
            report['errors'].append({'ticker': ticker, 'reason': reason})
            _atomic_json(state / f'{ticker}.json', dict(status='STALE', ticker=ticker,
                         checked_at=_utc_now().isoformat(), reason=reason))
        if report['circuit_reason']:
            report['stale'] += len(pending) - i - 1
            break
    report['status'] = ('BLOCKED' if report['circuit_reason'] else
                        'PARTIAL' if report['stale'] else 'ACTIVE/TESTED')
    return report
