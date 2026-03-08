from __future__ import annotations

import ast
from datetime import date
from typing import Any

TRUE_VALUES = {"y", "yes", "true", "1"}
FALSE_VALUES = {"n", "no", "false", "0"}
UNKNOWN_VALUES = {"?", "unknown", "na", "n/a", ""}

_UNKNOWN = object()


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def _is_unknown_like(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in UNKNOWN_VALUES
    return False


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = _ask(prompt).lower()
        if value in TRUE_VALUES:
            return True
        if value in FALSE_VALUES:
            return False
        print("Please answer with 'y' or 'n'.")


def ask_yes_no_unknown(prompt: str) -> bool | None:
    while True:
        value = _ask(prompt).lower()
        if value in TRUE_VALUES:
            return True
        if value in FALSE_VALUES:
            return False
        if value in UNKNOWN_VALUES:
            return None
        print("Please answer with 'y', 'n', or '?'.")


def ask_int_unknown(prompt: str) -> int | None:
    while True:
        value = _ask(prompt)
        if _is_unknown_like(value):
            return None
        try:
            return int(value)
        except ValueError:
            print("Please enter an integer or '?'.")


def ask_float_unknown(prompt: str) -> float | None:
    while True:
        value = _ask(prompt)
        if _is_unknown_like(value):
            return None
        try:
            return float(value)
        except ValueError:
            print("Please enter a number or '?'.")


def ask_enum_unknown(prompt: str, options: list[str]) -> str | None:
    allowed = [str(item).strip().lower() for item in options]
    allowed_text = "/".join(allowed)
    while True:
        value = _ask(prompt).strip().lower()
        if value in allowed:
            return value
        if _is_unknown_like(value):
            return None
        print(f"Please choose one of: {allowed_text} or '?'.")


def _coerce_signal_value(raw_value: Any, signal_def: dict[str, Any]) -> Any:
    if _is_unknown_like(raw_value):
        return None

    signal_type = str(signal_def.get("type", "")).strip().lower()
    key = signal_def.get("key", "unknown")

    if signal_type == "bool":
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, int) and raw_value in {0, 1}:
            return bool(raw_value)
        if isinstance(raw_value, str):
            lowered = raw_value.strip().lower()
            if lowered in TRUE_VALUES:
                return True
            if lowered in FALSE_VALUES:
                return False
        raise ValueError(f"Invalid boolean value for signal '{key}': {raw_value}")

    if signal_type == "int":
        if isinstance(raw_value, bool):
            raise ValueError(f"Invalid integer value for signal '{key}': {raw_value}")
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, float) and raw_value.is_integer():
            return int(raw_value)
        if isinstance(raw_value, str):
            try:
                return int(raw_value.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid integer value for signal '{key}': {raw_value}") from exc
        raise ValueError(f"Invalid integer value for signal '{key}': {raw_value}")

    if signal_type == "float":
        if isinstance(raw_value, bool):
            raise ValueError(f"Invalid float value for signal '{key}': {raw_value}")
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        if isinstance(raw_value, str):
            try:
                return float(raw_value.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid float value for signal '{key}': {raw_value}") from exc
        raise ValueError(f"Invalid float value for signal '{key}': {raw_value}")

    if signal_type == "enum":
        options = [str(item).strip().lower() for item in signal_def.get("options", [])]
        normalized = str(raw_value).strip().lower()
        if normalized in options:
            return normalized
        raise ValueError(
            f"Invalid enum value for signal '{key}': {raw_value}. Allowed: {options}"
        )

    raise ValueError(f"Unsupported signal type '{signal_type}' for signal '{key}'")


def normalize_signals_payload(
    payload_signals: dict[str, Any],
    inference_config: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload_signals, dict):
        raise ValueError("Input JSON field 'signals' must be an object/mapping.")

    signal_defs = inference_config.get("signals", [])
    if not isinstance(signal_defs, list):
        raise ValueError("inference config must define 'signals' as a list.")

    normalized: dict[str, Any] = {}
    for signal in signal_defs:
        key = str(signal.get("key", "")).strip()
        if not key:
            raise ValueError("inference config contains a signal without a key.")
        raw_value = payload_signals.get(key)
        normalized[key] = _coerce_signal_value(raw_value, signal)
    return normalized


def _is_unknown_value(value: Any) -> bool:
    return value is _UNKNOWN


class _ConditionEvaluator(ast.NodeVisitor):
    def __init__(self, signals: dict[str, Any]) -> None:
        self.signals = signals
        self.unknown_used = False

    def evaluate(self, expression: str) -> tuple[bool, bool]:
        node = ast.parse(expression, mode="eval")
        result = self.visit(node.body)
        if _is_unknown_value(result):
            self.unknown_used = True
            return False, True
        return bool(result), self.unknown_used

    def visit_Name(self, node: ast.Name) -> Any:
        lowered = node.id.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False

        if node.id not in self.signals or self.signals[node.id] is None:
            self.unknown_used = True
            return _UNKNOWN
        return self.signals[node.id]

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(item) for item in node.elts)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            for value_node in node.values:
                value = self.visit(value_node)
                if _is_unknown_value(value):
                    self.unknown_used = True
                    return False
                if not bool(value):
                    return False
            return True

        if isinstance(node.op, ast.Or):
            saw_unknown = False
            for value_node in node.values:
                value = self.visit(value_node)
                if _is_unknown_value(value):
                    saw_unknown = True
                    continue
                if bool(value):
                    return True
            if saw_unknown:
                self.unknown_used = True
            return False

        raise ValueError("Unsupported boolean operator in condition.")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if not isinstance(node.op, ast.Not):
            raise ValueError("Unsupported unary operator in condition.")

        value = self.visit(node.operand)
        if _is_unknown_value(value):
            self.unknown_used = True
            return False
        return not bool(value)

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if not self._compare(left, op, right):
                return False
            left = right
        return True

    def _compare(self, left: Any, op: ast.cmpop, right: Any) -> bool:
        if _is_unknown_value(left) or _is_unknown_value(right):
            self.unknown_used = True
            return False

        try:
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.GtE):
                return left >= right
            if isinstance(op, ast.Lt):
                return left < right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
        except TypeError:
            self.unknown_used = True
            return False

        raise ValueError("Unsupported comparison operator in condition.")

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def evaluate_condition(expression: str, signals: dict[str, Any]) -> tuple[bool, bool]:
    evaluator = _ConditionEvaluator(signals)
    return evaluator.evaluate(expression)


def _should_ask(signal_def: dict[str, Any], current_signals: dict[str, Any]) -> bool:
    ask_if = signal_def.get("ask_if")
    if not ask_if:
        return True
    result, _ = evaluate_condition(str(ask_if), current_signals)
    return result


def collect_signals(inference_config: dict[str, Any]) -> dict[str, Any]:
    signal_defs = inference_config.get("signals", [])
    if not isinstance(signal_defs, list):
        raise ValueError("inference config must define 'signals' as a list.")

    signals: dict[str, Any] = {}
    for signal in signal_defs:
        key = str(signal.get("key", "")).strip()
        if not key:
            raise ValueError("inference config contains a signal without a key.")

        if not _should_ask(signal, signals):
            signals[key] = None
            continue

        signal_type = str(signal.get("type", "")).strip().lower()
        prompt = str(signal.get("prompt", key)) + " "

        if signal_type == "bool":
            signals[key] = ask_yes_no_unknown(prompt)
            continue
        if signal_type == "int":
            signals[key] = ask_int_unknown(prompt)
            continue
        if signal_type == "float":
            signals[key] = ask_float_unknown(prompt)
            continue
        if signal_type == "enum":
            options = [str(item) for item in signal.get("options", [])]
            signals[key] = ask_enum_unknown(prompt, options)
            continue

        raise ValueError(f"Unsupported signal type '{signal_type}' for signal '{key}'")

    return signals


def _compose_rationale(
    gap: str,
    has_min_requirement: bool,
    unknown_used: bool,
) -> str:
    if gap == "no":
        base = "Full requirement is currently demonstrated."
    elif gap == "small":
        base = "Minimal requirement is demonstrated, but full requirement is not yet demonstrated."
    elif has_min_requirement:
        base = "Neither minimal nor full requirement is currently demonstrated."
    else:
        base = "Full requirement is not yet demonstrated."

    if unknown_used:
        return base + " Some answers were unknown and were scored conservatively."
    return base


def infer_gaps(
    quality_model: dict[str, Any],
    inference_config: dict[str, Any],
    signals: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    rules_by_id = inference_config.get("sub_characteristics", {})
    if not isinstance(rules_by_id, dict):
        raise ValueError("inference config must define 'sub_characteristics' as a mapping.")

    gaps: dict[str, str] = {}
    rationale: dict[str, str] = {}

    for item in quality_model.get("sub_characteristics", []):
        sid = item["id"]
        if sid not in rules_by_id:
            raise ValueError(f"Missing inference rule for sub-characteristic '{sid}'")

        rules = rules_by_id[sid]
        full_condition = str(rules.get("full_condition", "")).strip()
        min_condition_raw = rules.get("min_condition")
        min_condition = str(min_condition_raw).strip() if isinstance(min_condition_raw, str) else None

        if not full_condition:
            raise ValueError(f"Missing full_condition for sub-characteristic '{sid}'")

        has_min_requirement = item.get("minimal_requirement", "-") != "-"

        full_met, full_unknown = evaluate_condition(full_condition, signals)
        min_unknown = False

        if full_met:
            gap = "no"
        elif has_min_requirement and min_condition:
            min_met, min_unknown = evaluate_condition(min_condition, signals)
            gap = "small" if min_met else "large"
        else:
            gap = "large"

        unknown_used = full_unknown or min_unknown
        gaps[sid] = gap
        rationale[sid] = _compose_rationale(
            gap=gap,
            has_min_requirement=has_min_requirement,
            unknown_used=unknown_used,
        )

    return gaps, rationale


def run_guided_interview(
    quality_model: dict[str, Any],
    criticality_rules: dict[str, Any],
    inference_config: dict[str, Any],
) -> dict[str, Any]:
    print("\n=== GenAI Maturity Assessment Interview ===")

    system = {
        "name": _ask("System name: "),
        "owner_team": _ask("Owner team: "),
        "assessment_date": date.today().isoformat(),
        "assessor": _ask("Assessor name: "),
    }

    print("\n--- Criticality ---")
    criticality_answers: dict[str, bool] = {}
    for question in criticality_rules.get("questions", []):
        criticality_answers[question["key"]] = ask_yes_no(question["prompt"] + " ")

    print("\n--- Capability Interview ---")
    print("Answer each question with y/n/? or provide a number when requested.")
    signals = collect_signals(inference_config)

    gaps, inference_rationale = infer_gaps(quality_model, inference_config, signals)
    evidence = {sid: "" for sid in gaps}

    return {
        "system": system,
        "criticality_answers": criticality_answers,
        "gaps": gaps,
        "evidence": evidence,
        "signals": signals,
        "inference_rationale": inference_rationale,
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


def _derive_criticality_answers_from_label(
    criticality_label: str,
    criticality_rules: dict[str, Any] | None,
) -> dict[str, bool]:
    logic = {}
    if isinstance(criticality_rules, dict):
        logic = criticality_rules.get("criticality_logic", {}) or {}

    production_key = str(logic.get("production_key", "in_production"))
    critical_keys = [
        str(key)
        for key in logic.get("production_critical_if_any", [])
        if isinstance(key, str) and key.strip()
    ]

    answers = {production_key: False}
    for key in critical_keys:
        answers[key] = False

    normalized = str(criticality_label).strip().lower()
    if normalized == "production_non_critical":
        answers[production_key] = True
    elif normalized == "production_critical":
        answers[production_key] = True
        if critical_keys:
            answers[critical_keys[0]] = True

    return answers


def normalize_input_payload(
    payload: dict[str, Any],
    quality_model: dict[str, Any],
    allowed_gaps: set[str] | None = None,
    inference_config: dict[str, Any] | None = None,
    criticality_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required_ids = [item["id"] for item in quality_model.get("sub_characteristics", [])]
    by_id = {item["id"]: item for item in quality_model.get("sub_characteristics", [])}

    system = payload.get("system", {})
    criticality_answers = payload.get("criticality_answers", {})
    if not isinstance(criticality_answers, dict):
        raise ValueError("Input JSON field 'criticality_answers' must be an object/mapping.")
    if not criticality_answers and "criticality" in payload:
        criticality_answers = _derive_criticality_answers_from_label(
            criticality_label=str(payload.get("criticality", "")),
            criticality_rules=criticality_rules,
        )
    gaps = payload.get("gaps", {})
    signals_payload = payload.get("signals")
    evidence = payload.get("evidence", {})

    normalized_criticality_answers = {
        key: _to_bool(value, key) for key, value in criticality_answers.items()
    }

    if isinstance(gaps, dict) and gaps:
        missing = [sid for sid in required_ids if sid not in gaps]
        if missing:
            raise ValueError("Input JSON missing gaps for: " + ", ".join(missing))

        normalized_gaps = {sid: str(gaps[sid]).strip().lower() for sid in required_ids}
        normalized_signals: dict[str, Any] = {}
        inference_rationale = {sid: "" for sid in required_ids}
    else:
        if signals_payload is None:
            raise ValueError("Input JSON must include either 'gaps' or 'signals'.")
        if inference_config is None:
            raise ValueError("inference_config is required when using signals-based input.")

        normalized_signals = normalize_signals_payload(signals_payload, inference_config)
        normalized_gaps, inference_rationale = infer_gaps(
            quality_model=quality_model,
            inference_config=inference_config,
            signals=normalized_signals,
        )

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
        "signals": normalized_signals,
        "inference_rationale": inference_rationale,
    }
