import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from p3_helpers import cli, dump, drafts, records, setup, note, convert_v1

@pytest.fixture
def b(tmp_path):
    return setup(tmp_path/'build')

def check(b):
    r=cli('check','--build',b)
    assert r.returncode in (0,1),r.stdout+r.stderr
    return r,json.loads((b/'checks/check.json').read_text())

def test_fr11_clean_one_line(b):
    r,d=check(b)
    assert r.returncode==0 and r.stdout.splitlines()[0]=='OK'
    assert len(r.stdout.splitlines())==2 and 'notes=2' in r.stdout
    assert d['findings']==[] and d['stats']['cards']==2

@pytest.mark.parametrize('code',[f'L{i:02}' for i in range(1,14)])
def test_fr11_lint_detects(b,code):
    fault=next(n for n in records(Path('tests/fixtures/drafts_broken.jsonl')) if n.get('fault')==code)
    n=note(); n.update({k:v for k,v in fault.items() if k not in ('fault','id')})
    drafts(b,[n,note(2,3)])
    r,d=check(b)
    found=[f for f in d['findings'] if f['code']==code]
    assert r.returncode==1 and found
    assert found[0]['severity']==('blocker' if code in ('L03','L04','L05','L06','L10') else 'warn')
    assert found[0]['note_id']=='n001'

@pytest.mark.parametrize('code',[f'S{i:02}' for i in range(1,10)])
def test_fr11_schema_errors_located(b,code):
    fault=next(n for n in records(Path('tests/fixtures/drafts_broken.jsonl')) if n.get('fault')==code)
    n=note(); n.update({k:v for k,v in fault.items() if k not in ('fault',)})
    if code=='S01': n.pop('fields')
    drafts(b,[n,note(2,3)])
    r,d=check(b)
    fs=[f for f in d['findings'] if f['code']==code]
    assert r.returncode==1 and fs
    assert fs[0]['file'].endswith('drafts.jsonl') and fs[0]['line']==1 and fs[0]['field']
    assert fs[0]['severity']=='blocker'

def test_fr11_uncovered_slide(b):
    d=json.loads((b/'source/slides.json').read_text()); d['slides'].append({'n':2,'title':'Other','text':'Else','figures':[]})
    dump(b/'source/slides.json',d)
    r,d=check(b); assert d['coverage']['slides_uncovered']==[2] and r.returncode==1
    (b/'skipped.jsonl').write_text(json.dumps({'slide':2,'item':'aside','reason':'out_of_scope'})+'\n')
    assert check(b)[1]['coverage']['slides_uncovered']==[]

def test_fr11_objective_without_t1(b):
    dump(b/'source/objectives.json',{'objectives':[{'id':'ILO1','text':'Describe subject'},{'id':'ILO2','text':'Describe other'}]})
    assert check(b)[1]['coverage']['objectives_without_t1']==['ILO2']

def test_fr11_enumeration_objective_below_t1(b):
    ns=[note(1,2),note(2,3)]; drafts(b,ns)
    dump(b/'source/objectives.json',{'objectives':[{'id':'ILO1','text':'Enumerate the structures'}]})
    assert check(b)[1]['coverage']['objective_enumerations_below_t1']==['ILO1']

def test_fr11_tier3_share_warning(b):
    drafts(b,[note()]); _,d=check(b)
    assert d['stats']['tier3_share']==0
    assert any(f['code']=='C04' and f['severity']=='warn' for f in d['findings'])

def test_fr11_foreign_tag_blocker(b):
    n=note(); n['tags'].append('foreign::tag'); drafts(b,[n,note(2,3)])
    assert any(f['code']=='L10' and f['severity']=='blocker' for f in check(b)[1]['findings'])

def test_fr8_v1_l006_drafts_convert_and_validate(b,private_fixture):
    ns=convert_v1(private_fixture('l006_v1_drafts.jsonl'))
    original=records(private_fixture('l006_v1_drafts.jsonl'))
    assert len(ns)==40 and [n['fields'] for n in ns]==[n['fields'] for n in original]
    dump(b/'source/slides.json',{'slides':[{'n':i,'title':'','text':'','figures':[]} for i in range(1,25)]})
    dump(b/'source/objectives.json',{'objectives':[{'id':'ILO1','text':'Enumerate'},{'id':'ILO2','text':'Describe'}]})
    drafts(b,ns); _,d=check(b)
    assert not [f for f in d['findings'] if f['code'].startswith('S')]
    assert d['stats']['notes']==40

def test_malformed_json_exit2(b):
    (b/'drafts.jsonl').write_text('{}\n{\n')
    r=cli('check','--build',b)
    assert r.returncode==2 and 'line 2' in r.stdout and 'drafts.jsonl' in r.stdout

def test_nonscalar_schema_and_dropped_coverage(b):
    (b/'drafts.jsonl').write_text('null\n[]\n42\n')
    r,d=check(b); assert len(d['findings'])>=3
    n=note(); n['status']='dropped'; drafts(b,[n])
    assert check(b)[1]['coverage']['slides_uncovered']==[1]
