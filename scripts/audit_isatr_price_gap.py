"""Read-only audit of the single current ISATR price-verification gap."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.providers.bist_bulletin import BistDailyBulletinProvider
from bist_terminal.providers.yahoo import YahooChartProvider
from bist_terminal.quality.price_verification import verify_prices


def main():
    ticker="ISATR"
    trade_date="2026-10-02"
    observations=[]
    errors=[]
    for provider in (BistDailyBulletinProvider(trade_date),YahooChartProvider()):
        try:
            o=provider.get_latest_price(ticker)
            observations.append(o)
            print(
                f"ISATR_PROVIDER_OK provider={o.provider_id} trade_date={o.trade_date} "
                f"close={o.close} volume={o.volume} source={o.source_url}"
            )
        except Exception as exc:
            errors.append({
                "provider":getattr(provider,"provider_id",type(provider).__name__),
                "error_type":type(exc).__name__,
                "message":str(exc),
            })
            print(
                f"ISATR_PROVIDER_DEGRADED provider={getattr(provider,'provider_id',type(provider).__name__)} "
                f"error={type(exc).__name__}:{exc}"
            )
    result=verify_prices(
        observations,trade_date,tolerance_pct=0.15,
        official_ids={"bist_daily_bulletin"}
    )
    report={
        "ticker":ticker,
        "trade_date":trade_date,
        "observations":[{
            "provider_id":o.provider_id,
            "upstream_vendor":o.upstream_vendor,
            "trade_date":o.trade_date,
            "close":o.close,
            "volume":o.volume,
            "source_url":o.source_url,
        } for o in observations],
        "errors":errors,
        "verification":result.as_dict(),
        "decision":"DO_NOT_ADD_THIRD_SOURCE_OR_WEAKEN_VERIFIED_2X",
    }
    out=ROOT/"artifacts/isatr_price_gap_audit.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("ISATR_AUDIT",json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
