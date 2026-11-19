"""Durable intent, exact dispatch, readback and restart recovery via real product stores."""
import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow, covered, run
from test_workflow_quality import quality_ready


def approved(workflow):
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow)
    c.authorize(r.id,p.digest,'user')
    from test_verified_onboarding import setup_ready
    setup_ready(workflow)
    return p


def test_intent_is_durable_before_send_and_create_readback_reports_real_units(workflow):
    c,s,e,r,d=workflow;p=approved(workflow)
    def before(op,args):
        assert any(x.kind=='operation_intent' and x.payload['operation']==op and x.payload['arguments']==args for x in c.runs.read(r.id).events)
    e.before_send=before
    result=run(c.apply(r.id,p.digest))
    assert result['results'][0]['status']=='confirmed'
    assert result['results'][0]['note_ids']==[101]
    assert result['results'][0]['card_ids']==[201]
    assert result['counts']['notes_created']==1
    assert len(e.sent)==1
    replay=run(c.apply(r.id,p.digest))
    assert replay['results']==result['results'] and len(e.sent)==1


def test_lost_create_acknowledgement_stays_uncertain_and_never_resends(workflow):
    c,s,e,r,d=workflow;p=approved(workflow);e.drop=True
    result=run(c.apply(r.id,p.digest))
    assert result['results'][0]['status']=='uncertain' and len(e.notes)==1
    from ankiplusmcp.coordinator import Coordinator
    fresh=Coordinator(s)
    assert run(fresh.reconcile(r.id))['results'][0]['status']=='uncertain'
    assert run(fresh.apply(r.id,p.digest))['results'][0]['status']=='uncertain'
    assert len(e.sent)==1
    with pytest.raises(DomainError,match='UNCERTAIN'):run(fresh.stage(r.id))


def test_acknowledged_create_recovers_known_identity_without_a_second_send(workflow,monkeypatch):
    c,s,e,r,d=workflow;p=approved(workflow)
    original=c._verify
    async def crash(*args):raise KeyboardInterrupt('synthetic process death before readback')
    monkeypatch.setattr(c,'_verify',crash)
    with pytest.raises(KeyboardInterrupt):run(c.apply(r.id,p.digest))
    monkeypatch.setattr(c,'_verify',original)
    assert any(x.kind=='operation_ack' for x in c.runs.read(r.id).events)
    result=run(c.reconcile(r.id))
    assert result['results'][0]['status']=='confirmed'
    assert result['results'][0]['note_ids']==[101]
    assert len(e.sent)==1


def test_changed_collection_before_send_is_conflict_with_no_mutation(workflow):
    c,s,e,r,d=workflow;p=approved(workflow);e.binding['collection_session']='s2'
    result=run(c.apply(r.id,p.digest))
    assert result['results'][0]['status']=='conflict'
    assert not e.sent


def test_changed_fields_after_authorization_refuse_apply(workflow):
    c,s,e,r,d=workflow;p=approved(workflow)
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'Changed'}}}],1)
    with pytest.raises(DomainError,match='STALE'):run(c.apply(r.id,p.digest))
    assert not e.sent


def test_tier_three_resolves_created_card_ids_then_suspends_and_verifies(workflow):
    c,s,e,r,d=workflow
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'tier':3}}],1)
    p=approved(workflow);result=run(c.apply(r.id,p.digest))
    assert e.cards[201]['queue']==-1
    assert [op for op,a in e.sent]==['add_note','card_suspend']
    assert result['counts']['notes_created']==1 and result['counts']['cards_suspended']==1
    assert all(v['status']=='confirmed' for v in result['results'])


def test_repeat_run_reuses_verified_mapping_instead_of_creating_again(workflow):
    c,s,e,r,d=workflow;p=approved(workflow);run(c.apply(r.id,p.digest))
    second=c.start(r.workspace,[1]);run(c.coverage(second.id,'collagen',[d]))
    next_p=run(c.stage(second.id))
    assert next_p.decisions[0]['disposition']=='already_covered'
    assert next_p.decisions[0]['chosen_note_ids']==[101]
    assert not next_p.operations and len(e.sent)==1


def test_tier_three_repeat_does_not_unsuspend_the_prior_mapping(workflow):
    c,s,e,r,d=workflow;s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'tier':3}}],1)
    p=approved(workflow);run(c.apply(r.id,p.digest))
    second=c.start(r.workspace,[1]);run(c.coverage(second.id,'collagen',[d]));next_p=run(c.stage(second.id))
    assert next_p.decisions[0]['disposition']=='pending'
    assert e.cards[201]['queue']==-1 and len(e.notes)==1


def test_already_unsuspended_after_review_is_unchanged_not_sent(workflow):
    c,s,e,r,d=workflow
    e.notes[101]={'fields':{'Front':'What makes collagen?','Back':'Fibroblasts'},'tags':['#AnkiPlus::Cells']}
    e.cards[201]=dict(id=201,nid=101,did=1,ord=0,queue=-1,type=0,due=0,mod=1,backend_sha256='b'*64)
    d.update(disposition='propose_unsuspend',candidate_note_ids=[101],chosen_note_ids=[101],card_ids=[201])
    p=approved(workflow);e.cards[201]['queue']=0
    result=run(c.apply(r.id,p.digest))
    assert result['results'][0]['status']=='unchanged' and not e.sent


def test_preflight_failure_is_durably_failed_without_a_send_or_uncertain_intent(workflow):
    c,s,e,r,d=workflow;p=approved(workflow)
    original=e.call_tool
    async def unavailable(name,args):
        if name=='student_operation_state':raise TimeoutError('offline before conditional dispatch')
        return await original(name,args)
    e.call_tool=unavailable
    result=run(c.apply(r.id,p.digest))
    assert result['results'][0]['status']=='failed'
    assert result['results'][0]['delivery']=='not_sent'
    assert not c.unresolved() and not e.sent


def test_recovered_acknowledged_create_restores_mapping_for_repeat_run(workflow,monkeypatch):
    c,s,e,r,d=workflow;p=approved(workflow)
    original=c._verify
    async def crash(*args):raise KeyboardInterrupt()
    monkeypatch.setattr(c,'_verify',crash)
    with pytest.raises(KeyboardInterrupt):run(c.apply(r.id,p.digest))
    monkeypatch.setattr(c,'_verify',original)
    run(c.reconcile(r.id))
    second=c.start(r.workspace,[1]);run(c.coverage(second.id,'collagen',[d]))
    assert run(c.stage(second.id)).decisions[0]['disposition']=='already_covered'
    assert len(e.sent)==1


def test_tier_child_failure_is_visible_in_partial_summary(workflow):
    c,s,e,r,d=workflow;s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'tier':3}}],1)
    p=approved(workflow);original=e.call_tool
    async def unavailable(name,args):
        if name=='student_operation_state' and args['operation']=='card_suspend':raise TimeoutError()
        return await original(name,args)
    e.call_tool=unavailable
    result=run(c.apply(r.id,p.digest))
    assert result['counts']['notes_created']==1
    assert result['counts']['failed_operations']==1
    assert result['counts']['cards_suspended']==0
    assert len(e.sent)==1
