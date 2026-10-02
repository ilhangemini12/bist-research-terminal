from bist_terminal.financials.kap_bulk import (
    KapArchive,
    parse_html_xls,
    parse_tr_number,
    presentation_scale,
    notification_id_from_source_file,
)
from io import BytesIO
import zipfile


def html_fixture():
    return b"""<html><body>
<table><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr><tr><td>Finansal Tablo Niteligi</td><td>Konsolide</td></tr></table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 31.12.2025</td><td>Onceki Donem 31.12.2024</td></tr>
<tr><td></td><td>Finansal Durum Tablosu (Bilanco)</td><td></td><td></td><td></td></tr>
<tr><td></td><td>TOPLAM VARLIKLAR</td><td></td><td>1.250.000</td><td>1.000.000</td></tr>
<tr><td></td><td>TOPLAM OZKAYNAKLAR</td><td></td><td>500.000</td><td>450.000</td></tr>
<tr><td></td><td>NAKIT VE NAKIT BENZERLERI</td><td></td><td>100.000</td><td>90.000</td></tr>
<tr><td></td><td>DONEN VARLIKLAR</td><td></td><td>600.000</td><td>550.000</td></tr>
<tr><td></td><td>KISA VADELI YUKUMLULUKLER</td><td></td><td>300.000</td><td>280.000</td></tr>
<tr><td></td><td>STOKLAR</td><td></td><td>50.000</td><td>45.000</td></tr>
<tr><td></td><td>Diger</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger2</td><td></td><td>1</td><td>1</td></tr>
</table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 01.01.2025 - 31.12.2025</td><td>Onceki Donem 01.01.2024 - 31.12.2024</td></tr>
<tr><td></td><td>Kar veya Zarar Tablosu</td><td></td><td></td><td></td></tr>
<tr><td></td><td>HASILAT</td><td></td><td>900.000</td><td>800.000</td></tr>
<tr><td></td><td>BRUT KAR (ZARAR)</td><td></td><td>300.000</td><td>250.000</td></tr>
<tr><td></td><td>ESAS FAALIYET KARI (ZARARI)</td><td></td><td>200.000</td><td>170.000</td></tr>
<tr><td></td><td>DONEM KARI (ZARARI)</td><td></td><td>150.000</td><td>120.000</td></tr>
<tr><td></td><td>Diger</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger2</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger3</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger4</td><td></td><td>1</td><td>1</td></tr>
</table>
</body></html>"""


def test_turkish_numbers_and_scale():
    assert parse_tr_number("1.234.567") == 1234567
    assert parse_tr_number("-7.989") == -7989
    assert parse_tr_number("(1.250)") == -1250
    assert presentation_scale("1.000.000 TL") == ("TRY", 1_000_000.0)


def test_parse_html_xls_scales_and_periods():
    out = parse_html_xls(html_fixture(), "THYAO_1_2025_4.xls")
    assert out["current_period"] == "2025-12-31"
    assert out["currency"] == "TRY"
    assert out["scale"] == 1000.0
    assert out["facts"]["assets"] == 1_250_000_000.0
    assert out["facts"]["equity"] == 500_000_000.0
    assert out["facts"]["revenue"] == 900_000_000.0
    assert out["facts"]["net_income"] == 150_000_000.0


def test_archive_finds_prefixed_bank_symbol():
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("TVB-VAKBN_1557008_2025_4.xls", html_fixture())
        z.writestr("THYAO_1565996_2025_4.xls", html_fixture())
    arc = KapArchive(2025, "4", "https://example.invalid", bio.getvalue())
    assert arc.entry_for_ticker("VAKBN") == "TVB-VAKBN_1557008_2025_4.xls"
    assert arc.entry_for_ticker("THYAO") == "THYAO_1565996_2025_4.xls"


def test_notification_id_is_derived_from_bulk_filename():
    assert notification_id_from_source_file("THYAO_1565996_2025_4.xls")==1565996
    assert notification_id_from_source_file("TVB-VAKBN_1557008_2025_4.xls")==1557008
    assert notification_id_from_source_file("invalid.xls") is None
    assert notification_id_from_source_file(None) is None
