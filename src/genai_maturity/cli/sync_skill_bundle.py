from __future__ import annotations

import argparse
from pathlib import Path

from genai_maturity.skill_bundle import collect_skill_bundle_drift, sync_skill_bundle


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync skill artifacts from source config files."
    )
    parser.add_argument(
        "--repo-root",
        default=str(_default_repo_root()),
        help="Path to repository root.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether skill artifacts are in sync and exit non-zero if drift exists.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if args.check:
        drift = collect_skill_bundle_drift(repo_root)
        if drift:
            print("Skill bundle drift detected:")
            for issue in drift:
                print(f"- {issue}")
            print("Run sync to fix:")
            print("  PYTHONPATH=src python3 -m genai_maturity.cli.sync_skill_bundle --repo-root .")
            return 1
        print("Skill bundle is in sync.")
        return 0

    sync_skill_bundle(repo_root)
    print("Synced skill bundle from source config files.")
    print(f"- Repo root: {repo_root}")
    print("- Updated: skills/genai-maturity-assessor/SKILL.md")
    print("- Updated: skills/genai-maturity-assessor/configs/*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
