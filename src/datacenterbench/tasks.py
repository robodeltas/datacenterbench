"""Register the ten tasks: one fixed setup each, 3 trials, the mean rubric score."""

from __future__ import annotations

import zlib
from collections.abc import Callable

from inspect_robots import Epochs, Scene, Target, Task, episode_length, task

from datacenterbench.scoring import TARGET_KIND, rubric_score
from datacenterbench.specs import RELEASE, SPEC_BY_KEY, TaskSpec

K_TRIALS = 3  # published protocol: 3 trials per model per task (avg@3)
MAX_STEPS = 900  # the LLM-agent limit: 900 control steps (90 s of motion at 10 Hz)


def rubric_text(spec: TaskSpec) -> str:
    """The rubric as plain lines, shown to the person at the terminal before they score."""
    lines = [spec.name] + ([spec.rubric.guidance] if spec.rubric.guidance else [])
    lines += [f"{level.score}: {level.description}" for level in spec.rubric.levels]
    return "\n".join(lines)


def make_task(spec: TaskSpec, *, max_steps: int = MAX_STEPS) -> Task:
    """Build one fixed setup repeated 3 times, scored by its rubric, with a step limit."""
    scene = Scene(
        id=spec.key,
        instruction=spec.instruction,
        target=Target(kind=TARGET_KIND, spec={"scores": list(spec.rubric.scores)}),
        init_seed=zlib.crc32(spec.key.encode()),
        metadata={
            "benchmark": "datacenterbench",
            "release": RELEASE,
            "task": spec.key,
            "release_id": spec.release_id,
            "title": spec.name,
            "version": spec.version,
            "setup": spec.setup,
            "reset": spec.reset,
            # A non-blank string, so inspect-robots prints it above an operator prompt.
            "rubric": rubric_text(spec),
            "datacenterbench": {"task": spec.judge_task(), "keypad_code": spec.keypad_code},
            "equipment": [
                {"name": e.name, "quantity": e.quantity, "url": e.url, "note": e.note}
                for e in spec.equipment
            ],
            "photos": list(spec.photos),
        },
    )
    return Task(
        name=f"datacenterbench/{spec.key}",
        scenes=[scene],
        scorer=[rubric_score(), episode_length()],
        epochs=Epochs(count=K_TRIALS, reducer="mean"),
        max_steps=max_steps,
        metadata={"benchmark": "datacenterbench", "release": RELEASE, "k_trials": K_TRIALS},
    )


@task("datacenterbench/unplug")
def unplug(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: unplug the charger from the power strip."""
    return make_task(SPEC_BY_KEY["unplug"], max_steps=max_steps)


@task("datacenterbench/knob")
def knob(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: turn the knob to the mark."""
    return make_task(SPEC_BY_KEY["knob"], max_steps=max_steps)


@task("datacenterbench/toggle")
def toggle(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: flip the light switch."""
    return make_task(SPEC_BY_KEY["toggle"], max_steps=max_steps)


@task("datacenterbench/key")
def key(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: turn the key."""
    return make_task(SPEC_BY_KEY["key"], max_steps=max_steps)


@task("datacenterbench/cover")
def cover(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: open the spring-loaded cover."""
    return make_task(SPEC_BY_KEY["cover"], max_steps=max_steps)


@task("datacenterbench/slider")
def slider(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: move the slider to the other line."""
    return make_task(SPEC_BY_KEY["slider"], max_steps=max_steps)


@task("datacenterbench/keypad")
def keypad(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: enter a code on the keypad."""
    return make_task(SPEC_BY_KEY["keypad"], max_steps=max_steps)


@task("datacenterbench/plug")
def plug(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: plug the charger into the power strip."""
    return make_task(SPEC_BY_KEY["plug"], max_steps=max_steps)


@task("datacenterbench/join")
def join(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: join the Ethernet plug and coupler."""
    return make_task(SPEC_BY_KEY["join"], max_steps=max_steps)


@task("datacenterbench/clip")
def clip(max_steps: int = MAX_STEPS) -> Task:
    """Build the registered task: press the cable into the clip."""
    return make_task(SPEC_BY_KEY["clip"], max_steps=max_steps)


TASK_FACTORIES: dict[str, Callable[..., Task]] = {
    "unplug": unplug,
    "knob": knob,
    "toggle": toggle,
    "key": key,
    "cover": cover,
    "slider": slider,
    "keypad": keypad,
    "plug": plug,
    "join": join,
    "clip": clip,
}
