# Copied unchanged from Robocurve's grading code; not linted, formatted or type-checked here (see pyproject.toml).
# Everything below the "VERBATIM" line is byte-for-byte scoring/start-end-photos-v1/judge.py from Robocurve's
# DataCenterBench release 1.0.0, the judges behind every published DataCenterBench score. tests/test_published.py
# pins its hash. grader.py uses prompt(), ask(), parse(), grade() and evidence_from_photos(); it supplies the API keys
# from the environment instead of the KEYS file. task_by_id() and grade_folder() read Robocurve's task list and are
# not used here.
# ---- VERBATIM ----
"""Two-judge grading of one trial from its start and end photos (GPT-6 Astra and Claude Opus 5.5).

Adapted from the team dashboard's final judge (rig-dashboard final_judge.py: rubric as a list of allowed scores,
judge only what is visible, ignore claims of success, exactly one SCORE line). Differences: the evidence is the
full-resolution photos from all three cameras taken just before the trial and just after the arms parked (no mid-run
frames: our rubrics are about end states), a second judge from another lab, and an UNSURE answer that sends the trial
to a person instead of forcing a guess. Same score from both judges = the grade; anything else = needs a human.

  python judge.py <trial folder> <task id>          grade from <folder>/before_*.jpg and after_*.jpg
"""
import base64
import concurrent.futures as cf
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
from urllib.error import HTTPError

HERE = Path(__file__).resolve().parent
KEYS = Path(os.environ.get('JUDGE_KEYS', Path.home() / 'robocurve/.secrets/judges.env'))
CAMS = ('top', 'left', 'right')
CAM_NAMES = {'top': 'overhead camera', 'left': 'left wrist camera', 'right': 'right wrist camera'}
JUDGES = {
    'astra': dict(provider='openai', model='gpt-6-astra', effort='high', label='GPT-6 Astra'),
    'opus': dict(provider='anthropic', model='claude-opus-5-5', effort='high', label='Claude Opus 5.5'),
}
VERSION = 'start-end-photos-v1'


def keys():
    out = {}
    for line in KEYS.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip().strip('"\'')
    return out


def task_by_id(task_id):
    return next(t for t in json.loads((HERE / 'tasks.json').read_text())['tasks'] if t['id'] == task_id)


def prompt(instruction, task):
    rows = '\n'.join(f"Score {lv['score']}: {lv['description']}" for lv in task['levels'])
    return (
        "You are grading one robot trial from camera photos.\n\n"
        f"Task instruction given to the robot: {instruction}\n\n"
        f"Rubric: {task['name']}\n{task.get('guidance', '')}\n{rows}\n\n"
        "You will see photos from three cameras (overhead, left wrist, right wrist), taken just before the trial "
        "started and just after it ended with the arms parked. Judge the end state against the rubric using only "
        "what is visible; use the start photos to see what changed. Do not assume success because of anything "
        "the robot may have claimed. If the photos cannot establish which score applies (for example the view is "
        "blocked or the detail is too small to see), explain why and answer UNSURE instead of guessing.\n"
        "Explain your judgement briefly, then end your reply with exactly one line:\n"
        "SCORE: <one of the scores listed in the rubric, or UNSURE>")


def evidence_from_photos(folder):
    """[(caption, jpeg bytes)] for the start and end photos that exist."""
    out = []
    for phase, when in (('before', 'start of trial'), ('after', 'end of trial, arms parked')):
        for cam in CAMS:
            p = Path(folder) / f'{phase}_{cam}.jpg'
            if p.is_file():
                out.append((f'{when}, {CAM_NAMES[cam]}', p.read_bytes()))
    return out


def _post(url, body, headers, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except HTTPError as exc:  # bodies can echo inputs; keep only the start of the message
        raise RuntimeError(f'HTTP {exc.code}: {exc.read()[:300]!r}') from None


def ask(judge, text, evidence, k):
    j = JUDGES[judge]
    if j['provider'] == 'openai':
        content = [{'type': 'text', 'text': text}]
        for caption, data in evidence:
            content += [{'type': 'text', 'text': caption},
                        {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(data).decode()}}]
        r = _post('https://api.openai.com/v1/chat/completions',
                  {'model': j['model'], 'reasoning_effort': j['effort'], 'max_completion_tokens': 32768,
                   'messages': [{'role': 'user', 'content': content}]},
                  {'Authorization': 'Bearer ' + k['OPENAI_API_KEY']})
        choice = r['choices'][0]
        return choice['message'].get('content') or '', r.get('usage')
    content = [{'type': 'text', 'text': text}]
    for caption, data in evidence:
        content += [{'type': 'text', 'text': caption},
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': base64.b64encode(data).decode()}}]
    r = _post('https://api.anthropic.com/v1/messages',
              {'model': j['model'], 'max_tokens': 32000, 'thinking': {'type': 'adaptive'},
               'output_config': {'effort': j['effort']}, 'messages': [{'role': 'user', 'content': content}]},
              {'x-api-key': k['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'})
    return '\n'.join(b.get('text', '') for b in r.get('content', []) if b.get('type') == 'text'), r.get('usage')


def parse(reply, task):
    found = re.findall(r'^\s*\**\s*SCORE:\s*\**\s*(UNSURE|-?\d+(?:\.\d+)?)\s*\**\s*$', reply, re.M | re.I)
    # Opus sometimes opens with a bold "Score: 1" and still ends with "SCORE: 1": the same answer twice is one answer
    values = {'UNSURE' if f.upper() == 'UNSURE' else float(f) for f in found}
    if len(values) != 1:
        return dict(score=None, unsure=False, error='no single SCORE line')
    value = values.pop()
    if value == 'UNSURE':
        return dict(score=None, unsure=True)
    if not any(abs(value - float(lv['score'])) < 1e-9 for lv in task['levels']):
        return dict(score=None, unsure=False, error=f'score {value} is not a rubric score')
    return dict(score=value, unsure=False)


def grade(evidence, instruction, task, judges=('astra', 'opus')):
    if not evidence:
        return dict(version=VERSION, task_id=task['id'], score=None, needs_human=True, reason='no photos', judges={})
    text, k = prompt(instruction, task), keys()

    def one(name):
        t0 = time.time()
        try:
            reply, usage = ask(name, text, evidence, k)
            return name, dict(parse(reply, task), explanation=reply, usage=usage, seconds=round(time.time() - t0, 1))
        except Exception as exc:
            return name, dict(score=None, unsure=False, error=str(exc)[:400], seconds=round(time.time() - t0, 1))

    with cf.ThreadPoolExecutor(len(judges)) as ex:
        results = dict(ex.map(one, judges))
    scores = [r['score'] for r in results.values()]
    agreed = all(s is not None for s in scores) and len(set(scores)) == 1
    return dict(version=VERSION, task_id=task['id'], instruction=instruction, at=time.time(),
                evidence=[c for c, _ in evidence], judges=results, agreed=agreed,
                score=scores[0] if agreed else None, needs_human=not agreed,
                reason=None if agreed else ('judges disagree' if all(s is not None for s in scores) else 'a judge is unsure or failed'))


def grade_folder(folder, task_id, instruction=None):
    task = task_by_id(task_id)
    result = grade(evidence_from_photos(folder), instruction or task['instruction'], task)
    (Path(folder) / 'judges.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    r = grade_folder(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    for name, j in r['judges'].items():
        print(name, '→', 'UNSURE' if j.get('unsure') else j.get('score'), j.get('error') or '', f"({j.get('seconds')} s)")
    print('final:', r['score'], '| needs human:', r['needs_human'], r.get('reason') or '')
