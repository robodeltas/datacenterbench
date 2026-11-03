"""The judges and hand graders, end to end through inspect_robots.eval on a three-camera rig."""

from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
from inspect_robots import Epochs, Observation, Scene, TrialRecord, resolve
from inspect_robots import eval as rl_eval
from inspect_robots.errors import ConfigError
from inspect_robots.mock import NoopPolicy
from PIL import Image

from datacenterbench import (
    SPEC_BY_KEY,
    JudgesGrader,
    OperatorGrader,
    _published,
    grade_photos,
    make_task,
)
from datacenterbench.grader import (
    JUDGE_VERSION,
    frame_width,
    jpeg_bytes,
    judge_keys,
    scene_task,
    trial_frames,
)

from .fakes import ThreeCameraRig, frame_image

KNOB = SPEC_BY_KEY["knob"]


class Judges:
    """Stands in for the two judges' calls: answers per judge, keeps what each was sent."""

    def __init__(self, astra: Any = "SCORE: 0.5", opus: Any = "SCORE: 0.5") -> None:
        self.answers = {"astra": astra, "opus": opus}
        self.sent: list[tuple[str, str, list[tuple[str, bytes]]]] = []

    def __call__(
        self, judge: str, text: str, evidence: list[tuple[str, bytes]], k: Any
    ) -> tuple[str, dict[str, int]]:
        self.sent.append((judge, text, evidence))
        a = self.answers[judge]
        if isinstance(a, Exception):
            raise a
        return a, {"tokens": 1}


def run(
    grader: Any,
    *,
    spec: Any = KNOB,
    steps: int = 5,
    trials: int = 1,
    rig: ThreeCameraRig | None = None,
    **kw: Any,
) -> Any:
    task = replace(make_task(spec, max_steps=steps), epochs=Epochs(count=trials, reducer="mean"))
    with patch("inspect_robots.eval._git_commit", return_value=None):
        (log,) = rl_eval(
            task,
            NoopPolicy(),
            rig or ThreeCameraRig(size=8),
            sinks=[],
            store_actions=False,
            grader=grader,
            **kw,
        )
    return log


def ungraded_run(log: Any) -> bool:
    text = f"{log.error} {[s.error for s in log.samples]}"
    return log.status == "error" and ("not scored" in text or "ungraded" in text)


@pytest.fixture(autouse=True)
def placeholder_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    # Newer Inspect Robots runs the grader's preflight, which needs keys even with the calls faked.
    monkeypatch.delenv("JUDGE_KEYS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")


@pytest.fixture
def judges(monkeypatch: pytest.MonkeyPatch) -> Judges:
    j = Judges()
    monkeypatch.setattr(_published, "ask", j)
    return j


def test_agreed_judges_score_a_trial_like_the_published_ones(judges: Judges) -> None:
    log = run(JudgesGrader(min_width=1))
    (sample,) = log.samples
    assert sample.reduced["rubric_score"] == 0.5 and sample.operator_judgements == ("0.5",)
    assert {j for j, _, _ in judges.sent} == {"astra", "opus"}
    _, text, evidence = judges.sent[0]
    assert text == _published.prompt(KNOB.instruction, KNOB.judge_task())
    assert [c for c, _ in evidence] == [
        "start of trial, overhead camera",
        "start of trial, left wrist camera",
        "start of trial, right wrist camera",
        "end of trial, overhead camera",
        "end of trial, left wrist camera",
        "end of trial, right wrist camera",
    ]
    first = np.asarray(Image.open(io.BytesIO(evidence[0][1])))
    last = np.asarray(Image.open(io.BytesIO(evidence[5][1])))
    assert (
        abs(int(first.mean()) - int(frame_image(0, "top_cam").mean())) <= 2
    )  # JPEG, so nearly equal
    assert abs(int(last.mean()) - int(frame_image(5, "right_cam").mean())) <= 2
    meta = sample.trial_metadata[0]["datacenterbench_judges"]
    assert meta["agreed"] and meta["end_photo"] == "last frame" and meta["version"] == JUDGE_VERSION
    json.dumps(sample.trial_metadata[0])


@pytest.mark.parametrize(
    ("astra", "opus", "why"),
    [
        ("SCORE: 1", "SCORE: 0.5", "judges disagree"),
        ("SCORE: 1", "SCORE: UNSURE", "a judge is unsure or failed"),
        (RuntimeError("HTTP 500"), "SCORE: 1", "a judge is unsure or failed"),
    ],
)
def test_without_agreement_a_person_scores_it(
    monkeypatch: pytest.MonkeyPatch, astra: Any, opus: Any, why: str
) -> None:
    monkeypatch.setattr(_published, "ask", Judges(astra, opus))
    log = run(JudgesGrader(min_width=1))
    (sample,) = log.samples
    assert (
        sample.reduced.get("rubric_score") is None
        and why in sample.trial_metadata[0]["grading_error"]
    )
    assert ungraded_run(log)


def test_frames_too_small_are_left_for_a_person(judges: Judges) -> None:
    log = run(
        JudgesGrader()
    )  # the stand-in rig records 8 x 8 frames, as Robocurve's records 224 x 224
    (sample,) = log.samples
    assert (
        judges.sent == []
        and "8 px wide, too small for the judges" in sample.trial_metadata[0]["grading_error"]
    )
    assert "datacenterbench grade" in sample.trial_metadata[0]["grading_error"] and ungraded_run(
        log
    )


def test_the_keypad_task_goes_to_a_person_with_the_judges_as_a_cross_check(judges: Judges) -> None:
    log = run(JudgesGrader(min_width=1), spec=SPEC_BY_KEY["keypad"])
    (sample,) = log.samples
    err = sample.trial_metadata[0]["grading_error"]
    assert (
        "key log" in err and "the judges said 0.5" in err and sample.operator_judgements == (None,)
    )


def test_narrow_end_frames_are_left_for_a_person_too(judges: Judges) -> None:
    class ParksSmall(ThreeCameraRig):
        def observe_parked(self) -> Observation:
            return Observation(images={c: frame_image(99, c, 8) for c in self.cameras}, state={})

    log = run(JudgesGrader(min_width=12), rig=ParksSmall(size=16))
    assert judges.sent == []
    assert "8 px wide" in log.samples[0].trial_metadata[0]["grading_error"] and ungraded_run(log)


def test_frames_that_are_not_8_bit_are_refused(judges: Judges) -> None:
    class ParksFloat(ThreeCameraRig):
        def observe_parked(self) -> Observation:
            return Observation(images={c: np.full((8, 8, 3), 0.8) for c in self.cameras}, state={})

    log = run(JudgesGrader(min_width=1), rig=ParksFloat(size=8))
    assert judges.sent == []
    assert "float64, not uint8" in log.samples[0].trial_metadata[0]["grading_error"]
    with pytest.raises(ValueError, match="uint16, not uint8"):
        jpeg_bytes(np.full((4, 4, 3), 256, dtype=np.uint16))


def test_parked_photo_and_frame_store(judges: Judges, tmp_path: Path) -> None:
    class Parks(ThreeCameraRig):
        def observe_parked(self) -> Observation:
            return Observation(
                images={c: frame_image(99, c, self.size) for c in self.cameras}, state={}
            )

    log = run(
        JudgesGrader(min_width=1), rig=Parks(size=8), log_dir=str(tmp_path), store_frames=True
    )
    assert log.samples[0].trial_metadata[0]["datacenterbench_judges"]["end_photo"] == "parked"
    assert judges.sent[0][2][3][0] == "end of trial, arms parked, overhead camera"


def test_ungradable_cases() -> None:
    task_scene = make_task(KNOB).scenes[0]
    record = TrialRecord(scene_id="knob", epoch=0, seed=0)
    assert frame_width({}, {"other_cam": np.zeros((4, 4, 3))}) == 0
    with pytest.raises(ValueError, match="no steps"):
        trial_frames(record)
    JudgesGrader(grade=lambda *a: {}, min_width=1).grade(record, task_scene)
    assert "no steps" in record.metadata["grading_error"]
    log = run(
        JudgesGrader(grade=lambda *a: {}, min_width=1),
        rig=ThreeCameraRig(size=8, cameras=("top_cam", "left_cam")),
    )
    assert "no right_cam image" in log.samples[0].trial_metadata[0]["grading_error"]
    log = run(JudgesGrader(grade=lambda *a: {}), rig=ThreeCameraRig(size=8, cameras=("wrist",)))
    assert "no top_cam image" in log.samples[0].trial_metadata[0]["grading_error"]
    other = TrialRecord(scene_id="x", epoch=0, seed=0)
    JudgesGrader(grade=lambda *a: {}).grade(other, Scene(id="x", instruction="Do it."))
    assert "is it a datacenterbench task?" in other.metadata["grading_error"]


@pytest.mark.parametrize("verdict", ["y", "partial", "0.75"])
def test_a_console_verdict_does_not_stop_the_judges(judges: Judges, verdict: str) -> None:
    kept: list[TrialRecord] = []

    class Console(JudgesGrader):
        def grade(self, record: TrialRecord, scene: Scene) -> None:
            record.operator_judgement = verdict
            super().grade(record, scene)
            kept.append(record)

    log = run(Console(min_width=1))
    assert (
        log.samples[0].reduced["rubric_score"] == 0.5
        and kept[0].metadata["console_verdict"] == verdict
    )


def test_without_a_grader_the_run_ends_as_an_error() -> None:
    log = run(None)
    assert ungraded_run(log) and "no rubric score recorded" in str(log.error)


def test_a_recorded_rubric_score_is_kept() -> None:
    record = TrialRecord(scene_id="knob", epoch=0, seed=0, operator_judgement="1")
    JudgesGrader(grade=lambda *a: pytest.fail("no judging")).grade(
        record, make_task(KNOB).scenes[0]
    )
    assert record.operator_judgement == "1"


def test_preflight_keys_and_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "JUDGE_KEYS"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ConfigError, match="OPENAI_API_KEY and ANTHROPIC_API_KEY"):
        resolve("grader", "datacenterbench_judges")
    keys = tmp_path / "judges.env"
    keys.write_text("# judges\nOPENAI_API_KEY='o-file'\nANTHROPIC_API_KEY=a-file\n")
    monkeypatch.setenv("JUDGE_KEYS", str(keys))
    monkeypatch.setenv("OPENAI_API_KEY", "o-env")
    assert judge_keys() == {
        "OPENAI_API_KEY": "o-env",
        "ANTHROPIC_API_KEY": "a-file",
    }  # the environment wins
    built = resolve("grader", "datacenterbench_judges")
    assert isinstance(built, JudgesGrader) and built.config()["min_width"] == 640
    assert built.config()["scoring"] == "start-end-photos-v1" and set(built.config()["judges"]) == {
        "astra",
        "opus",
    }
    JudgesGrader(grade=lambda *a: {}).preflight()  # an injected grade needs no keys


def test_jpeg_and_scene_task() -> None:
    data = jpeg_bytes(np.zeros((4, 4, 3), dtype=np.uint8))
    assert data[:2] == b"\xff\xd8"
    assert scene_task(make_task(KNOB).scenes[0])["name"] == "Turn the knob to the mark"


def test_grade_photos_the_published_way(judges: Judges, tmp_path: Path) -> None:
    for phase in ("before", "after"):
        for cam in ("top", "left", "right"):
            (tmp_path / f"{phase}_{cam}.jpg").write_bytes(
                jpeg_bytes(np.full((16, 16, 3), 9, dtype=np.uint8))
            )
    r = grade_photos(tmp_path, "knob")
    assert r["agreed"] and r["score"] == 0.5 and len(judges.sent[0][2]) == 6
    assert judges.sent[0][1] == _published.prompt(KNOB.instruction, KNOB.judge_task())
    r = grade_photos(tmp_path, "keypad", "Type 52.")
    assert (
        r["needs_human"]
        and "key log" in r["reason"]
        and judges.sent[-1][1].startswith(
            "You are grading one robot trial from camera photos.\n\n"
            "Task instruction given to the robot: Type 52."
        )
    )


class Session:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.statuses: list[str | None] = []

    def write_line(self, text: str) -> None:
        self.lines.append(text)

    def status(self, line: str | None) -> None:
        self.statuses.append(line)


def answers(*replies: str | type[EOFError]) -> Any:
    queue = list(replies)

    def ask(prompt: str) -> str:
        item = queue.pop(0)
        if item is EOFError:
            raise EOFError
        assert isinstance(item, str)
        return item

    return ask


def test_operator_scores_through_eval() -> None:
    grader = OperatorGrader(input_fn=answers("0.3", "most", "0.5", "  half way  "))
    session = Session()
    grader.connect_session(session)  # type: ignore[arg-type]
    log = run(grader)
    (sample,) = log.samples
    assert sample.reduced["rubric_score"] == 0.5 and sample.operator_notes == ("half way",)
    assert session.statuses == [None] and session.lines[0] == "rubric: Turn the knob to the mark"
    assert session.lines[1] == f"  {KNOB.rubric.guidance}"
    assert (
        "  0.5: The knob turned clockwise noticeably but the line stops short of the goal mark."
        in session.lines
    )
    assert "note: this trial hit the step limit" in session.lines
    assert (
        "not one of this rubric's scores: '0.3'" in session.lines
        and "not one of this rubric's scores: 'most'" in session.lines
    )


@pytest.mark.parametrize(
    ("replies", "judgement", "note", "error"),
    [
        (("skip",), None, None, "scoring skipped at the terminal"),
        ((EOFError,), None, None, "no score given at the terminal (input closed)"),
        (("1", EOFError), "1", None, None),
        (("0", ""), "0", None, None),
    ],
)
def test_operator_answers(
    replies: tuple[Any, ...],
    judgement: str | None,
    note: str | None,
    error: str | None,
    capsys: Any,
) -> None:
    record = TrialRecord(scene_id="knob", epoch=0, seed=0)
    OperatorGrader(input_fn=answers(*replies)).grade(record, make_task(KNOB).scenes[0])
    assert (
        record.operator_judgement,
        record.operator_note,
        record.metadata.get("grading_error"),
    ) == (judgement, note, error)
    assert "rubric: Turn the knob" in capsys.readouterr().out


def test_operator_skip_is_flagged_not_averaged_away() -> None:
    log = run(OperatorGrader(input_fn=answers("1", "", "skip")), trials=2)
    assert (
        log.samples[0].operator_judgements == ("1", None)
        and log.samples[0].reduced["rubric_score"] == 1.0
    )
    assert ungraded_run(log)


def test_operator_keeps_a_rubric_score_and_needs_a_rubric(capsys: Any) -> None:
    record = TrialRecord(scene_id="knob", epoch=0, seed=0, operator_judgement="1")
    OperatorGrader(input_fn=answers()).grade(record, make_task(KNOB).scenes[0])
    assert record.operator_judgement == "1"
    record = TrialRecord(scene_id="knob", epoch=0, seed=0, operator_judgement="y")
    OperatorGrader(input_fn=answers("0.5", "")).grade(record, make_task(KNOB).scenes[0])
    assert record.operator_judgement == "0.5" and record.metadata["console_verdict"] == "y"
    other = TrialRecord(scene_id="x", epoch=0, seed=0)
    OperatorGrader(input_fn=answers()).grade(other, Scene(id="x", instruction="Do it."))
    assert (
        "no DataCenterBench rubric" in other.metadata["grading_error"]
        and "datacenterbench_operator:" in capsys.readouterr().out
    )
    assert isinstance(resolve("grader", "datacenterbench_operator"), OperatorGrader)
