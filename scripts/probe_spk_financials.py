from __future__ import annotations

from pathlib import Path
from pprint import pformat
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bist_terminal.providers.spk import SPKRegistryProvider


def slim(value, max_chars=1200):
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def main():
    p = SPKRegistryProvider(timeout=30)

    companies = p.listed_companies()
    print("SPK_COMPANIES_TYPE", type(companies).__name__)
    print("SPK_COMPANIES_COUNT", len(companies) if isinstance(companies, list) else "NA")
    if isinstance(companies, list):
        for i, row in enumerate(companies[:3]):
            print(f"SPK_COMPANY_{i}_KEYS", sorted(row) if isinstance(row, dict) else type(row).__name__)
            print(f"SPK_COMPANY_{i}", slim(row))

    topics = p.financial_report_topics()
    print("SPK_FIN_TOPICS_TYPE", type(topics).__name__)
    print("SPK_FIN_TOPICS", slim(topics))

    reports = p.financial_reports(
        dateBegin="2026-01-01T00:00:00",
        dateEnd="2026-10-01T23:59:59",
    )
    print("SPK_FIN_REPORTS_TYPE", type(reports).__name__)
    print("SPK_FIN_REPORTS_COUNT", len(reports) if isinstance(reports, list) else "NA")
    if isinstance(reports, list):
        for i, row in enumerate(reports[:5]):
            print(f"SPK_FIN_REPORT_{i}_KEYS", sorted(row) if isinstance(row, dict) else type(row).__name__)
            print(f"SPK_FIN_REPORT_{i}", slim(row))

        first = reports[0] if reports else None
        if isinstance(first, dict):
            rid = next((first.get(k) for k in ("id", "Id", "ID") if first.get(k) is not None), None)
            print("SPK_FIN_FIRST_ID", rid)
            if rid is not None:
                detail = p.financial_report(rid)
                print("SPK_FIN_DETAIL_TYPE", type(detail).__name__)
                print("SPK_FIN_DETAIL_KEYS", sorted(detail) if isinstance(detail, dict) else "NA")
                if isinstance(detail, dict):
                    print("SPK_FIN_DETAIL_VALUE_TYPES", {k:type(v).__name__ for k,v in detail.items()})
                print("SPK_FIN_DETAIL", slim(detail, 4000))


if __name__ == "__main__":
    main()
