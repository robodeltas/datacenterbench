# DataCenterBench Tier 1

Ten steps from data-center maintenance procedures, built as tasks for bimanual robot arms, with the scoring behind
every [published DataCenterBench score](https://robocurve.org/datacenterbench/). Built on
[Inspect Robots](https://github.com/robocurve/inspect-robots) and listed in
[WorldEvals](https://github.com/robocurve/worldevals).

Each task is one fixed setup on a board (a knob, a switch, a key, a cable, a number pad and so on) with 3 trials per
model. A trial scores 0, 0.5 or 1 from the task's rubric. A model's task score is the mean of its 3 trials (avg@3),
and its benchmark score is the mean of its ten task scores.

## Quick start

```bash
pip install "datacenterbench @ git+https://github.com/robocurve/datacenterbench"
inspect-robots list tasks     # shows datacenterbench/*
```

Try the pipeline without a robot on Inspect Robots' `cubepick` mock, scoring the trial by hand:

```bash
inspect-robots run --task datacenterbench/knob --policy random --embodiment cubepick \
  --grader datacenterbench_operator --epochs 1
```

The mock does not model these tasks. It only checks that the task, grader and scorer run.

## The tasks

| Task (`--task`) | Name | Instruction (all the model is told) |
|---|---|---|
| [`datacenterbench/unplug`](docs/tasks/unplug.md) | Unplug the charger from the power strip | Unplug the white phone charger from the white power strip. |
| [`datacenterbench/knob`](docs/tasks/knob.md) | Turn the knob to the mark | Turn the round knob on the white box clockwise until the black line on it points at the black mark on the box. |
| [`datacenterbench/toggle`](docs/tasks/toggle.md) | Flip the light switch | Flip the lever of the light switch on the white box to the other side. |
| [`datacenterbench/key`](docs/tasks/key.md) | Turn the key | Turn the key clockwise to its other position. Leave it there and release it. |
| [`datacenterbench/cover`](docs/tasks/cover.md) | Open the spring-loaded cover | Lift the clear cover on the grey box all the way open, until it stays open on its own. It is spring-loaded and snaps shut if it is not pushed far enough. |
| [`datacenterbench/slider`](docs/tasks/slider.md) | Move the slider to the other line | Move the small slider on the white dimmer from the black line it is on to the other black line. |
| [`datacenterbench/keypad`](docs/tasks/keypad.md) | Enter a code on the keypad | Type 52 on the number pad and nothing else. The iPhone next to it shows what you type. |
| [`datacenterbench/plug`](docs/tasks/plug.md) | Plug the charger into the power strip | Pick up the white phone charger and plug it into one of the outlets on the white power strip. Push it in until the prongs are fully inserted. |
| [`datacenterbench/join`](docs/tasks/join.md) | Join the Ethernet plug and coupler | Use one hand to hold the Ethernet coupler and the other to insert the Ethernet plug into it until it clicks into place. |
| [`datacenterbench/clip`](docs/tasks/clip.md) | Press the cable into the clip | Press the black network cable into the dark clip on the table, so the cable is held by the clip. |

Each task page has the setup photos from all three cameras, the setup and reset steps, the equipment with the
products the published runs used, the rubric, and the real-world procedure step the task stands in for. The board
and mounting supplies are on [Shared equipment](docs/equipment.md).

## Scoring

A trial gets a score only when two judges, GPT-6 Astra and Claude Opus 5.5 (both at reasoning effort high), give
the same one from start and end photos of the three cameras. When they disagree, or either answers UNSURE or fails,
a person scores it. The prompt, requests and answer checks are the published code, copied byte for byte.

- **`datacenterbench grade FOLDER TASK`:** the published way. The folder holds full-resolution photos taken just
  before the trial (`before_top.jpg`, `before_left.jpg`, `before_right.jpg`) and just after it with the arms parked
  (`after_top.jpg`, `after_left.jpg`, `after_right.jpg`). Needs `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Graded
  again this way, three published trials (Turn the knob, Flip the light switch, Plug the charger in) got their
  published scores of 0.5, 1 and 0, with both judges matching.
- **`--grader datacenterbench_judges`:** the same judges during a run, on the run's own first and parked (or last)
  frames. It only sends frames at least 640 px wide; narrower ones are left for a person. Robocurve's YAM setup
  records 224 x 224, and on the same three trials graded from those frames the judges answered UNSURE five times
  out of six, and the sixth answer was wrong.
- **`--grader datacenterbench_operator`:** shows the whole rubric (guidance and levels) and asks the person at the
  terminal for a score.

The keypad task was scored from the keypad display's own key log (exactly 52 is 1, one keypress away is 0.5,
anything else 0), which only Robocurve's setup records. With this package a person reads the display and scores
it, and the judges' answer is kept as a cross-check.

A trial with no rubric score is left out of the task score instead of counting as 0, and the run's log is marked as
an error with the reason. A console verdict (`/y`, `/n`, `/p`) is not a rubric score, so both graders still grade
that trial. Inspect Robots' own `operator` and `vlm` graders only record success or failure, so their trials are
left out too.

## Comparable runs

Scores compare when they come from the same release and protocol. The published runs (2026-10-21 and 22, plus four
reruns on 2026-10-27) used:

- **Robot:** I2RT YAM bimanual arms with Inspect Robots 0.58.0 or 0.59.0 and inspect-robots-yam 0.36.0, end-effector
  position targets at 25% of maximum speed, motor temperature cutoff 65 °C.
- **Agent:** inspect-robots-agent 0.26.0 or 0.27.0. At most 40 LLM calls and 900 control steps per trial, no time
  limit. Three cameras (overhead and both wrists) at 224 x 224 with rendered depth, images every step, the last 2
  kept.
- **Models:** GPT-6 Astra and GPT-6.1 Sol (max, ultrafast), Claude Opus 5.5 (max, fast mode), Gemini 4 Argon
  (high), Muse Wonder 1.0 (high), Grok 4.7 (xhigh), and Kimi K3, GLM 5.3 Flash and DeepSeek V4.1 Flash (high,
  through OpenRouter). Each at the highest reasoning level it offers.
- **Trials:** 3 per model per task, models taking turns so no model runs twice in a row on a rig.
- **Counted:** every trial that ran, including model give-ups, the 40-call limit, model errors (scored from the end
  state), and overheats during the model's own trial when the rig started cool.
- **Set aside and rerun with the same model:** infrastructure failures (API, network, motor bus or camera),
  overheats from heat left by the previous trial, batches restarted after a setup change, and interrupted tries.

Inspect Robots applies only part of this counting. It never grades or scores a trial that ended in an error, and
`--epochs 3` does not replace a trial that was set aside. To match the protocol:

1. Read each errored trial's reason in the log. Rerun infrastructure failures with the same model.
2. Score model errors by hand from the trial's end state and count them.
3. Run more trials until each model has 3 counted, scored trials on each task.

An LLM agent on a YAM rig, from a rig directory with `./run` and `config.ini`:

```bash
pip install "datacenterbench @ git+https://github.com/robocurve/datacenterbench"   # into the rig venv
./run --task datacenterbench/knob --epochs 3 --grader datacenterbench_operator --store-frames \
  -E auto_start=false -E control_interface=eef_pos -E report_joint_eff=true -E motor_temp_limit=65 \
  --policy agent -P model=openai/gpt-6.1-sol -P wire=responses -P effort=max -P service_tier=ultrafast \
  -P max_llm_calls=40 -P max_speed_frac=0.25 -P images=always -P image_horizon=2 -P depth=render
```

Take full-resolution start and end photos for `datacenterbench grade` if you want judge scores comparable with the
published ones. `-E auto_start=false` pauses before each trial so the scene can be reset after the arms reach home.
Keep clear of the arms while they move.

## Development

Inspect Robots comes from PyPI. The package needs 0.59 or later: 0.58 cannot leave an unscored trial out of a task
score. CI also runs the tests against 0.59.0 and Inspect Robots main. After changing dependencies, run `uv lock`
and commit `uv.lock`.

```bash
uv sync --locked --extra dev && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov
```

Coverage must be 100%, mypy is strict, and Ruff D1 requires contract docstrings for public modules, classes, and
functions. Task pages are generated from `specs.py` with `uv run python tools/task_pages.py`. See
[CLAUDE.md](CLAUDE.md) for repository conventions.

## Citation

```bibtex
@software{datacenterbench,
  author  = {Robocurve},
  title   = {DataCenterBench Tier 1: data-center maintenance steps for robot arms},
  year    = {2026},
  url     = {https://github.com/robocurve/datacenterbench},
  version = {1.0.0},
  license = {MIT}
}
```

[MIT license](LICENSE). Each task page quotes a short passage from the vendor manual it names, as its source.
