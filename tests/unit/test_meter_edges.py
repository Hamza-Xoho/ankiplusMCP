"""Edge cases not pinned in the phase acceptance table."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
def cli(cwd,*args):
    return subprocess.run([sys.executable,'-m','cards',*map(str,args)],cwd=cwd,
        env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1'),text=True,capture_output=True)

FIX=ROOT/'tests/fixtures/transcripts'

def call(i,ctx=1000):
    r=json.loads((FIX/'clean.jsonl').read_text()); r['message']['id']=f'm{i}'
    r['message']['usage']['input_tokens']=ctx
    return r

def dump(p, rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))

def run(tmp,p,*args):
    return cli(tmp,'meter','--session',p,'--out',tmp/'out',*args)

def test_streamed_final_usage_and_tool_blocks(tmp_path):
    a=call(1); b=call(1)
    b['message']['usage']['output_tokens']=99
    b['message']['content']=[{'type':'tool_use','id':'t1','name':'Read','input':{'file_path':'text.txt'}}]
    p=tmp_path/'stream.jsonl'; dump(p,[a,b,b])
    assert run(tmp_path,p).returncode==0
    d=json.loads((tmp_path/'out/cost.json').read_text())
    assert d['totals']['output']==99 and d['calls'][0]['tools']==['Read']

def test_error_retry_is_chronological(tmp_path):
    a=call(1); a['message']['content']=[{'type':'tool_use','id':'t1','name':'Read','input':{'file_path':'x.txt'}}]
    b=call(2); b['message']['content']=[{'type':'tool_use','id':'t2','name':'Read','input':{'file_path':'x.txt'}}]
    result={'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'t1','is_error':True,'content':'Error unavailable'}]}}
    p=tmp_path/'retry.jsonl'; dump(p,[a,result,b])
    assert run(tmp_path,p).returncode==1
    d=json.loads((tmp_path/'out/cost.json').read_text())
    assert [k for k,v in d['waste'].items() if not v['pass']]==['W-5']

def test_cache_lifetimes_and_subagent_cost():
    from cards.meter.prices import cost
    c={'model':'claude-sonnet-4-6','input':100,'cache_write':30,'cache_1h':10,'cache_5m':20,'cache_read':40,'output':50}
    assert cost([c,c])['usd']==.002394

def test_build_allows_only_explicitly_flagged_images(tmp_path):
    p=tmp_path/'source.jsonl'; dump(p,[json.loads(x) for x in (FIX/'w2.jsonl').read_text().splitlines()])
    b=tmp_path/'build'; (b/'source').mkdir(parents=True)
    (b/'source/slides.json').write_text(json.dumps({'slides':[{'n':1,'flags':['image_only']}]}))
    r=json.loads(p.read_text().splitlines()[0]); r['message']['content'][0]['input']['pages']='1'
    dump(p,[r,json.loads(p.read_text().splitlines()[1])])
    assert run(tmp_path,p,'--build',b).returncode==0
    r['message']['content'][0]['input']['pages']='1-2'; dump(p,[r,json.loads(p.read_text().splitlines()[1])])
    assert run(tmp_path,p,'--build',b).returncode==1

def test_build_allows_only_lint_flagged_sheet(tmp_path):
    b=tmp_path/'build'; (b/'checks').mkdir(parents=True)
    (b/'checks/check.json').write_text(json.dumps({'findings':[{'file':'renders/sheets/front-1.png'}]}))
    assert run(tmp_path,FIX/'w7.jsonl','--build',b).returncode==0
    (b/'checks/check.json').write_text(json.dumps({'findings':[]}))
    assert run(tmp_path,FIX/'w7.jsonl','--build',b).returncode==1

def test_latest_project_slug_and_p0_cutoff(tmp_path, monkeypatch):
    from argparse import Namespace
    from cards.meter import resolve
    from cards.common.errors import CardsError
    import pytest
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    project=tmp_path/'Cards α'; slug=__import__('re').sub(r'[^a-zA-Z0-9]','-',str(project))
    folder=tmp_path/'.claude/projects'/slug
    a=folder/'old.jsonl'; b=folder/'new.jsonl'
    dump(a,[call(1)]); dump(b,[call(2)])
    os.utime(a,(10,10)); os.utime(b,(30,30))
    args=Namespace(session=None,latest=str(project))
    assert resolve(args,{})==b
    assert resolve(args,{'history':[{'phase':'P0','started_at':'1970-01-01T00:00:20Z'}]})==b
    with pytest.raises(CardsError): resolve(args,{'history':[{'phase':'P0','started_at':'1970-01-01T00:00:40Z'}]})

def test_invalid_content_reports_field(tmp_path):
    r=call(1); r['message']['content']=[None]
    p=tmp_path/'bad.jsonl'; dump(p,[r])
    result=run(tmp_path,p)
    assert result.returncode==2 and 'line 1' in result.stdout and 'content' in result.stdout
    assert not result.stderr

def test_invalid_build_history_reports_field(tmp_path):
    b=tmp_path/'build'; b.mkdir(); (b/'build.json').write_text(json.dumps({'history':[{}]}))
    result=run(tmp_path,FIX/'clean.jsonl','--build',b)
    assert result.returncode==2 and 'build.json' in result.stdout and 'history' in result.stdout
    assert not result.stderr

def test_log_must_not_modify_transcript(tmp_path):
    b=tmp_path/'build'; b.mkdir(); p=b/'log.jsonl'; dump(p,[call(1)])
    before=p.read_bytes()
    result=run(tmp_path,p,'--build',b)
    assert result.returncode==2 and 'overlap' in result.stdout
    assert p.read_bytes()==before

def test_malformed_user_and_tool_arguments_are_located(tmp_path):
    cases=[({'type':'user','message':None},'message'),
           ({'type':'attachment','attachment':None},'attachment')]
    malformed=call(2)
    malformed['message']['content']=[{'type':'tool_use','name':'Read','id':'t2','input':{'file_path':None}}]
    cases.append((malformed,'file_path'))
    for row,field in cases:
        p=tmp_path/'invalid.jsonl'; dump(p,[call(1),row])
        result=run(tmp_path,p)
        assert result.returncode==2 and field in result.stdout and 'line 2' in result.stdout
        assert not result.stderr
