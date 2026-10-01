from bist_terminal.quality.freshness import price_freshness

def test_freshness(): assert price_freshness('2026-10-01','2026-10-01')=='FRESH' and price_freshness('2026-09-29','2026-10-01')=='STALE'
