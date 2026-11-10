"""Phase 6: shipped guard behavior and Claude runtime instruction contracts.

No new CLI subcommands in this phase; existing G-tests run with p0–p5.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / '.claude/skills/anki2'
HOOKS = {
    'block_fork.py': 'Agent',
    'block_pdf_read.py': 'Read',
    'block_local_http.py': 'Bash',
    'require_review_before_write.py': 'mcp__anki__add_notes|mcp__anki__add_note|mcp__anki__update_note_fields|mcp__anki__update_notes',
}
WRITE_TOOLS = HOOKS['require_review_before_write.py'].split('|')


def guard(project, script, tool, arguments=None, *, raw=None, mode='build'):
    payload = {'session_id': 'phase6-contract', 'transcript_path': str(project / 'session.jsonl'),
               'cwd': str(project), 'hook_event_name': 'PreToolUse', 'tool_name': tool,
               'tool_input': arguments or {}, 'tool_use_id': 'test-call'}
    return subprocess.run(['bash', str(ROOT / '.claude/hooks/run.sh'), script],
                          input=raw if raw is not None else json.dumps(payload),
                          env={**os.environ, 'CLAUDE_PROJECT_DIR': str(project), 'CARDS_PDF_GUARD': mode},
                          cwd=project, text=True, capture_output=True)


def blocked(result, alternative):
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert alternative.lower() in result.stderr.lower()
    assert 1 <= len(result.stderr.splitlines()) <= 3
    assert result.stdout == ''


def allowed(result):
    assert (result.returncode, result.stdout, result.stderr) == (0, '', '')


def active(project, status='pending', stale=False):
    build = project / 'builds/example'
    build.mkdir(parents=True)
    (build.parent / '.current').write_text('example\n')
    drafts = b'{"id":"n001"}\n'
    (build / 'drafts.jsonl').write_bytes(drafts)
    (build / 'build.json').write_text(json.dumps({'gate': {'status': status,
        'drafts_sha256': hashlib.sha256(b'stale' if stale else drafts).hexdigest()}}))
    return build


def test_c6_fork_blocked(tmp_path):
    blocked(guard(tmp_path, 'block_fork.py', 'Agent', {'subagent_type': 'fork'}), 'anki-maintainer')


@pytest.mark.parametrize('agent', ['anki-maintainer', 'anki-student', 'Explore'])
def test_c6_reviewers_allowed(tmp_path, agent):
    allowed(guard(tmp_path, 'block_fork.py', 'Agent', {'subagent_type': agent}))


@pytest.mark.parametrize('extension', ['pdf', 'PDF', 'PdF'])
def test_c6_pdf_read_blocked_during_build(tmp_path, extension):
    active(tmp_path)
    blocked(guard(tmp_path, 'block_pdf_read.py', 'Read', {'file_path': f'/lectures/L006.{extension}'}), 'cards source')


@pytest.mark.parametrize('extension', ['pdf', 'PDF'])
def test_c6_pdf_read_blocked_always_mode(tmp_path, extension):
    blocked(guard(tmp_path, 'block_pdf_read.py', 'Read', {'file_path': f'/lectures/L006.{extension}'}, mode='always'), 'cards source')


def test_c6_pdf_read_allowed_without_build(tmp_path):
    allowed(guard(tmp_path, 'block_pdf_read.py', 'Read', {'file_path': '/lectures/L006.pdf'}))


@pytest.mark.parametrize('mode', ['build', 'always'])
def test_c6_png_read_allowed(tmp_path, mode):
    active(tmp_path)
    allowed(guard(tmp_path, 'block_pdf_read.py', 'Read', {'file_path': '/builds/example/source/pages/p01.png'}, mode=mode))


@pytest.mark.parametrize('host', ['127.0.0.1:3141', 'localhost:8765', '0.0.0.0:3141', '[::1]:3141'])
def test_c6_local_http_blocked(tmp_path, host):
    blocked(guard(tmp_path, 'block_local_http.py', 'Bash', {'command': f'curl http://{host}/'}), 'mcp__anki__')


def test_c6_plain_bash_allowed(tmp_path):
    allowed(guard(tmp_path, 'block_local_http.py', 'Bash', {'command': '.venv/bin/cards check --build builds/example'}))


@pytest.mark.parametrize('tool', WRITE_TOOLS)
def test_c6_write_blocked_before_gate(tmp_path, tool):
    active(tmp_path)
    blocked(guard(tmp_path, 'require_review_before_write.py', tool), 'cards gate')


@pytest.mark.parametrize('tool', WRITE_TOOLS)
def test_c6_write_blocked_stale_gate(tmp_path, tool):
    active(tmp_path, 'passed', stale=True)
    blocked(guard(tmp_path, 'require_review_before_write.py', tool), 'cards gate')


@pytest.mark.parametrize('tool', WRITE_TOOLS)
def test_c6_write_allowed_after_gate(tmp_path, tool):
    active(tmp_path, 'passed')
    allowed(guard(tmp_path, 'require_review_before_write.py', tool))


@pytest.mark.parametrize('tool', WRITE_TOOLS)
def test_c6_write_allowed_without_build(tmp_path, tool):
    allowed(guard(tmp_path, 'require_review_before_write.py', tool))


@pytest.mark.parametrize('script,tool', [(s, t.split('|')[0]) for s, t in HOOKS.items()])
@pytest.mark.parametrize('raw', ['{broken', 'null'])
def test_c6_fail_closed(tmp_path, script, tool, raw):
    blocked(guard(tmp_path, script, tool, raw=raw), 'HOOK ERROR')


def test_c6_settings_wiring():
    settings = json.loads((ROOT / '.claude/settings.json').read_text())
    entries = settings.get('hooks', {}).get('PreToolUse', [])
    for script, matcher in HOOKS.items():
        matches = [hook for entry in entries if entry.get('matcher') == matcher
                   for hook in entry['hooks'] if script in hook.get('command', '')]
        assert len(matches) == 1, f'missing or duplicate wiring: {script}'
        hook = matches[0]
        assert hook['type'] == 'command'
        args = shlex.split(hook['command'].replace('$CLAUDE_PROJECT_DIR', str(ROOT)))
        assert args == ['bash', str(ROOT / '.claude/hooks/run.sh'), script]
        for path in [Path(args[1]), ROOT / '.claude/hooks' / script]:
            assert path.is_file() and os.access(path, os.X_OK)
    assert settings['model'] == 'claude-sonnet-5-5'
    assert settings['env']['CARDS_PDF_GUARD'] == 'build'
    assert not (ROOT / '.claude/settings.hooks.json').exists()
    # Phase 1's exclusions and the existing permission policy must survive merging.
    assert settings['disableClaudeAiConnectors'] is True
    assert settings['enabledMcpjsonServers'] == ['anki']
    assert settings['enabledPlugins'] == {}
    assert '~/.claude/CLAUDE.md' in settings['claudeMdExcludes']
    assert {'claude-flow', 'flow-nexus'} <= {x['serverName'] for x in settings['deniedMcpServers']}
    assert 'mcp__anki__add_notes' in settings['permissions']['allow']
    assert settings['permissions']['allow'] and settings['permissions']['deny']


def core():
    return (SKILL / 'SKILL.md').read_text()


def test_skill_core_size():
    assert 0 < len(core()) <= 10_000


def test_skill_frontmatter_pins():
    text = core()
    assert text.startswith('---\n')
    front = dict(re.findall(r'^(name|model|effort|description):\s*(.+)$', text.split('---', 2)[1], re.M))
    assert {k: front[k] for k in ('name', 'model', 'effort')} == {
        'name': 'anki2', 'model': 'claude-sonnet-5-5', 'effort': 'medium'}
    for trigger in ('card this', 'make cards', '/anki', 'HARVEST', 'repair'):
        assert trigger in front['description']
    assert 'general Anki questions' in front['description']
    assert len(front['description']) <= 1536


def test_skill_core_no_rubric():
    assert not re.search(r'\b(?:A(?:[1-9]|1[0-3])|S[1-9]|V[1-9])\b', core())
    assert not re.search(r'^\|.*(?:Fidelity|Unambiguous|Answerability).*\|', core(), re.M | re.I)


def phase_rows():
    return {cells[0].split()[0]: cells for line in core().splitlines()
            if re.match(r'^\| P[0-7]\b', line)
            for cells in [[cell.strip() for cell in line.strip('|').split('|')]]}


def test_skill_phase_map_complete():
    text = core()
    headings = re.findall(r'^## (.+)$', text, re.M)
    assert headings == ['Purpose', 'Job router', 'Invariants', 'Token discipline', 'Phase map', 'Resume rule', 'Stop conditions']
    rows = phase_rows()
    assert set(rows) == {f'P{i}' for i in range(8)}
    assert all(len(cells) == 6 and all(cells) for cells in rows.values())
    for phase, commands in {'P0': ['state init', 'state set'], 'P1': ['extract', 'target'],
                            'P2': ['source'], 'P3': ['check', 'render'], 'P4': ['packets', 'apply'],
                            'P5': ['gate'], 'P6': ['write'], 'P7': ['report']}.items():
        for command in commands:
            assert f'.venv/bin/cards {command}' in rows[phase][2]
    assert 'once' in rows['P2'][2] and '--all' in rows['P2'][2]
    assert 'drafts.jsonl' in ' '.join(rows['P2']) and 'skipped.jsonl' in ' '.join(rows['P2'])
    assert 'one Write each' in ' '.join(rows['P2'])
    assert all(word in ' '.join(rows['P4']) for word in ('anki-maintainer', 'anki-student', 'one message', 'PROMPT.md', 'path only'))
    assert all(word in ' '.join(rows['P6']) for word in ('add_notes', 'batch', 'expected.json', 'suspend', 'verify'))
    paths = set(re.findall(r'phases/[\w-]+\.md', text))
    assert {'phases/draft.md', 'phases/occlusion.md', 'phases/write.md'} <= paths
    assert all((SKILL / path).is_file() for path in paths)
    resume = text.split('## Resume rule\n', 1)[1].split('## Stop conditions', 1)[0]
    assert 'build.json' in resume and 'first' in resume and 'source --all' in resume
    assert 'without asking' in text and 'HARVEST' in text and '/anki`' in text


def test_fr9_house_style_only_in_phase_file():
    text = core()
    assert 'phases/draft.md' in text
    assert not re.search(r'<(?:b|u|i|br|span)\b|two or three clozes|no full stop|binary hint|hints name|one relationship per sentence', text, re.I)
    draft = (SKILL / 'phases/draft.md').read_text()
    for rule in ('<b>', '<br>', 'hint', 'Tier', 'source_ref', 'skipped.jsonl', 'fields', 'objective'):
        assert rule in draft
    assert 'phases/draft.md' not in ' '.join(phase_rows()[p][-1] for p in ('P0', 'P1', 'P3', 'P4', 'P5', 'P6', 'P7'))


def test_runtime_claude_routes_and_gate():
    text = (ROOT / 'CLAUDE.md').read_text()
    assert 'Writes happen without asking once `cards gate` passes (ADR-9)' in text
    assert '/anki2' in text and '.claude/skills/anki2/SKILL.md' in text
    assert 'wait for "yes"' not in text and 'act after "yes"' not in text and 'write after "yes"' not in text


def test_skill_terminal_commands_match_shipped_cli(tmp_path):
    """Follow the documented terminal sequence against real state, not a mock."""
    cards = str(ROOT / '.venv/bin/cards')
    source = tmp_path / 'lecture.txt'
    source.write_text('Lecture source')
    def run(*args):
        return subprocess.run([cards, *map(str, args)], cwd=tmp_path, capture_output=True, text=True)
    result = run('state', 'init', source)
    assert result.returncode == 0, result.stdout
    build = next((tmp_path / 'builds').glob('*/build.json')).parent
    state = json.loads((build / 'build.json').read_text())
    state['phase'] = 'P7'
    state['history'] = [{'phase': 'P7', 'status': 'start', 'started_at': '2026-11-05T00:00:00Z', 'ended_at': None}]
    (build / 'build.json').write_text(json.dumps(state))
    result = run('state', 'phase', '--build', build, 'P7', 'done')
    assert result.returncode == 0, result.stdout
    commands = re.findall(r'`(\.venv/bin/cards state phase --build <build> done (?:start|done))`', ' '.join(phase_rows()['P7']))
    assert commands, 'document the terminal transition'
    for command in commands:
        args = shlex.split(command.replace('<build>', str(build)))[1:]
        result = run(*args)
        assert result.returncode == 0, result.stdout
    assert json.loads((build / 'build.json').read_text())['phase'] == 'done'
    assert '`done done`' not in (SKILL / 'phases/write.md').read_text()
