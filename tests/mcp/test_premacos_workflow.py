import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/smoke-premacos.py'


def test_unicode_path_rehearsal(tmp_path):
    output=tmp_path/'results.json'
    completed=subprocess.run([sys.executable,str(SCRIPT),'--output',str(output)],text=True,capture_output=True,timeout=120)
    assert completed.returncode==0,completed.stderr
    report=json.loads(output.read_text())
    assert report['schema_version']==1 and report['performed_anki_operations']==0
    assert report['status']=='local_refactor_verified'
    assert set(report['scenarios'])=={'chapter_resume','draft_render','coverage_history','real_ocr','stdio'}
    assert all(v['status']=='passed' for v in report['scenarios'].values())
    assert report['desktop_compatibility']=='not_run'


def test_smoke_refuses_existing_output(tmp_path):
    output=tmp_path/'keep';output.write_text('keep')
    result=subprocess.run([sys.executable,str(SCRIPT),'--output',str(output)],capture_output=True,timeout=10)
    assert result.returncode==2 and output.read_text()=='keep'


def test_smoke_missing_dependency_fails(tmp_path):
    output=tmp_path/'failure.json'
    env={**os.environ,'PATH':'/nonexistent'}
    result=subprocess.run([sys.executable,str(SCRIPT),'--output',str(output)],env=env,capture_output=True,timeout=120)
    assert result.returncode==1
    report=json.loads(output.read_text()); assert report['status']=='failed'
    assert report['scenarios']['real_ocr']['status']=='failed'
    assert 'error' in report['scenarios']['real_ocr']


def test_smoke_failed_scenario_exits_one(tmp_path):
    output=tmp_path/'failure.json'
    code="import importlib.util; spec=importlib.util.spec_from_file_location('smoke',"+repr(str(SCRIPT))+"); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.run_scenarios=lambda root:{'chapter_resume':{'status':'failed','error':'injected'}};raise SystemExit(m.main(['--output',"+repr(str(output))+"]))"
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=10)
    assert result.returncode==1,result.stderr
    assert json.loads(output.read_text())['status']=='failed'
