"""The ten tasks as released: order, names, rubric levels, equipment, photos, the keypad code."""

import math
from importlib import metadata, reload
from pathlib import Path
from unittest.mock import patch

import pytest

from datacenterbench import RELEASE, SPEC_BY_KEY, SPECS, TaskSpec

ROOT = Path(__file__).resolve().parents[1]
RELEASE_IDS = [
    "DC-unplug",
    "DC-knob",
    "DC-toggle",
    "DC-key",
    "DC-cover",
    "DC-slider",
    "DC-keypad",
    "DC-plug",
    "DC-join",
    "DC-clip",
]


def test_release_and_order() -> None:
    assert RELEASE == "1.0.0"
    assert [s.release_id for s in SPECS] == RELEASE_IDS
    assert [s.key for s in SPECS] == [r.removeprefix("DC-") for r in RELEASE_IDS]
    assert list(SPEC_BY_KEY) == [s.key for s in SPECS]


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.key)
def test_spec(spec: TaskSpec) -> None:
    assert spec.version == 1
    assert spec.instruction.strip() == spec.instruction and spec.instruction
    scores = spec.rubric.scores
    assert scores[0] == 1 and scores[-1] == 0
    assert list(scores) == sorted(set(scores), reverse=True), "distinct, highest first as released"
    assert set(scores) <= {0, 0.5, 1}
    assert all(math.isfinite(s) for s in scores)
    # The prompt prints "Score 1", "Score 0": integer scores stay integers.
    assert type(scores[0]) is int and type(scores[-1]) is int
    assert all(level.description for level in spec.rubric.levels)
    assert spec.equipment and all(e.quantity >= 1 for e in spec.equipment)
    assert all(e.url is None or e.url.startswith("https://") for e in spec.equipment)
    assert all((ROOT / p).is_file() for p in spec.photos)
    assert spec.real_world.quote and spec.real_world.simplified
    task = spec.judge_task()
    assert task["id"] == spec.release_id and task["name"] == spec.name
    assert [lv["score"] for lv in task["levels"]] == list(scores)


def test_only_the_keypad_has_a_code() -> None:
    assert {s.key: s.keypad_code for s in SPECS if s.keypad_code} == {"keypad": "52"}


def test_no_purchase_records() -> None:
    text = (ROOT / "src/datacenterbench/specs.py").read_text() + (
        ROOT / "docs/equipment.md"
    ).read_text()
    for word in ("order 112-", "Rho", "receipt", "WN742"):
        assert word not in text


def test_version_fallback_for_uninstalled_source() -> None:
    import datacenterbench

    try:
        with patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError):
            assert reload(datacenterbench).__version__ == "0.0.0"
    finally:
        reload(datacenterbench)
