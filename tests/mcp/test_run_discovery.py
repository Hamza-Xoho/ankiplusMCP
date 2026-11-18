import os
import sqlite3
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from ankiplusmcp.runs import RunStore
from ankiplusmcp.run_models import SourceSelection,RunEvent
from ankiplusmcp.run_index import RunIndex,RunQuery


def started(tmp_path):
    store=RunStore(tmp_path); run=store.start('lecture1',SourceSelection(label='Cells'),1)
    return store,run


def test_catalog_returns_unchanged_run_ids(tmp_path):
    store,run=started(tmp_path); first=store.catalog()
    assert [i.snapshot.id for i in first.changed]==[run.id]
    again=store.catalog({i.snapshot.id:i.token for i in first.changed})
    assert again.changed==[] and again.unchanged_ids==[run.id] and again.errors=={}


def test_catalog_contains_bad_run_errors(tmp_path):
    store,run=started(tmp_path)
    bad=store.directory/'bad'; bad.mkdir(); (bad/'00000000000000000001.json').write_text('broken')
    (store.directory/'link').symlink_to(bad,target_is_directory=True)
    stage=store.directory/'.staging-incomplete';stage.mkdir(); (stage/'keep').write_text('keep')
    result=store.catalog()
    assert [i.snapshot.id for i in result.changed]==[run.id]
    assert result.errors=={'bad':'RUN_CORRUPT','link':'RUN'}
    assert (bad/'00000000000000000001.json').read_text()=='broken' and (stage/'keep').exists()


def damage(store,run):
    p=store.directory/run.id/'00000000000000000001.json'; old=p.read_bytes(); stamp=p.stat().st_mtime_ns
    p.write_text('broken');os.utime(p,ns=(stamp+1000000,stamp+1000000)); return p,old


def test_index_detects_changed_existing_event(tmp_path):
    store,run=started(tmp_path); index=RunIndex(store);assert index.search(RunQuery()).runs
    damage(store,run); result=index.search(RunQuery())
    assert result.runs==[] and result.errors=={run.id:'RUN_CORRUPT'}


def test_repaired_run_reappears(tmp_path):
    store,run=started(tmp_path); index=RunIndex(store);index.rebuild()
    p,old=damage(store,run); assert index.search(RunQuery()).errors
    p.write_bytes(old);result=index.search(RunQuery());assert result.runs[0].id==run.id and result.errors=={}


def test_unchanged_catalog_does_not_reparse(tmp_path,monkeypatch):
    store,run=started(tmp_path); first=store.catalog(); known={i.snapshot.id:i.token for i in first.changed}
    def forbidden(*a): raise AssertionError('unchanged records reparsed')
    monkeypatch.setattr(store,'_records',forbidden)
    assert store.catalog(known).unchanged_ids==[run.id]


def test_catalog_and_append_take_consistent_snapshot(tmp_path,monkeypatch):
    store,run=started(tmp_path); entered=Event();release=Event()
    import ankiplusmcp.runs as module
    original=module._publish
    def paused(*a): entered.set(); assert release.wait(3); return original(*a)
    monkeypatch.setattr(module,'_publish',paused)
    with ThreadPoolExecutor(2) as pool:
        f=pool.submit(store.append,run.id,RunEvent(kind='next'))
        try:
            assert entered.wait(1); g=pool.submit(store.catalog); release.set(); f.result(2)
            result=g.result(2); assert len(result.changed[0].snapshot.events)==2
        finally: release.set()


def test_old_index_schema_upgrades(tmp_path):
    store,run=started(tmp_path); index=RunIndex(store)
    with sqlite3.connect(index.path) as db:
        db.execute('CREATE TABLE runs (id TEXT PRIMARY KEY, source_hash TEXT, label TEXT, updated TEXT, sequence INTEGER, snapshot TEXT NOT NULL)')
    assert index.search(RunQuery()).runs[0].id==run.id
    with sqlite3.connect(index.path) as db: assert 'journal_token' in {row[1] for row in db.execute('PRAGMA table_info(runs)')}


def test_truncated_journal_refuses_search_append_and_rebuild(tmp_path):
    import pytest
    from ankiplusmcp.store import DomainError
    store,run=started(tmp_path);store.append(run.id,RunEvent(kind='coverage_decision',payload={'note_ids':[101]}))
    index=RunIndex(store);assert index.search(RunQuery(note_id=101)).runs
    (store.directory/run.id/'00000000000000000002.json').unlink()
    result=index.search(RunQuery());assert result.runs==[] and result.errors=={run.id:'RUN_CORRUPT'}
    with pytest.raises(DomainError,match='RUN_CORRUPT'):store.append(run.id,RunEvent(kind='later'))
    index.path.unlink();assert RunIndex(store).rebuild()==0
    assert RunIndex(store).search(RunQuery()).errors=={run.id:'RUN_CORRUPT'}


def test_legacy_indexed_truncation_is_reported(tmp_path):
    store,run=started(tmp_path);store.append(run.id,RunEvent(kind='second'))
    (store.directory/run.id/'.head.json').unlink()
    index=RunIndex(store);assert index.rebuild()==1
    (store.directory/run.id/'00000000000000000002.json').unlink()
    assert index.search(RunQuery()).errors=={run.id:'RUN_CORRUPT'}
    assert index.search(RunQuery()).errors=={run.id:'RUN_CORRUPT'}
