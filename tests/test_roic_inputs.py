from bist_terminal.financials.roic_inputs import (
    compute_roic,
    derive_average_invested_capital,
    derive_roic_ttm,
    effective_tax_rate,
    parse_roic_inputs,
)


def fixture():
    return b"""<html><body>
<table><tr><td>Sunum Para Birimi</td><td>1.000 TL</td></tr></table>
<table>
<tr><td></td><td></td><td></td><td>Cari Donem 01.01.2026 - 30.06.2026</td><td>Onceki Donem 01.01.2025 - 30.06.2025</td><td>Cari Donem 3 Aylik 01.04.2026 - 30.06.2026</td><td>Onceki Donem 3 Aylik 01.04.2025 - 30.06.2025</td></tr>
<tr><td></td><td>Kar veya Zarar ve Diger Kapsamli Gelir Tablosu</td><td></td><td></td><td></td><td></td><td></td></tr>
<tr><td></td><td>FINANSMAN GELIRI (GIDERI) ONCESI FAALIYET KARI (ZARARI)</td><td></td><td>180</td><td>140</td><td>80</td><td>60</td></tr>
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


def test_parse_roic_inputs_uses_exact_ebit_ytd_columns_and_scale():
    out=parse_roic_inputs(fixture())
    assert out["current_period"]=="2026-06-30"
    assert out["ebit_ytd"]==180_000
    assert out["pretax_profit_ytd"]==200_000
    assert out["tax_expense_income_ytd"]==-50_000
    assert out["observed_metrics"]==[
        "ebit_ytd","pretax_profit_ytd","tax_expense_income_ytd"
    ]


def test_effective_tax_rate_is_guarded():
    assert effective_tax_rate(200,-50)==0.25
    assert effective_tax_rate(-200,-50) is None
    assert effective_tax_rate(200,50) is None
    assert effective_tax_rate(100,-150) is None


def test_derive_roic_ttm_uses_comparable_ytd_bridge():
    rows=[
        {"archive_year":2025,"archive_period":2,"report_period":"2025-06-30","ebit_ytd":100,"pretax_profit_ytd":90,"tax_expense_income_ytd":-18},
        {"archive_year":2025,"archive_period":4,"report_period":"2025-12-31","ebit_ytd":240,"pretax_profit_ytd":220,"tax_expense_income_ytd":-44},
        {"archive_year":2026,"archive_period":2,"report_period":"2026-06-30","ebit_ytd":150,"pretax_profit_ytd":140,"tax_expense_income_ytd":-28},
    ]
    out=derive_roic_ttm(rows,2026)
    assert out["status"]=="ACTIVE"
    assert out["ebit_ttm"]==290
    assert out["pretax_profit_ttm"]==270
    assert out["tax_expense_income_ttm"]==-54
    assert out["effective_tax_rate"]==0.2
    assert out["basis"]=="2025FY+2026P2-2025P2"


def test_average_invested_capital_requires_two_exact_periods():
    financial=[
        {"report_period":"2025-06-30","payload":{"status":"PARSED_HIGH_CONFIDENCE","archive_year":2025,"archive_period":"2","current_period":"2025-06-30","facts":{"equity":500,"cash":100}}},
        {"report_period":"2026-06-30","payload":{"status":"PARSED_HIGH_CONFIDENCE","archive_year":2026,"archive_period":"2","current_period":"2026-06-30","facts":{"equity":600,"cash":120}}},
    ]
    extended=[
        {"archive_year":2025,"archive_period":2,"report_period":"2025-06-30","debt_components_complete":True,"financial_debt":200},
        {"archive_year":2026,"archive_period":2,"report_period":"2026-06-30","debt_components_complete":True,"financial_debt":240},
    ]
    out=derive_average_invested_capital(financial,extended,2026,2)
    assert out["status"]=="ACTIVE"
    assert out["prior_invested_capital"]==600
    assert out["current_invested_capital"]==720
    assert out["average_invested_capital"]==660


def test_roic_uses_nopat_over_average_invested_capital():
    assert compute_roic(100,0.25,500)==0.15
    assert compute_roic(100,None,500) is None
