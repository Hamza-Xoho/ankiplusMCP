"""Reviewers write Markdown; the CLI parses it, validates it and applies it."""
import json

import pytest

from tests.contract.test_p4_review import build, cli, folder
from tests.p3_helpers import records


def report(build, reviewer, text, k=1):
    path = build / f'review/round{k}/{reviewer}_report.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


MAINTAINER = """# Review Report — anki-maintainer

## Note n001 — FIX — A3 (blocker)
**Evidence:** article leak in the cloze.
**Rewrite Text:**
`Correct {{c1::answer}}`
**Rewrite Extra:** unchanged

## Note n002 — PASS
No issues found.

## Summary
**Verdict:** PASS_WITH_FIXES
**Stats:** notes=2, pass=1, fix=1, reject=0, blockers=1
"""

SET_FINDING = MAINTAINER.replace('## Note n002 — PASS', """## Set Finding — S2
**Notes affected:** n001, n002
**Finding:** tags drift from the source tag.
**Fix:** reapply the source tag.

## Note n002 — PASS""")

STUDENT = """# Review Report — anki-student

## Note n001 — PASS
**Attempt:** answer → right

## Note n002 — PASS
**Attempt:** answer → right

## Summary
**Verdict:** PASS
**Stats:** cards=2, attempts_right=2
"""


def both(build, maintainer=MAINTAINER, student=STUDENT, k=1):
    report(build, 'maintainer', maintainer, k)
    report(build, 'student', student, k)


def apply(build, k=1):
    return cli('apply', '--build', build, '--round', k)


def log(build, k=1):
    return json.loads((build / f'review/round{k}/apply_log.json').read_text())


def test_markdown_reports_apply(build):
    both(build)
    result = apply(build)
    assert result.returncode == 0, result.stdout
    notes = {note['id']: note for note in records(build / 'drafts.jsonl')}
    assert notes['n001']['fields']['Text'] == 'Correct {{c1::answer}}'
    assert notes['n001']['fields']['Extra'] == records(build / 'drafts.r1.jsonl')[0]['fields']['Extra']
    assert log(build)['applied'] == ['n001']


def test_set_findings_are_recorded(build):
    both(build, SET_FINDING)
    result = apply(build)
    assert result.returncode == 1
    assert log(build)['set_findings'][0]['code'] == 'S2'


def test_gate_reads_markdown_reports(build):
    both(build)
    assert apply(build).returncode == 0
    result = cli('gate', '--build', build)
    assert result.returncode == 0, result.stdout
    gate = json.loads((build / 'gate.json').read_text())
    assert gate['verdicts'] == {'maintainer': 'PASS_WITH_FIXES', 'student': 'PASS'}


def test_markdown_is_preferred_over_jsonl(build):
    both(build)
    (build / 'review/round1/maintainer_report.jsonl').write_text(
        json.dumps({'type': 'summary', 'reviewer': 'maintainer',
                    'verdict': 'FAIL', 'stats': {}}) + '\n')
    assert apply(build).returncode == 0


@pytest.mark.parametrize('mutation,field', [
    ('## Note n001 — FIX — A99\n**Evidence:** x\n', 'codes'),
    ('## Note n999 — PASS\n', 'note_id'),
    ('## Note n001 — MAYBE\n', 'verdict'),
])
def test_markdown_errors_name_the_line(build, mutation, field):
    both(build, MAINTAINER.replace('## Note n001 — FIX — A3 (blocker)\n**Evidence:** article leak in the cloze.\n**Rewrite Text:**\n`Correct {{c1::answer}}`\n**Rewrite Extra:** unchanged',
                                    mutation))
    before = (build / 'drafts.jsonl').read_bytes()
    result = apply(build)
    assert result.returncode == 2 and 'maintainer_report.md' in result.stdout
    assert 'line' in result.stdout and field in result.stdout
    assert (build / 'drafts.jsonl').read_bytes() == before


def test_student_markdown_requires_attempt(build):
    both(build, student='# Review Report — anki-student\n\n## Note n001 — PASS\n\n## Summary\n'
                        '**Verdict:** PASS\n**Stats:** notes=1\n')
    result = apply(build)
    assert result.returncode == 2 and 'attempt' in result.stdout


def test_packet_prompt_names_markdown_report(build):
    assert cli('packets', '--build', build, '--round', '1').returncode == 0
    for reviewer in ('maintainer', 'student'):
        prompt = (build / f'review/round1/{reviewer}/PROMPT.md').read_text()
        assert f'{reviewer}_report.md' in prompt


def test_set_finding_code_families_do_not_mix(build):
    both(build, student='# Review Report — anki-student\n\n## Note n001 — PASS\n'
                        '**Attempt:** answer → right\n\n## Set Finding — S2\n'
                        '**Notes affected:** n001\n**Finding:** x\n**Fix:** y\n\n'
                        '## Summary\n**Verdict:** PASS\n**Stats:** notes=1\n')
    assert apply(build).returncode == 2