from __future__ import annotations

import argparse
from pathlib import Path

from genai_maturity.engine.core import load_configs, validate_configs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = ROOT / "resources" / "configs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate config integrity for genai_maturity.")
    parser.add_argument(
        "--config-dir",
        default=str(DEFAULT_CONFIG_DIR),
        help="Path to config directory (default: package configs).",
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
    print("- interview inference rules and signal expressions are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
