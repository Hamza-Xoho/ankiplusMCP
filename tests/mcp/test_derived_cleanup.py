"""Explicit cleanup cannot erase source, drafts, media or permanent evidence."""
import pytest
from ankiplusmcp.server import API
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError


def test_cleanup_previews_requires_explicit_confirm_and_preserves_evidence(tmp_path):
    s=Service(tmp_path/'data',[tmp_path]);w=s.store.create('lecture',text='retained source')['id'];api=API(s)
    try:
        for relative in ('previews/old/front.png','media/only.png','reviews/r.json','jobs/completed.json','collection-media/file.png'):
            path=s.store.path(w,relative);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'retained')
        s.store.write_json(w,'jobs/completed.json',{'id':'completed','owner':s.jobs.owner,'operation':'render_cards','status':'completed','cancel_requested':False})
        c=api._coordinator();r=c.start(w);c.event(r.id,'test_evidence',{'kept':True})
        before=c.runs.read(r.id).model_dump();source=s.store.get(w)['source']['path']
        preview=api.cleanup_derived(w)
        assert preview['applied'] is False and s.store.path(w,'previews/old/front.png').exists()
        done=api.cleanup_derived(w,apply=True,expected_digest=preview['digest'])
        assert done['applied'] is True and not s.store.path(w,'previews/old/front.png').exists()
        assert s.store.path(w,'media/only.png').read_bytes()==b'retained'
        assert s.store.path(w,'collection-media/file.png').exists()
        assert c.runs.read(r.id).model_dump()==before
        from pathlib import Path
        assert Path(source).read_text()=='retained source'
    finally:s.close()


def test_cleanup_rejects_changed_preview_or_active_job(tmp_path):
    s=Service(tmp_path/'data',[tmp_path]);w=s.store.create('cards')['id'];api=API(s)
    try:
        p=s.store.path(w,'previews/old/front.png');p.parent.mkdir(parents=True);p.write_bytes(b'one')
        preview=api.cleanup_derived(w);p.write_bytes(b'two')
        with pytest.raises(DomainError,match='STALE'):api.cleanup_derived(w,apply=True,expected_digest=preview['digest'])
        s.store.write_json(w,'jobs/active.json',{'id':'active','owner':s.jobs.owner,'operation':'render_cards','status':'running','cancel_requested':False})
        with pytest.raises(DomainError,match='BUSY'):api.cleanup_derived(w,apply=True,expected_digest=api.cleanup_derived(w)['digest'])
        assert p.exists()
    finally:s.close()
