from bist_terminal.financials.extended_metrics import parse_extended_metrics, ttm_from_ytd_bridge


def fixture():
    return b"""<html><body>
<table><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr></table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 30.06.2026</td><td>Onceki Donem 31.12.2025</td></tr>
<tr><td></td><td>Finansal Durum Tablosu (Bilanco)</td><td></td><td></td><td></td></tr>
<tr><td></td><td>Kisa Vadeli Borclanmalar</td><td></td><td>100</td><td>80</td></tr>
<tr><td></td><td>Uzun Vadeli Borclanmalarin Kisa Vadeli Kisimlari</td><td></td><td>20</td><td>10</td></tr>
<tr><td></td><td>Uzun Vadeli Borclanmalar</td><td></td><td>300</td><td>250</td></tr>
<tr><td></td><td>Diger</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger2</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger3</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger4</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger5</td><td></td><td>1</td><td>1</td></tr>
</table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 01.01.2026 - 30.06.2026</td><td>Onceki Donem 01.01.2025 - 30.06.2025</td></tr>
<tr><td></td><td>Nakit Akis Tablosu</td><td></td><td></td><td></td></tr>
<tr><td></td><td>Amortisman ve Itfa Gideri Ile Ilgili Duzeltmeler</td><td></td><td>40</td><td>30</td></tr>
<tr><td></td><td>Maddi ve Maddi Olmayan Duran Varliklarin Alimindan Kaynaklanan Nakit Cikislari</td><td></td><td>-55</td><td>-45</td></tr>
<tr><td></td><td>Diger</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger2</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger3</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger4</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger5</td><td></td><td>1</td><td>1</td></tr>
<tr><td></td><td>Diger6</td><td></td><td>1</td><td>1</td></tr>
</table>
</body></html>"""


def test_parse_extended_metrics_exact_totals_and_scale():
    out=parse_extended_metrics(fixture())
    assert out["current_period"]=="2026-06-30"
    assert out["debt_components_complete"] is True
    assert out["financial_debt"]==420_000.0
    assert out["depreciation_amortization_ytd"]==40_000.0
    assert out["capex_cash_outflow_ytd"]==-55_000.0
    assert out["capex_spend_ytd"]==55_000.0


def test_ttm_bridge_requires_all_three_inputs():
    assert ttm_from_ytd_bridge(100,60,40)==120
    assert ttm_from_ytd_bridge(100,None,40) is None
