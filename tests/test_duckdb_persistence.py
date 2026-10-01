from datetime import date

import pytest

pytest.importorskip("duckdb")

from bist_terminal.storage.duckdb_store import DuckDBStore


def test_daily_ohlcv_parquet_roundtrip_restores_incremental_state(tmp_path):
    db1=tmp_path/"first.duckdb"
    parquet=tmp_path/"daily_ohlcv.parquet"
    store=DuckDBStore(db1)
    store.upsert_ohlcv({
        "ticker":"THYAO","trade_date":"2026-09-30","open":300.0,"high":305.0,
        "low":298.0,"close":304.0,"adjusted_close":304.0,"volume":1234567,
        "provider_id":"yahoo_chart","upstream_vendor":"Yahoo market data feed",
        "source_url":"https://example.invalid","retrieved_at":"2026-10-01T00:00:00Z"
    })
    store.export_parquet("daily_ohlcv",parquet)
    store.close()

    restored=DuckDBStore(tmp_path/"restored.duckdb")
    added=restored.import_parquet("daily_ohlcv",parquet)
    assert added == 1
    assert restored.table_count("daily_ohlcv") == 1
    assert restored.latest_history_date("THYAO","yahoo_chart") == date(2026,9,30)
    # Idempotent restore must not duplicate the primary-key row.
    assert restored.import_parquet("daily_ohlcv",parquet) == 0
    assert restored.table_count("daily_ohlcv") == 1
    restored.close()
