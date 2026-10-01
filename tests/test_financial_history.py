import pytest

pytest.importorskip("duckdb")

from bist_terminal.storage.duckdb_store import DuckDBStore


def test_financial_payload_history_returns_all_periods_in_order(tmp_path):
    store=DuckDBStore(tmp_path/"f.duckdb")
    try:
        for period,archive_period in [("2025-06-30","2"),("2025-03-31","1")]:
            store.upsert_financial({
                "ticker":"THYAO",
                "report_period":period,
                "publication_date":None,
                "statement_scope":"Konsolide",
                "payload":{
                    "status":"PARSED_HIGH_CONFIDENCE",
                    "archive_year":2025,
                    "archive_period":archive_period,
                    "facts":{"assets":1,"equity":1,"net_income":1},
                },
                "source_url":"https://example.invalid",
            })
        rows=store.financial_payload_history()["THYAO"]
        assert [r["report_period"] for r in rows]==["2025-03-31","2025-06-30"]
        assert rows[0]["payload"]["archive_period"]=="1"
        assert rows[1]["payload"]["archive_period"]=="2"
    finally:
        store.close()
