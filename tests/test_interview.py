from __future__ import annotations

import pytest

from genai_maturity.io import interview as interview_module
from genai_maturity.io.interview import (
    collect_signals,
    infer_gaps,
    normalize_input_payload,
    normalize_signals_payload,
)


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


def test_infer_gaps__maps_full_small_large_is_correct(
    minimal_quality_model: dict[str, object],
    minimal_inference_config: dict[str, object],
) -> None:
    signals = {"full_met": False, "min_met": True, "followup": None}

    gaps, rationale = infer_gaps(
        quality_model=minimal_quality_model,
        inference_config=minimal_inference_config,
        signals=signals,
    )

    assert gaps["availability"] == "large"
    assert gaps["adaptability"] == "small"
    assert rationale["adaptability"]


def test_infer_gaps__unknown_answers_are_conservative(
    minimal_quality_model: dict[str, object],
    minimal_inference_config: dict[str, object],
) -> None:
    signals = {"full_met": None, "min_met": None, "followup": None}

    gaps, rationale = infer_gaps(
        quality_model=minimal_quality_model,
        inference_config=minimal_inference_config,
        signals=signals,
    )

    assert gaps["availability"] == "large"
    assert gaps["adaptability"] == "large"
    assert "conservative" in rationale["adaptability"].lower()


def test_collect_signals__skips_followup_when_ask_if_is_false(
    minimal_inference_config: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(["n", "y"])

    monkeypatch.setattr(interview_module, "_ask", lambda prompt: next(answers))

    signals = collect_signals(minimal_inference_config)

    assert signals["full_met"] is False
    assert signals["min_met"] is True
    assert signals["followup"] is None


def test_normalize_input_payload__signals_mode_infers_gaps(
    minimal_quality_model: dict[str, object],
    minimal_inference_config: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality_answers": {"in_production": "true"},
        "signals": {"full_met": False, "min_met": True},
        "evidence": {},
    }

    normalized = normalize_input_payload(
        payload=payload,
        quality_model=minimal_quality_model,
        allowed_gaps={"no", "small", "large"},
        inference_config=minimal_inference_config,
    )

    assert normalized["gaps"]["availability"] == "large"
    assert normalized["gaps"]["adaptability"] == "small"
    assert normalized["signals"]["min_met"] is True
    assert normalized["inference_rationale"]["adaptability"]


def test_normalize_signals_payload__invalid_enum_raised_error() -> None:
    inference_config = {
        "signals": [
            {"key": "level", "type": "enum", "options": ["none", "partial", "full"]},
        ]
    }
    payload_signals = {"level": "advanced"}

    with pytest.raises(ValueError, match="Invalid enum value for signal 'level'"):
        normalize_signals_payload(payload_signals, inference_config)


def test_normalize_input_payload__derives_criticality_answers_from_label(
    minimal_quality_model: dict[str, object],
    minimal_criticality_rules: dict[str, object],
) -> None:
    payload = {
        "system": {"name": "Demo"},
        "criticality": "production_critical",
        "gaps": {"availability": "no", "adaptability": "small"},
        "evidence": {},
    }

    normalized = normalize_input_payload(
        payload=payload,
        quality_model=minimal_quality_model,
        allowed_gaps={"no", "small", "large"},
        criticality_rules=minimal_criticality_rules,
    )

    answers = normalized["criticality_answers"]
    assert answers["in_production"] is True
    assert answers["high_request_volume_top_third"] is True
    assert answers["strategic_importance"] is False
