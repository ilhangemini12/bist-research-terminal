from bist_terminal.providers.bist_bulletin import BistDailyBulletinProvider
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.models import PriceObservation
from bist_terminal.quality.price_verification import verify_prices
D="2026-09-30"
for t in ["THYAO","ASELS","AKBNK"]:
    a=BistDailyBulletinProvider(D).get_latest_price(t)
    h=YahooChartProvider().get_history(t,D,D).iloc[-1]
    b=PriceObservation(t,"BIST",D,D+"T18:10:00+03:00",float(h["Close"]),"TRY",False,float(h["Volume"]),"yahoo_chart","Yahoo market data feed")
    r=verify_prices([a,b],D,0.15,{"bist_daily_bulletin"})
    print(t,a.close,b.close,r.status,r.max_diff_pct)
