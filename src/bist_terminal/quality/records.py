from __future__ import annotations
from collections.abc import Iterable


def dedupe_records(rows: Iterable[dict], keys: tuple[str, ...]) -> tuple[list[dict], int]:
    seen = set(); unique = []; duplicates = 0
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key); unique.append(row)
    return unique, duplicates


def dedupe_kap_disclosures(rows: Iterable[dict]) -> tuple[list[dict], int]:
    """Prefer stable disclosure_id; fall back to a conservative compound key."""
    materialized = list(rows)
    if all(r.get("disclosure_id") for r in materialized):
        return dedupe_records(materialized, ("disclosure_id",))
    return dedupe_records(materialized, ("ticker", "published_at", "title", "source_url"))
