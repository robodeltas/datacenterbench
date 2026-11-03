"""Graders: the two judges behind every published score, and scoring by hand at the terminal.

``datacenterbench_judges`` grades a trial the way every published DataCenterBench trial was graded.
GPT-6 Astra and Claude Opus 5.5 (both at reasoning effort high) each see start and end photos from
the three cameras, with the task's instruction and rubric, and the trial gets a score only when both
give the same one. When they disagree, or either answers UNSURE or fails, a person scores it. The
prompt, requests and answer checks are the published code (``_published.py``). The photos differ:
the published grades used full-resolution photos (1920 x 1080 overhead) that Robocurve's rig
software took before each trial and after the arms parked, while this grader can only use the
trial's own first frame and its parked (or last) frame, at the size the embodiment records them. On
Robocurve's YAM setup that is 224 x 224, where the judges can't see what the rubrics ask about: on
three published trials graded again from those frames, five of six answers were UNSURE and the sixth
was wrong. So frames narrower than ``min_width`` (640) are not sent to the judges; the trial is left
for a person, with the way to grade it the published way: full-resolution photos and
``grade_photos`` (``datacenterbench grade``).

``datacenterbench_operator`` shows the rubric and asks the person at the terminal for a score.

The keypad task was scored from the keypad display's own key log, which this package can't read. Its
judges' answer is kept as a cross-check, and a person scores the trial from the display.

Both graders record the score as the trial's judgement (``"0.5"``) for the ``rubric_score`` scorer.
A console verdict (``/y``, ``/n``, ``/p``) is not a rubric score, so both still grade such a trial.
A trial neither could score keeps the reason in ``metadata["grading_error"]`` and is left out of the
task score.
"""

from __future__ import annotations

import io
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from inspect_robots import grader
from inspect_robots.errors import ConfigError
from inspect_robots.transcript import operator_event
from PIL import Image

from datacenterbench import _published
from datacenterbench.specs import SPEC_BY_KEY

if TYPE_CHECKING:
    import numpy.typing as npt
    from inspect_robots import OperatorSession, Scene, TrialRecord

JUDGE_VERSION = _published.VERSION
"""The published scoring's version, recorded with every grade."""

CAMERAS = {"top": "top_cam", "left": "left_cam", "right": "right_cam"}
"""The published camera names and the embodiment's (Robocurve's YAM setup) names for them."""

JPEG_QUALITY = 95
MIN_WIDTH = 640
"""Narrower frames are too small for the judges (the published photos were 1920 x 1080)."""
_NOTE_LIMIT = 2000
_ERROR_LIMIT = 500
KEY_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")


def judge_keys() -> dict[str, str]:
    """The judges' API keys: from a JUDGE_KEYS file (KEY=value lines) if set, then the env."""
    out: dict[str, str] = {}
    path = os.environ.get("JUDGE_KEYS")
    if path and Path(path).is_file():
        for line in Path(path).read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    out.update({k: os.environ[k] for k in KEY_NAMES if os.environ.get(k)})
    return out


# The published code reads its keys from a file of Robocurve's; here they come from judge_keys().
_published.keys = judge_keys


def jpeg_bytes(image: npt.NDArray[np.uint8]) -> bytes:
    """Encode a camera frame as JPEG, the format the published photos had."""
    frame = np.asarray(image)
    if frame.dtype != np.uint8:
        # Casting would change the picture (0.8 becomes 0, 256 becomes 0), so refuse instead.
        raise ValueError(
            f"a camera frame is {frame.dtype}, not uint8; the judges need 8-bit images"
        )
    buf = io.BytesIO()
    Image.fromarray(frame).convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def _images(inline: Mapping[str, Any] | None, refs: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if inline:
        return inline
    return {camera: ref.load() for camera, ref in (refs or {}).items()}


def trial_frames(record: TrialRecord) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    """The trial's start and end images by camera, and where the end came from.

    Start: the frame before the first step. End: the embodiment's photo after the arms parked when
    it took one (``"parked"``), else the frame after the last step (``"last frame"``).
    """
    if not record.steps:
        raise ValueError("the trial recorded no steps, so there is nothing to judge")
    start = _images(record.steps[0].observation.images, record.steps[0].image_refs)
    parked = record.parked_observation
    if parked is not None and parked.images:
        return start, parked.images, "parked"
    last = record.steps[-1]
    return start, _images(last.result.observation.images, last.result_image_refs), "last frame"


def frame_width(*frames: Mapping[str, Any]) -> int:
    """The width of the narrowest judged camera image in ``frames`` (0 when there is none)."""
    widths = [
        int(np.asarray(images[name]).shape[1])
        for images in frames
        for name in CAMERAS.values()
        if name in images
    ]
    return min(widths) if widths else 0


def frame_evidence(
    start: Mapping[str, Any], end: Mapping[str, Any], end_from: str
) -> list[tuple[str, bytes]]:
    """The judges' photos from the trial's frames, captioned as the published ones were."""
    end_caption = "end of trial, arms parked" if end_from == "parked" else "end of trial"
    evidence = []
    for images, when in ((start, "start of trial"), (end, end_caption)):
        for cam, name in CAMERAS.items():
            if name not in images:
                raise ValueError(
                    f"no {name} image at the {when}; the judges need all three cameras"
                )
            evidence.append((f"{when}, {_published.CAM_NAMES[cam]}", jpeg_bytes(images[name])))
    return evidence


def scene_task(scene: Scene) -> dict[str, Any]:
    """The task as the judges read it, from the scene a DataCenterBench task built."""
    task = (scene.metadata.get("datacenterbench") or {}).get("task")
    if not isinstance(task, dict) or not task.get("levels"):
        raise ValueError(
            f"scene {scene.id!r} has no DataCenterBench rubric; is it a datacenterbench task?"
        )
    return task


def level_text(task: Mapping[str, Any], value: float) -> str:
    """A score as the rubric writes it ("1", "0.5", "0")."""
    return str(next(lv["score"] for lv in task["levels"] if abs(float(lv["score"]) - value) < 1e-9))


def has_rubric_score(record: TrialRecord, task: Mapping[str, Any]) -> bool:
    """Whether the record already holds one of the rubric's scores (a console ``y`` does not)."""
    try:
        value = float(record.operator_judgement)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return any(abs(value - float(lv["score"])) < 1e-9 for lv in task["levels"])


def _set_aside_verdict(record: TrialRecord) -> None:
    if record.operator_judgement is not None:
        record.metadata["console_verdict"] = record.operator_judgement
        record.operator_judgement = None


def _summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """The published result, keeping every judge's answer (explanations trimmed)."""
    judges = {
        name: {
            k: (v[:_NOTE_LIMIT] if k == "explanation" and isinstance(v, str) else v)
            for k, v in j.items()
        }
        for name, j in (result.get("judges") or {}).items()
    }
    keep = ("version", "agreed", "score", "needs_human", "reason", "evidence")
    return {**{k: result.get(k) for k in keep}, "judges": judges}


class JudgesGrader:
    """The published judges: GPT-6 Astra and Claude Opus 5.5 must agree on a rubric score."""

    name = "datacenterbench_judges"

    def __init__(
        self, grade: Callable[..., dict[str, Any]] | None = None, min_width: int = MIN_WIDTH
    ) -> None:
        """Grade with ``grade`` (the published two-judge grade() by default); frames narrower than
        ``min_width`` are left for a person.
        """
        self._grade = grade or _published.grade
        self._min_width = min_width

    def config(self) -> dict[str, Any]:
        """The judge settings recorded in the run's log."""
        return {"scoring": JUDGE_VERSION, "judges": _published.JUDGES, "min_width": self._min_width}

    def preflight(self) -> None:
        """Refuse to start a run whose trials the judges could not grade (a missing key).

        Inspect Robots after 0.60 calls this before any trial; the registered factory also calls it
        when the grader is built, which covers 0.59 and 0.60.
        """
        if self._grade is not _published.grade:
            return
        missing = [k for k in KEY_NAMES if not judge_keys().get(k)]
        if missing:
            raise ConfigError(
                f"datacenterbench_judges needs {' and '.join(missing)}: the judges are OpenAI's "
                "GPT-6 Astra and Anthropic's Claude Opus 5.5 (or grade by hand with --grader "
                "datacenterbench_operator)"
            )

    def grade(self, record: TrialRecord, scene: Scene) -> None:
        """Record the judges' agreed score, or leave the trial for a person with the reason."""
        try:
            task = scene_task(scene)
            if has_rubric_score(record, task):
                return
            _set_aside_verdict(record)
            start, end, end_from = trial_frames(record)
            width = frame_width(start, end)
            if 0 < width < self._min_width:
                record.metadata["grading_error"] = (
                    f"the camera frames are {width} px wide, too small for the judges "
                    "(the published photos were 1920 x 1080); score it by hand, or grade "
                    "full-resolution start and end photos with `datacenterbench grade`"
                )
                return
            result = self._grade(frame_evidence(start, end, end_from), scene.instruction, task)
        except Exception as exc:  # post-rollout: an ungraded trial beats a crashed run
            reason = " ".join(str(exc).split())[:_ERROR_LIMIT] or type(exc).__name__
            record.metadata["grading_error"] = reason
            return
        record.metadata["datacenterbench_judges"] = dict(_summary(result), end_photo=end_from)
        keypad = (scene.metadata.get("datacenterbench") or {}).get("keypad_code")
        if keypad:
            agreed = result.get("agreed")
            said = level_text(task, result["score"]) if agreed else "no agreed score"
            record.metadata["grading_error"] = (
                "the keypad task is scored from the display's key log; a person reads the display "
                f"and scores it (the judges said {said})"
            )
            return
        if not result.get("agreed"):
            record.metadata["grading_error"] = (
                f"{result.get('reason') or 'no agreed score'}; a person scores it"
            )
            return
        judgement = level_text(task, result["score"])
        note = "; ".join(
            f"{name}: {(j.get('explanation') or '').strip()[-400:]}"
            for name, j in (result.get("judges") or {}).items()
        )[:_NOTE_LIMIT]
        record.operator_judgement = judgement
        record.operator_note = note
        record.events.append(
            operator_event(t=len(record.steps), verdict=judgement, source=self.name, note=note)
        )


class OperatorGrader:
    """Score by hand: show the rubric and ask the person at the terminal for one of its scores."""

    name = "datacenterbench_operator"

    def __init__(
        self,
        session: OperatorSession | None = None,
        *,
        input_fn: Callable[[str], str] = input,
    ) -> None:
        """Ask through ``input_fn``, writing through the run's session when one is connected."""
        self._session = session
        self._input = input_fn

    def connect_session(self, session: OperatorSession) -> None:
        """Adopt the run's session so the prompt shares the run's terminal."""
        self._session = session

    def _say(self, line: str) -> None:
        if self._session is not None:
            self._session.write_line(line)
        else:
            print(line)

    def grade(self, record: TrialRecord, scene: Scene) -> None:
        """Record the score the person picks; ``skip`` or closed input leaves the trial ungraded.

        A rubric score already on the record is kept; any other judgement (a console ``/y``) is
        moved to ``metadata["console_verdict"]`` and the person is asked for a score.
        """
        if self._session is not None:
            self._session.status(None)
        try:
            task = scene_task(scene)
        except ValueError as exc:
            record.metadata["grading_error"] = " ".join(str(exc).split())[:_ERROR_LIMIT]
            self._say(f"datacenterbench_operator: {exc}")
            return
        if has_rubric_score(record, task):
            return
        _set_aside_verdict(record)
        self._say(f"rubric: {task['name']}")
        for line in str(task.get("guidance") or "").splitlines():
            self._say(f"  {line}")
        for level in task["levels"]:
            self._say(f"  {level['score']}: {level['description']}")
        if record.truncated and record.termination_reason == "max_steps":
            self._say("note: this trial hit the step limit")
        scores = [level["score"] for level in task["levels"]]
        prompt = f"score? [{'/'.join(str(s) for s in scores)}, or skip] "
        while True:
            try:
                answer = self._input(prompt).strip()
            except EOFError:
                record.metadata["grading_error"] = "no score given at the terminal (input closed)"
                return
            if answer.lower() == "skip":
                record.metadata["grading_error"] = "scoring skipped at the terminal"
                return
            try:
                chosen = [s for s in scores if s == float(answer)]
            except ValueError:
                chosen = []
            if chosen:
                break
            self._say(f"not one of this rubric's scores: {answer!r}")
        try:
            note = self._input("note (optional): ").strip() or None
        except EOFError:
            note = None
        judgement = str(chosen[0])
        record.operator_judgement = judgement
        record.operator_note = note
        record.events.append(
            operator_event(t=len(record.steps), verdict=judgement, source=self.name, note=note)
        )


def grade_photos(folder: str | Path, key: str, instruction: str | None = None) -> dict[str, Any]:
    """Grade one trial the published way, from full-resolution photos in ``folder``.

    The folder holds ``before_top.jpg``, ``before_left.jpg``, ``before_right.jpg`` (taken just
    before the trial) and ``after_top.jpg``, ``after_left.jpg``, ``after_right.jpg`` (just after it,
    arms parked). Returns the published result: each judge's answer, whether they agreed, the score,
    and whether a person must score it.
    """
    spec = SPEC_BY_KEY[key]
    result: dict[str, Any] = _published.grade(
        _published.evidence_from_photos(folder), instruction or spec.instruction, spec.judge_task()
    )
    if spec.keypad_code:
        result["needs_human"] = True
        result["reason"] = (
            "the keypad task is scored from the display's key log; the judges are a cross-check"
        )
    return result


@grader("datacenterbench_judges")
def judges_grader(min_width: int = MIN_WIDTH) -> JudgesGrader:
    """The published DataCenterBench judges (GPT-6 Astra and Claude Opus 5.5); refuses to build
    without keys.
    """
    built = JudgesGrader(min_width=int(min_width))
    built.preflight()
    return built


@grader("datacenterbench_operator")
def operator_grader() -> OperatorGrader:
    """Score each trial by hand at the terminal, choosing one of the task's rubric scores."""
    return OperatorGrader()
