from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo


def validate_payload(payload, required_fields=(), expected_ticker: str | None = None) -> list[str]:
    """Validate a decoded provider payload before mapping it into domain models.

    This deliberately treats HTML/login/error bodies as malformed rather than trying to
    scrape through a provider failure.
    """
    if not isinstance(payload, dict):
        return ["MALFORMED_PAYLOAD"]
    errors: list[str] = []
    for field in required_fields:
        if field not in payload:
            errors.append(f"SCHEMA_CHANGED_MISSING_{field.upper()}")
    if expected_ticker is not None and payload.get("ticker") not in (None, expected_ticker):
        errors.append("WRONG_TICKER")
    return errors


def normalize_bist_timestamp(timestamp: str, timezone: str = "Europe/Istanbul") -> tuple[str | None, list[str]]:
    """Return an offset-aware BIST-local ISO timestamp plus validation flags."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None, ["INVALID_TIMESTAMP"]
    if dt.tzinfo is None:
        return None, ["TIMEZONE_MISSING"]
    local = dt.astimezone(ZoneInfo(timezone))
    flags = []
    if local.utcoffset() != dt.utcoffset():
        flags.append("TIMEZONE_NORMALIZED")
    return local.isoformat(), flags
