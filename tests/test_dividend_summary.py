import pytest

pytest.importorskip("duckdb")

from bist_terminal.storage.duckdb_store import DuckDBStore


def test_dividend_amount_sum_respects_window_and_provider(tmp_path):
    store=DuckDBStore(tmp_path/"d.duckdb")
    try:
        rows=[
            {"ticker":"THYAO","action_date":"2026-03-15","action_type":"dividend","amount":1.5,"split_ratio":None,"provider_id":"yahoo_chart","source_url":"x","retrieved_at":"2026-10-02T00:00:00Z"},
            {"ticker":"THYAO","action_date":"2026-06-15","action_type":"dividend","amount":2.0,"split_ratio":None,"provider_id":"yahoo_chart","source_url":"x","retrieved_at":"2026-10-02T00:00:00Z"},
            {"ticker":"THYAO","action_date":"2025-01-01","action_type":"dividend","amount":9.0,"split_ratio":None,"provider_id":"yahoo_chart","source_url":"x","retrieved_at":"2026-10-02T00:00:00Z"},
            {"ticker":"THYAO","action_date":"2026-07-01","action_type":"split","amount":None,"split_ratio":"2:1","provider_id":"yahoo_chart","source_url":"x","retrieved_at":"2026-10-02T00:00:00Z"},
        ]
        for row in rows:
            store.upsert_corporate_action(row)
        assert store.dividend_amount_sum("THYAO","2025-10-02","2026-10-02")==3.5
        assert store.dividend_amount_sum("THYAO","2026-04-01","2026-10-02")==2.0
    finally:
        store.close()
