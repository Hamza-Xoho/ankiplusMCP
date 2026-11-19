import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow,covered,run


def test_run_only_preference_diff_does_not_change_saved_future_preferences(workflow):
    c,s,e,r,d=workflow
    change=c.propose_run_preferences(r.id,{'uncertain_match':'create','review_mode':'automatic'})
    assert change['scope']=='this_run' and change['diff']
    c.confirm_run_preferences(r.id,change['id'])
    assert c.config.read().uncertain_match=='pending'
    d['uncertain']=True
    covered(workflow);p=run(c.stage(r.id))
    assert p.decisions[0]['disposition']=='propose_create'
    assert p.config['uncertain_match']=='create'
    assert p.saved_config['uncertain_match']=='pending'
    assert p.config['review_mode']=='automatic'
    from test_workflow_quality import quality_ready
    p=quality_ready(workflow)
    with pytest.raises(DomainError,match='AUTHORIZATION'):c.authorize(r.id,p.digest,'config')
    assert c.authorize(r.id,p.digest,'user').mode=='user'


def test_run_scope_confirmation_rejects_changed_saved_preferences(workflow):
    c,s,e,r,d=workflow;change=c.propose_run_preferences(r.id,{'selected_decks':[]})
    cfg=c.config.read();c.config.confirm(c.config.propose({'selected_decks':['Another Deck']},cfg.config_version).id)
    with pytest.raises(DomainError,match='STALE'):c.confirm_run_preferences(r.id,change['id'])


def test_confirmed_run_preferences_invalidate_existing_proposal(workflow):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id))
    change=c.propose_run_preferences(r.id,{'review_mode':'automatic'});c.confirm_run_preferences(r.id,change['id'])
    with pytest.raises(DomainError,match='STALE'):c.authorize(r.id,p.digest,'user')
