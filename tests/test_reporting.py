from __future__ import annotations

from pathlib import Path

from genai_maturity.reporting.html_report import render_html_report


def test_render_html_report__includes_inference_rationale(skill_root: Path, tmp_path: Path) -> None:
    template_path = skill_root / "assets" / "report_template.html.j2"
    css_path = skill_root / "assets" / "report.css"
    output_path = tmp_path / "report.html"

    item = {
        "sub_characteristic": "adaptability",
        "display_name": "Adaptability",
        "characteristic": "robustness",
        "current_gap": "small",
        "first_unmet_level": 3,
        "target_gate": "min",
        "priority": "critical",
        "evidence": "",
        "action": "Define adaptation workflow.",
        "inference_rationale": "Minimal requirement is demonstrated, but full requirement is not yet demonstrated.",
    }

    data = {
        "title": "GenAI Quality and Maturity Assessment",
        "system": {
            "name": "Demo",
            "owner_team": "AI Team",
            "assessment_date": "2026-03-08",
            "assessor": "Tester",
        },
        "generated_at_utc": "2026-03-08T10:00:00+00:00",
        "criticality": "production_non_critical",
        "required_level": 3,
        "actual_level": 2,
        "quality_score": 72.5,
        "maturity_status": "below_required",
        "characteristics": [],
        "priority_buckets": {"critical": [item], "important": [], "nice_to_have": []},
        "gap_items": [item],
        "action_counts": {"critical": 1, "important": 0, "nice_to_have": 0},
    }

    render_html_report(
        template_path=template_path,
        css_path=css_path,
        output_path=output_path,
        data=data,
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Scoring rationale:" in html
    assert "Minimal requirement is demonstrated, but full requirement is not yet demonstrated." in html
    assert "Expected maturity based on business criticality" in html
    assert "Current maturity" in html
