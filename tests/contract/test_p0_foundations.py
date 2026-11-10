"""Phase 0 acceptance exercised through the real CLI, using synthetic sources."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]

def cli(cwd, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, '-m', 'cards', *map(str, args)], cwd=cwd,
                          env=env, text=True, capture_output=True)

@pytest.fixture
def build(tmp_path):
    source_dir = tmp_path / 'sources'
    source_dir.mkdir()
    source = source_dir / 'MED241_L006_α lecture.txt'
    source.write_text('# α lecture\nText with <sub>2</sub>', encoding='utf-8')
    result = cli(tmp_path, 'state', 'init', source)
    assert result.returncode == 0, result.stderr + result.stdout
    return tmp_path / 'builds' / (tmp_path / 'builds/.current').read_text().strip()

def state(build):
    return json.loads((build / 'build.json').read_text())

@pytest.mark.parametrize('action', ['init', 'get', 'next', 'set', 'phase'])
def test_g3_status_line_first(build, action):
    if action == 'init':
        result = cli(build.parent.parent, 'state', 'init', state(build)['source']['path'])
        assert result.returncode == 0 and result.stdout.splitlines()[0] == 'OK'
        return
    tail = {'set': ['facts.anki_reachable=true'], 'phase': ['P0', 'start']}.get(action, [])
    result = cli(build.parent.parent, 'state', action, '--build', build, *tail)
    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == 'OK'

def test_g3_stdout_budget(build):
    commands = [
        ['init', state(build)['source']['path']],
        ['get', '--build', build], ['next', '--build', build],
        ['set', '--build', build, 'facts.deck_decision=' + 'α' * 4000],
        ['phase', '--build', build, 'P0', 'start'],
    ]
    for args in commands:
        result = cli(build.parent.parent, 'state', *args)
        assert result.returncode == 0
        assert len(result.stdout) <= 2000 and len(result.stdout.splitlines()) <= 40
    code = 'from cards.common.output import Result, render; print(render(Result("FINDINGS", ["x"*300]*80, ["detail.txt"], 1)), end="")'
    result = subprocess.run([sys.executable, '-c', code], env=dict(os.environ, PYTHONPATH=str(ROOT/'src')), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert len(result.stdout) <= 2000 and len(result.stdout.splitlines()) <= 40
    assert 'more in detail.txt' in result.stdout and result.stdout.endswith('→ detail.txt\n')

def test_g4_exit_codes_mapped(build):
    code = '''from cards.common.output import Result
from cards.common.errors import CardsError, Refused
from cards.common.dispatch import execute
import sys
mode = int(sys.argv[1])
def run():
    if mode == 2: raise CardsError('E10', 'bad', 'fix')
    if mode == 3: raise Refused('E10', 'early', 'run previous')
    return Result('OK' if mode == 0 else 'FINDINGS', [], [], mode)
sys.exit(execute(run))
'''
    for expected in range(4):
        result = subprocess.run([sys.executable, '-c', code, str(expected)], env=dict(os.environ, PYTHONPATH=str(ROOT/'src')), capture_output=True, text=True)
        assert result.returncode == expected, result.stderr
        assert result.stdout.splitlines()[0] == ['OK', 'FINDINGS', 'ERROR', 'ERROR'][expected]
        if expected >= 2:
            assert 'E10' in result.stdout and '—' in result.stdout

def test_g4_unknown_flag_exit2(build):
    r = cli(build.parent.parent, 'state', 'get', '--build', build, '--skip-checks')
    assert r.returncode == 2 and r.stdout.startswith('ERROR\n') and 'skip-checks' in r.stdout

def test_g5_rerun_identical(build):
    before = (build/'build.json').read_bytes()
    for args in [('get',), ('next',), ('set', 'facts.anki_reachable=true'), ('phase', 'P0', 'start')]:
        first = cli(build.parent.parent, 'state', *args, '--build', build)
        data = (build/'build.json').read_bytes()
        second = cli(build.parent.parent, 'state', *args, '--build', build)
        assert first.returncode == second.returncode == 0
        assert first.stdout == second.stdout
        assert data == (build/'build.json').read_bytes()
    assert before != (build/'build.json').read_bytes()

def test_g6_no_writes_outside_build(build):
    root = build.parent.parent
    source = Path(state(build)['source']['path'])
    source.chmod(0o444)
    source.parent.chmod(0o555)
    def snapshot():
        paths = [p for p in root.rglob('*') if not p.is_relative_to(build)]
        return {p: (p.read_bytes() if p.is_file() else None, p.stat().st_mode,
                    p.stat().st_mtime_ns) for p in paths}
    root_snapshot = snapshot()
    try:
        for args in [('get',), ('set', 'facts.deck_exists=false'), ('phase', 'P0', 'start'), ('next',)]:
            assert cli(root, 'state', *args, '--build', build).returncode == 0
        assert root_snapshot == snapshot()
    finally:
        source.parent.chmod(0o755)


def test_g7_provenance_present(build):
    cli(build.parent.parent, 'state', 'get', '--build', build)
    for path in [build/'build.json', build/'log.jsonl']:
        data = json.loads(path.read_text().splitlines()[0]) if path.suffix == '.jsonl' else json.loads(path.read_text())
        assert data['_meta']['tool'] == 'cards state'
        assert data['_meta']['version'] and data['_meta']['created'].endswith('Z')

def test_g8_errors_name_file_line_field(build):
    p = build/'build.json'
    data = state(build)
    data['phase'] = 'BAD'
    p.write_text(json.dumps(data))
    r = cli(build.parent.parent, 'state', 'get', '--build', build)
    assert r.returncode == 2
    assert all(s in r.stdout for s in ['build.json', 'line', 'phase', '—'])

def test_g9_spaces_and_unicode_paths(tmp_path):
    folder = tmp_path/'α β source'
    folder.mkdir()
    source = folder/'γ δ.md'
    source.write_text('# Δ\nα<sup>2</sup>')
    r = cli(tmp_path, 'state', 'init', source)
    assert r.returncode == 0
    b = tmp_path/'builds'/(tmp_path/'builds/.current').read_text().strip()
    assert state(b)['source']['path'] == str(source)
    assert cli(folder, 'state', 'get', '--build', b).returncode == 0

@pytest.mark.parametrize('args', [[], ['state'], *[['state', a] for a in ['init', 'get', 'set', 'phase', 'next']]])
def test_g10_help_short(tmp_path, args):
    r = cli(tmp_path, *args, '--help')
    assert r.returncode == 0 and len(r.stdout.splitlines()) <= 20
    assert 'usage:' in r.stdout

def test_g10_log_line_per_run(build):
    for args in [('get',), ('next',), ('set', 'wrong=true'), ('phase', 'P7', 'start')]:
        before = len((build/'log.jsonl').read_text().splitlines()) if (build/'log.jsonl').exists() else 1
        r = cli(build.parent.parent, 'state', *args, '--build', build)
        lines = (build/'log.jsonl').read_text().splitlines()
        assert len(lines) == before + 1
        entry = json.loads(lines[-1])
        assert entry['cmd'] == 'cards state' and entry['exit'] == r.returncode
        assert entry['stdout_chars'] == len(r.stdout) and entry['ms'] >= 0 and entry['ts']

def test_fr2_init_creates_state_and_pointer(build):
    d = state(build)
    assert d['phase'] == 'P0' and d['job'] == 'build'
    assert d['build_id'] == build.name and build.name.endswith('_MED241-L006')
    import hashlib
    assert d['source']['sha256'] == hashlib.sha256(Path(d['source']['path']).read_bytes()).hexdigest()
    assert (build.parent/'.current').read_text().strip() == build.name
    assert d['history'] == [] and d['gate']['status'] == 'pending'

def test_fr2_init_same_source_resumes(build):
    cli(build.parent.parent, 'state', 'phase', '--build', build, 'P0', 'start')
    before = (build/'build.json').read_bytes()
    r = cli(build.parent.parent, 'state', 'init', state(build)['source']['path'])
    assert r.returncode == 0 and build.name in r.stdout and 'P0' in r.stdout
    assert before == (build/'build.json').read_bytes()
    assert len(list(build.parent.glob('*/build.json'))) == 1

def test_fr2_next_after_interrupt(build):
    assert cli(build.parent.parent, 'state', 'phase', '--build', build, 'P0', 'start').returncode == 0
    r = cli(build.parent.parent, 'state', 'next', '--build', build)
    assert r.returncode == 0 and 'P0' in r.stdout and 'entry' in r.stdout.lower() and 'cards state' in r.stdout and '.md' in r.stdout
    assert state(build)['history'][-1]['status'] == 'start'
    assert cli(build.parent.parent, 'state', 'phase', '--build', build, 'P0', 'done').returncode == 0
    assert 'P1' in cli(build.parent.parent, 'state', 'next', '--build', build).stdout

def test_fr2_illegal_phase_transition_exit2(build):
    before = (build/'build.json').read_bytes()
    r = cli(build.parent.parent, 'state', 'phase', '--build', build, 'P5', 'start')
    assert r.returncode == 2 and 'transition' in r.stdout and '—' in r.stdout
    assert before == (build/'build.json').read_bytes()

def test_fr2_set_rejects_unknown_key(build):
    for key in ['phase', 'source.sha256', 'facts.unknown']:
        before = (build/'build.json').read_bytes()
        r = cli(build.parent.parent, 'state', 'set', '--build', build, key+'=true')
        assert r.returncode == 2 and key in r.stdout and '—' in r.stdout
        assert before == (build/'build.json').read_bytes()

def test_fr2_corrupt_state_backed_up(build):
    original = b'{"phase":\n BROKEN'
    (build/'build.json').write_bytes(original)
    r = cli(build.parent.parent, 'state', 'get', '--build', build)
    assert r.returncode == 2 and 'build.json' in r.stdout and 'line 2' in r.stdout
    assert any(p.read_bytes() == original for p in build.glob('build.json.*'))
    assert (build/'build.json').read_bytes() == original

def test_inv2_no_network_imports():
    files = list((ROOT/'src/cards').rglob('*.py'))
    assert files, 'cards package absent'
    banned = {'socket', 'http', 'urllib', 'requests', 'httpx', 'aiohttp', 'websocket'}
    for file in files:
        if file == ROOT/'src/cards/write/direct.py':
            continue
        for node in ast.walk(ast.parse(file.read_text())):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
            assert not any(n.split('.')[0] in banned for n in names), str(file)
