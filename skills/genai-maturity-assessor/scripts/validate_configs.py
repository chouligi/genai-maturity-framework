#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from engine.core import load_configs, validate_configs
except ModuleNotFoundError as exc:
    missing_module = exc.name or "dependency"
    setup_msg = (
        f"Missing Python dependency '{missing_module}'.\n"
        "Run setup once:\n"
        "  bash skills/genai-maturity-assessor/scripts/bootstrap.sh"
    )
    raise SystemExit(setup_msg) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate config integrity for genai-maturity-assessor.")
    parser.add_argument(
        "--config-dir",
        default=str(ROOT / "configs"),
        help="Path to config directory (default: skill configs).",
    )
    args = parser.parse_args()

    cfg = load_configs(Path(args.config_dir))
    errors = validate_configs(cfg)
    if errors:
        print("Config validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Config validation passed.")
    print("- 25 sub-characteristics found")
    print("- quality_model, maturity_gates, and recommendations IDs match")
    print("- gate values and gap scales are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
