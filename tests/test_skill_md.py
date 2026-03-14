from __future__ import annotations

import re
from pathlib import Path

import yaml

from genai_maturity.skill_bundle import (
    CONFIG_FILES,
    TRIGGER_PHRASE,
    collect_skill_bundle_drift,
    render_skill_markdown,
)


def test_skill_md__yaml_frontmatter_valid_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"

    text = skill_md_path.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)

    assert frontmatter_match is not None

    frontmatter = yaml.safe_load(frontmatter_match.group(1))
    assert frontmatter["name"] == "genai-maturity-assessor"
    assert isinstance(frontmatter["description"], str)
    assert frontmatter["description"].strip()


def test_skill_md__embeds_canonical_configs_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"
    config_dir = repo_root / "src" / "genai_maturity" / "resources" / "configs"

    skill_text = skill_md_path.read_text(encoding="utf-8")
    for filename, _ in CONFIG_FILES:
        config_text = (config_dir / filename).read_text(encoding="utf-8").strip()
        assert f"### {filename}" in skill_text
        assert config_text in skill_text


def test_skill_md__lite_only_no_pro_mode_section_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"

    text = skill_md_path.read_text(encoding="utf-8")
    assert "## Pro Mode" not in text
    assert "genai-maturity-report" not in text


def test_skill_md__includes_assessment_trigger_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"
    readme_path = repo_root / "README.md"

    skill_text = skill_md_path.read_text(encoding="utf-8")
    readme_text = readme_path.read_text(encoding="utf-8")

    assert TRIGGER_PHRASE in skill_text
    assert TRIGGER_PHRASE in readme_text


def test_skill_md__interview_is_one_question_at_a_time_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"

    skill_text = skill_md_path.read_text(encoding="utf-8")

    assert "Ask one question at a time. Wait for the user's answer before asking the next question." in skill_text
    assert "Ask criticality questions one at a time in order" in skill_text
    assert "Ask signal questions one at a time in order" in skill_text


def test_render_skill_markdown__matches_checked_in_skill_md_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "genai-maturity-assessor" / "SKILL.md"

    rendered = render_skill_markdown(repo_root=repo_root)
    current = skill_md_path.read_text(encoding="utf-8")

    assert rendered == current


def test_skill_configs__match_canonical_resources_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    canonical_dir = repo_root / "src" / "genai_maturity" / "resources" / "configs"
    skill_config_dir = repo_root / "skills" / "genai-maturity-assessor" / "configs"

    for filename, _ in CONFIG_FILES:
        canonical_text = (canonical_dir / filename).read_text(encoding="utf-8")
        skill_text = (skill_config_dir / filename).read_text(encoding="utf-8")
        assert skill_text == canonical_text


def test_collect_skill_bundle_drift__returns_empty_when_synced_is_correct() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert collect_skill_bundle_drift(repo_root=repo_root) == []
