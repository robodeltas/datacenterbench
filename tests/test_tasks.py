"""Registration, task shape and scene metadata."""

import json
from importlib.metadata import entry_points

import pytest
from inspect_robots import Epochs, resolve

from datacenterbench import (
    K_TRIALS,
    MAX_STEPS,
    SPECS,
    TARGET_KIND,
    TASK_FACTORIES,
    TaskSpec,
    make_task,
)
from datacenterbench.tasks import rubric_text


def test_entry_points_match_factories() -> None:
    tasks = {ep.name: ep.value for ep in entry_points(group="inspect_robots.tasks")}
    ours = {n: v for n, v in tasks.items() if n.startswith("datacenterbench/")}
    assert ours == {f"datacenterbench/{k}": f"datacenterbench.tasks:{k}" for k in TASK_FACTORIES}
    graders = {ep.name: ep.value for ep in entry_points(group="inspect_robots.graders")}
    assert graders["datacenterbench_judges"] == "datacenterbench.grader:judges_grader"
    assert graders["datacenterbench_operator"] == "datacenterbench.grader:operator_grader"
    scorers = {ep.name: ep.value for ep in entry_points(group="inspect_robots.scorers")}
    assert scorers["rubric_score"] == "datacenterbench.scoring:rubric_score"
    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts["datacenterbench"] == "datacenterbench.cli:main"


@pytest.mark.parametrize("key", list(TASK_FACTORIES))
def test_registered_task(key: str) -> None:
    task = resolve("task", f"datacenterbench/{key}")
    assert task.name == f"datacenterbench/{key}"
    assert task.max_steps == MAX_STEPS == 900
    assert task.epoch_spec == Epochs(count=K_TRIALS, reducer="mean") and K_TRIALS == 3
    assert [s.name for s in task.scorers] == ["rubric_score", "episode_length"]
    assert TASK_FACTORIES[key](max_steps=1800).max_steps == 1800


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.key)
def test_scene(spec: TaskSpec) -> None:
    (scene,) = make_task(spec).scenes
    assert scene.id == spec.key and scene.instruction == spec.instruction
    assert scene.target is not None and scene.target.kind == TARGET_KIND
    assert scene.target.spec == {"scores": list(spec.rubric.scores)}
    json.dumps(dict(scene.metadata))  # logs need JSON-native metadata
    assert scene.metadata["rubric"] == rubric_text(spec)
    assert scene.metadata["datacenterbench"] == {
        "task": spec.judge_task(),
        "keypad_code": spec.keypad_code,
    }


def test_rubric_text() -> None:
    text = rubric_text(SPECS[1]).splitlines()
    assert text[0] == "Turn the knob to the mark" and text[-1].startswith(
        "0: The knob did not turn"
    )
    assert (
        rubric_text(SPECS[0]).splitlines()[1].startswith("1: ")
    )  # no guidance line when there is none
