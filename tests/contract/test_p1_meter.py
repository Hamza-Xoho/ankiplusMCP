"""Phase 1 black-box acceptance, including the global CLI contracts."""
import json
from pathlib import Path
import pytest
from test_p0_foundations import cli, ROOT

FIX = ROOT/'tests/fixtures/transcripts'

def meter(tmp, source=None, *extra):
    return cli(tmp, 'meter', '--session', source or FIX/'clean.jsonl', '--out', tmp/'out', *extra)

def data(tmp):
    return json.loads((tmp/'out/cost.json').read_text())

@pytest.fixture
def l006(private_fixture):
    folder = private_fixture('transcripts/l006')
    files = list(folder.glob('*.jsonl'))
    assert len(files) == 1, 'missing fixture transcripts/l006 main JSONL: see HANDOVER §Setup'
    return files[0]

def test_fr24_usage_counted_once_per_message_id(tmp_path):
    row = json.loads((FIX/'clean.jsonl').read_text())
    source = tmp_path/'duplicates.jsonl'
    source.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
    assert meter(tmp_path, source).returncode == 0
    d = data(tmp_path)
    assert len(d['calls']) == 1
    assert d['totals']['input'] == 1000 and d['totals']['output'] == 10

def test_fr24_reproduces_l006_baseline(tmp_path, l006):
    assert meter(tmp_path, l006).returncode == 1
    d = data(tmp_path)
    assert len(d['calls']) == 76
    assert d['first_ctx'] == pytest.approx(79270, rel=.01)
    assert d['peak_ctx'] == pytest.approx(166115, rel=.01)
    assert len(d['compactions']) == 2
    assert len(d['subagents']) == 2 and all(s['is_fork'] for s in d['subagents'])
    assert all(s['first_ctx'] == 141689 for s in d['subagents'])
    assert d['cost']['usd'] == pytest.approx(9, abs=2)

def test_fr24_l006_fails_every_waste_check(tmp_path, l006):
    assert meter(tmp_path, l006).returncode == 1
    assert set(data(tmp_path)['waste']) == {f'W-{n}' for n in range(1,9)}
    for w in data(tmp_path)['waste'].values():
        assert w['pass'] is False and w['evidence']
        for e in w['evidence']:
            assert 'idx' in e and 'tool' in e and len(e['excerpt']) <= 120

def test_fr24_clean_session_passes(tmp_path):
    assert meter(tmp_path).returncode == 0
    assert all(w['pass'] and not w['evidence'] for w in data(tmp_path)['waste'].values())

@pytest.mark.parametrize('check', [f'W-{i}' for i in range(1,9)])
def test_fr24_waste_check_detects(tmp_path, check):
    assert meter(tmp_path, FIX/f'w{check[-1]}.jsonl').returncode == 1
    assert [k for k,v in data(tmp_path)['waste'].items() if not v['pass']] == [check]
    assert data(tmp_path)['waste'][check]['evidence']

def test_fr24_unknown_price_not_guessed(tmp_path):
    p=tmp_path/'unknown.jsonl'
    p.write_text((FIX/'clean.jsonl').read_text().replace('claude-sonnet-4-6','claude-sonnet-5-5'))
    assert meter(tmp_path,p).returncode == 0
    assert data(tmp_path)['cost']['usd'] is None
    assert data(tmp_path)['cost']['unknown_prices'] == ['claude-sonnet-5-5']
    assert 'cost n/a (no price for claude-sonnet-5-5)' in (tmp_path/'out/cost.md').read_text()

def test_fr24_missing_field_exit2(tmp_path):
    r=json.loads((FIX/'clean.jsonl').read_text()); del r['message']['usage']['output_tokens']
    p=tmp_path/'broken.jsonl'; p.write_text(json.dumps(r)+'\n')
    result=meter(tmp_path,p)
    assert result.returncode == 2
    assert all(x in result.stdout for x in ['broken.jsonl','line 1','output_tokens','—'])
    assert not (tmp_path/'out/cost.json').exists()

def test_fr27_line_mode_one_line(tmp_path):
    r=meter(tmp_path,None,'--line')
    assert r.returncode == 0
    assert len(r.stdout.splitlines()) == 1
    assert r.stdout.startswith('Usage: 1 calls · peak 1k · ≈$')
    assert r.stdout.rstrip().endswith('waste checks 8/8 pass')

def test_g3_status_line_first(tmp_path):
    assert meter(tmp_path).stdout.splitlines()[0] == 'OK'
    assert meter(tmp_path,FIX/'w1.jsonl').stdout.splitlines()[0] == 'FINDINGS'

def test_g3_stdout_budget(tmp_path, l006):
    r=meter(tmp_path,l006)
    assert r.returncode == 1
    assert len(r.stdout) <= 2000 and len(r.stdout.splitlines()) <= 40

def test_g4_exit_codes_mapped(tmp_path):
    assert meter(tmp_path).returncode == 0
    assert meter(tmp_path,FIX/'w1.jsonl').returncode == 1
    assert meter(tmp_path,FIX/'absent.jsonl').returncode == 2

def test_g4_unknown_flag_exit2(tmp_path):
    r=meter(tmp_path,None,'--skip-checks')
    assert r.returncode == 2 and 'skip-checks' in r.stdout

def test_g5_rerun_identical(tmp_path):
    assert meter(tmp_path).returncode == 0
    import re
    def normalized(name):
        text=(tmp_path/'out'/name).read_text()
        if name.endswith('.json'):
            return re.sub(r'("created": ")[^"]+(")', r'\1<created>\2',text)
        return re.sub(r'(<!-- cards meter \S+ )\S+( -->)',r'\1<created>\2',text)
    first={name:normalized(name) for name in ('cost.json','cost.md')}
    assert meter(tmp_path).returncode == 0
    assert first == {name:normalized(name) for name in first}

def test_g6_no_writes_outside_build(tmp_path):
    p=tmp_path/'source α'; p.mkdir(); source=p/'session β.jsonl'
    source.write_bytes((FIX/'clean.jsonl').read_bytes()); source.chmod(0o444); p.chmod(0o555)
    before=(source.read_bytes(),source.stat().st_mtime_ns,p.stat().st_mtime_ns)
    try:
        assert meter(tmp_path,source).returncode == 0
        assert before == (source.read_bytes(),source.stat().st_mtime_ns,p.stat().st_mtime_ns)
        assert set(tmp_path.iterdir()) == {p,tmp_path/'out'}
    finally: p.chmod(0o755)

def test_g7_provenance_present(tmp_path):
    assert meter(tmp_path).returncode == 0
    m=data(tmp_path)['_meta']
    assert m['tool'] == 'cards meter' and m['version'] and m['created'].endswith('Z')
    assert (tmp_path/'out/cost.md').read_text().startswith('<!-- cards meter ')

def test_g9_spaces_and_unicode_paths(tmp_path):
    p=tmp_path/'α β.jsonl'; p.write_bytes((FIX/'clean.jsonl').read_bytes())
    assert meter(tmp_path,p).returncode == 0

def test_g10_help_short(tmp_path):
    r=cli(tmp_path,'meter','--help')
    assert r.returncode == 0 and 'usage:' in r.stdout and len(r.stdout.splitlines()) <= 20

def test_g10_log_line_per_run(tmp_path):
    build=tmp_path/'build'; build.mkdir()
    for n in range(2):
        r=meter(tmp_path,None,'--build',build)
        assert r.returncode == 0
        rows=[json.loads(x) for x in (build/'log.jsonl').read_text().splitlines()]
        assert len(rows) == n+2
        assert rows[-1]['cmd'] == 'cards meter' and rows[-1]['stdout_chars'] == len(r.stdout)
