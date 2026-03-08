from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "io"))


@pytest.fixture()
def minimal_quality_model() -> dict[str, object]:
    return {
        "sub_characteristics": [
            {
                "id": "availability",
                "display_name": "Availability",
                "characteristic": "robustness",
                "minimal_requirement": "-",
            },
            {
                "id": "adaptability",
                "display_name": "Adaptability",
                "characteristic": "robustness",
                "minimal_requirement": "Documented manual process.",
            },
        ]
    }


@pytest.fixture()
def minimal_inference_config() -> dict[str, object]:
    return {
        "signals": [
            {"key": "full_met", "type": "bool", "prompt": "Full?"},
            {"key": "min_met", "type": "bool", "prompt": "Min?"},
            {"key": "followup", "type": "bool", "prompt": "Followup?", "ask_if": "full_met == true"},
        ],
        "sub_characteristics": {
            "availability": {"full_condition": "full_met"},
            "adaptability": {
                "min_condition": "min_met",
                "full_condition": "full_met",
            },
        },
    }


@pytest.fixture()
def minimal_criticality_rules() -> dict[str, object]:
    return {
        "criticality_logic": {
            "production_key": "in_production",
            "production_critical_if_any": [
                "high_request_volume_top_third",
                "strategic_importance",
            ],
        }
    }


@pytest.fixture()
def skill_root() -> Path:
    return ROOT
