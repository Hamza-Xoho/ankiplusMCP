"""Production review sessions operate on actual run/proposal state."""
import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow, covered, run


def opened(workflow):
    from ankiplusmcp.review_session import ReviewSession
    c,s,e,r,d=workflow;covered(workflow);run(c.stage(r.id))
    sessions=ReviewSession(c)
    return sessions,run(sessions.open(r.id))


def test_review_shows_exact_source_and_persists_exclusion_on_reconnect(workflow):
    c,s,e,r,d=workflow;sessions,page=opened(workflow)
    assert page['items'][0]['source_evidence'][0]['quote']=='Fibroblasts make collagen.'
    updated=run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'exclude'}]))
    assert updated['items'][0]['selected'] is False
    assert not c._latest(r.id).operations
    assert run(sessions.open(r.id))['items'][0]['selected'] is False
    assert not e.sent


def test_review_rejects_forged_session_and_stale_tab(workflow):
    c,s,e,r,d=workflow;sessions,page=opened(workflow)
    with pytest.raises(DomainError,match='SESSION'):run(sessions.decide(r.id,'forged',page['digest'],[{'concept_id':'fibroblast','action':'exclude'}]))
    run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'defer'}]))
    with pytest.raises(DomainError,match='STALE'):run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'keep'}]))


def test_edit_new_rebinds_fields_and_invalidates_prior_quality(workflow):
    from test_workflow_quality import quality_ready
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow);c.authorize(r.id,p.digest,'user')
    from ankiplusmcp.review_session import ReviewSession
    sessions=ReviewSession(c);page=run(sessions.open(r.id))
    changed=run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'edit-new','fields':{'Back':'Edited answer'}}]))
    assert c._latest(r.id).operations[0]['arguments']['fields']['Back']=='Edited answer'
    assert changed['quality_status']=='required'
    with pytest.raises(DomainError,match='STALE'):c.authorize(r.id,p.digest,'user')
    assert not e.sent


def test_existing_text_edit_defaults_to_new_draft_and_explicit_update_is_distinct(workflow):
    c,s,e,r,d=workflow
    e.notes[101]={'fields':{'Front':'Existing prompt','Back':'Existing answer'},'tags':['Premade::Original']}
    e.cards[201]=dict(id=201,nid=101,did=1,ord=0,queue=-1,type=0,due=0,mod=1,backend_sha256='b'*64)
    d.update(disposition='propose_unsuspend',candidate_note_ids=[101],chosen_note_ids=[101],card_ids=[201])
    sessions,page=opened(workflow)
    assert page['items'][0]['existing_notes'][0]['fields']['Back']=='Existing answer'
    assert page['items'][0]['fields']['Back']=='Existing answer'
    changed=run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'edit-new','fields':{'Back':'Adapted answer'},'note_id':101}]))
    op=c._latest(r.id).operations[0]
    assert op['operation']=='add_note' and op['arguments']['fields']['Front']=='Existing prompt'
    assert e.notes[101]['fields']['Back']=='Existing answer'
    changed=run(sessions.decide(r.id,changed['session_token'],changed['digest'],[{'concept_id':'fibroblast','action':'explicit-update','note_id':101,'fields':{'Back':'Explicit answer'}}]))
    assert c._latest(r.id).operations[0]['operation']=='update_note_fields'
    assert e.notes[101]['fields']['Back']=='Existing answer'


@pytest.mark.parametrize('decisions',[[None],[{'concept_id':'fibroblast','action':'edit-new','fields':'malformed'}]])
def test_malformed_review_decisions_are_bounded_domain_errors(workflow,decisions):
    c,s,e,r,d=workflow;sessions,page=opened(workflow)
    with pytest.raises(DomainError):run(sessions.decide(r.id,page['session_token'],page['digest'],decisions))
    assert not e.sent


def test_excluded_draft_technical_findings_do_not_block_unrelated_selected_cards(workflow):
    c,s,e,r,d=workflow
    cards=s.get_cards(r.workspace)['cards']
    s.save_cards(r.workspace,[*cards,dict(id='bad',kind='cloze',notetype='Basic',fields={'Front':'No cloze here','Back':'Invalid draft'},tags=['#AnkiPlus::Synthetic'],source_ref=[1])],1)
    covered(workflow)
    other={**d,'concept_id':'bad','draft_id':'bad'}
    run(c.coverage(r.id,'collagen',[other]))
    from ankiplusmcp.review_session import ReviewSession
    run(c.stage(r.id));sessions=ReviewSession(c);page=run(sessions.open(r.id))
    run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'bad','action':'exclude'}]))
    p=c._latest(r.id)
    assert len(p.operations)==1 and p.operations[0]['draft_id']=='fibroblast'
    assert not any(f.get('severity')=='blocker' for f in p.findings)


def test_source_contradiction_can_only_close_through_explicit_bound_resolution(workflow):
    c,s,e,r,d=workflow;d['source_disagreement']=True
    sessions,page=opened(workflow)
    still=run(sessions.decide(r.id,page['session_token'],page['digest'],[{'concept_id':'fibroblast','action':'keep','resolve_contradiction':True}]))
    assert c._latest(r.id).decisions[0]['disposition']=='pending'
    resolved=run(sessions.decide(r.id,still['session_token'],still['digest'],[{'concept_id':'fibroblast','action':'edit-new','fields':{'Back':'Fibroblasts'},'resolve_contradiction':True}]))
    assert c._latest(r.id).decisions[0]['disposition']=='propose_create'
    assert any(e.kind=='source_contradiction_resolved' for e in c.runs.read(r.id).events)
    second=c.start(r.workspace,[1]);d['source_disagreement']=False;run(c.coverage(second.id,'collagen',[d]))
    assert run(c.stage(second.id)).decisions[0]['disposition']=='propose_create'
    assert not e.sent
