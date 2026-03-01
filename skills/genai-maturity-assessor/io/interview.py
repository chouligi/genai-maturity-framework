from __future__ import annotations

from datetime import date
from typing import Any

TRUE_VALUES = {"y", "yes", "true", "1"}
FALSE_VALUES = {"n", "no", "false", "0"}


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = _ask(prompt).lower()
        if value in TRUE_VALUES:
            return True
        if value in FALSE_VALUES:
            return False
        print("Please answer with 'y' or 'n'.")


def ask_gap(prompt: str, allow_small: bool = True) -> str:
    allowed = ["no", "small", "large"] if allow_small else ["no", "large"]
    allowed_text = "/".join(allowed)
    while True:
        value = _ask(f"{prompt} ({allowed_text}): ").lower()
        if value in allowed:
            return value
        print(f"Please choose one of: {allowed_text}")


def run_guided_interview(quality_model: dict[str, Any], criticality_rules: dict[str, Any]) -> dict[str, Any]:
    print("\n=== GenAI Maturity Assessment Interview ===")

    system = {
        "name": _ask("System name: "),
        "owner_team": _ask("Owner team: "),
        "assessment_date": _ask(f"Assessment date [{date.today().isoformat()}]: ")
        or date.today().isoformat(),
        "assessor": _ask("Assessor name: "),
    }

    print("\n--- Criticality ---")
    criticality_answers: dict[str, bool] = {}
    for question in criticality_rules.get("questions", []):
        criticality_answers[question["key"]] = ask_yes_no(question["prompt"] + " ")

    print("\n--- Quality Gaps ---")
    print("Use: 'no' = full requirement met, 'small' = only minimal met, 'large' = neither met.")
    gaps: dict[str, str] = {}
    evidence: dict[str, str] = {}

    for item in quality_model.get("sub_characteristics", []):
        sid = item["id"]
        print(f"\n[{item['display_name']}] ({item['characteristic']})")
        print(f"Minimal requirement: {item['minimal_requirement']}")
        print(f"Full requirement: {item['full_requirement']}")
        allow_small = item.get("minimal_requirement", "-") != "-"
        gaps[sid] = ask_gap("Gap", allow_small=allow_small)
        evidence[sid] = _ask("Evidence (optional): ")

    return {
        "system": system,
        "criticality_answers": criticality_answers,
        "gaps": gaps,
        "evidence": evidence,
    }


def _to_bool(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in {0, 1}:
            return bool(value)
        msg = f"Invalid integer for boolean field '{key}': {value}"
        raise ValueError(msg)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        msg = f"Invalid string for boolean field '{key}': {value}"
        raise ValueError(msg)

    msg = f"Unsupported type for boolean field '{key}': {type(value).__name__}"
    raise ValueError(msg)


def normalize_input_payload(
    payload: dict[str, Any],
    quality_model: dict[str, Any],
    allowed_gaps: set[str] | None = None,
) -> dict[str, Any]:
    required_ids = [item["id"] for item in quality_model.get("sub_characteristics", [])]
    by_id = {item["id"]: item for item in quality_model.get("sub_characteristics", [])}

    system = payload.get("system", {})
    criticality_answers = payload.get("criticality_answers", {})
    gaps = payload.get("gaps", {})
    evidence = payload.get("evidence", {})

    missing = [sid for sid in required_ids if sid not in gaps]
    if missing:
        raise ValueError("Input JSON missing gaps for: " + ", ".join(missing))

    normalized_criticality_answers = {
        key: _to_bool(value, key) for key, value in criticality_answers.items()
    }
    normalized_gaps = {sid: str(gaps[sid]).strip().lower() for sid in required_ids}
    normalized_evidence = {sid: str(evidence.get(sid, "")) for sid in required_ids}

    if allowed_gaps is not None:
        for sid, gap in normalized_gaps.items():
            if gap not in allowed_gaps:
                raise ValueError(
                    f"Invalid gap value '{gap}' for '{sid}'. Allowed values: {sorted(allowed_gaps)}"
                )

    for sid, gap in normalized_gaps.items():
        has_min_requirement = by_id[sid].get("minimal_requirement", "-") != "-"
        if not has_min_requirement and gap == "small":
            raise ValueError(
                f"Sub-characteristic '{sid}' does not define a minimal requirement and cannot use gap='small'."
            )

    return {
        "system": system,
        "criticality_answers": normalized_criticality_answers,
        "gaps": normalized_gaps,
        "evidence": normalized_evidence,
    }
