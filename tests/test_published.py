"""The published judges' code: pinned byte for byte, and every path the package uses."""

from __future__ import annotations

import io
import json
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from datacenterbench import SPEC_BY_KEY, _published

# sha256 of everything after the "---- VERBATIM ----" line: release 1.0.0's
# scoring/start-end-photos-v1/judge.py, whose own pin in scoring.yaml is 260b0fe3d563b1fc.
VERBATIM_SHA256 = "260b0fe3d563b1fcad7047a56adcd846a3e41289e8cddce3d56acdb8abb503fe"
KNOB = SPEC_BY_KEY["knob"].judge_task()


def test_verbatim_file_is_unchanged() -> None:
    text = Path(_published.__file__).read_text()
    body = text.split("# ---- VERBATIM ----\n", 1)[1]
    assert sha256(body.encode()).hexdigest() == VERBATIM_SHA256


def test_prompt() -> None:
    p = _published.prompt("Turn it.", KNOB)
    assert "Rubric: Turn the knob to the mark\nThe knob carries a black line" in p
    assert (
        "Score 1: The line on the knob points at the goal mark" in p
        and "Score 0.5:" in p
        and "Score 0:" in p
    )
    assert p.endswith("SCORE: <one of the scores listed in the rubric, or UNSURE>")


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("Looks done.\nSCORE: 1", dict(score=1.0, unsure=False)),
        (
            "**Score: 0.5**\nmore\nSCORE: 0.5",
            dict(score=0.5, unsure=False),
        ),  # the same answer twice is one answer
        ("SCORE: UNSURE", dict(score=None, unsure=True)),
        ("SCORE: 1\nSCORE: 0", dict(score=None, unsure=False, error="no single SCORE line")),
        ("no score", dict(score=None, unsure=False, error="no single SCORE line")),
        ("SCORE: 0.75", dict(score=None, unsure=False, error="score 0.75 is not a rubric score")),
    ],
)
def test_parse(reply: str, expected: dict[str, Any]) -> None:
    assert _published.parse(reply, KNOB) == expected


def test_evidence_from_photos(tmp_path: Path) -> None:
    for name in ("before_top", "before_left", "after_top", "after_right"):
        (tmp_path / f"{name}.jpg").write_bytes(name.encode())
    ev = _published.evidence_from_photos(tmp_path)
    assert [c for c, _ in ev] == [
        "start of trial, overhead camera",
        "start of trial, left wrist camera",
        "end of trial, arms parked, overhead camera",
        "end of trial, arms parked, right wrist camera",
    ]
    assert ev[0][1] == b"before_top"


class Reply(io.BytesIO):
    def __enter__(self) -> Reply:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_ask_sends_the_published_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[str, dict[str, Any], dict[str, str]]] = []

    def fake(req: Any, timeout: float) -> Reply:
        body = json.loads(req.data)
        sent.append((req.full_url, body, dict(req.header_items())))
        if "openai" in req.full_url:
            return Reply(
                json.dumps(
                    dict(choices=[dict(message=dict(content="SCORE: 1"))], usage={"n": 1})
                ).encode()
            )
        return Reply(
            json.dumps(
                dict(
                    content=[dict(type="thinking"), dict(type="text", text="SCORE: 1")],
                    usage={"n": 2},
                )
            ).encode()
        )

    monkeypatch.setattr(_published.urllib.request, "urlopen", fake)
    keys = {"OPENAI_API_KEY": "o", "ANTHROPIC_API_KEY": "a"}
    ev = [("start of trial, overhead camera", b"jpg")]
    assert _published.ask("astra", "prompt", ev, keys) == ("SCORE: 1", {"n": 1})
    assert _published.ask("opus", "prompt", ev, keys) == ("SCORE: 1", {"n": 2})
    (u1, b1, h1), (u2, b2, h2) = sent
    assert (
        u1.endswith("/v1/chat/completions")
        and b1["model"] == "gpt-6-astra"
        and b1["reasoning_effort"] == "high"
    )
    assert b1["messages"][0]["content"][2]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert h1["Authorization"] == "Bearer o"
    assert (
        u2.endswith("/v1/messages")
        and b2["model"] == "claude-opus-5-5"
        and b2["output_config"] == {"effort": "high"}
    )
    assert (
        b2["messages"][0]["content"][2]["source"]["media_type"] == "image/jpeg"
        and h2["X-api-key"] == "a"
    )

    def refused(req: Any, timeout: float) -> Reply:
        raise HTTPError(req.full_url, 429, "busy", {}, io.BytesIO(b"rate limited"))  # type: ignore[arg-type]

    monkeypatch.setattr(_published.urllib.request, "urlopen", refused)
    with pytest.raises(RuntimeError, match="HTTP 429"):
        _published.ask("astra", "prompt", ev, keys)


@pytest.mark.parametrize(
    ("answers", "agreed", "score", "reason"),
    [
        ({"astra": "SCORE: 1", "opus": "SCORE: 1"}, True, 1.0, None),
        ({"astra": "SCORE: 1", "opus": "SCORE: 0.5"}, False, None, "judges disagree"),
        (
            {"astra": "SCORE: 1", "opus": "SCORE: UNSURE"},
            False,
            None,
            "a judge is unsure or failed",
        ),
        (
            {"astra": RuntimeError("HTTP 500"), "opus": "SCORE: 1"},
            False,
            None,
            "a judge is unsure or failed",
        ),
    ],
)
def test_grade_needs_both_judges(
    monkeypatch: pytest.MonkeyPatch,
    answers: dict[str, Any],
    agreed: bool,
    score: float | None,
    reason: str | None,
) -> None:
    def fake_ask(judge: str, text: str, evidence: Any, k: Any) -> tuple[str, dict[str, int]]:
        a = answers[judge]
        if isinstance(a, Exception):
            raise a
        return a, {"tokens": 1}

    monkeypatch.setattr(_published, "ask", fake_ask)
    r = _published.grade([("c", b"x")], "Turn it.", KNOB)
    assert (r["agreed"], r["score"], r["reason"], r["needs_human"]) == (
        agreed,
        score,
        reason,
        not agreed,
    )


def test_grade_without_photos() -> None:
    r = _published.grade([], "Turn it.", KNOB)
    assert r["needs_human"] and r["reason"] == "no photos"
