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


def test_latest_financial_prefers_high_confidence_on_same_report_date(tmp_path):
    store=DuckDBStore(tmp_path/"latest.duckdb")
    try:
        store.upsert_financial({
            "ticker":"PRZMA",
            "report_period":"2026-06-30",
            "publication_date":None,
            "statement_scope":"Legacy review scope",
            "payload":{
                "status":"PARSED_REVIEW_REQUIRED",
                "quality_score":80,
                "archive_year":2026,
                "archive_period":"2",
                "facts":{"assets":1,"equity":1},
            },
            "source_url":"https://example.invalid/review",
        })
        store.upsert_financial({
            "ticker":"PRZMA",
            "report_period":"2026-06-30",
            "publication_date":None,
            "statement_scope":"Validated repair scope",
            "payload":{
                "status":"PARSED_HIGH_CONFIDENCE",
                "quality_score":100,
                "archive_year":2026,
                "archive_period":"2",
                "facts":{"assets":1,"equity":1,"net_income":1},
            },
            "source_url":"https://example.invalid/repair",
        })
        store.upsert_financial({
            "ticker":"PRZMA",
            "report_period":"2026-03-31",
            "publication_date":"2026-05-01",
            "statement_scope":"Older",
            "payload":{
                "status":"PARSED_HIGH_CONFIDENCE",
                "quality_score":100,
                "archive_year":2026,
                "archive_period":"1",
                "facts":{"assets":1,"equity":1,"net_income":1},
            },
            "source_url":"https://example.invalid/older",
        })
        latest=store.latest_financial_payloads()["PRZMA"]
        assert latest["report_period"]=="2026-06-30"
        assert latest["payload"]["status"]=="PARSED_HIGH_CONFIDENCE"
        assert latest["payload"]["quality_score"]==100
        assert latest["source_url"]=="https://example.invalid/repair"
    finally:
        store.close()
