"""Daily FREE-FIRST pipeline."""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import datetime
import math
import os
import sys
import yaml
from datetime import timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices
from bist_terminal.models import PriceObservation
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.providers.bist_bulletin import BistDailyBulletinProvider
from bist_terminal.providers.registry import FallbackChain
from bist_terminal.providers.spk import SPKRegistryProvider
from bist_terminal.providers.spk_news import recent_spk_disclosures
from bist_terminal.quality.price_verification import verify_prices, retain_same_trade_date_verified
from bist_terminal.exports.static import write_latest
from bist_terminal.quality.market_calendar import load_calendar, latest_expected_trade_date, is_trading_day, resolve_run_trade_date
from bist_terminal.storage.duckdb_store import DuckDBStore
from bist_terminal.storage.history_files import history_parquet_files
from bist_terminal.storage.financial_files import financial_parquet_files
from bist_terminal.storage.capital_files import load_capital_records
from bist_terminal.storage.extended_financial_files import load_extended_metric_records
from bist_terminal.storage.roic_input_files import load_roic_input_records
from bist_terminal.calculations.fundamental import safe_div
from bist_terminal.calculations.growth import yoy_from_quarters, ttm_growth
from bist_terminal.calculations.technical import add_indicators
from bist_terminal.calculations.valuation import compute_valuation
from bist_terminal.calculations.extended_valuation import compute_extended_valuation
from bist_terminal.calculations.sector import sector_stats, discount_to_median
from bist_terminal.financials.quarterly import standalone_quarters, ttm_from_quarters
from bist_terminal.financials.extended_metrics import derive_extended_ttm
from bist_terminal.financials.roic_inputs import derive_roic_ttm, derive_average_invested_capital, compute_roic
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
    requested_as_of = (os.environ.get('BIST_AS_OF_DATE') or '').strip() or None
    run_trade_date = resolve_run_trade_date(today, cal, requested_as_of)
    if run_trade_date is None:
        print(f'SKIP_NON_TRADING_DAY {today.isoformat()}')
        return
    expected = run_trade_date.isoformat()
    if requested_as_of:
        print(f'MANUAL_AS_OF_OVERRIDE expected={expected} today={today.isoformat()}')
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
    extended_metric_records = {}
    try:
        extended_metric_records = load_extended_metric_records(ROOT)
        extended_metrics_status = 'ACTIVE' if extended_metric_records else 'UNAVAILABLE'
    except Exception as exc:
        extended_metric_records = {}
        extended_metrics_status = f'DEGRADED: {type(exc).__name__}: {exc}'

    roic_input_records = {}
    try:
        roic_input_records = load_roic_input_records(ROOT)
        roic_inputs_status = 'ACTIVE' if roic_input_records else 'UNAVAILABLE'
    except Exception as exc:
        roic_input_records = {}
        roic_inputs_status = f'DEGRADED: {type(exc).__name__}: {exc}'

    try:
        capital_records = load_capital_records(ROOT)
        capital_status = 'ACTIVE'
    except Exception as exc:
        capital_records = {}
        capital_status = f'DEGRADED: {type(exc).__name__}: {exc}'

    kap_news = []
    try:
        kap_news = recent_spk_disclosures(
            SPKRegistryProvider(timeout=30),
            capital_records,
            datetime.date.fromisoformat(expected),
            days=7,
        )
        news_status = 'ACTIVE'
        print(
            f'SPK_NEWS_OK rows={len(kap_news)} '
            f'mapped={sum(bool(x.get("ticker")) for x in kap_news)}'
        )
    except Exception as exc:
        news_status = f'DEGRADED: {type(exc).__name__}: {exc}'
        print(f'SPK_NEWS_DEGRADED {news_status}')

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
        previous_verification = store.get_verification(ticker, expected) if store else None
        durable_obs = []
        if store:
            for r in store.price_rows(ticker, expected):
                durable_obs.append(PriceObservation(
                    ticker=r['ticker'],
                    market='BIST',
                    trade_date=r['trade_date'],
                    timestamp=r['retrieved_at'] or (r['trade_date'] + 'T18:10:00+03:00'),
                    close=float(r['close']),
                    currency='TRY',
                    adjusted=False,
                    volume=r.get('volume'),
                    provider_id=r.get('provider_id') or 'unknown',
                    upstream_vendor=r.get('upstream_vendor') or r.get('provider_id') or 'unknown',
                    source_url=None,
                    retrieved_at=r.get('retrieved_at'),
                ))
        merged_obs = obs + durable_obs
        vr = verify_prices(
            merged_obs,
            expected,
            tolerance_pct=tolerance,
            official_ids={'bist_daily_bulletin'},
        )
        vr = retain_same_trade_date_verified(vr, previous_verification, expected)
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
        capital = capital_records.get(ticker, {})
        valuation = compute_valuation(
            price_status=vr.status,
            price=vr.verified_price,
            total_shares=capital.get('total_shares'),
            net_income_ttm=flow_facts.get('net_income') if financial_ok else None,
            equity=facts.get('equity') if financial_ok else None,
            revenue_ttm=flow_facts.get('revenue') if financial_ok else None,
        )
        extended_metrics = derive_extended_ttm(
            extended_metric_records.get(ticker, []),
            int(expected[:4]),
        )
        extended_valuation = compute_extended_valuation(
            market_cap=valuation.get('market_cap'),
            latest_financial_period=fin.get('report_period') if financial_ok else None,
            equity=facts.get('equity') if financial_ok else None,
            cash=facts.get('cash') if financial_ok else None,
            operating_profit_ttm=flow_facts.get('operating_profit') if financial_ok else None,
            revenue_ttm=flow_facts.get('revenue') if financial_ok else None,
            cash_from_operations_ttm=flow_facts.get('cash_from_operations') if financial_ok else None,
            extended=extended_metrics,
        )

        sector = sector_for(ticker)
        roic_result = {
            'roic_status': 'EXCLUDED_FINANCIAL_SECTOR' if sector in {'Bank','Insurance','Brokerage'} else 'INSUFFICIENT_INPUTS',
            'roic': None,
            'roic_basis': None,
            'roic_report_period': None,
            'effective_tax_rate': None,
            'average_invested_capital': None,
        }
        if sector not in {'Bank','Insurance','Brokerage'}:
            roic_ttm = derive_roic_ttm(
                roic_input_records.get(ticker, []),
                int(expected[:4]),
            )
            roic_period = roic_ttm.get('archive_period')
            capital_basis = (
                derive_average_invested_capital(
                    financial_history.get(ticker, []),
                    extended_metric_records.get(ticker, []),
                    int(expected[:4]),
                    int(roic_period),
                )
                if roic_period else {'status':'INSUFFICIENT_INPUTS'}
            )
            period_match = bool(
                roic_ttm.get('report_period')
                and fin.get('report_period')
                and roic_ttm.get('report_period') == fin.get('report_period')
            )
            roic_value = None
            if (
                roic_ttm.get('status') == 'ACTIVE'
                and capital_basis.get('status') == 'ACTIVE'
                and period_match
            ):
                roic_value = compute_roic(
                    roic_ttm.get('ebit_ttm'),
                    roic_ttm.get('effective_tax_rate'),
                    capital_basis.get('average_invested_capital'),
                )
            roic_result = {
                'roic_status': 'ACTIVE' if roic_value is not None else (
                    'PERIOD_MISMATCH' if roic_ttm.get('status') == 'ACTIVE'
                    and capital_basis.get('status') == 'ACTIVE'
                    and not period_match else 'INSUFFICIENT_INPUTS'
                ),
                'roic': roic_value,
                'roic_basis': (
                    f"{roic_ttm.get('basis')} | {capital_basis.get('basis')}"
                    if roic_value is not None else None
                ),
                'roic_report_period': roic_ttm.get('report_period'),
                'effective_tax_rate': roic_ttm.get('effective_tax_rate') if roic_value is not None else None,
                'average_invested_capital': capital_basis.get('average_invested_capital') if roic_value is not None else None,
            }
        dividend_ttm_per_share = 0.0
        if store:
            dividend_start = (
                datetime.date.fromisoformat(expected) - datetime.timedelta(days=365)
            ).isoformat()
            dividend_ttm_per_share = store.dividend_amount_sum(
                ticker, dividend_start, expected
            )
        dividend_yield = (
            dividend_ttm_per_share / vr.verified_price
            if vr.status == 'VERIFIED_2X' and vr.verified_price and vr.verified_price > 0
            else None
        )
        dividend_payout_ratio = None
        if (
            dividend_ttm_per_share > 0
            and capital.get('total_shares')
            and flow_facts.get('net_income')
            and flow_facts.get('net_income') > 0
        ):
            dividend_payout_ratio = (
                dividend_ttm_per_share * capital.get('total_shares')
                / flow_facts.get('net_income')
            )

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
                    rsi14_series = ind['RSI14'].dropna() if 'RSI14' in ind else []
                    rsi14_prev = (
                        float(rsi14_series.iloc[-2])
                        if hasattr(rsi14_series, 'iloc') and len(rsi14_series) >= 2 else None
                    )
                    rsi_recent_low = (
                        float(rsi14_series.tail(10).min())
                        if hasattr(rsi14_series, 'tail') and len(rsi14_series) else None
                    )
                    technical = {
                        'rsi7': num('RSI7'),
                        'rsi14': num('RSI14'),
                        'rsi14_prev': rsi14_prev,
                        'rsi_recent_low': rsi_recent_low,
                        'rsi21': num('RSI21'),
                        'volume': num('Volume'),
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
            'sector': sector,
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
            'total_shares': capital.get('total_shares'),
            'capital_method': capital.get('method'),
            'capital_source_url': capital.get('source_url'),
            'valuation_status': valuation.get('valuation_status'),
            'valuation_basis': ttm_status,
            'market_cap': valuation.get('market_cap'),
            'pe': valuation.get('pe'),
            'pb': valuation.get('pb'),
            'ps': valuation.get('ps'),
            'earnings_yield': valuation.get('earnings_yield'),
            **extended_valuation,
            **roic_result,
            'dividend_ttm_per_share': dividend_ttm_per_share,
            'dividend_yield': dividend_yield,
            'dividend_payout_ratio': dividend_payout_ratio,
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

    sector_groups = {}
    for row in rows:
        sector_groups.setdefault(row.get('sector') or 'Other', []).append(row)
    for sector, peers in sector_groups.items():
        pe_med = sector_stats([r.get('pe') if (r.get('pe') or 0) > 0 else None for r in peers])['median']
        pb_med = sector_stats([r.get('pb') if (r.get('pb') or 0) > 0 else None for r in peers])['median']
        ps_med = sector_stats([r.get('ps') if (r.get('ps') or 0) > 0 else None for r in peers])['median']
        roe_med = sector_stats([r.get('roe') for r in peers])['median']
        for row in peers:
            row['sector_pe_median'] = pe_med
            row['sector_pb_median'] = pb_med
            row['sector_ps_median'] = ps_med
            row['sector_roe_median'] = roe_med
            row['pe_discount_to_sector_median'] = discount_to_median(row.get('pe'), pe_med)
            row['pb_discount_to_sector_median'] = discount_to_median(row.get('pb'), pb_med)
            row['ps_discount_to_sector_median'] = discount_to_median(row.get('ps'), ps_med)
    print(f'SECTOR_STATS_OK sectors={len(sector_groups)}')

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
    capital_covered = sum(bool(r.get('total_shares')) for r in rows)
    valuation_active = sum(r.get('valuation_status') == 'ACTIVE' for r in rows)
    pe_covered = sum(r.get('pe') is not None for r in rows)
    pb_covered = sum(r.get('pb') is not None for r in rows)
    extended_active = sum(r.get('extended_valuation_status') == 'ACTIVE' for r in rows)
    ev_ebitda_covered = sum(r.get('ev_ebitda') is not None for r in rows)
    net_debt_ebitda_covered = sum(r.get('net_debt_ebitda') is not None for r in rows)
    fcf_yield_covered = sum(r.get('fcf_yield') is not None for r in rows)
    roic_covered = sum(r.get('roic_status') == 'ACTIVE' for r in rows)
    high_roic_count = sum((r.get('roic') or 0) > 0.15 for r in rows)
    dividend_positive = sum((r.get('dividend_yield') or 0) > 0 for r in rows)
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
        'provider': 'kap_capital_explicit',
        'status': 'ACTIVE' if capital_status == 'ACTIVE' and capital_covered else 'DEGRADED',
        'upstream': 'KAP / MKK',
        'successes': capital_covered,
        'failures': len(rows) - capital_covered,
        'skipped_after_circuit': 0,
        'message': (
            f'Explicit KAP total-share coverage: {capital_covered}/{len(rows)}; '
            f'experimental nominal-ratio fallback excluded'
            if capital_status == 'ACTIVE' else capital_status
        ),
    })
    sources.append({
        'provider': 'kap_extended_financial_metrics',
        'status': 'ACTIVE' if extended_metrics_status == 'ACTIVE' else 'DEGRADED',
        'upstream': 'KAP / MKK',
        'successes': extended_active,
        'failures': len(rows) - extended_active,
        'skipped_after_circuit': 0,
        'message': (
            f'Period-matched extended valuation inputs active: {extended_active}/{len(rows)}'
            if extended_metrics_status == 'ACTIVE' else extended_metrics_status
        ),
    })
    sources.append({
        'provider': 'kap_roic_inputs',
        'status': 'ACTIVE' if roic_inputs_status == 'ACTIVE' and roic_covered else 'DEGRADED',
        'upstream': 'KAP / MKK',
        'successes': roic_covered,
        'failures': len(rows) - roic_covered,
        'skipped_after_circuit': 0,
        'message': (
            f'Guarded non-financial ROIC active: {roic_covered}/{len(rows)}; '
            f'exact KAP EBIT/tax plus average invested capital, financial sectors excluded'
            if roic_inputs_status == 'ACTIVE' else roic_inputs_status
        ),
    })
    sources.append({
        'provider': 'spk_disclosures',
        'status': 'ACTIVE' if news_status == 'ACTIVE' else 'DEGRADED',
        'upstream': 'SPK',
        'successes': len(kap_news),
        'failures': 0 if news_status == 'ACTIVE' else 1,
        'skipped_after_circuit': 0,
        'message': (
            f'Recent 7-day official disclosure metadata: {len(kap_news)}; '
            f'exact current-universe title matches: {sum(bool(x.get("ticker")) for x in kap_news)}'
            if news_status == 'ACTIVE' else news_status
        ),
    })
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
            'news': expected,
        },
        'stocks': rows,
        'kap_news': kap_news,
        'sources': sources,
        'summary': {
            'tracked_stocks': len(rows),
            'verified_price_count': verified,
            'unverified_price_count': len(rows) - verified,
            'financial_high_confidence_count': financial_covered,
            'financial_coverage_pct': round((financial_covered / len(rows) * 100), 1) if rows else 0,
            'technical_rsi14_count': technical_covered,
            'technical_coverage_pct': round((technical_covered / len(rows) * 100), 1) if rows else 0,
            'capital_explicit_count': capital_covered,
            'capital_coverage_pct': round((capital_covered / len(rows) * 100), 1) if rows else 0,
            'valuation_active_count': valuation_active,
            'pe_count': pe_covered,
            'pb_count': pb_covered,
            'extended_valuation_active_count': extended_active,
            'ev_ebitda_count': ev_ebitda_covered,
            'net_debt_ebitda_count': net_debt_ebitda_covered,
            'fcf_yield_count': fcf_yield_covered,
            'roic_active_count': roic_covered,
            'high_roic_gt_15_count': high_roic_count,
            'dividend_positive_count': dividend_positive,
            'kap_news_count': len(kap_news),
            'kap_news_mapped_count': sum(bool(x.get('ticker')) for x in kap_news),
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
        f'verified={verified} unverified={len(rows)-verified} financials={financial_covered}/{len(rows)} '
        f'technical={technical_covered}/{len(rows)} capital={capital_covered}/{len(rows)} '
        f'valuation_active={valuation_active}/{len(rows)} pe={pe_covered} pb={pb_covered} '
        f'extended_active={extended_active}/{len(rows)} ev_ebitda={ev_ebitda_covered} '
        f'net_debt_ebitda={net_debt_ebitda_covered} fcf_yield={fcf_yield_covered} '
        f'roic={roic_covered} high_roic={high_roic_count} '
        f'dividend_positive={dividend_positive} news={len(kap_news)} '
        f'news_mapped={sum(bool(x.get("ticker")) for x in kap_news)} universe={universe_status}'
    )


if __name__ == '__main__':
    main()
