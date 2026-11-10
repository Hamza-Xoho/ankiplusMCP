import json
from tests.p3_helpers import cli, setup, dump, drafts, note
from tests.contract.test_p4_review import reports

def test_gate_schema_failure_is_structured(tmp_path):
    b=setup(tmp_path/'b'); dump(b/'build.json',{'review':{'round':1}}); reports(b)
    assert cli('apply','--build',b,'--round','1').returncode==0
    drafts(b,[{}])
    r=cli('gate','--build',b)
    assert r.returncode==1 and 'schema' in r.stdout and not r.stderr
    assert json.loads((b/'gate.json').read_text())['status']=='failed'

def test_report_refuses_without_completed_write(tmp_path):
    b=setup(tmp_path/'b'); dump(b/'build.json',{'write':{}})
    r=cli('report','--build',b)
    assert r.returncode==3 and 'write not done' in r.stdout and not (b/'report.md').exists()

def test_import_header_rejects_newline(tmp_path):
    import pytest
    from cards.write.importfile import emit
    from cards.common.errors import CardsError
    with pytest.raises(CardsError): emit(tmp_path/'import.txt',[note()],'Deck\n#tags:injected','Model')
    assert not (tmp_path/'import.txt').exists()

def test_report_multiline_metadata_stays_short(tmp_path,monkeypatch):
    from tests.contract.test_p5_write import completed
    from pathlib import Path
    b=setup(tmp_path/'builds'/'example'); dump(b/'build.json',{'review':{'round':1},'facts':{},'write':{}}); reports(b)
    assert cli('apply','--build',b,'--round','1').returncode==0
    completed(b)
    state=json.loads((b/'build.json').read_text()); state['review']['independent']='\n'.join(['unknown']*30); dump(b/'build.json',state)
    monkeypatch.setenv('CLAUDE_SESSION_ID',str(Path('tests/fixtures/transcripts/clean.jsonl').resolve()))
    r=cli('report','--build',b); assert r.returncode==0 and len(r.stdout.splitlines())<=25

def test_report_refuses_changed_drafts(tmp_path,monkeypatch):
    from tests.contract.test_p5_write import completed
    from pathlib import Path
    b=setup(tmp_path/'builds'/'example'); dump(b/'build.json',{'review':{'round':1},'facts':{},'write':{}}); reports(b)
    assert cli('apply','--build',b,'--round','1').returncode==0
    completed(b)
    monkeypatch.setenv('CLAUDE_SESSION_ID',str(Path('tests/fixtures/transcripts/clean.jsonl').resolve()))
    with (b/'drafts.jsonl').open('a') as f: f.write('\n')
    r=cli('report','--build',b); assert r.returncode==3 and 'stale' in r.stdout

def reviewed(tmp_path):
    b=setup(tmp_path/'b'); dump(b/'build.json',{'review':{'round':1}}); reports(b)
    assert cli('apply','--build',b,'--round','1').returncode==0
    return b

def test_gate_malformed_report_is_structured(tmp_path):
    b=reviewed(tmp_path)
    (b/'review/round1/student_report.jsonl').write_text('[]\n')
    r=cli('gate','--build',b); assert r.returncode==2 and r.stdout.startswith('ERROR\n') and not r.stderr

def test_write_refuses_new_skip_file(tmp_path):
    b=reviewed(tmp_path); (b/'skipped.jsonl').unlink()
    assert cli('gate','--build',b).returncode==0
    (b/'skipped.jsonl').write_text('{}\n')
    r=cli('write','--build',b); assert r.returncode==3 and 'stale' in r.stdout and not (b/'write').exists()

def test_write_refuses_new_incomplete_review_round(tmp_path):
    b=reviewed(tmp_path); assert cli('gate','--build',b).returncode==0
    (b/'review/round2').mkdir()
    state=json.loads((b/'build.json').read_text()); state['review']['round']=2; dump(b/'build.json',state)
    r=cli('write','--build',b); assert r.returncode==3 and 'stale' in r.stdout
