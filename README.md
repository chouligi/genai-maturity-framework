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
3. Answer interview questions.
4. Receive Markdown report in chat.

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
