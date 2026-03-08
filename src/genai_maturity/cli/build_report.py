from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from genai_maturity.engine.core import build_assessment_result, load_configs, validate_configs
from genai_maturity.io.exporters import write_gap_csv, write_json
from genai_maturity.io.interview import normalize_input_payload, run_guided_interview
from genai_maturity.reporting.html_report import render_html_report

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = ROOT / "resources" / "configs"
DEFAULT_ASSETS_DIR = ROOT / "resources" / "assets"


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


def _file_to_data_uri(path: Path) -> str:
    import base64
    import mimetypes

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _load_brand_logo_data_uri(assets_dir: Path) -> str | None:
    preferred = [
        assets_dir / "beyond_the_demo_logo.png",
        assets_dir / "logo.png",
        assets_dir / "logo.jpg",
        assets_dir / "logo.jpeg",
        assets_dir / "logo.svg",
    ]
    for candidate in preferred:
        if candidate.exists() and candidate.is_file():
            return _file_to_data_uri(candidate)

    for ext in ("*.png", "*.jpg", "*.jpeg", "*.svg", "*.webp"):
        for path in sorted(assets_dir.glob(ext)):
            if path.is_file():
                return _file_to_data_uri(path)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build GenAI maturity assessment report (JSON/CSV/HTML/PDF)."
    )
    parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR))
    parser.add_argument("--assets-dir", default=str(DEFAULT_ASSETS_DIR))
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
            inference_config=cfg.interview_inference,
            criticality_rules=cfg.criticality_rules,
        )
    else:
        normalized = run_guided_interview(
            cfg.quality_model,
            cfg.criticality_rules,
            cfg.interview_inference,
        )

    _validate_gap_values(normalized["gaps"], cfg)
    result = build_assessment_result(
        cfg=cfg,
        system=normalized["system"],
        criticality_answers=normalized["criticality_answers"],
        gaps=normalized["gaps"],
        evidence=normalized["evidence"],
        inference_rationale=normalized.get("inference_rationale", {}),
    )

    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
    generated_at_display = now_utc.strftime("%Y-%m-%d %H:%M")
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd() / "reports" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    result["generated_at_utc"] = now_utc.isoformat()

    json_path = output_dir / "assessment_result.json"
    csv_path = output_dir / "gaps.csv"
    html_path = output_dir / "assessment_report.html"
    pdf_path = output_dir / "assessment_report.pdf"

    write_json(json_path, result)
    write_gap_csv(csv_path, result["gap_items"])

    inference_rationale = result.get("inference_rationale", {})
    report_gap_items = [
        {
            **item,
            "inference_rationale": inference_rationale.get(item["sub_characteristic"], ""),
        }
        for item in result["gap_items"]
    ]

    system_for_view = {**result["system"], "assessment_date": generated_at_display}

    report_view = {
        "title": "GenAI Quality and Maturity Assessment",
        "brand_logo_data_uri": _load_brand_logo_data_uri(assets_dir),
        "system": system_for_view,
        "generated_at_utc": result["generated_at_utc"],
        "generated_at": generated_at_display,
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
        "priority_buckets": _priority_buckets(report_gap_items),
        "gap_items": report_gap_items,
        "action_counts": {
            "critical": len([x for x in report_gap_items if x["priority"] == "critical"]),
            "important": len([x for x in report_gap_items if x["priority"] == "important"]),
            "nice_to_have": len([x for x in report_gap_items if x["priority"] == "nice_to_have"]),
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
            "-m",
            "genai_maturity.cli.render_pdf_playwright",
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
