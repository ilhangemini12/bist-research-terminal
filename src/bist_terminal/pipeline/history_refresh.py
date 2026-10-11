"""Resumable daily history refresh using immutable, Yahoo-only Parquet shards.

The restored store is the cursor. Corporate actions are published before OHLCV,
so an interrupted ticker cannot leave a durable history cursor ahead of its
corporate actions. Existing base files and bootstrap shards are never rewritten.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time

import pandas as pd

from bist_terminal.models import PriceObservation
from bist_terminal.providers.base import Blocked, RateLimited, SchemaChanged, NoData
from bist_terminal.providers.yahoo import YahooChartProvider

OHLCV_COLUMNS = [
    'ticker', 'trade_date', 'open', 'high', 'low', 'close', 'adjusted_close',
    'volume', 'provider_id', 'upstream_vendor', 'source_url', 'retrieved_at',
]
ACTION_COLUMNS = [
    'ticker', 'action_date', 'action_type', 'amount', 'split_ratio',
    'provider_id', 'source_url', 'retrieved_at',
]


def _number(value, *, optional=False, positive=False):
    if value is None or pd.isna(value):
        if optional:
            return None
        raise ValueError('missing numeric field')
    result = float(value)
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError('non-finite or invalid numeric field')
    return result


def _normalize(ticker, history, actions, start, end, provider, retrieved_at):
    bars, events = {}, {}
    for row in history.to_dict('records'):
        day = date.fromisoformat(str(row['Date'])[:10])
        if not start <= day <= end:
            continue
        values = {key.lower(): _number(row.get(key), positive=True)
                  for key in ('Open', 'High', 'Low', 'Close')}
        tolerance = max(values.values()) * 1e-8
        if (values['low'] > min(values['open'], values['close']) + tolerance
                or values['high'] < max(values['open'], values['close']) - tolerance
                or values['low'] > values['high']):
            raise ValueError(f'inconsistent OHLC at {day}')
        normalized = dict(
            ticker=ticker, trade_date=day.isoformat(), **values,
            adjusted_close=_number(row.get('Adjusted Close'), optional=True, positive=True),
            volume=_number(row.get('Volume'), optional=True),
            provider_id=provider.provider_id, upstream_vendor=provider.upstream_vendor,
            source_url=row.get('source_url'), retrieved_at=retrieved_at,
        )
        if day in bars and bars[day] != normalized:
            raise ValueError(f'conflicting duplicate history at {day}')
        bars[day] = normalized
    for row in actions.to_dict('records'):
        day = date.fromisoformat(str(row['date'])[:10])
        if not start <= day <= end:
            continue
        kind = row['action_type']
        if kind not in ('dividend', 'split'):
            raise ValueError('unknown corporate action')
        amount, ratio = None, None
        if kind == 'dividend':
            amount = _number(row.get('amount'))
        else:
            ratio = str(row.get('split_ratio', ''))
            parts = ratio.split(':')
            if len(parts) not in (1, 2):
                raise ValueError('invalid split ratio')
            for part in parts:
                _number(part, positive=True)
        normalized = dict(
            ticker=ticker, action_date=day.isoformat(), action_type=kind,
            amount=amount, split_ratio=ratio, provider_id=provider.provider_id,
            source_url=row.get('source_url'), retrieved_at=retrieved_at,
        )
        key = (day, kind)
        if key in events and events[key] != normalized:
            raise ValueError(f'conflicting duplicate action at {day}')
        events[key] = normalized
    return [bars[key] for key in sorted(bars)], [events[key] for key in sorted(events)]


def _write_shard(root, table, rows, columns):
    if not rows:
        return None
    # Retrieval time is metadata, not data identity: retries reuse identical data.
    content = [{k: v for k, v in row.items() if k != 'retrieved_at'} for row in rows]
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest()
    directory = Path(root) / 'data' / 'parquet' / 'history'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{table}_incremental_{digest}.parquet'
    if target.exists():
        return target
    fd, temporary = tempfile.mkstemp(prefix='.history-', suffix='.tmp', dir=directory)
    os.close(fd)
    try:
        pd.DataFrame(rows, columns=columns).to_parquet(temporary, index=False, compression='zstd')
        with open(temporary, 'rb') as stream:
            os.fsync(stream.fileno())
        # Unlike replace(), link cannot overwrite a shard created by another writer.
        try:
            os.link(temporary, target)
        except FileExistsError:
            pass
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def _observation(store, ticker, end, provider):
    row = store.con.execute(
        'select close,volume,source_url,retrieved_at from daily_ohlcv '
        'where ticker=? and trade_date=? and provider_id=?',
        [ticker, end, provider.provider_id],
    ).fetchone()
    if row is None:
        return None
    return PriceObservation(
        ticker=ticker, market='BIST', trade_date=end.isoformat(),
        timestamp=end.isoformat() + 'T00:00:00+03:00', close=float(row[0]),
        volume=row[1], currency='TRY', adjusted=False,
        provider_id=provider.provider_id, upstream_vendor=provider.upstream_vendor,
        source_url=row[2], retrieved_at=str(row[3]) if row[3] else None,
    )


def unresolved_split_tickers(root, expected_date):
    """Flag appended split events until their prior price basis is reviewed.

    Bootstrap history is a coherent provider snapshot. Incremental split events
    may change that basis across the append boundary; preserve the evidence and
    suppress technical calculations for the following 366 calendar days.
    Reading immutable action shards makes the guard survive runner restarts.
    """
    end = date.fromisoformat(str(expected_date)[:10])
    start = end - timedelta(days=366)
    flagged = set()
    directory = Path(root) / 'data/parquet/history'
    for path in directory.glob('corporate_actions_incremental_*.parquet'):
        actions = pd.read_parquet(path, columns=['ticker', 'action_date', 'action_type'])
        for row in actions.to_dict('records'):
            if row['action_type'] == 'split' and start <= date.fromisoformat(str(row['action_date'])[:10]) <= end:
                flagged.add(str(row['ticker']))
    return sorted(flagged)


def refresh_history(root, store, tickers, expected_date, provider=None, *,
                    pacing_seconds=0.2, sleep=time.sleep):
    """Refresh through the last closed session; never append a future/live bar.

    ``observations`` contains PriceObservation objects for the exact expected date
    and can replace redundant latest-price Yahoo requests. It is deliberately not
    JSON serializable; callers should omit it from persisted status reports.
    Provider-level blocking trips immediately, other failures after two consecutive
    tickers. Successful ticker shards survive either provider or runner failure.
    """
    end = date.fromisoformat(str(expected_date)[:10])
    provider = provider or YahooChartProvider()
    if provider.provider_id != 'yahoo_chart':
        raise ValueError('history publication is restricted to the Yahoo lineage')
    universe = list(dict.fromkeys(str(t).removesuffix('.IS') for t in tickers))
    result = dict(status='ACTIVE', expected_date=end.isoformat(),
                  requested=len(universe), updated=0, already_current=0,
                  current=0, stale=0, rows_added=0, actions_added=0,
                  errors=[], observations={}, circuit_open=False, circuit_reason=None, attempted=[])
    consecutive_failures = 0
    for ticker in universe:
        try:
            latest = store.latest_history_date(ticker, provider.provider_id)
            if latest and latest > end:
                latest = store.con.execute(
                    'select max(trade_date) from daily_ohlcv where ticker=? '
                    'and provider_id=? and trade_date<=?',
                    [ticker, provider.provider_id, end],
                ).fetchone()[0]
            if latest == end:
                result['already_current'] += 1
            else:
                start = latest + timedelta(days=1) if latest else end - timedelta(days=5 * 366)
                if result['attempted'] and pacing_seconds > 0:
                    sleep(pacing_seconds)
                result['attempted'].append(ticker)
                history, actions = provider.get_history_bundle(ticker, start.isoformat(), end.isoformat())
                retrieved_at = datetime.now(timezone.utc).isoformat()
                bars, events = _normalize(ticker, history, actions, start, end, provider, retrieved_at)
                # Write actions first: after a crash, restoring OHLCV implies that
                # all actions from that same request have already been persisted.
                action_path = _write_shard(root, 'corporate_actions', events, ACTION_COLUMNS)
                history_path = _write_shard(root, 'daily_ohlcv', bars, OHLCV_COLUMNS)
                store.con.execute('begin transaction')
                try:
                    actions_added = store.import_parquet('corporate_actions', action_path) if action_path else 0
                    rows_added = store.import_parquet('daily_ohlcv', history_path) if history_path else 0
                    store.con.execute('commit')
                except Exception:
                    store.con.execute('rollback')
                    raise
                result['actions_added'] += actions_added
                result['rows_added'] += rows_added
                if bars:
                    result['updated'] += 1
                if not bars or bars[-1]['trade_date'] != end.isoformat():
                    result['errors'].append({'ticker': ticker, 'type': 'NoData',
                        'message': 'Requested closed-day history bar is unavailable'})
            observation = _observation(store, ticker, end, provider)
            if observation:
                result['observations'][ticker] = observation
            consecutive_failures = 0
        except Exception as exc:
            consecutive_failures = 0 if isinstance(exc, NoData) else consecutive_failures + 1
            result['errors'].append({'ticker': ticker, 'type': type(exc).__name__, 'message': str(exc)[:240]})
            if isinstance(exc, (Blocked, RateLimited, SchemaChanged)) or consecutive_failures >= 2:
                result['circuit_open'] = True
                result['circuit_reason'] = type(exc).__name__ + ': ' + str(exc)[:240]
                result['status'] = 'BLOCKED' if isinstance(exc, Blocked) else 'PARTIAL'
                break
    # Query every ticker, including those after an open circuit, so existing good
    # data is counted accurately and can still feed downstream verification.
    for ticker in universe:
        observation = _observation(store, ticker, end, provider)
        if observation:
            result['observations'][ticker] = observation
    result['current'] = len(result['observations'])
    result['stale'] = len(universe) - result['current']
    result['corporate_action_review_tickers'] = [t for t in unresolved_split_tickers(root, end) if t in universe]
    if result['status'] != 'BLOCKED' and (result['stale'] or result['errors'] or result['corporate_action_review_tickers']):
        result['status'] = 'PARTIAL'
    return result
