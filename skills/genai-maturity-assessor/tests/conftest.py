from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "io"))


@pytest.fixture()
def minimal_quality_model() -> dict[str, object]:
    return {
        "sub_characteristics": [
            {
                "id": "availability",
                "display_name": "Availability",
                "characteristic": "robustness",
                "minimal_requirement": "-",
            },
            {
                "id": "adaptability",
                "display_name": "Adaptability",
                "characteristic": "robustness",
                "minimal_requirement": "Documented manual process.",
            },
        ]
    }


@pytest.fixture()
def skill_root() -> Path:
    return ROOT
