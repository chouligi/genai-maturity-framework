#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${SKILL_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not available on PATH." >&2
  exit 1
fi

PYTHONPATH=src python3 -m genai_maturity.cli.sync_skill_bundle --repo-root "${PROJECT_ROOT}"
echo "Skill bundle sync complete."
