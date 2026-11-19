"""Verified milestones use real local checks; external host evidence is synthetic in tests."""
import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow,run


def test_onboarding_resumes_storage_and_guide_without_claiming_external_checks(workflow):
    from ankiplusmcp.onboarding import Onboarding
    c,s,e,r,d=workflow;o=Onboarding(s)
    first=run(o.advance('storage',{}))
    assert 'storage' not in first.remaining_checks and not first.onboarding_complete
    saved=run(o.advance('guide',{}))
    from pathlib import Path
    assert Path(saved.guide_path).is_file()
    assert not saved.onboarding_complete
    resumed=Onboarding(s).status()
    assert resumed.guide_path==saved.guide_path and 'storage' not in resumed.remaining_checks
    assert {'connection','interactive_review','quality_runtime'}<=set(resumed.remaining_checks)


def test_caller_assertions_cannot_complete_onboarding(workflow):
    from ankiplusmcp.onboarding import Onboarding
    c,s,e,r,d=workflow;o=Onboarding(s)
    for step in ('connection','interactive_review','quality_runtime'):
        result=run(o.advance(step,{'verified':True,'passed':True}))
        assert not result.onboarding_complete and step in result.remaining_checks


def test_no_premade_deck_custom_sources_and_confirmed_preferences_survive_resume(workflow):
    from ankiplusmcp.onboarding import Onboarding
    c,s,e,r,d=workflow
    cfg=c.config.read();c.config.confirm(c.config.propose({'selected_decks':[],'source_materials':['custom notes and images']},cfg.config_version).id)
    o=Onboarding(s);run(o.advance('storage',{}));status=run(o.advance('guide',{}))
    assert status.configuration.selected_decks==[]
    from pathlib import Path
    assert 'custom notes and images' in Path(status.guide_path).read_text()
    assert not status.onboarding_complete


def test_connection_milestone_uses_real_adapter_checks_and_failure_preserves_other_progress(workflow):
    from ankiplusmcp.onboarding import Onboarding
    c,s,e,r,d=workflow;o=Onboarding(s);run(o.advance('storage',{}))
    # Extend only external discovery/metadata; the onboarding implementation is real.
    original_list=e.list_tools;original_call=e.call_tool
    async def listed():
        from types import SimpleNamespace
        result=await original_list()
        result.tools.extend(SimpleNamespace(name=n) for n in ('model_field_names','model_templates','model_styling'))
        return result
    async def called(name,args):
        from types import SimpleNamespace
        if name=='model_field_names':value={'model_name':'Basic','field_names':['Front','Back']}
        elif name=='model_templates':value={'model_name':'Basic','templates':{'Card 1':{'Front':'{{Front}}','Back':'{{Back}}'}}}
        elif name=='model_styling':value={'model_name':'Basic','css':'.card{}'}
        else:return await original_call(name,args)
        return SimpleNamespace(isError=False,structuredContent=value)
    e.list_tools=listed;e.call_tool=called
    result=run(o.advance('connection',{}))
    assert 'connection' not in result.remaining_checks
    e.binding['profile_name']='Other'
    failed=run(o.advance('connection',{}))
    assert 'connection' in failed.remaining_checks and 'storage' not in failed.remaining_checks
    assert not failed.onboarding_complete


def test_setup_facade_reports_verified_milestones_without_caller_completion_flags(workflow):
    from ankiplusmcp.server import API
    c,s,e,r,d=workflow;api=API(s)
    result=run(api.advance_student_setup('storage',{}))
    assert 'storage' not in result['remaining_checks']
    assert api.get_student_setup()['configuration']['onboarding_complete'] is False
    result=run(api.advance_student_setup('guide',{}))
    assert result['guide_path'] and not result['ready_to_apply']


def test_apply_requires_verified_setup_in_addition_to_quality_and_approval(workflow):
    from test_coordinator import covered
    from test_workflow_quality import quality_ready
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow);c.authorize(r.id,p.digest,'user')
    with pytest.raises(DomainError,match='SETUP'):run(c.apply(r.id,p.digest))
    assert not e.sent



def setup_ready(workflow):
    """Synthetic trusted host observer; invokes real milestone implementations."""
    import hashlib,hmac
    from ankiplusmcp.onboarding import Onboarding
    from ankiplusmcp.quality import QualityGate
    from ankiplusmcp.review_session import ReviewSession
    from ankiplusmcp.review_app import html
    from ankiplusmcp.runs import _encoded
    c,s,e,r,d=workflow;o=Onboarding(s)
    run(o.advance('preferences',{}));run(o.advance('storage',{}));run(o.advance('connection',{}))
    run(o.advance('quality_runtime',{'run_id':r.id}))
    page=run(ReviewSession(c).open(r.id))
    receipt={'run_id':r.id,'session_token_sha256':hashlib.sha256(page['session_token'].encode()).hexdigest(),
        'resource_sha256':hashlib.sha256(html().encode()).hexdigest(),'bridge_version':'2.0.4','runtime':'SYNTHETIC TEST OBSERVER',
        'observations':{'initialize':True,'tool_call':True,'readback':True,'reconnect':True}}
    gate=QualityGate(c)
    receipt['attestation']=hmac.new(gate.key_path.read_bytes(),_encoded({'purpose':'interactive-review','receipt':receipt}),hashlib.sha256).hexdigest()
    run(o.advance('interactive_review',receipt));result=run(o.advance('guide',{}))
    assert result.onboarding_complete, result.model_dump()
    return result


def test_confirmed_preference_replay_survives_verified_health_progress(workflow):
    from ankiplusmcp.server import API
    from ankiplusmcp.onboarding import Onboarding
    c,s,e,r,d=workflow;api=API(s)
    cfg=c.config.read();change=api.propose_preferences({'source_materials':['custom notes']},cfg.config_version)
    api.confirm_preferences(change['id']);run(Onboarding(s).advance('storage',{}))
    saved=api.confirm_preferences(change['id'])
    assert saved['configuration']['source_materials']==['custom notes']


def test_setup_cannot_complete_without_explicitly_confirmed_interview_choices(tmp_path):
    from ankiplusmcp.service import Service
    from ankiplusmcp.onboarding import Onboarding
    s=Service(tmp_path/'fresh',[tmp_path])
    try:
        status=Onboarding(s).status()
        assert 'preferences' in status.remaining_checks
        proposal=Onboarding(s).propose_choices({})
        assert proposal['scope']=='future_preferences'
        from ankiplusmcp.server import API
        result=API(s).confirm_preferences(proposal['id'])
        assert 'preferences' not in result['remaining_checks']
        assert not result['configuration']['onboarding_complete']
    finally:s.close()


def test_setup_can_inspect_own_decks_without_requiring_a_premade_deck(workflow):
    from types import SimpleNamespace
    from ankiplusmcp.server import API
    c,s,e,r,d=workflow;original=e.list_tools;call=e.call_tool
    async def tools():
        value=await original();value.tools.append(SimpleNamespace(name='list_decks'));return value
    async def response(name,args):
        if name=='list_decks':return SimpleNamespace(isError=False,structuredContent={'decks':[{'deck_id':1,'name':'My Lecture','is_filtered':False},{'deck_id':2,'name':'Filtered','is_filtered':True}],'total':2})
        return await call(name,args)
    e.list_tools=tools;e.call_tool=response
    result=run(API(s).get_collection_choices())
    assert result['decks'][0]['name']=='My Lecture'
    assert result['decks'][0]['eligible_for_scope'] is True
    assert result['decks'][1]['eligible_for_scope'] is False
    assert not e.sent
