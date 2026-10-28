"""Free, read-only BIST terminal data quality gate.

Does not change data, relax VERIFIED_2X, or call external price sources.
Known gaps stay visible as warnings. Severe regressions fail CI.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, date, timezone
from pathlib import Path

def analyze(payload, now=None):
    health = payload.get("health", {})
    now = now or datetime.now(timezone.utc).date()
    if isinstance(now, datetime):
        now = now.date()
    problems, warnings = [], []
    try:
        market_date = date.fromisoformat(str(health["expected_market_date"]))
        tracked = int(health["tracked"])
        verified = int(health["verified_prices"])
        fresh = int(health["fresh_history"])
    except (KeyError, TypeError, ValueError) as exc:
        return {"status":"FAIL","errors":["Malformed health metrics"],"warnings":[],"ratio":None}
    if tracked <= 0 or not (0 <= verified <= tracked and 0 <= fresh <= tracked):
        problems.append("Inconsistent tracked/verified/fresh counts")
    ratio = verified / tracked if tracked > 0 else 0
    lag = (now - market_date).days
    if lag < 0:
        problems.append("Expected market date is in the future")
    if lag > 5:
        problems.append("Market data older than 5 calendar days")
    if ratio < 0.95:
        problems.append("VERIFIED_2X coverage below 95%")
    if fresh / tracked < 0.95 if tracked else True:
        problems.append("Fresh OHLC coverage below 95%")
    if health.get("status") != "OK":
        warnings.append("Data health is " + str(health.get("status","UNKNOWN")))
    if health.get("capital_refresh_status") != "OK":
        warnings.append("Capital refresh is " + str(health.get("capital_refresh_status","UNKNOWN")))
    if health.get("financial_refresh_status") != "OK":
        warnings.append("Financial refresh is " + str(health.get("financial_refresh_status","UNKNOWN")))
    missing = health.get("unverified_tickers",[])
    if missing:
        warnings.append("Unverified tickers: " + ", ".join(map(str, missing[:30])))
    return {"status":"FAIL" if problems else ("PARTIAL" if warnings else "OK"),
            "errors":problems,"warnings":warnings,"ratio":round(ratio,6),
            "date":market_date.isoformat(),"age_days":lag,"tracked":tracked,"verified":verified,"fresh":fresh}

def main():
    payload = json.loads(Path("dashboard/data/health.json").read_text(encoding="utf-8"))
    result = analyze(payload)
    print("BIST_HEALTH_GATE_RESULT", json.dumps(result,ensure_ascii=False,sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as out:
            out.write("## BIST Verified-2X Health Guard\n\n")
            out.write(f"**Status:** {result['status']} | **Verified:** {result['verified']}/{result['tracked']} | **Fresh:** {result['fresh']} | **Date:** {result['date']}\n\n")
            for key in ("errors","warnings"):
                for message in result[key]:
                    out.write(f"- {key.upper()}: {message}\n")
    if result["errors"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
