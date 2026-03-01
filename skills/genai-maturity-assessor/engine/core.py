from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

GATE_VALUES = {"none", "min", "full"}


@dataclass
class LoadedConfigs:
    quality_model: dict[str, Any]
    maturity_gates: dict[str, dict[int, str]]
    gap_scales: dict[str, Any]
    recommendations: dict[str, Any]
    criticality_rules: dict[str, Any]


class ConfigError(Exception):
    """Raised when config files are invalid."""


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def _load_gates_csv(path: Path) -> dict[str, dict[int, str]]:
    gates: dict[str, dict[int, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sid = row["sub_characteristic"].strip()
            gates[sid] = {level: row[f"l{level}"].strip() for level in range(1, 6)}
    return gates


def load_configs(config_dir: Path) -> LoadedConfigs:
    quality_model = _load_yaml(config_dir / "quality_model.yaml")
    maturity_gates = _load_gates_csv(config_dir / "maturity_gates.csv")
    gap_scales = _load_yaml(config_dir / "gap_scales.yaml")
    recommendations = _load_yaml(config_dir / "recommendations.yaml")
    criticality_rules = _load_yaml(config_dir / "criticality_rules.yaml")
    return LoadedConfigs(
        quality_model=quality_model,
        maturity_gates=maturity_gates,
        gap_scales=gap_scales,
        recommendations=recommendations,
        criticality_rules=criticality_rules,
    )


def validate_configs(cfg: LoadedConfigs) -> list[str]:
    errors: list[str] = []

    subchars = cfg.quality_model.get("sub_characteristics", [])
    if not isinstance(subchars, list):
        errors.append("quality_model.yaml: 'sub_characteristics' must be a list")
        return errors

    quality_ids = [item.get("id") for item in subchars if isinstance(item, dict)]
    if len(quality_ids) != 25:
        errors.append(
            f"quality_model.yaml: expected exactly 25 sub-characteristics, found {len(quality_ids)}"
        )

    if len(set(quality_ids)) != len(quality_ids):
        errors.append("quality_model.yaml: duplicate sub-characteristic IDs found")

    gate_ids = set(cfg.maturity_gates.keys())
    if len(gate_ids) != 25:
        errors.append(f"maturity_gates.csv: expected exactly 25 rows, found {len(gate_ids)}")

    recs = cfg.recommendations.get("recommendations", {})
    if not isinstance(recs, dict):
        errors.append("recommendations.yaml: 'recommendations' must be a mapping")
        rec_ids: set[str] = set()
    else:
        rec_ids = set(recs.keys())

    quality_set = set(quality_ids)
    if quality_set != gate_ids:
        missing_in_gates = sorted(quality_set - gate_ids)
        missing_in_quality = sorted(gate_ids - quality_set)
        if missing_in_gates:
            errors.append(
                "maturity_gates.csv is missing IDs from quality_model.yaml: "
                + ", ".join(missing_in_gates)
            )
        if missing_in_quality:
            errors.append(
                "quality_model.yaml is missing IDs from maturity_gates.csv: "
                + ", ".join(missing_in_quality)
            )

    if quality_set != rec_ids:
        missing_in_recs = sorted(quality_set - rec_ids)
        missing_in_quality = sorted(rec_ids - quality_set)
        if missing_in_recs:
            errors.append(
                "recommendations.yaml is missing IDs from quality_model.yaml: "
                + ", ".join(missing_in_recs)
            )
        if missing_in_quality:
            errors.append(
                "quality_model.yaml is missing IDs from recommendations.yaml: "
                + ", ".join(missing_in_quality)
            )

    for sid, levels in cfg.maturity_gates.items():
        for level in range(1, 6):
            gate = levels.get(level)
            if gate not in GATE_VALUES:
                errors.append(
                    f"maturity_gates.csv: invalid gate '{gate}' for '{sid}' at level l{level}"
                )

    gaps = cfg.gap_scales.get("gaps", {})
    expected_gaps = {"no": 0, "small": 1, "large": 2}
    if gaps != expected_gaps:
        errors.append(
            "gap_scales.yaml: expected gaps mapping exactly {'no': 0, 'small': 1, 'large': 2}"
        )

    fulfillment = cfg.gap_scales.get("fulfillment", {})
    full_met = set(fulfillment.get("full_met", []))
    min_met = set(fulfillment.get("min_met", []))
    if full_met != {"no"}:
        errors.append("gap_scales.yaml: fulfillment.full_met must be exactly ['no']")
    if min_met != {"no", "small"}:
        errors.append("gap_scales.yaml: fulfillment.min_met must be exactly ['no', 'small']")

    return errors


def classify_criticality(answers: dict[str, bool], rules: dict[str, Any]) -> tuple[str, int]:
    required = rules.get("required_maturity", {})
    logic = rules.get("criticality_logic", {})
    production_key = logic.get("production_key", "in_production")
    critical_keys = logic.get("production_critical_if_any", [])

    in_production = bool(answers.get(production_key, False))
    if not in_production:
        label = "proof_of_concept"
    elif any(bool(answers.get(key, False)) for key in critical_keys):
        label = "production_critical"
    else:
        label = "production_non_critical"

    return label, int(required[label])


def gate_satisfied(gap: str, gate: str, gap_scales: dict[str, Any]) -> bool:
    if gate == "none":
        return True
    if gate == "min":
        return gap in set(gap_scales["fulfillment"]["min_met"])
    if gate == "full":
        return gap in set(gap_scales["fulfillment"]["full_met"])
    return False


def compute_quality_score(gaps: dict[str, str], gap_scales: dict[str, Any]) -> float:
    total = sum(gap_scales["gaps"][gap] for gap in gaps.values())
    denom = 2 * len(gaps)
    return round(100.0 * (1.0 - (total / denom)), 2)


def compute_characteristic_scores(
    quality_model: dict[str, Any], gaps: dict[str, str], gap_scales: dict[str, Any]
) -> dict[str, float]:
    scores: dict[str, float] = {}
    subchars = quality_model["sub_characteristics"]
    by_characteristic: dict[str, list[str]] = {}
    for item in subchars:
        by_characteristic.setdefault(item["characteristic"], []).append(item["id"])

    for characteristic, ids in by_characteristic.items():
        local_gaps = {sid: gaps[sid] for sid in ids}
        scores[characteristic] = compute_quality_score(local_gaps, gap_scales)
    return scores


def compute_actual_maturity(
    gaps: dict[str, str], maturity_gates: dict[str, dict[int, str]], gap_scales: dict[str, Any]
) -> int:
    actual = 1
    for level in range(1, 6):
        level_ok = True
        for sid, level_gates in maturity_gates.items():
            if not gate_satisfied(gaps[sid], level_gates[level], gap_scales):
                level_ok = False
                break
        if level_ok:
            actual = level
        else:
            break
    return actual


def _first_unmet_level(
    sid: str, gap: str, maturity_gates: dict[str, dict[int, str]], gap_scales: dict[str, Any]
) -> int | None:
    for level in range(1, 6):
        gate = maturity_gates[sid][level]
        if not gate_satisfied(gap, gate, gap_scales):
            return level
    return None


def _compose_action(
    sid: str,
    gap: str,
    needed_gate: str,
    recommendations: dict[str, Any],
    has_min_requirement: bool,
) -> str:
    rec = recommendations["recommendations"][sid]
    if needed_gate == "min":
        return rec["min_action"]

    if needed_gate == "full" and gap == "small":
        return rec["full_action"]

    if needed_gate == "full" and gap == "large" and has_min_requirement:
        return f"Step 1: {rec['min_action']} Step 2: {rec['full_action']}"

    return rec["full_action"]


def build_gap_priorities(
    quality_model: dict[str, Any],
    gaps: dict[str, str],
    evidence: dict[str, str],
    maturity_gates: dict[str, dict[int, str]],
    recommendations: dict[str, Any],
    gap_scales: dict[str, Any],
    actual_level: int,
    required_level: int,
) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in quality_model["sub_characteristics"]}
    items: list[dict[str, Any]] = []

    for sid, gap in gaps.items():
        first_unmet = _first_unmet_level(sid, gap, maturity_gates, gap_scales)
        if first_unmet is None:
            continue

        if first_unmet <= min(required_level, actual_level + 1):
            priority = "critical"
        elif first_unmet <= required_level:
            priority = "important"
        else:
            priority = "nice_to_have"

        target_gate = maturity_gates[sid][first_unmet]
        has_min = by_id[sid].get("minimal_requirement", "-") != "-"
        action = _compose_action(sid, gap, target_gate, recommendations, has_min)

        items.append(
            {
                "sub_characteristic": sid,
                "display_name": by_id[sid]["display_name"],
                "characteristic": by_id[sid]["characteristic"],
                "current_gap": gap,
                "first_unmet_level": first_unmet,
                "target_gate": target_gate,
                "priority": priority,
                "evidence": evidence.get(sid, "").strip(),
                "action": action,
            }
        )

    rank = {"critical": 0, "important": 1, "nice_to_have": 2}
    items.sort(key=lambda item: (rank[item["priority"]], item["first_unmet_level"], item["display_name"]))
    return items


def build_assessment_result(
    cfg: LoadedConfigs,
    system: dict[str, Any],
    criticality_answers: dict[str, bool],
    gaps: dict[str, str],
    evidence: dict[str, str],
) -> dict[str, Any]:
    criticality_label, required_level = classify_criticality(
        criticality_answers, cfg.criticality_rules
    )
    actual_level = compute_actual_maturity(gaps, cfg.maturity_gates, cfg.gap_scales)
    quality_score = compute_quality_score(gaps, cfg.gap_scales)
    characteristic_scores = compute_characteristic_scores(
        cfg.quality_model, gaps, cfg.gap_scales
    )

    gap_items = build_gap_priorities(
        quality_model=cfg.quality_model,
        gaps=gaps,
        evidence=evidence,
        maturity_gates=cfg.maturity_gates,
        recommendations=cfg.recommendations,
        gap_scales=cfg.gap_scales,
        actual_level=actual_level,
        required_level=required_level,
    )

    return {
        "system": system,
        "criticality": criticality_label,
        "required_maturity_level": required_level,
        "actual_maturity_level": actual_level,
        "maturity_status": "met" if actual_level >= required_level else "below_required",
        "quality_score": quality_score,
        "characteristic_scores": characteristic_scores,
        "gap_items": gap_items,
        "gaps": gaps,
        "evidence": evidence,
    }
