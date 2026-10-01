from datetime import date

import pytest

pytest.importorskip("duckdb")

from bist_terminal.storage.duckdb_store import DuckDBStore


def test_daily_ohlcv_parquet_roundtrip_restores_incremental_state(tmp_path):
    db1 = tmp_path / "first.duckdb"
    parquet = tmp_path / "daily_ohlcv.parquet"
    store = DuckDBStore(db1)
    store.upsert_ohlcv({
        "ticker": "THYAO",
        "trade_date": "2026-09-30",
        "open": 300.0,
        "high": 305.0,
        "low": 298.0,
        "close": 304.0,
        "adjusted_close": 304.0,
        "volume": 1234567,
        "provider_id": "yahoo_chart",
        "upstream_vendor": "Yahoo market data feed",
        "source_url": "https://example.invalid",
        "retrieved_at": "2026-10-01T00:00:00Z",
    })
    store.export_parquet("daily_ohlcv", parquet)
    store.close()

    restored = DuckDBStore(tmp_path / "restored.duckdb")
    added = restored.import_parquet("daily_ohlcv", parquet)
    assert added == 1
    assert restored.table_count("daily_ohlcv") == 1
    assert restored.latest_history_date("THYAO", "yahoo_chart") == date(2026, 9, 30)
    assert restored.import_parquet("daily_ohlcv", parquet) == 0
    assert restored.table_count("daily_ohlcv") == 1
    restored.close()


def test_index_membership_history_is_point_in_time_and_idempotent(tmp_path):
    parquet = tmp_path / "index_membership_history.parquet"
    rows = [
        {"ticker": "AKBNK", "company_name": "Akbank"},
        {"ticker": "THYAO", "company_name": "Turk Hava Yollari"},
    ]

    store = DuckDBStore(tmp_path / "membership.duckdb")
    store.append_membership_snapshot(
        "XU100", "2026-10-01", rows, "2026-10-01T14:00:00Z"
    )
    store.append_membership_snapshot(
        "XU100", "2026-10-01", rows, "2026-10-01T14:05:00Z"
    )

    assert store.table_count("index_membership_history") == 2
    assert store.membership_for_date("XU100", "2026-10-01") == ["AKBNK", "THYAO"]
    assert store.latest_membership_snapshot_date("XU100") == date(2026, 10, 1)

    store.export_parquet("index_membership_history", parquet)
    store.close()

    restored = DuckDBStore(tmp_path / "membership-restored.duckdb")
    assert restored.import_parquet("index_membership_history", parquet) == 2
    assert restored.table_count("index_membership_history") == 2
    assert restored.membership_for_date("XU100", "2026-10-01") == ["AKBNK", "THYAO"]
    assert restored.import_parquet("index_membership_history", parquet) == 0
    restored.close()
