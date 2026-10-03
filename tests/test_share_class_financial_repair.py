from scripts.repair_share_class_financials import norm, source_names_recipient

def test_exact_issuer_normalization_is_stable():
    assert norm("KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.") == norm("Kardemir Karabük Demir Çelik Sanayi ve Ticaret A.Ş.")

def test_source_filename_must_explicitly_name_recipient():
    f="KRDMA-KRDMB-KRDMD_1650387_2026_2.xls"
    assert source_names_recipient(f,"KRDMA")
    assert source_names_recipient(f,"KRDMB")
    assert source_names_recipient(f,"KRDMD")
    assert not source_names_recipient(f,"ISCTR")
