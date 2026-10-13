from __future__ import annotations

from statistics import median
import math


def apply_broker_targets(stocks: list[dict], by_ticker: dict[str,list[dict]]) -> list[dict]:
    """Attach factual broker targets to stock rows.

    A single broker is labeled SINGLE_SOURCE, never consensus. Consensus is emitted
    only with at least two independent broker target rows.
    """
    out=[]
    for row in stocks:
        r=dict(row)
        # Count independent broker identities, never duplicate rows. Conflicting
        # targets at the same latest timestamp are unavailable for that broker.
        grouped = {}
        for item in by_ticker.get(str(r.get("ticker") or "").upper(), []) or []:
            broker = str(item.get("broker_id") or "").strip().casefold()
            try:
                price = float(item.get("target_price"))
            except (TypeError, ValueError, OverflowError):
                continue
            if not broker or isinstance(item.get("target_price"), bool) or not math.isfinite(price) or price <= 0:
                continue
            rank = (str(item.get("portfolio_date") or item.get("observed_date") or ""),
                    str(item.get("retrieved_at") or ""))
            grouped.setdefault(broker, []).append((rank, {**item, "broker_id": broker, "target_price": price}))
        records = []
        for broker in sorted(grouped):
            latest = max(x[0] for x in grouped[broker])
            peers = [x[1] for x in grouped[broker] if x[0] == latest]
            if len({x["target_price"] for x in peers}) == 1:
                records.append(peers[0])
        prices=[float(x["target_price"]) for x in records]
        brokers=sorted({str(x.get("broker_name") or x.get("broker_id") or "") for x in records if x.get("broker_name") or x.get("broker_id")})
        dates=[str(x.get("portfolio_date") or x.get("observed_date")) for x in records if x.get("portfolio_date") or x.get("observed_date")]
        reference=median(prices) if prices else None
        count=len(records)
        status="CONSENSUS_2PLUS" if count>=2 else ("SINGLE_SOURCE" if count==1 else "UNAVAILABLE")
        verified_price=r.get("price") if r.get("price_status")=="VERIFIED_2X" else None
        if (isinstance(verified_price, bool) or not isinstance(verified_price, (int, float))
                or not math.isfinite(verified_price)):
            verified_price = None
        upside=(reference/verified_price-1) if reference is not None and verified_price and verified_price>0 else None
        r.update({
            "target_status":status,
            "target_price":reference,
            "target_consensus":reference if count>=2 else None,
            "target_source_count":count,
            "target_sources":brokers,
            "target_latest_date":max(dates) if dates else None,
            "target_upside":upside,
            "model_portfolio_active":any(bool(x.get("model_portfolio_active")) for x in records),
            "model_portfolio_brokers":sorted({
                str(x.get("broker_name") or x.get("broker_id") or "")
                for x in records if x.get("model_portfolio_active")
            }),
            "target_details":[{
                "broker_id":x.get("broker_id"),
                "broker_name":x.get("broker_name"),
                "target_price":float(x.get("target_price")),
                "portfolio_date":x.get("portfolio_date"),
                "observed_date":x.get("observed_date"),
                "date_basis":x.get("date_basis"),
                "source_url":x.get("source_url"),
            } for x in records],
        })
        out.append(r)
    return out
