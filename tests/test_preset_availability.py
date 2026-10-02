from pathlib import Path
import re
import yaml

ROOT=Path(__file__).resolve().parents[1]
BLOCKED_FIELDS={"net_debt_ebitda","roic","fcf_yield"}
EXPECTED_DISABLED={"LOW_DEBT","HIGH_ROIC","HIGH_FCF_YIELD"}


def test_unavailable_input_presets_are_explicitly_disabled():
    presets=yaml.safe_load((ROOT/"config/presets.yaml").read_text(encoding="utf-8"))["presets"]
    disabled={k for k,v in presets.items() if v.get("status")=="DISABLED_MISSING_VERIFIED_INPUT"}
    assert disabled==EXPECTED_DISABLED
    for key in disabled:
        assert presets[key].get("reason")
        assert any(field in presets[key]["rules"] for field in BLOCKED_FIELDS)


def test_active_presets_do_not_depend_on_unavailable_verified_fields():
    presets=yaml.safe_load((ROOT/"config/presets.yaml").read_text(encoding="utf-8"))["presets"]
    for key,preset in presets.items():
        if preset.get("status")=="DISABLED_MISSING_VERIFIED_INPUT":
            continue
        identifiers=set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b",preset["rules"]))
        assert not (identifiers & BLOCKED_FIELDS), (key, identifiers & BLOCKED_FIELDS)
