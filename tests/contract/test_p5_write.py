"""Phase 5 contracts through the real CLI."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from tests.p3_helpers import cli, dump, drafts, records, note, setup, convert_v1
from tests.contract.test_p4_review import reports, finding

@pytest.fixture
def build(tmp_path,monkeypatch):
    monkeypatch.setenv('CLAUDE_SESSION_ID',str(Path('tests/fixtures/transcripts/clean.jsonl').resolve()))
    b=setup(tmp_path/'builds'/'example')
    dump(b/'build.json',{'review':{'round':1},'facts':{},'write':{}})
    reports(b)
    assert cli('apply','--build',b,'--round','1').returncode==0
    return b

def run(b, cmd): return cli(cmd,'--build',b)
def load(b,p): return json.loads((b/p).read_text())
def gate(b):
    p=run(b,'gate'); assert p.returncode==0,p.stdout

def planned(b):
    gate(b); p=run(b,'write'); assert p.returncode==0,p.stdout

def test_fr17_gate_passes(build):
    gate(build)
    from hashlib import sha256
    g=load(build,'gate.json')
    assert g['status']=='passed' and g['drafts_sha256']==sha256((build/'drafts.jsonl').read_bytes()).hexdigest()
    assert load(build,'build.json')['gate']['status']=='passed'
    reports(build,k=2)
    p=build/'review/round2/student_report.jsonl'; p.write_text(p.read_text().replace('PASS','FAIL'))
    assert cli('apply','--build',build,'--round','2').returncode==0
    r=run(build,'gate'); assert r.returncode==1 and load(build,'gate.json')['round']==2

def test_fr17_gate_fails_on_fail_verdict(build):
    p=build/'review/round1/student_report.jsonl'
    p.write_text(p.read_text().replace('PASS','FAIL'))
    r=run(build,'gate'); assert r.returncode==1 and 'student' in r.stdout
    assert load(build,'gate.json')['status']=='failed'

def test_fr17_gate_fails_on_open_blocker(build):
    b=setup(build.parent/'blocked'); dump(b/'build.json',{'review':{'round':1}})
    reports(b,[finding(rewrite=None)])
    assert cli('apply','--build',b,'--round','1').returncode==1
    p=run(b,'gate'); assert p.returncode==1 and 'blocker' in p.stdout
    assert load(b,'gate.json')['status']=='failed'

def test_fr17_gate_no_bypass(build):
    for flag in ('--force','--skip-gate','--approve'):
        r=cli('gate','--build',build,flag); assert r.returncode==2 and 'ERROR' in r.stdout
    p=build/'review/round1/student_report.jsonl'; p.write_text(p.read_text().replace('PASS','FAIL'))
    r=subprocess.run([sys.executable,'-m','cards','gate','--build',str(build)],env={**os.environ,'CARDS_SKIP_GATE':'1','CARDS_FORCE':'1'},capture_output=True,text=True)
    assert r.returncode==1 and load(build,'gate.json')['status']=='failed'

def test_fr18_write_refused_before_gate(build):
    r=run(build,'write'); assert r.returncode==3 and 'gate' in r.stdout and not (build/'write').exists()

def test_fr18_write_refused_after_drafts_change(build):
    gate(build)
    with (build/'drafts.jsonl').open('a') as f: f.write('\n')
    r=run(build,'write'); assert r.returncode==3 and 'drafts' in r.stdout and not (build/'write').exists()

def test_fr18_batches_shape(build):
    ns=[note(i) for i in range(1,206)]; ns[-1].update(action='update',nid=123)
    drafts(build,ns)
    (build/'review/round1/apply_log.json').unlink(); assert cli('apply','--build',build,'--round','1').returncode==0
    planned(build)
    assert load(build,'write/expected.json')['updated']==1 and load(build,'write/expected.json')['created']==204
    batches=[load(build,str(p.relative_to(build))) for p in sorted((build/'write/batches').glob('*.json'))]
    assert [len(b['notes']) for b in batches]==[100,100,4]
    assert all(set(b)=={'deck_name','model_name','notes'} and all(set(n)=={'fields','tags'} for n in b['notes']) for b in batches)
    assert load(build,'write/updates.json')==[{'note_id':123,'fields':ns[-1]['fields']}]
    assert [n for b in batches for n in b['notes']]==[{'fields':n['fields'],'tags':n['tags']} for n in ns[:-1]]
    ns[-1].update(kind='io',action='create',nid=None,notetype='Image Occlusion',fields={'Image':'image.png','Occlusion':'mask.svg'},media=[{'path':'image.png','filename':'image.png'}],preview='preview.png')
    drafts(build,ns); (build/'review/round1/apply_log.json').unlink()
    assert cli('apply','--build',build,'--round','1').returncode==0
    planned(build)
    batches=[load(build,str(p.relative_to(build))) for p in sorted((build/'write/batches').glob('*.json'))]
    assert {b['model_name'] for b in batches}=={'ColdRecall Cloze','Image Occlusion'}
    assert sum(len(b['notes']) for b in batches)==205
    assert all(('Image' in n['fields'])==(b['model_name']=='Image Occlusion') for b in batches for n in b['notes'])

def test_fr18_suspend_list(build):
    planned(build); s=load(build,'write/suspend.json')
    assert s['draft_ids']==['n002'] and s['reason']=={'n002':'tier3'}
    b=setup(build.parent/'unresolved'); dump(b/'build.json',{'review':{'round':2}})
    ns=[note(),note(2,3)]; ns[0]['status']='unresolved'; drafts(b,ns)
    reports(b,k=2); assert cli('apply','--build',b,'--round','2').returncode==0
    planned(b); assert load(b,'write/suspend.json')['reason']=={'n001':'unresolved','n002':'tier3'}

def test_fr18_expected_counts(build):
    planned(build); e=load(build,'write/expected.json')
    assert (e['created'],e['updated'],e['suspend_notes'])==(2,0,1)
    assert e['verify'][0].startswith('tag:#ColdRecall::#Source::') and 'is:suspended' in e['verify'][1]

def test_fr20_import_file_format(build):
    planned(build); lines=(build/'write/import.txt').read_text().splitlines()
    assert lines[:5]==['#separator:tab','#html:true','#notetype:ColdRecall Cloze','#deck:Endoplasmic Reticulum, Mitochondria & Golgi Apparatus','#tags column:3']
    assert len(lines)==7 and all(len(l.split('\t'))==3 for l in lines[5:])

def completed(b):
    planned(b)
    state=load(b,'build.json'); state['write']={'status':'done','created':2,'updated':0,'suspended':1}
    dump(b/'build.json',state)
    (b.parent/'.current').write_text(b.name+'\n')

def test_fr21_report_short(build):
    completed(build); p=run(build,'report')
    assert p.returncode==0,p.stdout
    assert len(p.stdout.splitlines())<=25 and not (build.parent/'.current').exists()
    text=(build/'report.md').read_text(); assert 'created 2' in text and 'Sync' in text

def test_fr27_report_usage_line(build):
    completed(build); p=run(build,'report'); assert p.returncode==0,p.stdout
    line=(build/'report.md').read_text().splitlines()[-1]
    assert line.startswith('Usage: ') and 'calls · peak' in line and 'waste checks 8/8 pass' in line
    assert p.stdout.splitlines()[-1]==line

@pytest.fixture(params=['gate','write','report'])
def command(request,build):
    if request.param=='write': gate(build)
    if request.param=='report': completed(build)
    return build,request.param

def test_g3_status_line_first(command):
    b,c=command; assert run(b,c).stdout.splitlines()[0]=='OK'
def test_g3_stdout_budget(command):
    b,c=command; s=run(b,c).stdout; assert len(s.splitlines()) <= (25 if c=='report' else 40) and len(s)<=2000

def test_g4_exit_codes_mapped(command):
    b,c=command; r=run(b,c); assert r.returncode==0 and r.stdout.startswith('OK\n')
    r=cli(c,'--build',b,'--force'); assert r.returncode==2 and 'ERROR' in r.stdout

def test_g5_rerun_identical(command):
    b,c=command; assert run(b,c).returncode==0
    def content():
        return {str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file() and p.name not in ('log.jsonl','cost.json','cost.md')}
    before=content(); assert run(b,c).returncode==0; assert content()==before

def test_g6_no_writes_outside_build(command):
    b,c=command; sentinel=b.parent/'unrelated'; sentinel.write_text('keep')
    before={p:p.read_bytes() for p in b.parent.rglob('*') if p.is_file() and not p.is_relative_to(b) and p.name!='.current'}
    assert run(b,c).returncode==0
    after={p:p.read_bytes() for p in b.parent.rglob('*') if p.is_file() and not p.is_relative_to(b) and p.name!='.current'}
    assert after==before

def test_g7_provenance_present(command):
    b,c=command; assert run(b,c).returncode==0
    p={'gate':'gate.json','write':'write/expected.json','report':'report.md'}[c]
    text=(b/p).read_text(); assert ('_meta' in text if c!='report' else text.startswith('<!-- cards report '))
    if c=='write':
        manifest=load(b,'write/provenance.json'); assert set(manifest['_meta'])=={'tool','version','created'}
        assert manifest['_meta']['tool']=='cards write'
        from hashlib import sha256
        assert all(sha256((b/p).read_bytes()).hexdigest()==h for p,h in manifest['artifacts'].items())
    elif c=='gate': assert set(load(b,'gate.json')['_meta'])=={'tool','version','created'}
    else: assert 'cards report 0.' in text and load(b,'usage/cost.json')['_meta']['tool']=='cards meter'

def test_g10_help_short(command):
    _,c=command; p=cli(c,'--help'); assert p.returncode==0 and len(p.stdout.splitlines())<=20


def test_report_waste_findings(build,monkeypatch):
    completed(build)
    monkeypatch.setenv('CLAUDE_SESSION_ID',str(Path('tests/fixtures/transcripts/w4.jsonl').resolve()))
    r=run(build,'report'); assert r.returncode==1 and r.stdout.startswith('FINDINGS\n')
    assert 'W-4 failed' in (build/'report.md').read_text().splitlines()[-1]
