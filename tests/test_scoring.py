"""rubric_score reads the recorded level; anything else is left out, never scored 0."""

import pytest
from inspect_robots import Target, TrialRecord

from datacenterbench import TARGET_KIND, rubric_score, scoring

LEVELS = Target(kind=TARGET_KIND, spec={"scores": [1, 0.5, 0]})


def record(verdict: str | None, **metadata: str) -> TrialRecord:
    return TrialRecord(
        scene_id="knob", epoch=0, seed=0, operator_judgement=verdict, metadata=dict(metadata)
    )


@pytest.mark.parametrize(
    ("verdict", "target", "expected"),
    [
        ("0.5", LEVELS, 0.5),
        ("1", LEVELS, 1.0),
        ("0", LEVELS, 0.0),
        (" 1.0 ", LEVELS, 1.0),
        ("0.3", None, 0.3),  # without the rubric target, any score in [0, 1]
        ("0.3", Target(kind="other"), 0.3),
    ],
)
def test_scores(verdict: str, target: Target | None, expected: float) -> None:
    scorer = rubric_score()
    assert scorer.name == "rubric_score"
    score = scorer(record(verdict), target)
    assert score.value == expected
    assert score.explanation == f"rubric score {verdict.strip()}"


UNSCORED = [
    (record("0.75"), "is not one of this rubric's scores"),
    (record("y"), "not a rubric score: 'y'"),  # success/failure graders are not rubric scores
    (record("nan"), "not a rubric score"),
    (record("1.5"), "not a rubric score"),
    (record(None, grading_error="Astra API HTTP 500"), "the judge failed: Astra API HTTP 500"),
    (record(None), "no rubric score recorded"),
]


def test_a_trial_the_grader_gave_up_on_abstains_when_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Inspect Robots counts this trial as ungraded and ends the run as an error itself.
    monkeypatch.setattr(scoring, "ABSTAINS", True)
    score = rubric_score()(record(None, grading_error="Astra API HTTP 500"), LEVELS)
    assert score.value is None
    assert "the judge failed: Astra API HTTP 500" in (score.explanation or "")


@pytest.mark.parametrize(("trial", "why"), UNSCORED[:-2] + UNSCORED[-1:])
def test_a_trial_nobody_explained_is_a_scorer_error_even_with_abstentions(
    trial: TrialRecord, why: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No grading_error: an abstention would leave the run "success", so raise instead.
    monkeypatch.setattr(scoring, "ABSTAINS", True)
    with pytest.raises(scoring.NotScored, match=why.replace("(", r"\(")):
        rubric_score()(trial, LEVELS)


@pytest.mark.parametrize(("trial", "why"), UNSCORED)
def test_unscored_is_left_out_on_older_inspect_robots(
    trial: TrialRecord, why: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scoring, "ABSTAINS", False)
    with pytest.raises(scoring.NotScored, match=why.replace("(", r"\(")):
        rubric_score()(trial, LEVELS)


def test_detects_abstention_support(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scoring, "value_to_float", lambda value: None)
    assert scoring._supports_abstaining() is True

    def old(value: object) -> float:
        return float(value)  # type: ignore[arg-type]

    monkeypatch.setattr(scoring, "value_to_float", old)
    assert scoring._supports_abstaining() is False
