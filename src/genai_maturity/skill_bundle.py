from __future__ import annotations

import shutil
from pathlib import Path

TRIGGER_PHRASE = "assess my genai system"

CONFIG_FILES: tuple[tuple[str, str], ...] = (
    ("criticality_rules.yaml", "yaml"),
    ("interview_inference.yaml", "yaml"),
    ("quality_model.yaml", "yaml"),
    ("maturity_gates.csv", "csv"),
    ("gap_scales.yaml", "yaml"),
    ("recommendations.yaml", "yaml"),
)

SKILL_LITE_HEADER = """---
name: genai-maturity-assessor
description: "Standalone Lite-mode GenAI maturity assessor with embedded question bank, scoring rubrics, and report template."
---

# GenAI Maturity Assessor (Lite-Only, Standalone)

Generated file. Do not edit manually; run the skill bundle sync command.

This file is intentionally self-contained for assistant UIs that ingest only one `SKILL.md`.

## Trigger Phrase

When a user wants to start an assessment, they can type exactly:

`__TRIGGER_PHRASE__`

## Runtime Contract

If external files are unavailable, run the assessment using the embedded configs in this file.

1. Do not invent interview questions.
2. Use exact prompts from `criticality_rules.yaml` and `interview_inference.yaml` below.
3. Respect all `ask_if` conditions exactly.
4. Accept unknown as `?` and score conservatively.
5. Infer gaps only from embedded inference rules.
6. Compute criticality, quality score, maturity level, priorities, and actions with the rules below.
7. Return the result in the report template below.

## Lite Mode Workflow

### Step 1: Capture Metadata
Ask one question at a time. Wait for the user's answer before asking the next question.

Ask:
- `System name`
- `Owner team`
- `Assessor name`
- `Assessment date` (default to today if not provided)

### Step 2: Ask Business Criticality Questions
Ask criticality questions one at a time in order, exactly as defined in `criticality_rules.yaml`.

### Step 3: Ask Capability Signals
Ask signal questions one at a time in order from `interview_inference.yaml`.

- For `bool`: accept `y`, `n`, `?`
- For `int`: accept integer or `?`
- For `float`: accept number or `?`
- For `enum`: accept listed option or `?`
- If `ask_if` is false: skip question and set signal to unknown (`None`)

### Step 4: Infer Gaps (`no` / `small` / `large`)
For each sub-characteristic:
- If `full_condition` is true: gap = `no`
- Else if minimal requirement exists and `min_condition` is true: gap = `small`
- Else: gap = `large`

Unknown handling:
- If any referenced signal is unknown in a condition, treat that condition as false.
- Add rationale suffix: `Some answers were unknown and were scored conservatively.`

Rationale text per inferred gap:
- `no`: `Full requirement is currently demonstrated.`
- `small`: `Minimal requirement is demonstrated, but full requirement is not yet demonstrated.`
- `large` with minimal requirement: `Neither minimal nor full requirement is currently demonstrated.`
- `large` without minimal requirement: `Full requirement is not yet demonstrated.`

### Step 5: Classify Criticality and Required Maturity
Use embedded `criticality_rules.yaml`:
- Not in production -> `proof_of_concept` -> required level `L1`
- In production and any critical trigger true -> `production_critical` -> required level `L5`
- Otherwise in production -> `production_non_critical` -> required level `L3`

### Step 6: Compute Scores and Maturity
Gap values:
- `no = 0`
- `small = 1`
- `large = 2`

Quality score:
- `quality_score = round(100 * (1 - sum(gap_values) / (2 * number_of_sub_characteristics)), 2)`

Characteristic score:
- Same formula, but only for sub-characteristics in that characteristic.

Gate satisfaction:
- gate `none`: always satisfied
- gate `min`: satisfied when gap in `['no', 'small']`
- gate `full`: satisfied when gap in `['no']`

Actual maturity:
- Highest level from L1..L5 where all sub-characteristics satisfy that level gate in `maturity_gates.csv`.

### Step 7: Build Priority Actions
For each sub-characteristic with unmet gate:
1. Find `first_unmet_level` = first level where gate is not satisfied.
2. Priority:
- `critical` if `first_unmet_level <= min(required_level, actual_level + 1)`
- `important` if `first_unmet_level <= required_level`
- `nice_to_have` otherwise
3. Determine action using `recommendations.yaml`:
- if target gate is `min`: use `min_action`
- if target gate is `full` and gap is `small`: use `full_action`
- if target gate is `full` and gap is `large` and minimal requirement exists:
  `Step 1: {min_action} Step 2: {full_action}`
- otherwise: use `full_action`
4. Sort by priority rank (`critical`, `important`, `nice_to_have`), then `first_unmet_level`, then name.

### Step 8: Output Report (Markdown)
Use this exact structure.

```md
# GenAI Maturity Assessment (Lite Mode)

## System Snapshot
- System: <system_name>
- Team: <owner_team>
- Assessor: <assessor>
- Assessment date: <assessment_date>
- Mode: Lite (no-code, Markdown-only)

## Business Criticality
- Classification: <Proof of Concept | Production Non-Critical | Production Critical>
- Required maturity level: L<required_level>
- Current maturity level: L<actual_level>
- Status: <Met required maturity | Below required maturity>

## Quality Overview
- Overall quality score: <quality_score>
- Utility: <score>
- Economy: <score>
- Robustness: <score>
- Productionizability: <score>
- Modifiability: <score>
- Comprehensibility: <score>
- Responsibility: <score>

## Priority Actions

### Critical
1. <DisplayName>: <action>

### Important
1. <DisplayName>: <action>

### Nice to Have
1. <DisplayName>: <action>

## Scoring Rationale (Inferred)
- <DisplayName>: <rationale>

## Notes
- Unknown (`?`) answers are scored conservatively.
- For JSON/CSV/HTML/PDF artifacts and CLI workflows, see `README.md`.
```
"""


def render_skill_markdown(repo_root: Path) -> str:
    config_dir = repo_root / "src" / "genai_maturity" / "resources" / "configs"
    header = SKILL_LITE_HEADER.replace("__TRIGGER_PHRASE__", TRIGGER_PHRASE).rstrip()

    sections: list[str] = []
    for filename, language in CONFIG_FILES:
        content = (config_dir / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### {filename}\n```{language}\n{content}\n```")

    embedded = "\n\n".join(sections)
    return f"{header}\n\n## Embedded Source Config Files\n\n{embedded}\n"


def collect_skill_bundle_drift(repo_root: Path) -> list[str]:
    canonical_dir = repo_root / "src" / "genai_maturity" / "resources" / "configs"
    skill_dir = repo_root / "skills" / "genai-maturity-assessor"
    skill_config_dir = skill_dir / "configs"
    issues: list[str] = []

    for filename, _ in CONFIG_FILES:
        source_path = canonical_dir / filename
        target_path = skill_config_dir / filename
        if not target_path.exists():
            issues.append(f"missing file: {target_path}")
            continue
        if source_path.read_text(encoding="utf-8") != target_path.read_text(encoding="utf-8"):
            issues.append(f"out-of-sync file: {target_path}")

    skill_md_path = skill_dir / "SKILL.md"
    expected_skill_md = render_skill_markdown(repo_root)
    if not skill_md_path.exists():
        issues.append(f"missing file: {skill_md_path}")
    elif skill_md_path.read_text(encoding="utf-8") != expected_skill_md:
        issues.append(f"out-of-sync file: {skill_md_path}")

    return issues


def sync_skill_bundle(repo_root: Path) -> None:
    canonical_dir = repo_root / "src" / "genai_maturity" / "resources" / "configs"
    skill_dir = repo_root / "skills" / "genai-maturity-assessor"
    skill_config_dir = skill_dir / "configs"
    skill_config_dir.mkdir(parents=True, exist_ok=True)

    for filename, _ in CONFIG_FILES:
        shutil.copyfile(canonical_dir / filename, skill_config_dir / filename)

    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(render_skill_markdown(repo_root), encoding="utf-8")
