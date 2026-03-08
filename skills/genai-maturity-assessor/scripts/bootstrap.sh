#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${SKILL_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed. Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment at ${PROJECT_ROOT}/.venv"
  uv venv .venv
else
  echo "Using existing virtual environment at ${PROJECT_ROOT}/.venv"
fi

echo "Installing package and development dependencies"
uv pip install --python .venv/bin/python -e ".[dev]"

echo "Installing Playwright Chromium"
uv run --python .venv/bin/python python -m playwright install chromium

echo "Setup complete."
echo "Run report: uv run --python .venv/bin/python genai-maturity-report"
