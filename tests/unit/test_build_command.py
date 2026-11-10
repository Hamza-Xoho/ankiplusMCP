"""`cards build` owns the phase order; the agent only acts at pause prompts."""
import json
import os
import subprocess
import sys
from pathlib import Path

from cards import build

SOURCE = """Muscles of the Arm

Objectives
1. Identify muscles
2. Describe innervation

The biceps brachii originates from the supraglenoid tubercle.
"""


def cli(*args, cwd):
    env = {**os.environ, 'CARDS_BUILDS': str(Path(cwd) / 'builds')}
    return subprocess.run([sys.executable, '-m', 'cards', *map(str, args)],
                          capture_output=True, text=True, cwd=cwd, env=env)


def fixture(tmp_path):
    source = tmp_path / 'MED241_L015_arm.txt'
    source.write_text(SOURCE)
    made = cli('build', '--pdf', source, cwd=tmp_path)
    assert made.returncode == 0, made.stdout
    folder = next((tmp_path / 'builds').glob('*/build.json')).parent
    return folder, made


def state(build_dir):
    return json.loads((build_dir / 'build.json').read_text())


def test_build_pauses_at_p2_with_resume_command(tmp_path):
    folder, made = fixture(tmp_path)
    lines = made.stdout.splitlines()
    assert lines[0] == 'OK' and len(lines) <= 40 and len(made.stdout) <= 2000
    assert '⏸️  P2 Drafting' in made.stdout
    assert 'cards build --continue' in made.stdout
    assert str(folder / 'build.json') in made.stdout
    data = state(folder)
    assert data['phase'] == 'P2'
    assert [h['phase'] for h in data['history'] if h['status'] == 'done'] == ['P0', 'P1']
    assert data['history'][-1] == {**data['history'][-1], 'phase': 'P2', 'status': 'start'}


def test_build_continue_without_active_build_refuses(tmp_path):
    made = cli('build', '--continue', cwd=tmp_path)
    assert made.returncode == 3 and made.stdout.startswith('ERROR')


def test_build_done_build_is_not_replayed(tmp_path):
    folder, _ = fixture(tmp_path)
    data = state(folder)
    data['phase'] = 'done'
    (folder / 'build.json').write_text(json.dumps(data))
    made = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert made.returncode == 0 and 'complete' in made.stdout


def scope_fixture(tmp_path):
    from cards.common.paths import Build
    folder = tmp_path / 'b'
    folder.mkdir()
    (folder / 'drafts.jsonl').write_text(
        '{"id":"n001","fields":{}}\n{"id":"n002","fields":{}}\n')
    maintainer = ('# Review Report — anki-maintainer\n\n## Note n001 — PASS\n\n'
                  '## Note n002 — PASS\n\n## Summary\n**Verdict:** PASS\n**Stats:** notes=2\n')
    student = ('# Review Report — anki-student\n\n## Note n001 — FIX — V1 (blocker)\n'
               '**Evidence:** x\n**Attempt:** answer → alternative\n\n## Note n002 — PASS\n'
               '**Attempt:** answer → right\n\n## Summary\n**Verdict:** PASS_WITH_FIXES\n'
               '**Stats:** notes=2\n')
    (folder / 'review/round1').mkdir(parents=True)
    (folder / 'review/round1/maintainer_report.md').write_text(maintainer)
    (folder / 'review/round1/student_report.md').write_text(student)
    return Build(folder)


def test_review_scope_rules(tmp_path):
    b = scope_fixture(tmp_path)
    blocker = {'conflicts': [], 'open_blockers': [{'note_id': 'n001'}], 'unresolved': [],
               'css_fix_needed': []}
    assert build.review_scope(b, 1, blocker) == (['n001'], False)
    wide = {'conflicts': [{'id': f'n00{i}'} for i in range(1, 5)], 'open_blockers': [],
            'unresolved': [], 'css_fix_needed': []}
    assert build.review_scope(b, 1, wide) == ([f'n00{i}' for i in range(1, 5)], True)
    assert build.review_scope(b, 2, wide) is None


def test_verdict_disagreement_scopes_a_small_round(tmp_path):
    b = scope_fixture(tmp_path)
    clean = {'conflicts': [], 'open_blockers': [], 'unresolved': [], 'css_fix_needed': []}
    assert build.review_scope(b, 1, clean) == (['n001'], False)


def test_build_help_is_valid():
    made = cli('build', '--help', cwd=Path.cwd())
    assert made.returncode == 0 and '--pdf' in made.stdout and '--continue' in made.stdout


STAMP = '2026-11-06T00:00:00Z'


def prepared(tmp_path, phase, previous):
    folder, _ = fixture(tmp_path)
    data = state(folder)
    data['phase'] = phase
    data['history'] = [
        {'phase': previous, 'status': 'done', 'started_at': STAMP, 'ended_at': STAMP},
        {'phase': phase, 'status': 'start', 'started_at': STAMP, 'ended_at': None}]
    (folder / 'build.json').write_text(json.dumps(data))
    return folder


def test_build_refuses_a_skipped_phase(tmp_path):
    folder = prepared(tmp_path, 'P4', 'P2')  # P3 never completed
    made = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert made.returncode == 3 and 'previous phase P3' in made.stdout


def test_build_refuses_gate_without_review(tmp_path):
    folder = prepared(tmp_path, 'P5', 'P4')
    made = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert made.returncode == 3 and 'review apply log missing' in made.stdout


def test_build_refuses_write_before_gate(tmp_path):
    folder = prepared(tmp_path, 'P6', 'P5')
    made = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert made.returncode == 3 and 'gate not passed' in made.stdout