import json,subprocess,sys
from pathlib import Path
from test_coordinator import workflow


def test_onboarding_cli_resumes_real_storage_and_guide_in_selected_data_folder(tmp_path):
    root=tmp_path/'Student data with spaces'
    command=[sys.executable,'-m','ankiplusmcp','onboard','--workspace-root',str(root),'--json']
    first=subprocess.run([*command,'--step','storage'],capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    assert 'storage' not in json.loads(first.stdout)['remaining_checks']
    guide=subprocess.run([*command,'--step','guide'],capture_output=True,text=True)
    assert guide.returncode==0,guide.stderr
    result=json.loads(guide.stdout)
    assert Path(result['guide_path']).is_file() and not result['onboarding_complete']
    resumed=subprocess.run(command,capture_output=True,text=True)
    assert resumed.returncode==0 and json.loads(resumed.stdout)['guide_path']==result['guide_path']


def test_host_evidence_importer_refuses_missing_cumulative_controls(workflow,tmp_path):
    from test_coordinator import covered,run
    from test_sources import wait
    from ankiplusmcp.quality import QualityGate
    from test_workflow_quality import receipt
    c,s,e,r,d=workflow;covered(workflow);wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id))
    ticket=QualityGate(c).prepare(r.id,p.content_digest,'maintainer');value=receipt(ticket,'maintainer')
    del value['launch']['max_turns']
    file=tmp_path/'observed-synthetic.json';file.write_text(json.dumps(value))
    result=subprocess.run([sys.executable,'-m','ankiplusmcp','verify-host-evidence','--workspace-root',str(s.store.root),
        '--kind','quality','--run-id',r.id,'--content-digest',p.content_digest,'--observed-execution',str(file)],capture_output=True,text=True)
    assert result.returncode==2
    assert 'cumulative' in result.stdout or 'cumulative' in result.stderr
    assert not any(e.kind=='quality_accepted' for e in c.runs.read(r.id).events)
