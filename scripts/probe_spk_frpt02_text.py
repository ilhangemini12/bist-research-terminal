"""One-off live validation of the production SPK PDF financial parser."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from bist_terminal.financials.spk_pdf import parse_pdf_base64
from bist_terminal.providers.spk import SPKRegistryProvider

REPORT_ID=1986

def main():
    detail=SPKRegistryProvider().financial_report(REPORT_ID)
    out=parse_pdf_base64(detail["fileData"],metadata={
        "report_id":detail.get("id"),
        "company_code":detail.get("companyCode"),
        "subject":detail.get("subject"),
        "publication_date":detail.get("date"),
    })
    print("SPK_PRODUCTION_PARSER_PROBE_OK")
    print(f"SPK_PRODUCTION_PARSER_STATUS status={out['status']} score={out['quality_score']} pages={out['pdf_pages']} text_pages={out['text_pages']}")
    print(f"SPK_PRODUCTION_PARSER_PERIODS {out['periods']}")
    print(f"SPK_PRODUCTION_PARSER_PAGES {out['statement_pages']}")
    print(f"SPK_PRODUCTION_PARSER_CHECKS {out['checks']}")
    for period in out["periods"][:3]:
        facts=out["facts_by_period"].get(period,{})
        selected={k:facts.get(k) for k in [
            "total_assets","equity","total_sources","current_assets","current_liabilities",
            "cash","inventories","revenue","gross_profit","operating_profit","pretax_income",
            "net_income","cash_from_operations"
        ] if k in facts}
        print(f"SPK_PRODUCTION_PARSER_FACTS period={period} {selected}")
    if out["status"] != "PARSED_HIGH_CONFIDENCE":
        raise RuntimeError(f"production parser did not reach high confidence: {out['status']} score={out['quality_score']}")
    if out["checks"].get("balance_identity_ok") is not True:
        raise RuntimeError("balance identity check failed")

if __name__=="__main__":
    main()
