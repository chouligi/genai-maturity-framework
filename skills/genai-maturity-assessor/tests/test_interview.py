from __future__ import annotations

import pytest

from interview import normalize_input_payload


def test_normalize_input_payload__parses_string_booleans_is_correct(
    minimal_quality_model: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality_answers": {
            "in_production": "false",
            "strategic_importance": "Yes",
            "dependent_teams_ge_4": 0,
        },
        "gaps": {"availability": "no", "adaptability": "small"},
        "evidence": {},
    }

    normalized = normalize_input_payload(
        payload=payload,
        quality_model=minimal_quality_model,
        allowed_gaps={"no", "small", "large"},
    )

    assert normalized["criticality_answers"]["in_production"] is False
    assert normalized["criticality_answers"]["strategic_importance"] is True
    assert normalized["criticality_answers"]["dependent_teams_ge_4"] is False


def test_normalize_input_payload__invalid_boolean_raised_error(
    minimal_quality_model: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality_answers": {"in_production": "sometimes"},
        "gaps": {"availability": "no", "adaptability": "small"},
        "evidence": {},
    }

    with pytest.raises(ValueError, match="Invalid string for boolean field 'in_production'"):
        normalize_input_payload(
            payload=payload,
            quality_model=minimal_quality_model,
            allowed_gaps={"no", "small", "large"},
        )


def test_normalize_input_payload__missing_gap_raised_error(
    minimal_quality_model: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality_answers": {"in_production": True},
        "gaps": {"availability": "no"},
        "evidence": {},
    }

    with pytest.raises(ValueError, match="Input JSON missing gaps for: adaptability"):
        normalize_input_payload(
            payload=payload,
            quality_model=minimal_quality_model,
            allowed_gaps={"no", "small", "large"},
        )


def test_normalize_input_payload__small_gap_without_minimum_raised_error(
    minimal_quality_model: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality_answers": {"in_production": True},
        "gaps": {"availability": "small", "adaptability": "small"},
        "evidence": {},
    }

    with pytest.raises(
        ValueError,
        match="Sub-characteristic 'availability' does not define a minimal requirement",
    ):
        normalize_input_payload(
            payload=payload,
            quality_model=minimal_quality_model,
            allowed_gaps={"no", "small", "large"},
        )
