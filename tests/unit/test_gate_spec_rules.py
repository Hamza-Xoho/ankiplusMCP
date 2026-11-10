"""Gate pass rule follows TRD T-9: verdicts, open blockers, lint. Conflicts on unresolved notes
and set findings are reported, not gate failures. Rubric defines verdict on the post-rewrite state."""
import json
from pathlib import Path
from tests.contract.test_p5_write import build, load, run  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def test_set_findings_and_conflicts_do_not_fail_gate(build):
    p = build / 'review/round1/apply_log.json'
    log = json.loads(p.read_text())
    log['set_findings'] = [{'type': 'set', 'reviewer': 'maintainer', 'code': 'S1', 'notes': [],
                            'finding': 'f', 'fix': 'x'}]
    log['conflicts'] = [{'id': 'n001', 'findings': []}]
    p.write_text(json.dumps(log))
    r = run(build, 'gate')
    assert r.returncode == 0, r.stdout
    assert load(build, 'gate.json')['status'] == 'passed'


def test_rubric_verdict_is_post_rewrite_state():
    for who in ('maintainer', 'student'):
        t = (ROOT / f'.claude/skills/anki2/templates/review/{who}/report-format.md').read_text()
        assert 'after your rewrites' in t
        assert 'FAIL = any blocker' not in t
