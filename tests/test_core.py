from __future__ import annotations

from pathlib import Path

from genai_maturity.engine.core import (
    build_gap_priorities,
    classify_criticality,
    compute_actual_maturity,
    load_configs,
    validate_configs,
)


def test_validate_configs__project_configs_valid_is_correct(skill_root: Path) -> None:
    cfg = load_configs(skill_root / "configs")
    errors = validate_configs(cfg)
    assert errors == []


def test_classify_criticality__production_critical_when_any_trigger_true() -> None:
    rules = {
        "required_maturity": {
            "proof_of_concept": 1,
            "production_non_critical": 3,
            "production_critical": 5,
        },
        "criticality_logic": {
            "production_key": "in_production",
            "production_critical_if_any": ["strategic_importance", "revenue_impact_gt_1pct"],
        },
    }
    answers = {
        "in_production": True,
        "strategic_importance": False,
        "revenue_impact_gt_1pct": True,
    }

    label, required = classify_criticality(answers, rules)

    assert label == "production_critical"
    assert required == 5


def test_compute_actual_maturity__returns_highest_satisfied_level_is_correct() -> None:
    gaps = {"a": "no", "b": "small"}
    maturity_gates = {
        "a": {1: "full", 2: "full", 3: "full", 4: "full", 5: "full"},
        "b": {1: "none", 2: "min", 3: "full", 4: "full", 5: "full"},
    }
    gap_scales = {
        "gaps": {"no": 0, "small": 1, "large": 2},
        "fulfillment": {"full_met": ["no"], "min_met": ["no", "small"]},
    }

    actual = compute_actual_maturity(gaps, maturity_gates, gap_scales)

    assert actual == 2


def test_build_gap_priorities__categorizes_priority_levels_is_correct() -> None:
    quality_model = {
        "sub_characteristics": [
            {
                "id": "critical_id",
                "display_name": "Critical",
                "characteristic": "robustness",
                "minimal_requirement": "Manual fallback exists.",
            },
            {
                "id": "important_id",
                "display_name": "Important",
                "characteristic": "utility",
                "minimal_requirement": "Basic eval exists.",
            },
            {
                "id": "nice_id",
                "display_name": "Nice",
                "characteristic": "economy",
                "minimal_requirement": "-",
            },
        ]
    }
    gaps = {"critical_id": "large", "important_id": "large", "nice_id": "large"}
    evidence = {"critical_id": "", "important_id": "", "nice_id": ""}
    maturity_gates = {
        "critical_id": {1: "full", 2: "full", 3: "full", 4: "full", 5: "full"},
        "important_id": {1: "none", 2: "none", 3: "min", 4: "full", 5: "full"},
        "nice_id": {1: "none", 2: "none", 3: "none", 4: "none", 5: "full"},
    }
    recommendations = {
        "recommendations": {
            "critical_id": {"min_action": "critical min", "full_action": "critical full"},
            "important_id": {"min_action": "important min", "full_action": "important full"},
            "nice_id": {"min_action": "nice min", "full_action": "nice full"},
        }
    }
    gap_scales = {
        "gaps": {"no": 0, "small": 1, "large": 2},
        "fulfillment": {"full_met": ["no"], "min_met": ["no", "small"]},
    }

    items = build_gap_priorities(
        quality_model=quality_model,
        gaps=gaps,
        evidence=evidence,
        maturity_gates=maturity_gates,
        recommendations=recommendations,
        gap_scales=gap_scales,
        actual_level=1,
        required_level=3,
    )

    by_id = {item["sub_characteristic"]: item for item in items}

    assert by_id["critical_id"]["priority"] == "critical"
    assert by_id["important_id"]["priority"] == "important"
    assert by_id["nice_id"]["priority"] == "nice_to_have"
