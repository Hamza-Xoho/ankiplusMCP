"""The compatibility harness must not be confused with production host acceptance."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'scripts/prepare-desktop-experiment.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def prepared(tmp_path):
    return load(SCRIPT,'prepare_experiment').prepare(tmp_path/'Study notes — اختبار')


def test_preparation_is_exclusive_and_does_not_register_a_host(tmp_path):
    report=prepared(tmp_path);root=Path(report['root'])
    assert report['performed_anki_operations']==0
    assert report['desktop_compatibility']=='not_run'
    assert report['reviewer_execution']=='not_run'
    assert not (root/'host-evidence.json').exists()
    before=(root/'probe_server.py').read_bytes()
    with pytest.raises(FileExistsError):load(SCRIPT,'again').prepare(root)
    assert (root/'probe_server.py').read_bytes()==before
    config=json.loads((root/'registration.json').read_text())
    assert set(config['mcpServers'])=={'ankiplus-compat-probe'}
    assert config['mcpServers']['ankiplus-compat-probe']['command']==sys.executable


def test_probe_rejects_stale_or_invalid_decisions_without_writing(tmp_path):
    report=prepared(tmp_path);root=Path(report['root']);module=load(root/'probe_server.py','probe_state')
    state=module.ProbeState(root/'data')
    first=state.read();assert first['revision']==0
    edited=state.decide(0,[{'id':'sample-a','selected':False,'text':'Edited sample'}])
    assert edited['revision']==1 and edited['cards'][0]['selected'] is False
    assert module.ProbeState(root/'data').read()==edited
    for revision,decisions in [(0,[{'id':'sample-a','selected':True,'text':'stale'}]),
        (1,[{'id':'unknown','selected':True,'text':'invalid'}]),
        (1,[{'id':'sample-a','selected':True,'text':''}])]:
        with pytest.raises(ValueError):state.decide(revision,decisions)
        assert state.read()==edited


def test_probe_stdio_resource_ui_metadata_and_distinct_content_channels(tmp_path):
    root=Path(prepared(tmp_path)['root'])
    # A placeholder is enough for the protocol test; bundle/build is a separate real gate.
    (root/'review.html').write_text('<!doctype html><title>Synthetic probe</title>')
    async def run():
        entry=json.loads((root/'.mcp.json').read_text())['mcpServers']['ankiplus-compat-probe']
        params=StdioServerParameters(command=entry['command'],args=entry['args'],env=dict(os.environ))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize();listed=await session.list_tools();tools={t.name:t for t in listed.tools}
                assert tools['open_sample_review'].meta['ui']['resourceUri']=='ui://ankiplus-probe/review.html'
                assert tools['open_sample_review'].meta['ui/resourceUri']=='ui://ankiplus-probe/review.html'
                resource=await session.read_resource('ui://ankiplus-probe/review.html')
                assert resource.contents[0].mimeType=='text/html;profile=mcp-app'
                channels=await session.call_tool('observe_content_channels',{})
                assert channels.content[0].text=='TEXT_CHANNEL_ONLY: indigo'
                assert channels.structuredContent=={'STRUCTURED_CHANNEL_ONLY':'copper'}
                opened=await session.call_tool('open_sample_review',{});assert opened.structuredContent['revision']==0
                result=await session.call_tool('save_sample_decisions',{'expected_revision':0,'decisions':[{'id':'sample-a','selected':False,'text':'edited'}]})
                assert result.structuredContent['revision']==1 and not result.isError
                stale=await session.call_tool('save_sample_decisions',{'expected_revision':0,'decisions':[]})
                assert stale.isError
    asyncio.run(run())
    assert json.loads((root/'data/state.json').read_text())['revision']==1


def test_missing_ui_bundle_is_an_explicit_failure(tmp_path):
    root=Path(prepared(tmp_path)['root'])
    result=subprocess.run([sys.executable,str(root/'probe_server.py'),'--check'],capture_output=True,text=True)
    assert result.returncode==2 and 'bundle' in result.stderr.lower()


def test_prepared_report_does_not_invent_companion_capabilities(tmp_path):
    root=Path(prepared(tmp_path)['root'])
    report=json.loads((root/'experiment.json').read_text())
    assert report['companion']['status']=='not_run' and report['companion']['operations']==[]
    assert report['independent_reviewers']['status']=='not_run'
    assert 'mutation_authorization' in report['companion']


def test_synthetic_reviewer_packets_preserve_rubrics_and_separate_inputs(tmp_path):
    module=load(SCRIPT,'reviewer_preparation');root=Path(prepared(tmp_path)['root'])
    info=module.prepare_reviewers(root)
    from cards.review.packets import TEMPLATES
    maintainer=Path(info['maintainer']);student=Path(info['student'])
    for role,path in [('maintainer',maintainer),('student',student)]:
        for name in ('rubric.md','brief.md','report-format.md'):
            assert (path/name).read_bytes()==(TEMPLATES/role/name).read_bytes()
        assert not (path/'EXPECTATIONS.md').exists()
    assert (maintainer/'source_slices.md').is_file()
    assert not (student/'source_slices.md').exists() and not (student/'drafts.jsonl').exists()
    sheets=json.loads((student/'sheets.json').read_text())['sheets']
    assert sheets and (student/sheets[0]['fronts']).read_bytes().startswith(b'\x89PNG')
    assert sheets[0]['fronts']!=sheets[0]['backs']
    for role,effort in [('maintainer','high'),('student','medium')]:
        agent=(root/'.claude/agents'/f'compat-{role}.md').read_text()
        assert 'model: claude-sonnet-5-5' in agent and f'effort: {effort}' in agent
        assert 'mcp__anki__' not in agent
        assert agent.split('---',2)[2]==(ROOT/f'.claude/agents/anki-{role}.md').read_text().split('---',2)[2]
        assert f'Use compat-{role}.' in (Path(info[role])/'PROMPT.md').read_text()
    assert info['independently_verified'] is False


def test_schema_measurement_is_utf8_bytes_and_not_a_tokenizer():
    checker=load(ROOT/'scripts/check-desktop-experiment.py','check_experiment')
    measured=checker.schema_measurement([{'name':'اختبار','inputSchema':{'type':'object'}}])
    assert measured['tool_count']==1
    assert measured['utf8_bytes']==len(json.dumps([{'name':'اختبار','inputSchema':{'type':'object'}}],ensure_ascii=False,separators=(',',':')).encode())
    assert measured['tokenizer']=='not_measured'
    assert measured['host_context_loading']=='not_measured'


def test_probe_manifest_identifies_generated_files_and_dirty_source(tmp_path):
    import hashlib
    report=prepared(tmp_path);root=Path(report['root'])
    assert type(report['source_dirty']) is bool
    assert report['generated_sha256']['probe_server.py']==hashlib.sha256((root/'probe_server.py').read_bytes()).hexdigest()
    template=json.loads((root/'HOST-RESULTS.template.json').read_text())
    assert template['overall_status']=='not_run'
    assert template['companion']['writes']=='not_authorized'
    assert template['surfaces']['chat']['embedded_review']=='not_run'


def test_reviewer_probe_cannot_claim_blind_recall_from_parallel_sheets(tmp_path):
    module=load(SCRIPT,'blind_recall_preparation');root=Path(prepared(tmp_path)['root'])
    info=module.prepare_reviewers(root)
    assert info['blind_recall_evidence']=='blocked_by_existing_parallel_image_packet'
    assert 'Cannot verify blind recall' in (root/'EXPECTATIONS.md').read_text()
    template=json.loads((root/'HOST-RESULTS.template.json').read_text())
    assert template['reviewers']['blind_recall']=='unverified_parallel_front_back_exposure'


def test_preparation_includes_opt_in_project_mcp_registration(tmp_path):
    root=Path(prepared(tmp_path)['root'])
    project=json.loads((root/'.mcp.json').read_text())
    assert (root/'.mcp.json').read_bytes()==(root/'registration.json').read_bytes()
    assert set(project['mcpServers'])=={'ankiplus-compat-probe'}
    entry=project['mcpServers']['ankiplus-compat-probe']
    assert Path(entry['command']).is_absolute()
    assert entry['args']==[str(root/'probe_server.py'),'--data-root',str(root/'data')]


def test_probe_matches_sdk_resource_uri_aliases_and_preserves_app_only_save(tmp_path):
    root=Path(prepared(tmp_path)['root'])
    module=load(root/'probe_server.py','ui_metadata_compatibility')
    async def run():
        server=module.create_server(root/'data')
        from mcp.types import ListToolsRequest
        response=await server.request_handlers[ListToolsRequest](ListToolsRequest(method='tools/list'))
        tools={tool.name:tool for tool in response.root.tools}
        for name in ('open_sample_review','save_sample_decisions'):
            assert tools[name].meta['ui/resourceUri']==tools[name].meta['ui']['resourceUri']=='ui://ankiplus-probe/review.html'
        assert tools['save_sample_decisions'].meta['ui']['visibility']==['app']
        assert not tools['read_sample_state'].meta
    asyncio.run(run())
