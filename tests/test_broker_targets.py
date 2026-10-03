import pytest

from bist_terminal.calculations.broker_targets import apply_broker_targets


def stock(price=300.0,status="VERIFIED_2X"):
    return {"ticker":"THYAO","price":price,"price_status":status}


def test_single_source_is_not_called_consensus():
    out=apply_broker_targets([stock()],{"THYAO":[{
        "broker_id":"gedik","broker_name":"Gedik Yatırım","target_price":483.0,
        "model_portfolio_active":True,"portfolio_date":None,
        "observed_date":"2026-10-03","date_basis":"OBSERVED_CURRENT_PUBLIC_PAGE","source_url":"u"
    }]})[0]
    assert out["target_status"]=="SINGLE_SOURCE"
    assert out["target_price"]==483.0
    assert out["target_consensus"] is None
    assert out["target_source_count"]==1
    assert out["target_upside"]==pytest.approx(0.61)
    assert out["model_portfolio_brokers"]==["Gedik Yatırım"]


def test_two_sources_emit_median_consensus():
    out=apply_broker_targets([stock(100)],{"THYAO":[
        {"broker_id":"a","broker_name":"A","target_price":120,"model_portfolio_active":True,"portfolio_date":"2026-09-01"},
        {"broker_id":"b","broker_name":"B","target_price":140,"model_portfolio_active":False,"portfolio_date":"2026-09-15"},
    ]})[0]
    assert out["target_status"]=="CONSENSUS_2PLUS"
    assert out["target_price"]==130
    assert out["target_consensus"]==130
    assert out["target_upside"]==pytest.approx(0.3)


def test_unverified_price_does_not_get_upside():
    out=apply_broker_targets([stock(100,"SINGLE_SOURCE")],{"THYAO":[
        {"broker_id":"g","broker_name":"G","target_price":150,"model_portfolio_active":True,"observed_date":"2026-10-03"}
    ]})[0]
    assert out["target_price"]==150
    assert out["target_upside"] is None
