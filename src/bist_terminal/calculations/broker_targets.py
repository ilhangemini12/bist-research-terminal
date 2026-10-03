from __future__ import annotations

from statistics import median


def apply_broker_targets(stocks: list[dict], by_ticker: dict[str,list[dict]]) -> list[dict]:
    """Attach factual broker targets to stock rows.

    A single broker is labeled SINGLE_SOURCE, never consensus. Consensus is emitted
    only with at least two independent broker target rows.
    """
    out=[]
    for row in stocks:
        r=dict(row)
        records=[
            x for x in (by_ticker.get(str(r.get("ticker") or "").upper(),[]) or [])
            if x.get("target_price") is not None and float(x.get("target_price"))>0
        ]
        records=sorted(records,key=lambda x:(str(x.get("broker_id") or ""),str(x.get("portfolio_date") or x.get("observed_date") or "")))
        prices=[float(x["target_price"]) for x in records]
        brokers=sorted({str(x.get("broker_name") or x.get("broker_id") or "") for x in records if x.get("broker_name") or x.get("broker_id")})
        dates=[str(x.get("portfolio_date") or x.get("observed_date")) for x in records if x.get("portfolio_date") or x.get("observed_date")]
        reference=median(prices) if prices else None
        count=len(records)
        status="CONSENSUS_2PLUS" if count>=2 else ("SINGLE_SOURCE" if count==1 else "UNAVAILABLE")
        verified_price=r.get("price") if r.get("price_status")=="VERIFIED_2X" else None
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
