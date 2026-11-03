"""DataCenterBench Tier 1: ten data-center maintenance steps on a robot, with the published
two-judge scoring.

Importing the package registers the ten tasks (``datacenterbench/<key>``), the
``datacenterbench_judges`` and ``datacenterbench_operator`` graders and the ``rubric_score`` scorer.
Installed entry points make them discoverable to Inspect Robots without importing.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from datacenterbench.grader import (
    JudgesGrader,
    OperatorGrader,
    grade_photos,
    judges_grader,
    operator_grader,
)
from datacenterbench.scoring import TARGET_KIND, rubric_score
from datacenterbench.specs import (
    RELEASE,
    SPEC_BY_KEY,
    SPECS,
    Equipment,
    Level,
    RealWorld,
    Rubric,
    TaskSpec,
)
from datacenterbench.tasks import K_TRIALS, MAX_STEPS, TASK_FACTORIES, make_task

try:
    __version__ = version("datacenterbench")
except PackageNotFoundError:  # running from an uninstalled source tree
    __version__ = "0.0.0"

__all__ = [
    "K_TRIALS",
    "MAX_STEPS",
    "RELEASE",
    "SPECS",
    "SPEC_BY_KEY",
    "TARGET_KIND",
    "TASK_FACTORIES",
    "Equipment",
    "JudgesGrader",
    "Level",
    "OperatorGrader",
    "RealWorld",
    "Rubric",
    "TaskSpec",
    "__version__",
    "grade_photos",
    "judges_grader",
    "make_task",
    "operator_grader",
    "rubric_score",
]
