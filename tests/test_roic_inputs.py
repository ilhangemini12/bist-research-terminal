from bist_terminal.financials.roic_inputs import (
    compute_roic,
    effective_tax_rate,
    parse_roic_tax_inputs,
)


def fixture():
    return b"""<html><body>
<table><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr></table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 01.01.2026 - 30.06.2026</td><td>Onceki Donem 01.01.2025 - 30.06.2025</td><td>Cari Donem 3 Aylik 01.04.2026 - 30.06.2026</td><td>Onceki Donem 3 Aylik 01.04.2025 - 30.06.2025</td></tr>
<tr><td></td><td>Kar veya Zarar ve Diger Kapsamli Gelir Tablosu</td><td></td><td></td><td></td><td></td><td></td></tr>
<tr><td></td><td>SURDURULEN FAALIYETLER VERGI ONCESI KARI (ZARARI)</td><td></td><td>200</td><td>160</td><td>90</td><td>70</td></tr>
<tr><td></td><td>SURDURULEN FAALIYETLER VERGI (GIDERI) GELIRI</td><td></td><td>-50</td><td>-40</td><td>-20</td><td>-15</td></tr>
<tr><td></td><td>Diger</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
<tr><td></td><td>Diger2</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
<tr><td></td><td>Diger3</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
<tr><td></td><td>Diger4</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
<tr><td></td><td>Diger5</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
<tr><td></td><td>Diger6</td><td></td><td>1</td><td>1</td><td></td><td></td></tr>
</table>
</body></html>"""


def test_parse_roic_inputs_uses_ytd_columns_and_scale():
    out=parse_roic_tax_inputs(fixture())
    assert out["current_period"]=="2026-06-30"
    assert out["pretax_profit_ytd"]==200_000
    assert out["tax_expense_income_ytd"]==-50_000


def test_effective_tax_rate_is_guarded():
    assert effective_tax_rate(200,-50)==0.25
    assert effective_tax_rate(-200,-50) is None
    assert effective_tax_rate(200,50) is None


def test_roic_uses_nopat_over_average_invested_capital():
    assert compute_roic(100,0.25,500)==0.15
    assert compute_roic(100,None,500) is None
