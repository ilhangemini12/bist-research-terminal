from bist_terminal.providers.gedik_model import (
    model_portfolio_date,
    parse_model_portfolio_html,
    parse_tr_price,
)


HTML="""
<html><body>
<section>
  <h2>Hisse Model Portföy</h2>
  <table>
    <tr><th>Şirket Adı</th><th>Hisse Kodu</th><th>Hedef Fiyat</th><th>Potansiyel Getiri</th><th>BIST-100 Ağırlık (%)</th></tr>
    <tr><td>Aksa</td><td>AKSA</td><td>20,15₺</td><td>%87,4</td><td>%0,3</td></tr>
    <tr><td>Türk Hava Yolları</td><td>THYAO</td><td>483,00₺</td><td>%64,6</td><td>%4,8</td></tr>
  </table>
  <div>Model Portföy Güncellemesi: Tüpraş’ı çıkarıyor, Astor Enerji’yi ekliyoruz 22.09.2026 Görüntüle</div>
  <div>Model Portföy Raporu - 06.08.2026 06.08.2026</div>
</section>
<section>
  <div>Yatırım Fonu Model Portföyler Yatırım Fonu Önerisi - 24.09.2026 24.09.2026</div>
</section>
</body></html>
"""


def test_parse_tr_price():
    assert parse_tr_price("20,15₺")==20.15
    assert parse_tr_price("1.234,50 TL")==1234.5
    assert parse_tr_price("-")==None


def test_model_portfolio_date_ignores_newer_fund_date():
    text="Model Portföy Güncellemesi örnek 22.09.2026 Yatırım Fonu Model Portföyler 24.09.2026"
    assert model_portfolio_date(text)=="2026-09-22"


def test_parse_public_model_portfolio_facts_only():
    out=parse_model_portfolio_html(HTML)
    assert out["portfolio_date"]=="2026-09-22"
    assert [r["ticker"] for r in out["rows"]]==["AKSA","THYAO"]
    assert out["rows"][0]["target_price"]==20.15
    assert "potential" not in out["rows"][0]
    assert "weight" not in out["rows"][0]
