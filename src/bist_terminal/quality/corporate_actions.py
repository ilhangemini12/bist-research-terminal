from __future__ import annotations

KNOWN_ACTIONS = {"DIVIDEND", "SPLIT", "BONUS_ISSUE", "RIGHTS_ISSUE", "CAPITAL_INCREASE"}


def corporate_action_day_check(raw_close: float, adjusted_close: float | None, action_type: str | None) -> list[str]:
    """Guard against silently treating adjusted and raw closes as the same observation."""
    if adjusted_close is None or raw_close == adjusted_close:
        return []
    if action_type and action_type.upper() in KNOWN_ACTIONS:
        return ["CORPORATE_ACTION_NORMALIZATION_REQUIRED"]
    return ["UNEXPLAINED_ADJUSTED_RAW_MISMATCH"]
