from datetime import date

from bist_terminal.providers.spk_news import (
    normalize_company_title,
    recent_spk_disclosures,
    title_to_ticker_map,
)


class FakeSPK:
    def special_disclosures(self, **params):
        assert params["dateBegin"]=="2026-09-26"
        assert params["dateEnd"]=="2026-10-02"
        return [
            {"id":2,"companyCode":11,"companyTitle":"ABC SANAYİ VE TİCARET A.Ş.","subject":"Yeni yatırım","date":"2026-10-02T00:00:00","mimeType":"application/pdf"},
            {"id":1,"companyCode":12,"companyTitle":"Başka Şirket A.Ş.","subject":"Genel kurul","date":"2026-10-01T00:00:00","mimeType":"application/pdf"},
            {"id":2,"companyCode":11,"companyTitle":"ABC SANAYİ VE TİCARET A.Ş.","subject":"duplicate","date":"2026-10-02T00:00:00","mimeType":"application/pdf"},
        ]


def test_title_normalization_and_exact_mapping_only():
    cap={"ABCD":{"company_title":"ABC Sanayi ve Ticaret A.Ş."}}
    m=title_to_ticker_map(cap)
    assert m[normalize_company_title("ABC SANAYİ VE TİCARET A.Ş.")]=="ABCD"
    assert normalize_company_title("ABC Sanayi ve Ticaret A.Ş.")=="ABC SANAYI VE TICARET A S"


def test_recent_disclosures_dedupes_and_does_not_fuzzy_match():
    cap={"ABCD":{"company_title":"ABC Sanayi ve Ticaret A.Ş."}}
    rows=recent_spk_disclosures(FakeSPK(),cap,date(2026,10,2),days=7)
    assert len(rows)==2
    assert rows[0]["ticker"]=="ABCD"
    assert rows[0]["mapped_current_universe"] is True
    assert rows[1]["ticker"] is None
    assert rows[1]["mapped_current_universe"] is False
