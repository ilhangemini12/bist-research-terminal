from bist_terminal.financials.share_class import normalize_company_title, source_filename_names_ticker

def test_exact_issuer_normalization_is_stable():
    assert normalize_company_title("KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.") == normalize_company_title("Kardemir Karabük Demir Çelik Sanayi ve Ticaret A.Ş.")

def test_source_filename_must_explicitly_name_recipient():
    f="KRDMA-KRDMB-KRDMD_1650387_2026_2.xls"
    assert source_filename_names_ticker(f,"KRDMA")
    assert source_filename_names_ticker(f,"KRDMB")
    assert source_filename_names_ticker(f,"KRDMD")
    assert not source_filename_names_ticker(f,"ISCTR")
