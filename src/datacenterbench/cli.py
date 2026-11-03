"""``datacenterbench grade FOLDER TASK``: grade one trial the published way, from full-resolution
photos.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from datacenterbench.grader import _summary, grade_photos, judge_keys
from datacenterbench.specs import SPEC_BY_KEY


def main(argv: Sequence[str] | None = None) -> int:
    """Print the two judges' answers for one trial's photos; exit 1 when a person must score it."""
    ap = argparse.ArgumentParser(prog="datacenterbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grade", help="grade a trial from before_*.jpg and after_*.jpg photos")
    g.add_argument("folder", help="holds before_top/left/right.jpg and after_top/left/right.jpg")
    g.add_argument("task", choices=sorted(SPEC_BY_KEY), help="the task key, e.g. knob")
    g.add_argument("--instruction", help="the instruction the robot got, if not the task's own")
    a = ap.parse_args(argv)
    missing = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not judge_keys().get(k)]
    if missing:
        ap.error(f"set {' and '.join(missing)} (or JUDGE_KEYS, a file of KEY=value lines)")
    result = grade_photos(a.folder, a.task, a.instruction)
    print(json.dumps(_summary(result), indent=1))
    return 1 if result.get("needs_human") else 0
