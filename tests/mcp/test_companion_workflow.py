import asyncio
from contextlib import asynccontextmanager
import pytest
from ankiplusmcp.service import Service
from ankiplusmcp.server import API, create_server
from ankiplusmcp.store import DomainError
from test_anki_adapter import Companion


def test_collection_coverage_is_connected_to_product_api(tmp_path):
    c=Companion()
    identity=dict(identity_complete=True,profile_name='Main',collection_path='/synthetic/collection.anki2',
                  collection_created_ts=1,collection_session='a',identity_sha256='a'*64)
    c.handlers['collection_identity']=lambda _:identity
    c.handlers['find_notes']=lambda _: {'noteIds':[17],'hasMore':False}
    c.handlers['notes_info']=lambda _: {'notes':[{'noteId':17,'cards':[23,24],
        'fields':{'Text':{'value':'{{c1::a}} {{c2::b}}'}}}]}
    c.handlers['conditional_student_operation']=lambda _: {}
    c.handlers['student_operation_state']=lambda args: {'version':1,'operation':args['operation'],
        'arguments':args['arguments'],'binding':{k:v for k,v in identity.items() if k!='identity_complete'},
        'target':[{'id':17,'fields':{'Text':'{{c1::a}} {{c2::b}}'},'cards':[{'id':23,'nid':17,'queue':-1},{'id':24,'nid':17,'queue':0}]}]}
    @asynccontextmanager
    async def connection():
        from ankiplusmcp.anki_adapter import AnkiAdapter
        yield AnkiAdapter(c,profile='Main',collection_path='/synthetic/collection.anki2')
    s=Service(tmp_path/'work',[tmp_path])
    try:
        s.companion_connection=connection
        result=asyncio.run(API(s).search_collection_coverage('deck:Default'))
        assert result['notes'][0]['card_ids']==[23,24]
        assert result['notes'][0]['suspended_card_ids']==[23]
        assert result['evidence_origin']=='companion_readback'
        assert result['semantic_completeness_verified'] is False
        async def discover():
            server=create_server(s)
            tools=await server.list_tools()
            assert 'search_collection_coverage' in {t.name for t in tools}
        asyncio.run(discover())
    finally:s.close()


def test_unconfigured_product_refuses_collection_access(tmp_path):
    s=Service(tmp_path/'work',[tmp_path])
    try:
        with pytest.raises(DomainError,match='UNSUPPORTED'):
            asyncio.run(API(s).search_collection_coverage('deck:Default'))
    finally:s.close()

@pytest.mark.parametrize('url', ['https://example.org/mcp','http://localhost.evil/mcp',
    'http://127.0.0.1:80/mcp','http://127.0.0.1:8080/mcp','http://user:secret@localhost:3141/mcp'])
def test_transport_rejects_nonlocal_or_reserved_endpoints(url):
    from ankiplusmcp.companion_connection import CompanionConnection
    with pytest.raises(DomainError): CompanionConnection(url,profile='Main',collection_path='/synthetic/collection.anki2')

@pytest.mark.parametrize('damage',['fields','siblings'])
def test_coverage_refuses_mixed_note_and_card_snapshots(tmp_path, damage):
    from ankiplusmcp.anki_adapter import AnkiAdapter
    c=Companion()
    binding=dict(profile_name='Main',collection_path='/synthetic/collection.anki2',
        collection_created_ts=1,collection_session='a',identity_sha256='a'*64)
    c.handlers['collection_identity']=lambda _:dict(binding,identity_complete=True)
    c.handlers['find_notes']=lambda _: {'noteIds':[17],'hasMore':False}
    c.handlers['notes_info']=lambda _: {'notes':[{'noteId':17,'cards':[23], 'fields':{'Text':{'value':'before'}}}]}
    c.handlers['conditional_student_operation']=lambda _:{}
    c.handlers['student_operation_state']=lambda args:dict(version=1,binding=binding,operation=args['operation'],arguments=args['arguments'],
        target=[{'id':17,'fields':{'Text':'after' if damage=='fields' else 'before'},'cards':
            [{'id':23,'nid':17,'queue':0}]+([{'id':24,'nid':17,'queue':0}] if damage=='siblings' else [])}])
    @asynccontextmanager
    async def connection(): yield AnkiAdapter(c,profile='Main',collection_path=binding['collection_path'])
    s=Service(tmp_path/'work',[tmp_path]);s.companion_connection=connection
    try:
        with pytest.raises(DomainError,match='CONFLICT'):
            asyncio.run(API(s).search_collection_coverage('deck:Default'))
    finally:s.close()


def test_connection_initialization_failure_is_sanitized(monkeypatch):
    import ankiplusmcp.companion_connection as module
    @asynccontextmanager
    async def broken(*args,**kwargs):
        raise RuntimeError('secret-test-credential')
        yield
    monkeypatch.setattr(module,'streamable_http_client',broken)
    connection=module.CompanionConnection('http://127.0.0.1:3141/mcp',profile='Main',collection_path='/synthetic/collection.anki2')
    async def attempt():
        async with connection(): pass
    with pytest.raises(DomainError,match='TRANSPORT') as error:
        asyncio.run(attempt())
    assert 'secret-test-credential' not in str(error.value)
