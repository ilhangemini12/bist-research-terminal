from bist_terminal.financials.spk_pdf import extract_periods, parse_statement_pages, parse_tr_number


def test_parse_tr_number_turkish_formats():
    assert parse_tr_number("226.447.802") == 226447802
    assert parse_tr_number("(11.950.957)") == -11950957
    assert parse_tr_number("0,63") == 0.63
    assert parse_tr_number("-") is None


def test_extract_periods_turkish_dates():
    assert extract_periods("Dipnot 31 Aralık 2025 31 Aralık 2024 1 Ocak 2024") == [
        "2025-12-31", "2024-12-31", "2024-01-01"
    ]


def test_statement_parser_uses_statement_pages_and_last_n_values():
    pages=[
        "Kapak",
        "31 Aralık 2025 31 Aralık 2024 1 Ocak 2024\n"
        "Toplam Dönen Varlıklar 10 120.000 100.000 90.000\n"
        "Stoklar 7 20.000 18.000 16.000\n"
        "Nakit ve Nakit Benzerleri 6 30.000 25.000 20.000\n"
        "Toplam Varlıklar 220.000 200.000 180.000",
        "31 Aralık 2025 31 Aralık 2024 1 Ocak 2024\n"
        "Toplam Kısa Vadeli Yükümlülükler 40.000 38.000 35.000\n"
        "Toplam Uzun Vadeli Yükümlülükler 30.000 27.000 25.000\n"
        "Özkaynaklar\n"
        "Dönem Net Karı/Zararı (+/-) 28 16.000 12.000 -\n"
        "Toplam Özkaynaklar 150.000 135.000 120.000\n"
        "Toplam Kaynaklar 220.000 200.000 180.000",
        "Dipnot 31 Aralık 2025 31 Aralık 2024\n"
        "Hasılat 29 480.000 458.000\n"
        "Brüt Kar (Zarar) 70.000 63.000\n"
        "Esas Faaliyet Karı (Zararı) 40.000 35.000\n"
        "Sürdürülen Faaliyetler Vergi Öncesi Dönem Karı (Zararı) 28.000 20.000\n"
        "Net Dönem Karı (Zararı) 16.000 12.000",
        "31 Aralık 2025 31 Aralık 2024\n"
        "A. İşletme Faaliyetlerinden Elde Edilen Nakit Akışları 24.000 19.000\n"
        "Dönem Karı/Zararı 16.000 12.000",
        # Note pages repeat labels with different values and must not override statements.
        "DİPNOT 29\nHasılat 31 Aralık 2025 31 Aralık 2024\nYurtiçi Satışlar 999.999 999.999",
    ]
    out=parse_statement_pages(pages,metadata={"report_id":1986})
    assert out["status"] == "PARSED_HIGH_CONFIDENCE"
    assert out["quality_score"] >= 85
    assert out["checks"]["balance_identity_ok"] is True
    cur=out["facts_by_period"]["2025-12-31"]
    assert cur["total_assets"] == 220000
    assert cur["equity"] == 150000
    assert cur["revenue"] == 480000
    assert cur["net_income"] == 16000
    assert cur["cash_from_operations"] == 24000
    assert cur["cash"] == 30000


def test_statement_parser_is_conservative_when_balance_does_not_tie():
    pages=[
        "31 Aralık 2025 31 Aralık 2024\nToplam Varlıklar 220.000 200.000",
        "31 Aralık 2025 31 Aralık 2024\nToplam Özkaynaklar 150.000 135.000\nToplam Kaynaklar 221.000 200.000",
        "31 Aralık 2025 31 Aralık 2024\nHasılat 480.000 458.000\nNet Dönem Karı (Zararı) 16.000 12.000",
    ]
    out=parse_statement_pages(pages)
    assert out["checks"]["balance_identity_ok"] is False
    assert out["status"] != "PARSED_HIGH_CONFIDENCE"
