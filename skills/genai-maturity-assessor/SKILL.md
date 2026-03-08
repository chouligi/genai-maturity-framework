---
name: genai-maturity-assessor
description: Assess the quality and maturity of GenAI systems with a guided interview and a config-driven scoring engine. Use when you need to determine business criticality, evaluate quality gaps (no/small/large), compute maturity against paper-level gates, and generate HTML/PDF reports plus JSON/CSV artifacts.
---

# GenAI Maturity Assessor

## Overview

Run a complete GenAI quality and maturity assessment using editable config files. Keep scoring logic in code and keep framework definitions in `configs/` for easy review and updates.

## Workflow

0. Run one-time environment bootstrap.
1. Validate config integrity.
2. Run a guided interview or load an input JSON.
3. Compute quality score and maturity level.
4. Generate `assessment_result.json`, `gaps.csv`, `assessment_report.html`, and optionally `assessment_report.pdf`.

## Commands

One-time setup:

```bash
bash skills/genai-maturity-assessor/scripts/bootstrap.sh
```

Validate configs:

```bash
uv run --python .venv/bin/python python skills/genai-maturity-assessor/scripts/validate_configs.py
```

Run guided interview:

```bash
uv run --python .venv/bin/python python skills/genai-maturity-assessor/scripts/build_report.py
```

Run with pre-filled input:

```bash
uv run --python .venv/bin/python python skills/genai-maturity-assessor/scripts/build_report.py \
  --input-json skills/genai-maturity-assessor/examples/assessment_input_example.json \
  --output-dir /tmp/genai_assessment_out
```

Skip PDF render:

```bash
uv run --python .venv/bin/python python skills/genai-maturity-assessor/scripts/build_report.py --no-pdf
```

Run a fully mature sample:

```bash
uv run --python .venv/bin/python python skills/genai-maturity-assessor/scripts/build_report.py \
  --input-json skills/genai-maturity-assessor/examples/assessment_input_fully_mature.json \
  --output-dir /tmp/genai_assessment_full --no-pdf
```

## Config Files

- `configs/quality_model.yaml`: quality characteristics and GenAI-adapted requirements.
- `configs/maturity_gates.csv`: canonical maturity gates per level (`none|min|full`) per sub-characteristic.
- `configs/gap_scales.yaml`: gap encoding and fulfillment semantics.
- `configs/recommendations.yaml`: remediation actions for minimal/full targets.
- `configs/criticality_rules.yaml`: business criticality and required maturity mapping.
- `configs/interview_inference.yaml`: deterministic signal questions and gap inference rules.

## Input and Output Contracts

Interactive mode asks:

1. System metadata.
2. Criticality questions.
3. Capability questions (signals), then infers each sub-characteristic gap (`no`, `small`, `large`).

Pre-filled JSON input shape:

```json
{
  "system": {
    "name": "My GenAI System",
    "owner_team": "AI Platform",
    "assessment_date": "2026-02-28",
    "assessor": "Jane Doe"
  },
  "criticality_answers": {
    "in_production": true,
    "high_request_volume_top_third": false,
    "dependent_teams_ge_4": true,
    "revenue_impact_gt_1pct": false,
    "strategic_importance": true
  },
  "gaps": {
    "accuracy": "small",
    "effectiveness": "large"
  },
  "evidence": {
    "accuracy": "Golden set is 70 examples",
    "effectiveness": "No recent A/B run"
  }
}
```

Signals-based JSON input is also supported:

```json
{
  "system": {
    "name": "My GenAI System"
  },
  "criticality_answers": {
    "in_production": true
  },
  "signals": {
    "golden_set_size": 220,
    "eval_automated_metrics": true,
    "eval_human_review": true
  },
  "evidence": {}
}
```

Reusable input examples are provided in `examples/`:

- `examples/assessment_input_example.json`
- `examples/assessment_input_fully_mature.json`

Generated artifacts:

- `assessment_result.json`
- `gaps.csv`
- `assessment_report.html`
- `assessment_report.pdf` (if Playwright rendering works)

## PDF Rendering

Use Playwright Chromium through `scripts/render_pdf_playwright.py`.

If Playwright is unavailable, the script still produces HTML/JSON/CSV and reports the PDF error clearly.

## Dependencies

- Python dependencies are listed in `requirements.txt`.
- Bootstrap installs `playwright` and the Chromium browser needed for PDF rendering.
