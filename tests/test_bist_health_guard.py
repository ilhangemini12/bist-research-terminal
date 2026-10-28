import unittest
from datetime import date
from scripts.bist_health_guard import analyze

def mk(verified=322, fresh=322, tracked=323, when="2026-10-27",status="PARTIAL"):
    return {"health":{"status":status,"expected_market_date":when,"verified_prices":verified,
        "fresh_history":fresh,"tracked":tracked,"unverified_tickers":["ISATR"],
        "capital_refresh_status":"BLOCKED","financial_refresh_status":"PARTIAL"}}

class HealthGateTests(unittest.TestCase):
    def test_known_isatr_gap_remains_visible_no_false_green(self):
        r=analyze(mk(),now=date(2026,10,28))
        self.assertEqual(r["status"],"PARTIAL")
        self.assertEqual(r["verified"],322)
        self.assertEqual(r["warnings"][-1],"Unverified tickers: ISATR")
    def test_major_verified_coverage_regression_fails(self):
        self.assertEqual(analyze(mk(verified=240),now=date(2026,10,28))["status"],"FAIL")
    def test_major_fresh_history_regression_fails(self):
        self.assertEqual(analyze(mk(fresh=110),now=date(2026,10,28))["status"],"FAIL")
    def test_stale_payload_fails(self):
        self.assertEqual(analyze(mk(),now=date(2026,11,4))["status"],"FAIL")
    def test_future_market_date_fails(self):
        self.assertEqual(analyze(mk(),now=date(2026,10,26))["status"],"FAIL")
    def test_inconsistent_counts_fail(self):
        self.assertEqual(analyze(mk(verified=324),now=date(2026,10,28))["status"],"FAIL")
    def test_malformed_payload_fail_closed(self):
        self.assertEqual(analyze({},now=date(2026,10,28))["status"],"FAIL")

if __name__=="__main__":
    unittest.main()
