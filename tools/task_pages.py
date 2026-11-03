"""Write docs/tasks/<key>.md for every task from the specs (tests fail when a page drifts).

uv run python tools/task_pages.py
"""

from __future__ import annotations

from pathlib import Path

from datacenterbench.specs import RELEASE, SPECS, TaskSpec

ROOT = Path(__file__).resolve().parents[1]


def render(spec: TaskSpec) -> str:
    """The task's reference page: instruction, photos, setup, equipment, rubric, real-world step."""
    equipment = "\n".join(
        f"| {e.name} | {e.quantity} | {f'[link]({e.url})' if e.url else 'on hand'} "
        f"| {e.note or ''} |"
        for e in spec.equipment
    )
    levels = "\n".join(f"| {level.score} | {level.description} |" for level in spec.rubric.levels)
    guidance = f"```text\n{spec.rubric.guidance}\n```\n\n" if spec.rubric.guidance else ""
    top, left, right = (p.removeprefix("docs/") for p in spec.photos)
    rw = spec.real_world
    source = f"[{rw.source_title}]({rw.source_url})" if rw.source_url else (rw.source_title or "")
    locator = f", {rw.locator}" if rw.locator else ""
    keypad = (
        "\n\nThis task is scored from the keypad display's own key log, which only Robocurve's "
        "setup records. The judges' answer is a cross-check, and with this package a person reads "
        "the display and scores the trial.\n"
        if spec.keypad_code
        else "\n"
    )
    return f"""# {spec.name}

Task `datacenterbench/{spec.key}`, version {spec.version}, from release {RELEASE}.

## Instruction

What the model is told, word for word:

> {spec.instruction}

## Setup

![Setup for {spec.name}, overhead camera](../{top})

{spec.setup}

Between trials: {spec.reset}

Wrist cameras at the start: [left](../{left}), [right](../{right}).

## Equipment

| Object | Quantity | Product | As used |
|---|--:|---|---|
{equipment}

The board and mounting supplies are on [Shared equipment](../equipment.md).

## Rubric

A trial scores one of these levels. The judges see the task name, the guidance and every level
below, word for word.

{guidance}| Score | End state |
|--:|---|
{levels}{keypad}
## The real-world step

{rw.step}: {rw.procedure}

> {rw.quote}

Source: {source}{locator}. {rw.simplified}
"""


def main() -> None:
    """Rewrite every task page."""
    for spec in SPECS:
        (ROOT / "docs" / "tasks" / f"{spec.key}.md").write_text(render(spec))


if __name__ == "__main__":
    main()
