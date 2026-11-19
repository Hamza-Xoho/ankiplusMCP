"""Mechanical verification of imported execution evidence, not a real reviewer run."""
from copy import deepcopy
import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow, covered, run
from test_sources import wait


def receipt(ticket, role):
    agent='synthetic-'+role
    reads=[{'artifact':name,'sha256':value,'order':index+1,'turn':1,'agent_id':agent,'tool':'Read'} for index,(name,value) in enumerate(ticket['files'].items())]
    if role=='student':
        # The local gate requires fronts then durably committed attempts then backs.
        fronts=[r for r in reads if r['artifact'].startswith('fronts')]
        backs=[r for r in reads if r['artifact'].startswith('backs')]
        other=[r for r in reads if r not in fronts+backs]
        reads=other+fronts+backs
        for i,r in enumerate(reads):r['order']=i+1
        committed=max((r['order'] for r in fronts),default=0)+1
        for r in backs:r['order']+=2
    else:committed=None
    report=f'# Review Report — anki-{role}\n\n## Note fibroblast — PASS\n'
    if role=='student':report+='**Attempt:** Fibroblasts → right\n'
    report+='\n## Summary\n**Verdict:** PASS\n**Stats:** notes=1, pass=1\n'
    return dict(ticket_id=ticket['ticket_id'],role=role,agent_id=agent,author_agent_id='synthetic-author',
        model='claude-sonnet-5-5',effort='high' if role=='maintainer' else 'medium',
        launch={'max_turns':14 if role=='maintainer' else 6,'tools':ticket['tools'],'omit_author_context':True},
        reads=reads,attempts_committed_at=committed,attempts={i:'Fibroblasts' for i in ticket['tile_ids']} if role=='student' else {},report=report)


def attest(c,run_id,content_digest,value):
    # Test-only synthetic trusted host signer. Production MCP never exposes signing.
    import hashlib,hmac
    from ankiplusmcp.runs import _encoded
    key=(c.config.directory/'.quality-verifier.key').read_bytes()
    return {**value,'attestation':hmac.new(key,_encoded({'run_id':run_id,'content_digest':content_digest,'receipt':value}),hashlib.sha256).hexdigest()}


def quality_ready(workflow):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow
    gate=QualityGate(c)
    wait(s,r.workspace,s.render_cards(r.workspace))
    p=run(c.stage(r.id))
    for role in ('maintainer','student'):
        ticket=gate.prepare(r.id,p.content_digest,role)
        if role=='student':gate.release(r.id,p.content_digest,ticket['ticket_id'],{i:'Fibroblasts' for i in ticket['tile_ids']})
        gate.submit(r.id,p.content_digest,attest(c,r.id,p.content_digest,receipt(ticket,role)))
    return run(c.stage(r.id))


def test_quality_receipts_enable_exact_user_authorization(workflow):
    covered(workflow);p=quality_ready(workflow);c,s,e,r,d=workflow
    auth=c.authorize(r.id,p.digest,'user')
    assert auth.proposal_digest==p.digest and auth.mode=='user'
    assert len(p.quality)==2
    assert all(q['evidence_origin']=='imported_host_execution' for q in p.quality)


@pytest.mark.parametrize('damage',['budget','model','author','back_order','hash','ticket','turn','duplicate'])
def test_forged_or_weakened_quality_evidence_is_rejected(workflow,damage):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;covered(workflow)
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id));gate=QualityGate(c)
    ticket=gate.prepare(r.id,p.content_digest,'student')
    gate.release(r.id,p.content_digest,ticket['ticket_id'],{i:'Fibroblasts' for i in ticket['tile_ids']})
    value=receipt(ticket,'student')
    if damage=='budget':value['launch']['max_turns']=7
    if damage=='model':value['model']='author-model'
    if damage=='author':value['agent_id']=value['author_agent_id']
    if damage=='back_order':value['attempts_committed_at']=999
    if damage=='hash':value['reads'][0]['sha256']='0'*64
    if damage=='ticket':value['ticket_id']='forged'
    if damage=='turn':value['reads'][0]['turn']=7
    if damage=='duplicate':value['reads'].append(deepcopy(value['reads'][0]))
    with pytest.raises(DomainError):gate.submit(r.id,p.content_digest,attest(c,r.id,p.content_digest,value))
    assert not any(x.kind=='quality_accepted' for x in c.runs.read(r.id).events)


def test_late_quality_result_cannot_bind_changed_fields(workflow):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;covered(workflow)
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id));gate=QualityGate(c)
    ticket=gate.prepare(r.id,p.content_digest,'maintainer')
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'Changed'}}}],1)
    with pytest.raises(DomainError,match='STALE'):gate.submit(r.id,p.content_digest,attest(c,r.id,p.content_digest,receipt(ticket,'maintainer')))


def test_automatic_authorization_is_distinct_from_user_and_requires_saved_policy(workflow):
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow)
    with pytest.raises(DomainError,match='AUTHORIZATION'):c.authorize(r.id,p.digest,'config')
    change=c.config.propose({'review_mode':'automatic'},c.config.read().config_version);c.config.confirm(change.id)
    with pytest.raises(DomainError,match='STALE'):c.authorize(r.id,p.digest,'user')


def test_unattested_quality_claims_cannot_authorize_through_public_input(workflow):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;covered(workflow)
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id));gate=QualityGate(c)
    ticket=gate.prepare(r.id,p.content_digest,'maintainer')
    with pytest.raises(DomainError,match='attest'):
        gate.submit(r.id,p.content_digest,receipt(ticket,'maintainer'))


def test_modified_quality_packet_cannot_authorize_an_accepted_report(workflow):
    from pathlib import Path
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow)
    ticket=next(x.payload for x in c.runs.read(r.id).events if x.kind=='quality_issued')
    (Path(ticket['packet_path'])/'rubric.md').write_text('tampered rubric')
    with pytest.raises(DomainError,match='QUALITY'):c.authorize(r.id,p.digest,'user')


def test_new_failed_quality_report_invalidates_old_passing_authorization(workflow):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow);gate=QualityGate(c)
    ticket=gate.prepare(r.id,p.content_digest,'maintainer');value=receipt(ticket,'maintainer')
    value['report']=value['report'].replace('— PASS','— REJECT — A1 (blocker)').replace('**Verdict:** PASS','**Verdict:** FAIL')
    value['report']=value['report'].replace('## Summary','**Evidence:** Synthetic quality defect.\n\n## Summary')
    with pytest.raises(DomainError):gate.submit(r.id,p.content_digest,attest(c,r.id,p.content_digest,value))
    with pytest.raises(DomainError):c.authorize(r.id,p.digest,'user')


def test_student_report_cannot_rewrite_committed_front_answer(workflow):
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;covered(workflow)
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id));gate=QualityGate(c)
    ticket=gate.prepare(r.id,p.content_digest,'student');value=receipt(ticket,'student')
    gate.release(r.id,p.content_digest,ticket['ticket_id'],value['attempts'])
    value['report']=value['report'].replace('**Attempt:** Fibroblasts','**Attempt:** A different answer')
    with pytest.raises(DomainError):gate.submit(r.id,p.content_digest,attest(c,r.id,p.content_digest,value))


def test_quality_packet_reviews_actual_existing_target_not_unused_new_draft(workflow):
    import json
    from pathlib import Path
    from test_coordinator import existing
    from ankiplusmcp.quality import QualityGate
    c,s,e,r,d=workflow;existing(workflow)
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(c.stage(r.id))
    ticket=QualityGate(c).prepare(r.id,p.content_digest,'maintainer')
    cards=json.loads((Path(ticket['packet_path'])/'drafts.json').read_bytes())['cards']
    assert cards[0]['fields']['Back']=='Existing answer'
    assert cards[0]['fields']['Front']=='Existing question'


def test_image_only_pdf_evidence_packet_contains_actual_cited_page(tmp_path):
    import pymupdf as fitz
    from pathlib import Path
    from contextlib import asynccontextmanager
    from test_coordinator import SyntheticCompanion
    from ankiplusmcp.anki_adapter import AnkiAdapter
    from ankiplusmcp.service import Service
    from ankiplusmcp.coordinator import Coordinator
    from ankiplusmcp.quality import QualityGate
    pdf=tmp_path/'diagram.pdf';doc=fitz.open();page=doc.new_page();page.insert_text((40,40),'Synthetic diagram evidence');doc.save(pdf);doc.close()
    s=Service(tmp_path/'data',[tmp_path]);external=SyntheticCompanion()
    @asynccontextmanager
    async def connection():yield AnkiAdapter(external,profile='Main',collection_path=external.binding['collection_path'])
    s.companion_connection=connection
    try:
        w=s.store.create('lecture',str(pdf))['id'];wait(s,w,s.extract_source(w))
        s.save_cards(w,[dict(id='diagram',kind='basic',notetype='Basic',fields={'Front':'Diagram question','Back':'Synthetic answer'},tags=['#AnkiPlus::Synthetic'],source_ref=[1])],0)
        c=Coordinator(s);c.config.confirm(c.config.propose({'profile':'Main','note_type':'Basic'},1).id);r=c.start(w,[1])
        source=s.store.get(w)['source']['sha256']
        run(c.coverage(r.id,'diagram',[{'concept_id':'diagram','draft_id':'diagram','disposition':'propose_create','source_refs':[{'source_hash':source,'page':1}]}]))
        p=run(c.stage(r.id));ticket=QualityGate(c).prepare(r.id,p.content_digest,'maintainer')
        pages=[n for n in ticket['files'] if n.startswith('source-page-') and n.endswith('.png')]
        assert pages and (Path(ticket['packet_path'])/pages[0]).read_bytes().startswith(b'\x89PNG')
    finally:s.close()
