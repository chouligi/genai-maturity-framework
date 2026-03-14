---
name: genai-maturity-assessor
description: "Assess GenAI system maturity in two modes: Lite mode (no-code Markdown report in assistant UI) and Pro mode (Python package with JSON/CSV/HTML/PDF artifacts)."
---

# GenAI Maturity Assessor

This skill supports two usage modes:

1. **Lite mode (no-code):** chat interview + Markdown report.
2. **Pro mode (package):** CLI workflow with JSON/CSV/HTML/PDF outputs.

## Quick Links

- Full usage guide: `README.md`
- Package code: `src/genai_maturity/`
- Test suite: `tests/`
- Skill metadata: `skills/genai-maturity-assessor/agents/assistant.yaml`

## Lite Mode (Assistant UI)

Use this when you want no local setup.

If your assistant asks which file to import, use:
- `skills/genai-maturity-assessor/SKILL.md` (primary)
- `skills/genai-maturity-assessor/agents/assistant.yaml` (manifest/config, when supported)

- Conduct interview in chat.
- Infer gaps and maturity.
- Return structured Markdown report.
- Do not require local dependency installation.

Example output reference:
- `examples/reports/example_lite_report.md`

## Pro Mode (CLI)

Use this when you want export artifacts and PDF generation.

### Setup
```bash
bash skills/genai-maturity-assessor/scripts/bootstrap.sh
```

### Validate
```bash
uv run --python .venv/bin/python genai-maturity-validate
```

### Interview run
```bash
uv run --python .venv/bin/python genai-maturity-report
```

### Run from existing input JSON (skip interview)
```bash
uv run --python .venv/bin/python genai-maturity-report \
  --input-json src/genai_maturity/resources/examples/assessment_input_example.json \
  --output-dir /tmp/genai_assessment_out
```

### Render PDF from existing HTML
```bash
uv run --python .venv/bin/python genai-maturity-render-pdf \
  --input-html /path/to/assessment_report.html \
  --output-pdf /path/to/assessment_report.pdf
```

Example PDF reference:
- `examples/reports/example_pro_report.pdf`
