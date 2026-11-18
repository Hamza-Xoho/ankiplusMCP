from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
import os
import pytest
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError

@pytest.fixture
def env(tmp_path):
    s=Service(tmp_path/'data',[tmp_path])
    try: yield s,s.store.create('lecture',text='# First\nText')['id']
    finally: s.close()

@pytest.mark.parametrize('change,code',[('cancel','CANCELLED'),('source','SOURCE_CHANGED'),('media','MEDIA_CHANGED'),('revision','STALE')])
def test_publication_rejects_changed_dependencies(env,change,code):
    s,w=env; s.store.write_json(w,'media/input.json',1)
    target=s.store.path(w,'old.txt'); target.write_text('old')
    ticket=s.publisher.capture(w,inputs={'media/input.json':'MEDIA_CHANGED'},expected_revision=0)
    with s.publisher.temporary(w,'old.txt') as stage:
        s.store.path(w,stage).write_text('new')
        if change=='source':
            p=Path(ticket.manifest['source']['path']); p.chmod(0o600); p.write_text('changed')
        if change=='media': s.store.write_json(w,'media/input.json',2)
        if change=='revision':
            with s.store.edit(w): pass
        before=s.store.get(w)
        with pytest.raises(DomainError,match=code):
            s.publisher.publish(ticket,replacements={stage:'old.txt'},json_records={'latest.json':{}},cancel=lambda:change=='cancel')
        assert target.read_text()=='old' and not s.store.path(w,'latest.json').exists()
        assert s.store.get(w)==before
    assert not s.store.path(w,stage).exists()


def test_changed_media_cannot_publish_pointer(env):
    s,w=env; s.store.write_json(w,'media/input.json',1)
    ticket=s.publisher.capture(w,inputs={'media/input.json':'MEDIA_CHANGED'})
    s.store.write_json(w,'media/input.json',2)
    with pytest.raises(DomainError,match='MEDIA_CHANGED'): s.publisher.publish(ticket,json_records={'latest.json':{}})
    assert not s.store.path(w,'latest.json').exists()


def test_success_advances_artifact_epoch_only(env):
    s,w=env; ticket=s.publisher.capture(w)
    s.publisher.publish(ticket,json_records={'latest.json':{'ready':True}})
    state=s.store.get(w)
    assert state['revision']==0 and state['artifact_revision']==1


def test_work_does_not_block_reads(env):
    s,w=env; entered=Event(); release=Event()
    def slow():
        ticket=s.publisher.capture(w); entered.set(); assert release.wait(3); s.publisher.publish(ticket)
    with ThreadPoolExecutor(2) as pool:
        f=pool.submit(slow)
        try:
            assert entered.wait(1)
            assert pool.submit(s.get_cards,w).result(timeout=.5)['cards']==[]
        finally: release.set(); f.result(3)


def test_temporary_cleanup_preserves_target(env):
    s,w=env; s.store.path(w,'old').write_text('old')
    with pytest.raises(RuntimeError):
        with s.publisher.temporary(w,'old') as stage:
            s.store.path(w,stage).write_text('new'); raise RuntimeError()
    assert not s.store.path(w,stage).exists() and s.store.path(w,'old').read_text()=='old'


def test_partial_publish_failure_preserves_history(env,monkeypatch):
    s,w=env; s.store.path(w,'history').write_text('permanent')
    for name in ('a','b'): s.store.path(w,name).write_text('old')
    ticket=s.publisher.capture(w); original=os.replace
    with s.publisher.temporary(w,'a') as a, s.publisher.temporary(w,'b') as b:
        for name in (a,b): s.store.path(w,name).write_text('new')
        def fail(src,dst):
            if Path(dst).name=='b': raise OSError('injected')
            return original(src,dst)
        monkeypatch.setattr(os,'replace',fail)
        with pytest.raises(OSError): s.publisher.publish(ticket,replacements={a:'a',b:'b'})
    assert s.store.path(w,'history').read_text()=='permanent'
    assert s.store.path(w,'a').read_text()=='new' and s.store.path(w,'b').read_text()=='old'

@pytest.mark.parametrize('path',['/absolute','../escape','input/file','input','link/file'])
def test_publication_path_containment(env,path,tmp_path):
    s,w=env; s.store.path(w,'link').symlink_to(tmp_path,target_is_directory=True)
    ticket=s.publisher.capture(w)
    with pytest.raises(DomainError): s.publisher.publish(ticket,json_records={path:{}})
    assert s.store.get(w).get('artifact_revision',0)==0
