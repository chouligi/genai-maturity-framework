# GenAI Maturity Assessment

Welcome to the GenAI Maturity Assessment toolkit.  
Use this guide to assess the maturity of your GenAI system in a way that fits your workflow:

- **Lite mode (no-code):** run in assistant UI and produce a Markdown report.
- **Pro mode (package):** run as Python package and produce JSON/CSV/HTML/PDF artifacts.

## 1) Lite Mode (No-Code, Assistant UI)

Use this when you do not want local setup.

### What you get
- Guided interview in chat
- Final report in **Markdown** (`.md`-style content)
- No local Python/Playwright installation required

### Which file to add in your assistant UI
1. If your assistant UI asks for a skill instruction file, use `skills/genai-maturity-assessor/SKILL.md`.
2. If your assistant UI supports a skill manifest/config file, use `skills/genai-maturity-assessor/agents/assistant.yaml`.
3. If it asks for only one file and you are unsure, use `skills/genai-maturity-assessor/SKILL.md`.

### How to use
1. Install/add the skill in your assistant UI.
2. Ask the assistant to run **Lite mode** assessment.
3. Recommended trigger phrase:
   `assess my genai system`
4. Answer interview questions.
5. Receive Markdown report in chat.

### Example Lite report
- File: [`examples/reports/example_lite_report.md`](examples/reports/example_lite_report.md)

Inline preview:
```md
## GenAI Maturity Assessment (Lite Mode)

## System Snapshot
- System: My Awesome genAI system
- Team: My awesome team
- Assessor: Jon Doe
- Mode: Lite (no-code, Markdown-only)

## Business Criticality
- Classification: Production Critical
- Required maturity level: L5
- Current maturity level: L1
- Status: Below required maturity

## Priority Actions
### Critical
1. Availability: Define and meet availability SLA targets with monitored fallback behavior.
2. Fairness: Evaluate across relevant groups and apply disparity mitigations.
```

### Limitations
- No local file exports by default (unless the assistant environment supports tools/filesystem writes).
- No PDF rendering in Lite mode.

## 2) Pro Mode (Python Package)

Use this when you want reproducible artifacts and PDF output.

### Prerequisites
- Python 3.11+
- `uv` (recommended)

### Install
```bash
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]"
uv run --python .venv/bin/python python -m playwright install chromium
```

### Run guided interview
```bash
uv run --python .venv/bin/python genai-maturity-report
```

### Run from existing answers (skip interview)
```bash
uv run --python .venv/bin/python genai-maturity-report \
  --input-json src/genai_maturity/resources/examples/assessment_input_example.json \
  --output-dir /tmp/genai_assessment_out
```

Notes for input JSON:
- `gaps` are required (all sub-characteristics must be present when using gaps mode).
- `evidence` is optional. If omitted, empty evidence is used.
- `evidence` is only used as supporting context in outputs (HTML report and `gaps.csv`); it does not change score,
  maturity level, or prioritization logic.

### Rebuild from an existing assessment result
`assessment_result.json` is accepted directly (criticality is inferred when needed):
```bash
uv run --python .venv/bin/python genai-maturity-report \
  --input-json /path/to/assessment_result.json \
  --output-dir /tmp/genai_assessment_rerender
```

### Validate configs
```bash
uv run --python .venv/bin/python genai-maturity-validate
```

### PDF-only render from an existing HTML report
```bash
uv run --python .venv/bin/python genai-maturity-render-pdf \
  --input-html /path/to/assessment_report.html \
  --output-pdf /path/to/assessment_report.pdf
```

### Outputs (Pro mode)
- `assessment_result.json`
- `gaps.csv`
- `assessment_report.html`
- `assessment_report.pdf` (if Playwright Chromium is available)

### Example Pro report (PDF)
- File: [`examples/reports/example_pro_report.pdf`](examples/reports/example_pro_report.pdf)

Inline example artifact set:
```text
assessment_result.json
gaps.csv
assessment_report.html
assessment_report.pdf
```

Inline preview of report-style summary:
```md
## Maturity Level
- Current maturity: L1
- Expected maturity based on business criticality: L5

## Action Summary
- Critical actions: 3
- Important actions: 12
- Nice-to-have actions: 0
```

## Package Structure
- Core package: `src/genai_maturity`
- Tests: `tests/`
- Skill integration assets/metadata: `skills/genai-maturity-assessor/`

## Source of Truth and Sync

Rules are maintained in one place:
- Canonical configs: `src/genai_maturity/resources/configs/`

## Customizing Assessment Rules

You can modify the assessment requirements according to your needs. See below how to apply the modifications.

### A) Business Criticality Requirements

Edit:
- `src/genai_maturity/resources/configs/criticality_rules.yaml`

What you can change:
- `required_maturity`:
  - Set required level for each class (`proof_of_concept`, `production_non_critical`, `production_critical`)
- `criticality_logic.production_critical_if_any`:
  - Define which triggers make an in-production system "production_critical"
- `questions`:
  - Change wording of interview prompts for criticality inputs

Important:
- Keep keys `proof_of_concept`, `production_non_critical`, and `production_critical`.
- Keep `criticality_logic.production_key` and trigger keys aligned with `questions[].key`.

### B) Quality Requirements and Maturity Levels

Edit:
- `src/genai_maturity/resources/configs/quality_model.yaml`
- `src/genai_maturity/resources/configs/interview_inference.yaml`
- `src/genai_maturity/resources/configs/maturity_gates.csv`
- `src/genai_maturity/resources/configs/recommendations.yaml`

What each file controls:
- `quality_model.yaml`:
  - Sub-characteristic definitions
  - Minimal and full requirement text used in interpretation
- `interview_inference.yaml`:
  - Capability interview question bank (`signals`)
  - Conditional ask logic (`ask_if`)
  - Mapping from answers to inferred gaps (`min_condition`, `full_condition`)
- `maturity_gates.csv`:
  - Required gate per maturity level (L1..L5) for each sub-characteristic (`none|min|full`)
- `recommendations.yaml`:
  - Suggested actions used in the final priority action list

Important:
- IDs must stay consistent across `quality_model.yaml`, `interview_inference.yaml`, `maturity_gates.csv`,
  and `recommendations.yaml`.
- Current validator expects 25 sub-characteristics.

Generated skill artifacts:
- `skills/genai-maturity-assessor/SKILL.md` (single-file Lite upload)
- `skills/genai-maturity-assessor/configs/*` (folder-style skill bundle)

After changing source config files, run:
```bash
PYTHONPATH=src python3 -m genai_maturity.cli.sync_skill_bundle --repo-root .
```

Or use:
```bash
bash skills/genai-maturity-assessor/scripts/sync_bundle.sh
```

Check sync status explicitly:
```bash
PYTHONPATH=src python3 -m genai_maturity.cli.sync_skill_bundle --repo-root . --check
```

Then validate:
```bash
pytest -q
```
