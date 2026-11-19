"""Strict companion boundary tests; synthetic transport cannot contact Anki."""
import asyncio
from types import SimpleNamespace
import pytest
from ankiplusmcp.store import DomainError


def run(coro): return asyncio.run(coro)

class Companion:
    def __init__(self): self.calls=[]; self.handlers={}
    async def list_tools(self):
        return SimpleNamespace(tools=[SimpleNamespace(name=n) for n in self.handlers])
    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        value=self.handlers[name](arguments)
        return SimpleNamespace(isError=False, structuredContent=value)

@pytest.fixture
def adapter():
    from ankiplusmcp.anki_adapter import AnkiAdapter
    c=Companion()
    c.handlers['collection_identity']=lambda _: dict(identity_complete=True, profile_name='Main',
        collection_path='/synthetic/collection.anki2', collection_created_ts=1,
        collection_session='a', identity_sha256='a'*64)
    return AnkiAdapter(c, profile='Main', collection_path='/synthetic/collection.anki2'), c


def test_missing_conditional_capability_fails_closed(adapter):
    a,c=adapter
    with pytest.raises(DomainError, match='UNSUPPORTED'): run(a.operation_state('add_note', {}))
    assert c.calls == []


def test_profile_binding_is_explicit(adapter):
    a,c=adapter
    c.handlers['collection_identity']=lambda _: dict(identity_complete=True, profile_name='Other')
    with pytest.raises(DomainError, match='CONFLICT'): run(a.collection_identity())


def test_complete_search_paginates_and_rejects_duplicates(adapter):
    a,c=adapter
    c.handlers['find_notes']=lambda args: {'noteIds':[1,2] if args['offset']==0 else [3],
                                          'hasMore':args['offset']==0}
    assert run(a.search_notes('deck:Default')) == [1,2,3]
    c.handlers['find_notes']=lambda args: {'noteIds':[1], 'hasMore':True}
    with pytest.raises(DomainError): run(a.search_notes('deck:Default'))


def test_full_note_read_preserves_one_to_many_card_ownership(adapter):
    a,c=adapter
    c.handlers['notes_info']=lambda _: {'notes':[{'noteId':17,'modelName':'Cloze','tags':[],
        'fields':{'Text':{'value':'{{c1::a}} {{c2::b}}'}},'cards':[23,24],'mod':1}], 'notFound':0}
    notes=run(a.read_notes([17]))
    assert notes[0].card_ids == [23,24]
    assert notes[0].fields['Text']=='{{c1::a}} {{c2::b}}'
    assert ('notes_info', {'notes':[17]}) in c.calls
    assert not any('excerpt_chars' in args for name,args in c.calls)

@pytest.mark.parametrize('damage',['truncated','missing','foreign'])
def test_incomplete_or_foreign_read_is_refused(adapter, damage):
    a,c=adapter
    note={'noteId':17,'fields':{'Text':{'value':'a'}},'cards':[23], 'modelName':'Cloze','tags':[],'mod':1}
    if damage=='truncated': note['fields']['Text']['truncated']=True
    if damage=='foreign': note['noteId']=99
    c.handlers['notes_info']=lambda _: {'notes':[] if damage=='missing' else [note]}
    with pytest.raises(DomainError): run(a.read_notes([17]))


def test_arbitrary_dispatch_is_impossible(adapter):
    a,c=adapter
    with pytest.raises(DomainError, match='UNSUPPORTED'): run(a.operation_state('delete_notes', {'notes':[17]}))
    assert not c.calls


def test_explicit_suspension_uses_captured_state(adapter):
    a,c=adapter
    binding=run(a.collection_identity())
    state={'version':1,'operation':'card_suspend','arguments':{'card_ids':[23]},'binding':binding,'target':[]}
    c.handlers['conditional_student_operation']=lambda args: {'version':1,'binding':binding,'result':{'suspended_count':1}}
    result=run(a.set_suspended([23],True,expected_state=state))
    assert result['result']['suspended_count']==1
    assert c.calls[-1][1]['expected_state']==state


def test_update_rejects_incomplete_fields_against_captured_model(adapter):
    a,c=adapter
    binding=run(a.collection_identity())
    args={'id':17,'fields':{'Front':'new'}}
    target={'fields':{'Front':'old','Back':'answer'},'model':{'name':'Basic','flds':[{'name':'Front'},{'name':'Back'}],
        'tmpls':[{'qfmt':'{{Front}}','afmt':'{{FrontSide}} {{Back}}'}],'css':''}}
    state={'version':1,'operation':'update_note_fields','arguments':args,'binding':binding,'target':target}
    with pytest.raises(DomainError,match='Complete'):
        run(a.update_note({'arguments':args,'expected_state':state}))


def test_create_batch_keeps_acknowledged_items_on_later_failure(adapter):
    a,c=adapter
    binding=run(a.collection_identity())
    model={'name':'Basic','flds':[{'name':'Front'},{'name':'Back'}],
           'tmpls':[{'qfmt':'{{Front}}','afmt':'{{FrontSide}} {{Back}}'}],'css':''}
    envelopes=[]
    for front in ('one','two'):
        args={'deck_name':'Default','model_name':'Basic','fields':{'Front':front,'Back':'answer'},'tags':[]}
        envelopes.append({'arguments':args,'expected_state':{'version':1,'operation':'add_note','arguments':args,'binding':binding,'target':{'model':model,'deck':{'id':1,'name':'Default'}}}})
    def write(args):
        if args['arguments']['fields']['Front']=='two': raise TimeoutError('private detail')
        return {'version':1,'binding':binding,'result':{'note_id':17}}
    c.handlers['conditional_student_operation']=write
    results=run(a.create_notes(envelopes))
    assert [r['status'] for r in results]==['acknowledged','uncertain']
    assert results[0]['acknowledgement']['result']['note_id']==17
    assert 'private detail' not in str(results)


@pytest.mark.parametrize('damage',['foreign','empty_template','missing_css','duplicate_fields'])
def test_note_type_reads_reject_malformed_or_foreign_metadata(adapter, damage):
    a,c=adapter
    fields={'model_name':'Basic','field_names':['Front','Back'],'fields':[{'name':'Front'},{'name':'Back'}],'total':2}
    templates={'model_name':'Basic','templates':{'Card 1':{'Front':'{{Front}}','Back':'{{Back}}'}},'template_count':1}
    styling={'model_name':'Basic','css':'.card {}'}
    if damage=='foreign': templates['model_name']='Foreign'
    if damage=='empty_template': templates['templates']['Card 1']['Front']=''
    if damage=='missing_css': del styling['css']
    if damage=='duplicate_fields': fields['field_names']=['Front','Front']
    for name,value in [('model_field_names',fields),('model_templates',templates),('model_styling',styling)]:
        c.handlers[name]=lambda args,value=value:value
    with pytest.raises(DomainError): run(a.read_note_type('Basic'))
