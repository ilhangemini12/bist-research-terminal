"""Daily FREE-FIRST pipeline."""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import datetime
import math
import sys
import yaml
from datetime import timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.bist_bulletin import BistDailyBulletinProvider
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.quality.price_verification import verify_prices
from bist_terminal.exports.static import write_latest
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date, is_trading_day
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.history_files import history_parquet_files
from bist_terminal.storage.financial_files import financial_parquet_files
from bist_terminal.calculations.fundamental import safe_div
from bist_terminal.calculations.growth import yoy_from_quarters, ttm_growth
from bist_terminal.calculations.technical import add_indicators
from bist_terminal.financials.quarterly import standalone_quarters, ttm_from_quarters
from bist_terminal.financials.kap_bulk import notification_id_from_source_file


def load_runtime():
    return yaml.safe_load((ROOT / 'config/runtime.yaml').read_text(encoding='utf-8')) or {}


def build_price_providers(runtime, expected_trade_date):
    cfg = runtime.get('providers', {})
    out = []
    if cfg.get('bist_daily_bulletin', {}).get('enabled', True):
        out.append(BistDailyBulletinProvider(expected_trade_date))
    if cfg.get('yahoo_chart', {}).get('enabled', True):
        out.append(YahooChartProvider())
    return out


def provider_health(chain, attempts_by_ticker):
    counts = {}
    for _, attempts in attempts_by_ticker.items():
        for a in attempts:
            d = asdict(a)
            pid = d['provider_id']
            row = counts.setdefault(pid, Counter())
            row['success'] += int(d['ok'])
            row['failure'] += int(not d['ok'] and not d['skipped'])
            row['skipped'] += int(d['skipped'])
    rows = []
    for pid, state in chain.circuits.items():
        c = counts.get(pid, Counter())
        status = (
            'BLOCKED' if state.open and state.reason and 'Blocked' in state.reason
            else (
                'RATE_LIMITED' if state.open and state.reason and 'RateLimited' in state.reason
                else ('DEGRADED' if state.open or c['failure'] else 'ACTIVE')
            )
        )
        rows.append({
            'provider': pid,
            'status': status,
            'upstream': next(
                (getattr(p, 'upstream_vendor', 'unknown') for p in chain.providers if getattr(p, 'provider_id', '') == pid),
                'unknown',
            ),
            'successes': c['success'],
            'failures': c['failure'],
            'skipped_after_circuit': c['skipped'],
            'message': state.reason,
        })
    return rows


def restore_durable_state(store):
    """Restore core Parquet state plus immutable OHLCV/corporate-action shards."""
    restored = {}
    for table in ['prices', 'price_verification', 'index_membership_current', 'index_membership_history']:
        parquet = ROOT / f'data/parquet/{table}.parquet'
        restored[table] = store.import_parquet(table, parquet)
        if parquet.exists():
            print(
                f'DAILY_STATE_RESTORED table={table} '
                f'rows_added={restored[table]} total={store.table_count(table)}'
            )
    restored['financials'] = 0
    for parquet in financial_parquet_files(ROOT):
        added = store.import_parquet('financials', parquet)
        restored['financials'] += added
        print(
            f'DAILY_FINANCIAL_RESTORED file={parquet.name} '
            f'rows_added={added} total={store.table_count("financials")}'
        )
    for table in ['daily_ohlcv','corporate_actions']:
        restored[table] = 0
        for parquet in history_parquet_files(ROOT, table):
            added = store.import_parquet(table, parquet)
            restored[table] += added
            print(
                f'DAILY_HISTORY_RESTORED table={table} file={parquet.name} '
                f'rows_added={added} total={store.table_count(table)}'
            )
    return restored


def main():
    runtime = load_runtime()
    today = datetime.date.today()
    cal = load_calendar(ROOT / 'config/bist_calendar_2026.yaml')
    if not is_trading_day(today, cal):
        print(f'SKIP_NON_TRADING_DAY {today.isoformat()}')
        return

    expected = latest_expected_trade_date(today, cal).isoformat()
    index_codes = enabled_indices(ROOT / 'config/indices.yaml')
    try:
        universe = BistIndexUniverseProvider(
            cache_dir=ROOT / 'data/cache/bist_universe'
        ).get_components(index_codes)
        tickers = universe.tickers
        universe_status = 'CACHE' if universe.cache_used else 'LIVE_REFERENCE'
    except Exception as exc:
        write_latest({
            'mode': 'LIVE_PIPELINE_UNIVERSE_UNAVAILABLE',
            'data_as_of': {'prices': expected, 'financials': 'N/A', 'targets': 'N/A'},
            'stocks': [],
            'sources': [{
                'provider': 'bist_index_components',
                'status': 'DEGRADED',
                'upstream': 'Borsa Istanbul',
                'message': f'{type(exc).__name__}: {exc}',
            }],
            'summary': {'tracked_stocks': 0, 'verified_price_count': 0, 'unverified_price_count': 0},
            'universe': {'indices': index_codes, 'status': 'UNAVAILABLE'},
        })
        raise

    providers = build_price_providers(runtime, expected)
    threshold = int(runtime.get('pipeline', {}).get('provider_failure_threshold', 3))
    chain = FallbackChain(providers, failure_threshold=threshold)
    tolerance = float(runtime.get('price_verification', {}).get('tolerance_pct', 0.15))

    ticker_indices = {}
    for code, members in universe.members.items():
        for member in members:
            ticker_indices.setdefault(member['symbol'], []).append(code)

    def sector_for(ticker):
        memberships = set(ticker_indices.get(ticker, []))
        if 'XBANK' in memberships:
            return 'Bank'
        if 'XSGRT' in memberships:
            return 'Insurance'
        if 'XAKUR' in memberships:
            return 'Brokerage'
        if 'XUSIN' in memberships:
            return 'Industrials'
        return 'Other'

    rows = []
    attempts = {}
    store = None
    storage_status = 'ACTIVE'
    snapshot_rows = 0
    financial_latest = {}
    financial_history = {}
    technical_covered = 0

    try:
        store = DuckDBStore(ROOT / 'data/bist.duckdb')
        restore_durable_state(store)
        financial_latest = store.latest_financial_payloads()
        financial_history = store.financial_payload_history()
        stamp = datetime.datetime.now(timezone.utc).isoformat()
        for code, members in universe.members.items():
            normalized = [
                {'ticker': r['symbol'], 'company_name': r.get('name')}
                for r in members
            ]
            store.replace_current_membership(code, normalized, stamp)
            store.append_membership_snapshot(code, expected, normalized, stamp)
            snapshot_rows += len(normalized)
    except Exception as exc:
        storage_status = f'DEGRADED: {type(exc).__name__}: {exc}'

    for ticker in tickers:
        obs, att = chain.collect(ticker)
        attempts[ticker] = att
        vr = verify_prices(
            obs,
            expected,
            tolerance_pct=tolerance,
            official_ids={'bist_daily_bulletin'},
        )
        if store:
            for o in obs:
                store.upsert_price({
                    'ticker': o.ticker,
                    'trade_date': o.trade_date,
                    'close': o.close,
                    'volume': o.volume,
                    'provider_id': o.provider_id,
                    'upstream_vendor': o.upstream_vendor,
                    'status': vr.status,
                    'retrieved_at': o.retrieved_at,
                })
            store.upsert_verification({
                'ticker': ticker,
                'trade_date': expected,
                'verified_price': vr.verified_price,
                'status': vr.status,
                'sources': vr.sources,
                'upstreams': vr.upstreams,
                'max_diff_pct': vr.max_diff_pct,
                'reason': vr.reason,
                'verified_at': datetime.datetime.now(timezone.utc).isoformat(),
            })
        fin = financial_latest.get(ticker, {})
        fin_payload = fin.get('payload') or {}
        financial_notification_id = fin_payload.get('notification_id') or notification_id_from_source_file(fin_payload.get('source_file'))
        financial_notification_url = fin_payload.get('notification_url') or (
            f'https://www.kap.org.tr/tr/Bildirim/{financial_notification_id}' if financial_notification_id else None
        )
        facts = fin_payload.get('facts') or {}
        previous_facts = fin_payload.get('previous_facts') or {}
        financial_status = fin_payload.get('status')
        financial_ok = financial_status == 'PARSED_HIGH_CONFIDENCE' and bool(facts)
        annual = str(fin_payload.get('archive_period') or '') == '4'
        quarters = standalone_quarters(financial_history.get(ticker, []))
        qttm = ttm_from_quarters(quarters)
        flow_facts = qttm if qttm else (facts if financial_ok and annual else {})
        revenue_q=[q['facts'].get('revenue') for q in quarters]
        net_income_q=[q['facts'].get('net_income') for q in quarters]
        quarterly_growth={
            'revenue_quarter_yoy':yoy_from_quarters(revenue_q),
            'net_income_quarter_yoy':yoy_from_quarters(net_income_q),
            'revenue_ttm_growth':ttm_growth(revenue_q),
            'net_income_ttm_growth':ttm_growth(net_income_q),
        }
        ttm_status = 'TTM_4Q' if qttm else ('ANNUAL_FALLBACK' if financial_ok and annual else 'INSUFFICIENT_QUARTERS')

        def yoy(metric):
            cur = facts.get(metric)
            prev = previous_facts.get(metric)
            if cur is None or prev is None or prev <= 0:
                return None
            return cur / prev - 1

        derived = {}
        if financial_ok:
            derived = {
                'roe': safe_div(flow_facts.get('net_income'), facts.get('equity')),
                'roa': safe_div(flow_facts.get('net_income'), facts.get('assets')),
                'gross_margin': safe_div(flow_facts.get('gross_profit'), flow_facts.get('revenue')),
                'operating_margin': safe_div(flow_facts.get('operating_profit'), flow_facts.get('revenue')),
                'current_ratio': safe_div(facts.get('current_assets'), facts.get('current_liabilities')),
                'quick_ratio': safe_div(
                    (facts.get('current_assets') - (facts.get('inventories') or 0))
                    if facts.get('current_assets') is not None else None,
                    facts.get('current_liabilities'),
                ),
                'revenue_growth_yoy': yoy('revenue'),
                'net_income_growth_yoy': yoy('net_income'),
            }

        technical = {}
        history_rows = 0
        if store:
            try:
                history = store.history_frame(ticker)
                history_rows = len(history)
                if history_rows >= 20:
                    ind = add_indicators(history)
                    last = ind.iloc[-1]
                    def num(name):
                        value = last.get(name)
                        if value is None:
                            return None
                        try:
                            out = float(value)
                        except (TypeError, ValueError):
                            return None
                        return out if math.isfinite(out) else None
                    technical = {
                        'rsi7': num('RSI7'),
                        'rsi14': num('RSI14'),
                        'rsi21': num('RSI21'),
                        'sma5': num('SMA5'),
                        'sma10': num('SMA10'),
                        'sma20': num('SMA20'),
                        'sma50': num('SMA50'),
                        'sma100': num('SMA100'),
                        'sma200': num('SMA200'),
                        'ema12': num('EMA12'),
                        'ema20': num('EMA20'),
                        'ema26': num('EMA26'),
                        'ema50': num('EMA50'),
                        'ema200': num('EMA200'),
                        'macd': num('MACD'),
                        'macd_signal': num('MACD_SIGNAL'),
                        'macd_hist': num('MACD_HIST'),
                        'atr14': num('ATR14'),
                        'bb_mid': num('BB_MID'),
                        'bb_upper': num('BB_UPPER'),
                        'bb_lower': num('BB_LOWER'),
                        'adx': num('ADX'),
                        'plus_di': num('PLUS_DI'),
                        'minus_di': num('MINUS_DI'),
                        'roc5': num('ROC5'),
                        'roc20': num('ROC20'),
                        'obv': num('OBV'),
                        'volume_ma20': num('VOLUME_MA20'),
                        'volume_ratio': num('VOLUME_RATIO'),
                        'hvol20': num('HVOL20'),
                        'hvol60': num('HVOL60'),
                        'hvol252': num('HVOL252'),
                        'dist_52w_high': num('DIST_52W_HIGH'),
                        'dist_52w_low': num('DIST_52W_LOW'),
                    }
                    if technical.get('rsi14') is not None:
                        technical_covered += 1
            except Exception as exc:
                print(f'TECHNICAL_DEGRADED {ticker} {type(exc).__name__}: {exc}')

        rows.append({
            'ticker': ticker,
            'indices': sorted(ticker_indices.get(ticker, [])),
            'sector': sector_for(ticker),
            'price': vr.verified_price,
            'close': vr.verified_price,
            'price_status': vr.status,
            'verification_reason': vr.reason,
            'trade_date': vr.trade_date,
            'sources': vr.sources,
            'source_lineage': vr.upstreams,
            'max_diff_pct': vr.max_diff_pct,
            'financial_report_period': fin.get('report_period'),
            'financial_status': financial_status,
            'financial_quality_score': fin_payload.get('quality_score'),
            'financial_source_url': fin.get('source_url'),
            'financial_notification_id': financial_notification_id,
            'financial_notification_url': financial_notification_url,
            'assets': facts.get('assets') if financial_ok else None,
            'equity': facts.get('equity') if financial_ok else None,
            'cash': facts.get('cash') if financial_ok else None,
            'current_assets': facts.get('current_assets') if financial_ok else None,
            'current_liabilities': facts.get('current_liabilities') if financial_ok else None,
            'inventories': facts.get('inventories') if financial_ok else None,
            'financial_quarters_available': len(quarters),
            'ttm_status': ttm_status,
            'ttm_quarters_used': qttm.get('quarters_used') if qttm else [],
            'revenue_ttm': flow_facts.get('revenue') if financial_ok else None,
            'gross_profit_ttm': flow_facts.get('gross_profit') if financial_ok else None,
            'operating_profit_ttm': flow_facts.get('operating_profit') if financial_ok else None,
            'net_income_ttm': flow_facts.get('net_income') if financial_ok else None,
            'cash_from_operations_ttm': flow_facts.get('cash_from_operations') if financial_ok else None,
            'technical_history_rows': history_rows,
            **derived,
            **quarterly_growth,
            **technical,
        })

    if store:
        for table in [
            'prices',
            'price_verification',
            'index_membership_current',
            'index_membership_history',
        ]:
            store.export_parquet(table, ROOT / f'data/parquet/{table}.parquet')
        history_count = store.table_count('index_membership_history')
        store.close()
        print(
            f'UNIVERSE_SNAPSHOT_OK date={expected} '
            f'rows_written={snapshot_rows} history_rows={history_count}'
        )
    else:
        history_count = 0

    verified = sum(r['price_status'] == 'VERIFIED_2X' for r in rows)
    financial_covered = sum(r.get('financial_status') == 'PARSED_HIGH_CONFIDENCE' for r in rows)
    financial_periods = [r.get('financial_report_period') for r in rows if r.get('financial_status') == 'PARSED_HIGH_CONFIDENCE' and r.get('financial_report_period')]
    financial_as_of = max(financial_periods) if financial_periods else 'N/A'
    sources = [
        {
            'provider': 'bist_index_components',
            'status': 'ACTIVE',
            'upstream': 'Borsa Istanbul',
            'message': f'{universe_status}; {len(tickers)} unique tickers',
        },
        {
            'provider': 'duckdb_store',
            'status': 'ACTIVE' if storage_status == 'ACTIVE' else 'DEGRADED',
            'upstream': 'local',
            'message': storage_status,
        },
    ] + provider_health(chain, attempts)
    sources.append({
        'provider': 'kap_bulk_financials',
        'status': 'ACTIVE' if financial_covered else 'DEGRADED',
        'upstream': 'KAP / MKK',
        'successes': financial_covered,
        'failures': len(rows) - financial_covered,
        'skipped_after_circuit': 0,
        'message': f'Latest normalized high-confidence financial coverage: {financial_covered}/{len(rows)}',
    })

    write_latest({
        'mode': 'LIVE_PIPELINE',
        'data_as_of': {
            'prices': expected,
            'financials': financial_as_of,
            'targets': 'terms-compatible discovery partial',
        },
        'stocks': rows,
        'sources': sources,
        'summary': {
            'tracked_stocks': len(rows),
            'verified_price_count': verified,
            'unverified_price_count': len(rows) - verified,
            'financial_high_confidence_count': financial_covered,
            'financial_coverage_pct': round((financial_covered / len(rows) * 100), 1) if rows else 0,
            'technical_rsi14_count': technical_covered,
            'technical_coverage_pct': round((technical_covered / len(rows) * 100), 1) if rows else 0,
        },
        'universe': {
            'indices': index_codes,
            'status': universe_status,
            'snapshot_date': expected,
            'history_status': 'ACCUMULATING_FROM_2026-10-01',
            'history_rows': history_count,
            'members_by_index': {k: len(v) for k, v in universe.members.items()},
        },
    })
    print(
        f'LIVE_PIPELINE_OK expected={expected} tracked={len(rows)} '
        f'verified={verified} unverified={len(rows)-verified} financials={financial_covered}/{len(rows)} technical={technical_covered}/{len(rows)} universe={universe_status}'
    )


if __name__ == '__main__':
    main()
