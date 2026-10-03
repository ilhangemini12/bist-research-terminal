from pathlib import Path
import re
import yaml

ROOT=Path(__file__).resolve().parents[1]

# Production availability after the verified KAP metric pipelines:
# - net_debt_ebitda is guarded and emitted only for period-matched rows.
# - fcf_yield is guarded and emitted only where CFO/capex checkpoints are valid.
# - roic is guarded and emitted only for non-financial issuers with exact KAP
#   EBIT/pretax/tax checkpoints plus current/prior comparable invested capital.
# Missing rows remain N/A; no verified-input preset currently requires a blanket disable.
UNAVAILABLE_VERIFIED_FIELDS=set()
EXPECTED_DISABLED=set()


def test_unavailable_input_presets_are_explicitly_disabled():
    presets=yaml.safe_load((ROOT/"config/presets.yaml").read_text(encoding="utf-8"))["presets"]
    disabled={k for k,v in presets.items() if v.get("status")=="DISABLED_MISSING_VERIFIED_INPUT"}
    assert disabled==EXPECTED_DISABLED
    for key in disabled:
        assert presets[key].get("reason")
        assert any(field in presets[key]["rules"] for field in UNAVAILABLE_VERIFIED_FIELDS)


def test_active_presets_do_not_depend_on_unavailable_verified_fields():
    presets=yaml.safe_load((ROOT/"config/presets.yaml").read_text(encoding="utf-8"))["presets"]
    for key,preset in presets.items():
        if preset.get("status")=="DISABLED_MISSING_VERIFIED_INPUT":
            continue
        identifiers=set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b",preset["rules"]))
        assert not (identifiers & UNAVAILABLE_VERIFIED_FIELDS), (key, identifiers & UNAVAILABLE_VERIFIED_FIELDS)


def test_verified_extended_metric_presets_are_active_and_guarded():
    presets=yaml.safe_load((ROOT/"config/presets.yaml").read_text(encoding="utf-8"))["presets"]
    assert presets["LOW_DEBT"].get("status") is None
    assert "net_debt_ebitda" in presets["LOW_DEBT"]["rules"]
    assert presets["LOW_DEBT"].get("description")

    assert presets["HIGH_FCF_YIELD"].get("status") is None
    assert "fcf_yield" in presets["HIGH_FCF_YIELD"]["rules"]
    assert presets["HIGH_FCF_YIELD"].get("description")

    assert presets["HIGH_ROIC"].get("status") is None
    assert "roic" in presets["HIGH_ROIC"]["rules"]
    description=presets["HIGH_ROIC"].get("description","").lower()
    assert "ebit" in description
    assert "invested capital" in description
    assert "n/a" in description
