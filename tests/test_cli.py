"""datacenterbench grade: the published way, from a folder of start and end photos."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from datacenterbench import _published
from datacenterbench.cli import main
from datacenterbench.grader import jpeg_bytes


def photos(folder: Path) -> Path:
    for phase in ("before", "after"):
        for cam in ("top", "left", "right"):
            (folder / f"{phase}_{cam}.jpg").write_bytes(
                jpeg_bytes(np.zeros((8, 8, 3), dtype=np.uint8))
            )
    return folder


@pytest.mark.parametrize(
    ("answers", "code", "score"),
    [(("SCORE: 1", "SCORE: 1"), 0, 1.0), (("SCORE: 1", "SCORE: 0"), 1, None)],
)
def test_grade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: Any,
    answers: tuple[str, str],
    code: int,
    score: float | None,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setattr(
        _published,
        "ask",
        lambda j, t, e, k: (dict(zip(("astra", "opus"), answers, strict=True))[j], None),
    )
    assert main(["grade", str(photos(tmp_path)), "toggle"]) == code
    out = json.loads(capsys.readouterr().out)
    assert out["score"] == score and set(out["judges"]) == {"astra", "opus"}


def test_keys_are_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: Any) -> None:
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "JUDGE_KEYS"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit):
        main(["grade", str(tmp_path), "toggle"])
    assert "set OPENAI_API_KEY and ANTHROPIC_API_KEY" in capsys.readouterr().err
