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
