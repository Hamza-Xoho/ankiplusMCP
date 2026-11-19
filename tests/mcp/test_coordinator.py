"""Connected product tests. Only the external MCP transport is synthetic."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
from types import SimpleNamespace
import pytest
from ankiplusmcp.anki_adapter import AnkiAdapter
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def run(coro): return asyncio.run(coro)


class SyntheticCompanion:
    def __init__(self):
        self.binding=dict(profile_name='Main',collection_path='/synthetic/collection.anki2',collection_created_ts=1,collection_session='s1',identity_sha256='a'*64)
        self.model={'name':'Basic','flds':[{'name':'Front'},{'name':'Back'}],'tmpls':[{'qfmt':'{{Front}}','afmt':'{{Back}}'}],'css':'.card{}'}
        self.notes={}; self.cards={}; self.media={}; self.queries=[]; self.sent=[]; self.drop=False; self.before_send=None
    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name=n) for n in ('collection_identity','find_notes','notes_info','student_operation_state','conditional_student_operation','read_media_file','model_field_names','model_templates','model_styling')])
    def note(self,nid):
        note=self.notes[nid]
        return dict(id=nid,fields=deepcopy(note['fields']),tags=note['tags'][:],model=deepcopy(self.model),mod=1,
                    cards=[deepcopy(c) for c in self.cards.values() if c['nid']==nid])
    def state(self,op,args):
        if op=='add_note': target={'model':deepcopy(self.model),'deck':{'id':1,'name':'Default'}}
        elif op=='update_note_fields':target=self.note(args['id'])
        elif op in ('card_suspend','card_unsuspend'):target=[self.note(n) for n in sorted({self.cards[c]['nid'] for c in args['card_ids']})]
        else: target=None
        return dict(version=1,operation=op,arguments=deepcopy(args),binding=deepcopy(self.binding),target=target)
    async def call_tool(self,name,args):
        if name=='model_field_names':value={'model_name':'Basic','field_names':['Front','Back']}
        elif name=='model_templates':value={'model_name':'Basic','templates':{'Card 1':{'Front':'{{Front}}','Back':'{{Back}}'}}}
        elif name=='model_styling':value={'model_name':'Basic','css':'.card{}'}
        elif name=='collection_identity': value=dict(self.binding,identity_complete=True)
        elif name=='find_notes':
            self.queries.append(args['query']); value={'noteIds':list(self.notes),'hasMore':False}
        elif name=='notes_info':value={'notes':[{'noteId':nid,'fields':{k:{'value':v} for k,v in self.notes[nid]['fields'].items()},'cards':[c for c,v in self.cards.items() if v['nid']==nid]} for nid in args['notes'] if nid in self.notes]}
        elif name=='student_operation_state':value=self.state(args['operation'],args['arguments'])
        elif name=='conditional_student_operation':
            op= args['operation']; a=args['arguments']
            if self.before_send:self.before_send(op,a)
            if self.state(op,a)!=args['expected_state']:return SimpleNamespace(isError=True,structuredContent={})
            self.sent.append((op,deepcopy(a)))
            if op=='add_note':
                nid=max(self.notes,default=100)+1; cid=nid+100
                self.notes[nid]={'fields':deepcopy(a['fields']),'tags':a['tags'][:]}
                self.cards[cid]=dict(id=cid,nid=nid,did=1,ord=0,queue=0,type=0,due=0,mod=1,backend_sha256='b'*64)
                result={'note_id':nid}
            elif op=='update_note_fields':self.notes[a['id']]['fields']=deepcopy(a['fields']);result={'note_id':a['id']}
            elif op in ('card_suspend','card_unsuspend'):
                for cid in a['card_ids']:self.cards[cid]['queue']=-1 if op=='card_suspend' else 0
                result={'card_ids':a['card_ids']}
            else: raise AssertionError(op)
            if self.drop:raise TimeoutError('synthetic lost acknowledgement')
            value={'version':1,'binding':deepcopy(self.binding),'result':result}
        else:raise AssertionError(name)
        return SimpleNamespace(isError=False,structuredContent=value)


@pytest.fixture
def workflow(tmp_path):
    from ankiplusmcp.coordinator import Coordinator
    service=Service(tmp_path/'data',[tmp_path])
    external=SyntheticCompanion()
    @asynccontextmanager
    async def connection():yield AnkiAdapter(external,profile='Main',collection_path='/synthetic/collection.anki2')
    service.companion_connection=connection
    workspace=service.store.create('lecture',text='# Cells\nFibroblasts make collagen.')['id']
    wait(service,workspace,service.extract_source(workspace))
    service.save_cards(workspace,[dict(id='fibroblast',kind='basic',fields={'Front':'What makes collagen?','Back':'Fibroblasts'},notetype='Basic',deck='Default',tags=['#AnkiPlus::Cells'],tier=1,source_ref=[1])],0)
    coordinator=Coordinator(service)
    config=coordinator.config
    config.confirm(config.propose({'profile':'Main','note_type':'Basic','selected_decks':['Default']},1).id)
    current=coordinator.start(workspace,[1])
    sha=service.store.get(workspace)['source']['sha256']
    decision=dict(concept_id='fibroblast',draft_id='fibroblast',disposition='propose_create',source_refs=[dict(source_hash=sha,page=1,quote='Fibroblasts make collagen.')])
    yield coordinator,service,external,current,decision
    service.close()


def covered(workflow):
    c,s,e,r,d=workflow
    return run(c.coverage(r.id,'collagen',[d]))


def test_verified_coverage_is_scoped_and_durable(workflow):
    c,s,e,r,d=workflow
    covered(workflow)
    assert 'deck:"Default"' in e.queries[0] and 'tag:' in e.queries[0]
    events=c.runs.read(r.id).events
    assert any(x.kind=='collection_coverage' and x.payload['evidence_origin']=='companion_readback' for x in events)
    assert c.coverage_store.latest(r.id)[0].source_refs[0].quote=='Fibroblasts make collagen.'


@pytest.mark.parametrize('query',['collagen) or deck:*','"unterminated','(collagen'])
def test_query_cannot_escape_approved_scope(workflow,query):
    c,s,e,r,d=workflow
    with pytest.raises(DomainError):run(c.coverage(r.id,query,[d]))
    assert not e.queries


def test_stage_is_immutable_and_authorization_requires_quality(workflow):
    c,s,e,r,d=workflow
    covered(workflow)
    p=run(c.stage(r.id))
    assert p.operations[0]['operation']=='add_note'
    assert p.source['pages']==[1]
    assert p.content_digest and p.digest
    with pytest.raises(DomainError,match='QUALITY'):c.authorize(r.id,p.digest,'user')
    assert not e.sent
    assert run(c.stage(r.id)).digest==p.digest
    assert any(x.kind=='proposal_staged' for x in c.runs.read(r.id).events)


def test_stale_fields_refuse_authorization_even_before_quality(workflow):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id))
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'Changed'}}}],1)
    with pytest.raises(DomainError,match='STALE'):c.authorize(r.id,p.digest,'user')


def test_source_contradiction_remains_pending(workflow):
    c,s,e,r,d=workflow;d['source_disagreement']=True
    covered(workflow);p=run(c.stage(r.id))
    assert not p.operations
    assert p.decisions[0]['disposition']=='pending'


def test_student_facade_connects_run_coverage_and_stage(workflow):
    from ankiplusmcp.server import API
    c,s,e,r,d=workflow;api=API(s)
    result=run(api.record_run_coverage(r.id,'collagen',[d]))
    assert result['batch_id']
    proposal=run(api.stage_run(r.id))
    assert proposal['operations']==1
    assert proposal['quality_required']
    assert api.get_run_proposal(r.id)['cards'][0]['fields']['Back']=='Fibroblasts'
    with pytest.raises(DomainError,match='QUALITY'):api.authorize_run(r.id,proposal['digest'],'user')


def existing(workflow):
    c,s,e,r,d=workflow
    e.notes[101]={'fields':{'Front':'Existing question','Back':'Existing answer'},'tags':['Premade::Original']}
    e.cards[201]=dict(id=201,nid=101,did=1,ord=0,queue=-1,type=0,due=0,mod=1,backend_sha256='b'*64)
    d.update(disposition='propose_unsuspend',candidate_note_ids=[101],chosen_note_ids=[101],card_ids=[201])
    covered(workflow)


def test_stage_refuses_existing_note_changes_since_coverage(workflow):
    c,s,e,r,d=workflow;existing(workflow)
    e.notes[101]['fields']['Back']='Unreviewed foreign edit'
    with pytest.raises(DomainError,match='CONFLICT'):run(c.stage(r.id))


def test_modified_proposal_record_cannot_reuse_its_old_digest(workflow):
    import json
    from test_workflow_quality import quality_ready
    c,s,e,r,d=workflow;covered(workflow);p=quality_ready(workflow)
    event=next(e for e in reversed(c.runs.read(r.id).events) if e.kind=='proposal_staged')
    path=c.runs._path(r.id)/(f'{event.sequence:020d}.json')
    value=json.loads(path.read_bytes());value['payload']['proposal']['operations'][0]['arguments']['fields']['Back']='Forged content'
    path.write_text(json.dumps(value))
    with pytest.raises(DomainError,match='RUN_CORRUPT'):c.authorize(r.id,p.digest,'user')
    assert not e.sent
