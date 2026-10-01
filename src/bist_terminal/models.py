from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import StrEnum
from typing import Any

class ProviderStatus(StrEnum):
    ACTIVE="ACTIVE"; DEGRADED="DEGRADED"; RATE_LIMITED="RATE_LIMITED"; BLOCKED="BLOCKED"
    SCHEMA_CHANGED="SCHEMA_CHANGED"; STALE="STALE"; LOGIN_REQUIRED="LOGIN_REQUIRED"
    PAID_SOURCE_SKIPPED="PAID_SOURCE_SKIPPED"; DISABLED="DISABLED"

class PriceConfidence(StrEnum):
    VERIFIED_2X="VERIFIED_2X"; VERIFIED_OFFICIAL="VERIFIED_OFFICIAL"; SINGLE_SOURCE="SINGLE_SOURCE"
    SOURCE_CONFLICT="SOURCE_CONFLICT"; STALE="STALE"; UNVERIFIED="UNVERIFIED"

@dataclass(frozen=True)
class PriceObservation:
    ticker: str
    market: str
    trade_date: str
    timestamp: str
    close: float
    currency: str = "TRY"
    adjusted: bool = False
    volume: float | None = None
    provider_id: str = "unknown"
    upstream_vendor: str = "unknown"
    source_url: str | None = None
    retrieved_at: str | None = None

    def lineage_key(self) -> str:
        return (self.upstream_vendor or self.provider_id).strip().lower()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
