from __future__ import annotations

from pathlib import Path
import json

TABLES = {
    'prices',
    'price_verification',
    'daily_ohlcv',
    'corporate_actions',
    'index_membership_current',
    'index_membership_history',
    'financials',
    'provider_health',
    'capital_current',
}


class DuckDBStore:
    """DuckDB state store. Parquet is the durable Git-friendly state/export format."""

    def __init__(self, path='data/bist.duckdb'):
        try:
            import duckdb
        except ImportError as e:
            raise RuntimeError('duckdb dependency missing; run pip install -r requirements.txt') from e
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.duckdb = duckdb
        self.con = duckdb.connect(str(path))
        self._init()

    def _init(self):
        self.con.execute('''create table if not exists prices(
          ticker varchar, trade_date date, close double, volume double, provider_id varchar, upstream_vendor varchar,
          status varchar, retrieved_at timestamp, primary key(ticker,trade_date,provider_id))''')
        self.con.execute('''create table if not exists price_verification(
          ticker varchar, trade_date date, verified_price double, status varchar, sources json, upstreams json,
          max_diff_pct double, reason varchar, verified_at timestamp, primary key(ticker,trade_date))''')
        self.con.execute('''create table if not exists daily_ohlcv(
          ticker varchar, trade_date date, open double, high double, low double, close double, adjusted_close double,
          volume double, provider_id varchar, upstream_vendor varchar, source_url varchar, retrieved_at timestamp,
          primary key(ticker,trade_date,provider_id))''')
        self.con.execute('''create table if not exists corporate_actions(
          ticker varchar, action_date date, action_type varchar, amount double, split_ratio varchar, provider_id varchar,
          source_url varchar, retrieved_at timestamp, primary key(ticker,action_date,action_type,provider_id))''')
        self.con.execute('''create table if not exists index_membership_current(
          index_code varchar, ticker varchar, company_name varchar, retrieved_at timestamp,
          primary key(index_code,ticker))''')
        self.con.execute('''create table if not exists index_membership_history(
          index_code varchar, snapshot_date date, ticker varchar, company_name varchar, retrieved_at timestamp,
          primary key(index_code,snapshot_date,ticker))''')
        self.con.execute('''create table if not exists financials(
          ticker varchar, report_period varchar, publication_date date, statement_scope varchar, payload json,
          source_url varchar, primary key(ticker,report_period,statement_scope))''')
        self.con.execute('''create table if not exists provider_health(
          provider_id varchar primary key,status varchar,last_success timestamp,last_failure timestamp,latest_data_date date,message varchar)''')
        self.con.execute('''create table if not exists capital_current(
          ticker varchar primary key,total_shares double,method varchar,source_url varchar,mkk_member_oid varchar,
          company_title varchar,retrieved_at timestamp)''')

    def close(self):
        self.con.close()

    def upsert_price(self, row: dict):
        self.con.execute(
            '''insert or replace into prices values (?,?,?,?,?,?,?,?)''',
            [row.get(k) for k in ['ticker','trade_date','close','volume','provider_id','upstream_vendor','status','retrieved_at']],
        )

    def upsert_verification(self, row: dict):
        self.con.execute(
            '''insert or replace into price_verification values (?,?,?,?,?,?,?,?,?)''',
            [
                row.get('ticker'), row.get('trade_date'), row.get('verified_price'), row.get('status'),
                json.dumps(row.get('sources') or []), json.dumps(row.get('upstreams') or []),
                row.get('max_diff_pct'), row.get('reason'), row.get('verified_at'),
            ],
        )

    def price_rows(self, ticker: str, trade_date) -> list[dict]:
        rows = self.con.execute(
            '''select ticker, trade_date, close, volume, provider_id, upstream_vendor, status, retrieved_at
               from prices
               where ticker=? and trade_date=?
               order by provider_id''',
            [ticker, trade_date],
        ).fetchall()
        return [{
            'ticker':r[0],
            'trade_date':str(r[1]) if r[1] else None,
            'close':r[2],
            'volume':r[3],
            'provider_id':r[4],
            'upstream_vendor':r[5],
            'status':r[6],
            'retrieved_at':str(r[7]) if r[7] else None,
        } for r in rows]

    def get_verification(self, ticker: str, trade_date) -> dict | None:
        row = self.con.execute(
            '''select ticker, trade_date, verified_price, status, sources, upstreams,
                      max_diff_pct, reason, verified_at
               from price_verification
               where ticker=? and trade_date=?''',
            [ticker, trade_date],
        ).fetchone()
        if not row:
            return None

        def decode_json(value):
            if value is None:
                return []
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return []
            return value

        return {
            'ticker': row[0],
            'trade_date': str(row[1]) if row[1] else None,
            'verified_price': row[2],
            'status': row[3],
            'sources': decode_json(row[4]),
            'upstreams': decode_json(row[5]),
            'max_diff_pct': row[6],
            'reason': row[7],
            'verified_at': str(row[8]) if row[8] else None,
        }

    def upsert_ohlcv(self, row: dict):
        self.con.execute(
            '''insert or replace into daily_ohlcv values (?,?,?,?,?,?,?,?,?,?,?,?)''',
            [row.get(k) for k in ['ticker','trade_date','open','high','low','close','adjusted_close','volume','provider_id','upstream_vendor','source_url','retrieved_at']],
        )

    def upsert_corporate_action(self, row: dict):
        self.con.execute(
            '''insert or replace into corporate_actions values (?,?,?,?,?,?,?,?)''',
            [row.get(k) for k in ['ticker','action_date','action_type','amount','split_ratio','provider_id','source_url','retrieved_at']],
        )

    def upsert_capital(self, row: dict):
        self.con.execute(
            '''insert or replace into capital_current values (?,?,?,?,?,?,?)''',
            [row.get(k) for k in ['ticker','total_shares','method','source_url','mkk_member_oid','company_title','retrieved_at']],
        )

    def capital_map(self) -> dict[str, dict]:
        rows=self.con.execute(
            '''select ticker,total_shares,method,source_url,mkk_member_oid,company_title,retrieved_at
               from capital_current'''
        ).fetchall()
        return {
            r[0]: {
                'ticker':r[0],'total_shares':r[1],'method':r[2],'source_url':r[3],
                'mkk_member_oid':r[4],'company_title':r[5],
                'retrieved_at':str(r[6]) if r[6] else None,
            } for r in rows
        }

    def upsert_financial(self, row: dict):
        payload = row.get('payload')
        if not isinstance(payload, str):
            payload = json.dumps(payload or {}, ensure_ascii=False)
        self.con.execute(
            '''insert or replace into financials values (?,?,?,?,?,?)''',
            [
                row.get('ticker'), row.get('report_period'), row.get('publication_date'),
                row.get('statement_scope') or 'UNKNOWN', payload, row.get('source_url'),
            ],
        )

    def latest_financial_payloads(self) -> dict[str, dict]:
        rows = self.con.execute('''
          select ticker, report_period, publication_date, statement_scope, payload, source_url
          from (
            select *, row_number() over (
              partition by ticker order by cast(report_period as date) desc, publication_date desc nulls last
            ) as rn
            from financials
          )
          where rn=1
        ''').fetchall()
        out = {}
        for ticker, report_period, publication_date, scope, payload, source_url in rows:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            out[ticker] = {
                'report_period': str(report_period),
                'publication_date': str(publication_date) if publication_date else None,
                'statement_scope': scope,
                'payload': payload or {},
                'source_url': source_url,
            }
        return out


    def financial_payload_history(self) -> dict[str, list[dict]]:
        rows = self.con.execute('''
          select ticker, report_period, publication_date, statement_scope, payload, source_url
          from financials
          order by ticker, cast(report_period as date), publication_date nulls last
        ''').fetchall()
        out: dict[str, list[dict]] = {}
        for ticker, report_period, publication_date, scope, payload, source_url in rows:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            out.setdefault(ticker, []).append({
                'ticker': ticker,
                'report_period': str(report_period),
                'publication_date': str(publication_date) if publication_date else None,
                'statement_scope': scope,
                'payload': payload or {},
                'source_url': source_url,
            })
        return out

    def replace_current_membership(self, index_code: str, rows: list[dict], retrieved_at: str):
        self.con.execute('delete from index_membership_current where index_code=?', [index_code])
        for r in rows:
            self.con.execute(
                'insert into index_membership_current values (?,?,?,?)',
                [index_code, r.get('ticker'), r.get('company_name') or r.get('name'), retrieved_at],
            )

    def append_membership_snapshot(self, index_code: str, snapshot_date, rows: list[dict], retrieved_at: str):
        """Persist an immutable-by-date universe snapshot for point-in-time backtests.

        Re-running the same trading date is idempotent because the primary key is
        (index_code, snapshot_date, ticker).
        """
        for r in rows:
            self.con.execute(
                'insert or replace into index_membership_history values (?,?,?,?,?)',
                [index_code, snapshot_date, r.get('ticker'), r.get('company_name') or r.get('name'), retrieved_at],
            )

    def membership_for_date(self, index_code: str, snapshot_date) -> list[str]:
        rows = self.con.execute(
            'select ticker from index_membership_history where index_code=? and snapshot_date=? order by ticker',
            [index_code, snapshot_date],
        ).fetchall()
        return [r[0] for r in rows]

    def latest_membership_snapshot_date(self, index_code: str):
        row = self.con.execute(
            'select max(snapshot_date) from index_membership_history where index_code=?',
            [index_code],
        ).fetchone()
        return row[0] if row and row[0] else None

    def dividend_amount_sum(self, ticker: str, start_date, end_date, provider_id: str = 'yahoo_chart') -> float:
        row = self.con.execute(
            '''select coalesce(sum(amount),0)
               from corporate_actions
               where ticker=? and provider_id=? and action_type='dividend'
                 and action_date>=? and action_date<=?''',
            [ticker, provider_id, start_date, end_date],
        ).fetchone()
        return float(row[0] or 0)

    def latest_history_date(self, ticker: str, provider_id: str):
        row = self.con.execute(
            'select max(trade_date) from daily_ohlcv where ticker=? and provider_id=?',
            [ticker, provider_id],
        ).fetchone()
        return row[0] if row and row[0] else None

    def history_frame(self, ticker: str, provider_id: str = 'yahoo_chart'):
        """Return normalized OHLCV history in calculation-engine column names."""
        return self.con.execute(
            '''select
                 trade_date as "Date",
                 open as "Open",
                 high as "High",
                 low as "Low",
                 close as "Close",
                 adjusted_close as "Adjusted Close",
                 volume as "Volume"
               from daily_ohlcv
               where ticker=? and provider_id=?
               order by trade_date''',
            [ticker, provider_id],
        ).df()

    def table_count(self, table: str) -> int:
        if table not in TABLES:
            raise ValueError('invalid table')
        return int(self.con.execute(f'select count(*) from {table}').fetchone()[0])

    def import_parquet(self, table, path):
        if table not in TABLES:
            raise ValueError('invalid table')
        p = Path(path)
        if not p.exists() or p.stat().st_size == 0:
            return 0
        before = self.table_count(table)
        self.con.execute(f"insert or replace into {table} select * from read_parquet(?)", [str(p)])
        return self.table_count(table) - before

    def export_parquet(self, table, path):
        if table not in TABLES:
            raise ValueError('invalid table')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con.execute(f"copy {table} to ? (format parquet, compression zstd)", [str(path)])
