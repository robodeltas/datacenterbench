# datacenterbench: agent guide

A standalone Inspect Robots benchmark plugin: the ten DataCenterBench Tier 1 tasks (release 1.0.0 of Robocurve's
benchmark), each one fixed setup with 3 mean-reduced trials, scored by the published two-judge rule or by hand.

## Map

| Path | Contract |
|---|---|
| `src/datacenterbench/specs.py` | Frozen `TaskSpec`s copied from the release: instruction, name, rubric (guidance, levels), setup, reset, equipment (without purchase records), photos, the real-world step, the keypad code. The source of truth. |
| `src/datacenterbench/tasks.py` | One `Scene` per task (the judges' task in `metadata["datacenterbench"]`, allowed scores in the `Target`), 3 trials, `max_steps` 900 by default, ten registered factories. |
| `src/datacenterbench/scoring.py` | `rubric_score`: reads the recorded rubric score. Without one it abstains when the grader recorded `grading_error` (Inspect Robots then ends the run as an error) and raises `NotScored` otherwise, and always on 0.59 and 0.60, which have no abstentions. |
| `src/datacenterbench/grader.py` | `datacenterbench_judges` (published judges on the run's frames, only at least `min_width` wide), `datacenterbench_operator` (by hand), `grade_photos` (the published way, full-resolution photos). |
| `src/datacenterbench/_published.py` | The release's `scoring/start-end-photos-v1/judge.py`, byte for byte after the VERBATIM line. Excluded from ruff and mypy; a test pins its hash. `grader.py` replaces its `keys()` with `judge_keys()`. |
| `src/datacenterbench/cli.py` | `datacenterbench grade FOLDER TASK`. |
| `tools/task_pages.py` | Renders `docs/tasks/<key>.md` from the specs; a test fails when a page drifts. |

## Rules

- Never edit an instruction, a task name, a rubric or the verbatim judge to tidy them. They decide scores. A real
  change is a new task version and a new release, made in Robocurve's benchmark release first and copied here.
- Rubric scores 0 and 1 stay integers where the release has them: the judge prompt prints `Score 1`, not
  `Score 1.0`.
- Entry-point name, `@task` name and `Task.name` match exactly: `datacenterbench/<key>`. Keep the WorldEvals
  catalog's `task_keys` in sync.
- Inspect Robots 0.59 is the floor: 0.59 and 0.60 leave a trial out of the mean only through `NotScored`; later
  versions abstain, but only a trial with `grading_error` makes the run an error, so `rubric_score` abstains only
  there. Keep the integration tests passing on 0.59.0, the locked version and main (CI's `compat-min` and
  `compat-main`).
- Purchase records (order numbers, receipts, payment) stay with Robocurve; the specs keep product, link and how it
  was used.

## Gates

```bash
uv sync --locked --extra dev && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov
```

Mypy is strict and coverage stays at 100%. CI installs from `uv.lock`; run `uv lock` after changing dependencies.
`ci-ok` is the single required check.

## Public writing

No em dashes in prose, bold only for definition-list lead-ins, no decorative emoji, headers use colons. Keep
instruction and rubric text, commands, numbers and safety notes unchanged when editing prose.
