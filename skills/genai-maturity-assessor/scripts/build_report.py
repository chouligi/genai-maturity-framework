#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "io"))

try:
    from engine.core import build_assessment_result, load_configs, validate_configs
    from exporters import write_gap_csv, write_json
    from interview import normalize_input_payload, run_guided_interview
    from reporting.html_report import render_html_report
except ModuleNotFoundError as exc:
    missing_module = exc.name or "dependency"
    setup_msg = (
        f"Missing Python dependency '{missing_module}'.\n"
        "Run setup once:\n"
        "  bash skills/genai-maturity-assessor/scripts/bootstrap.sh\n"
        "Or manually:\n"
        "  uv venv .venv\n"
        "  uv pip install --python .venv/bin/python "
        "-r skills/genai-maturity-assessor/requirements.txt\n"
        "  uv run --python .venv/bin/python python -m playwright install chromium"
    )
    raise SystemExit(setup_msg) from exc


def _load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_gap_values(gaps: dict[str, str], cfg: Any) -> None:
    allowed = set(cfg.gap_scales["gaps"].keys())
    by_id = {item["id"]: item for item in cfg.quality_model["sub_characteristics"]}
    for sid, gap in gaps.items():
        if gap not in allowed:
            raise ValueError(f"Invalid gap value '{gap}' for {sid}. Allowed: {sorted(allowed)}")
        if by_id[sid].get("minimal_requirement", "-") == "-" and gap == "small":
            raise ValueError(
                f"Sub-characteristic '{sid}' does not define a minimal requirement and cannot use gap='small'."
            )


def _priority_buckets(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {"critical": [], "important": [], "nice_to_have": []}
    for item in items:
        buckets[item["priority"]].append(item)
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build GenAI maturity assessment report (JSON/CSV/HTML/PDF)."
    )
    parser.add_argument("--config-dir", default=str(ROOT / "configs"))
    parser.add_argument("--assets-dir", default=str(ROOT / "assets"))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--input-json",
        default=None,
        help="Use a pre-filled assessment JSON instead of interactive interview.",
    )
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF rendering step.")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    assets_dir = Path(args.assets_dir)

    cfg = load_configs(config_dir)
    errors = validate_configs(cfg)
    if errors:
        print("Config validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    if args.input_json:
        payload = _load_payload(Path(args.input_json))
        normalized = normalize_input_payload(
            payload=payload,
            quality_model=cfg.quality_model,
            allowed_gaps=set(cfg.gap_scales["gaps"].keys()),
        )
    else:
        normalized = run_guided_interview(cfg.quality_model, cfg.criticality_rules)

    _validate_gap_values(normalized["gaps"], cfg)
    result = build_assessment_result(
        cfg=cfg,
        system=normalized["system"],
        criticality_answers=normalized["criticality_answers"],
        gaps=normalized["gaps"],
        evidence=normalized["evidence"],
    )

    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "reports" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    result["generated_at_utc"] = now_utc.isoformat()

    json_path = output_dir / "assessment_result.json"
    csv_path = output_dir / "gaps.csv"
    html_path = output_dir / "assessment_report.html"
    pdf_path = output_dir / "assessment_report.pdf"

    write_json(json_path, result)
    write_gap_csv(csv_path, result["gap_items"])

    report_view = {
        "title": "GenAI Quality and Maturity Assessment",
        "system": result["system"],
        "generated_at_utc": result["generated_at_utc"],
        "criticality": result["criticality"],
        "required_level": result["required_maturity_level"],
        "actual_level": result["actual_maturity_level"],
        "quality_score": result["quality_score"],
        "maturity_status": result["maturity_status"],
        "characteristics": [
            {
                "id": cid,
                "display_name": cfg.quality_model["characteristics"][cid]["display_name"],
                "score": score,
            }
            for cid, score in result["characteristic_scores"].items()
        ],
        "priority_buckets": _priority_buckets(result["gap_items"]),
        "gap_items": result["gap_items"],
        "action_counts": {
            "critical": len([x for x in result["gap_items"] if x["priority"] == "critical"]),
            "important": len([x for x in result["gap_items"] if x["priority"] == "important"]),
            "nice_to_have": len([x for x in result["gap_items"] if x["priority"] == "nice_to_have"]),
        },
    }

    render_html_report(
        template_path=assets_dir / "report_template.html.j2",
        css_path=assets_dir / "report.css",
        output_path=html_path,
        data=report_view,
    )

    pdf_status = "skipped"
    if not args.no_pdf:
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "render_pdf_playwright.py"),
            "--input-html",
            str(html_path),
            "--output-pdf",
            str(pdf_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            pdf_status = "generated"
        else:
            pdf_status = "failed"
            result["pdf_error"] = (proc.stderr or proc.stdout).strip()
            write_json(json_path, result)

    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    print(f"HTML: {html_path}")
    print(f"PDF:  {pdf_path if pdf_status == 'generated' else f'not generated ({pdf_status})'}")
    if pdf_status == "failed":
        print("PDF rendering failed; HTML/JSON/CSV were still generated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
