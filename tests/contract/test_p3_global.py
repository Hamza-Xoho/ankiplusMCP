"""Reapply the global contracts to every Phase 3 command."""
import json
from pathlib import Path
import re
import sys
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from p3_helpers import cli,dump,setup

@pytest.fixture(params=['check','render','figures'])
def command(request,tmp_path):
    b=setup(tmp_path/'build space é')
    source=tmp_path/'source.txt'; source.write_text('read only source')
    source.chmod(0o444)
    if request.param=='figures':
        (b/'source/figures').mkdir()
        Image.new('RGB',(100,100),'white').save(b/'source/figures/p01_f1.png')
        dump(b/'source/slides.json',{'slides':[{'n':1,'title':'Figure','text':'','figures':[{
            'fig_id':'p01_f1','file':'figures/p01_f1.png','ocr_labels':[
            {'left':.1,'top':.1,'width':.2,'height':.1,'text':'label','group':1}]}]}]})
    args=[request.param,'--build',b]
    if request.param=='figures': args+=['--fig','p01_f1']
    return args,b,source

def test_g3_status_line_first(command):
    r=cli(*command[0]); assert r.stdout.splitlines()[0] in ('OK','FINDINGS','ERROR')

def test_g3_stdout_budget(command):
    r=cli(*command[0]); assert len(r.stdout)<=2000 and len(r.stdout.splitlines())<=40

def test_g4_exit_codes_mapped(command):
    args,b,_=command
    r=cli(*args); assert r.returncode==0,r.stdout+r.stderr
    assert r.stdout.startswith('OK\n')
    r=cli(*args,'--bogus'); assert r.returncode==2 and r.stdout.startswith('ERROR\n')
    r=cli(args[0],'--build',b/'missing',*(['--fig','p01_f1'] if args[0]=='figures' else []))
    assert r.returncode==3 and r.stdout.startswith('ERROR\n')
    if args[0]=='check':
        (b/'drafts.jsonl').write_text('{bad json\n')
        r=cli(*args)
        assert r.returncode==2 and 'line 1' in r.stdout
    elif args[0]=='render':
        r=cli(*args,'--per-sheet','0')
        assert r.returncode==2 and r.stdout.startswith('ERROR\n')
        (b/'drafts.jsonl').unlink()
        r=cli(*args)
        assert r.returncode==3 and 'drafts missing' in r.stdout
    else:
        d=json.loads((b/'source/slides.json').read_text())
        d['slides'][0]['figures'][0]['ocr_labels']=[]
        dump(b/'source/slides.json',d)
        r=cli(*args)
        assert r.returncode==1 and r.stdout.startswith('FINDINGS\n')
        (b/'source/slides.json').unlink()
        r=cli(*args)
        assert r.returncode==3 and 'extract' in r.stdout

def normalized(p):
    if p.suffix in ('.png','.jpg'): return p.read_bytes()
    return re.sub(r'("created":\s*")[^"]+',r'\1TIME',p.read_text())

def test_g5_rerun_identical(command):
    args,b,_=command
    assert cli(*args).returncode in (0,1)
    def snap(): return {str(p.relative_to(b)):normalized(p) for p in b.rglob('*') if p.is_file() and p.name!='log.jsonl'}
    before=snap(); assert cli(*args).returncode in (0,1)
    assert before==snap()

def test_g6_no_writes_outside_build(command):
    args,b,source=command
    def snap(): return {str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in b.parent.rglob('*') if p.is_file() and not p.is_relative_to(b)}
    before=snap(); b.parent.chmod(0o555)
    try:
        r=cli(*args); assert r.returncode in (0,1),r.stdout+r.stderr
        assert snap()==before
    finally: b.parent.chmod(0o755)

def test_g7_provenance_present(command):
    args,b,_=command
    r=cli(*args); assert r.returncode in (0,1),r.stdout+r.stderr
    out={'check':'checks/check.json','render':'renders/sheets.json','figures':'drafts.jsonl'}[args[0]]
    if args[0]=='figures': d=json.loads((b/out).read_text().splitlines()[0])
    else: d=json.loads((b/out).read_text())
    assert d['_meta']['tool']=='cards '+args[0] and d['_meta']['version'] and d['_meta']['created']

def test_g10_help_short(command):
    r=cli(command[0][0],'--help'); assert r.returncode==0 and len(r.stdout.splitlines())<=20
