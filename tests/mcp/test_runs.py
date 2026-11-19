from pathlib import Path

import pytest


def api():
    import ankiplusmcp.runs as module
    return module


def selection(pages=(1, 2)):
    return api().SourceSelection(source_hash='a' * 64, pages=list(pages), label='Cell biology')


def test_chapter_selections_and_repeat_runs_keep_distinct_histories(tmp_path):
    store = api().RunStore(tmp_path)
    first = store.start('lecture1', selection(), 1)
    chapter = store.start('lecture1', selection((3, 4)), 1)
    repeat = store.start('lecture1', selection(), 1)
    assert len({first.id, chapter.id, repeat.id}) == 3
    assert store.read(first.id).selection.pages == [1, 2]
    assert store.read(chapter.id).selection.pages == [3, 4]


def test_receipts_accumulate_and_duplicate_event_is_idempotent(tmp_path):
    m = api()
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    first = m.RunEvent(kind='operation_result', payload={'batch': 'one', 'note_ids': [101], 'origin': 'caller_supplied'})
    second = m.RunEvent(kind='operation_result', payload={'batch': 'two', 'note_ids': [102], 'origin': 'verified_readback'})
    assert store.append(run.id, first) == 2
    assert store.append(run.id, first) == 2
    assert store.append(run.id, second) == 3
    reopened = m.RunStore(tmp_path).read(run.id)
    assert [r.payload['note_ids'] for r in reopened.events if r.kind == 'operation_result'] == [[101], [102]]
    with pytest.raises(m.DomainError, match='event'):
        store.append(run.id, first.model_copy(update={'payload': {'note_ids': [999]}}))


def test_run_identifiers_cannot_escape_root(tmp_path):
    m = api()
    store = m.RunStore(tmp_path)
    with pytest.raises(m.DomainError):
        store.read('../outside')
    with pytest.raises(m.DomainError):
        store.start('../outside', selection(), 1)
    assert not (tmp_path.parent / 'outside').exists()


def test_failed_publication_preserves_visible_history(tmp_path, monkeypatch):
    m = api()
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    original = m.os.replace
    def interrupt(source, destination):
        if Path(destination).name == '00000000000000000002.json':
            raise OSError('simulated failure before publication')
        return original(source, destination)
    monkeypatch.setattr(m.os, 'replace', interrupt)
    with pytest.raises(OSError):
        store.append(run.id, m.RunEvent(kind='decision', payload={'keep': 'n1'}))
    assert len(store.read(run.id).events) == 1
    assert not list((tmp_path / 'runs' / run.id).glob('*.tmp'))


def test_index_rebuild_keeps_source_run_and_card_search(tmp_path):
    m = api()
    from ankiplusmcp.run_index import RunIndex, RunQuery
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    store.append(run.id, m.RunEvent(kind='operation_result', payload={'note_ids': [101], 'card_ids': [501], 'outcome': 'confirmed'}))
    index = RunIndex(store)
    assert index.rebuild() == 1
    assert index.search(RunQuery(card_id=501)).runs[0].id == run.id
    assert index.search(RunQuery(note_id=501)).runs == []
    index.path.unlink()
    assert index.rebuild() == 1
    assert index.search(RunQuery(source_hash='a' * 64, outcome='confirmed')).runs[0].id == run.id
    assert index.search(RunQuery(text='biology')).runs[0].id == run.id
    assert index.search(RunQuery(limit=1)).next_offset is None


def test_snapshot_is_immutable_and_conflicting_version_is_refused(tmp_path):
    m = api()
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    one = store.save_snapshot(run.id, 'proposal-1', {'fields': {'Text': 'nucleus'}})
    assert store.save_snapshot(run.id, 'proposal-1', {'fields': {'Text': 'nucleus'}}) == one
    with pytest.raises(m.DomainError):
        store.save_snapshot(run.id, 'proposal-1', {'fields': {'Text': 'different'}})


def test_index_reflects_later_results_without_manual_rebuild(tmp_path):
    m = api()
    from ankiplusmcp.run_index import RunIndex, RunQuery
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    index = RunIndex(store)
    assert index.rebuild() == 1
    store.append(run.id, m.RunEvent(kind='operation_result', payload={'card_ids': [700]}))
    assert [r.id for r in index.search(RunQuery(card_id=700)).runs] == [run.id]


def test_concurrent_appends_preserve_every_event(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    m = api()
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    def append(number):
        return m.RunStore(tmp_path).append(run.id, m.RunEvent(kind='decision', payload={'number': number}))
    with ThreadPoolExecutor(max_workers=4) as pool:
        sequences = list(pool.map(append, range(12)))
    assert sorted(sequences) == list(range(2, 14))
    assert len(store.read(run.id).events) == 13


def test_run_root_cannot_follow_external_symlink(tmp_path):
    m = api()
    outside = tmp_path / 'outside'
    outside.mkdir()
    root = tmp_path / 'data'
    root.mkdir()
    (root / 'runs').symlink_to(outside, target_is_directory=True)
    with pytest.raises(m.DomainError):
        m.RunStore(root)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('bad', [None, '123', [True], [-1]])
def test_invalid_identity_payload_cannot_poison_index(tmp_path, bad):
    m = api()
    from ankiplusmcp.run_index import RunIndex, RunQuery
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    with pytest.raises(ValueError):
        store.append(run.id, m.RunEvent(kind='operation_result', payload={'card_ids': bad}))
    assert RunIndex(store).search(RunQuery()).runs[0].id == run.id


def test_malformed_historical_run_is_reported_without_hiding_other_history(tmp_path):
    import json
    m = api()
    from ankiplusmcp.run_index import RunIndex, RunQuery
    store = m.RunStore(tmp_path)
    good = store.start('lecture1', selection(), 1)
    bad = store.start('lecture2', selection(), 1)
    store.append(bad.id, m.RunEvent(kind='operation_result', payload={'card_ids': [501]}))
    path = tmp_path / 'runs' / bad.id / '00000000000000000002.json'
    event = json.loads(path.read_bytes())
    event['payload']['card_ids'] = None
    path.write_text(json.dumps(event))
    index = RunIndex(store)
    assert index.rebuild() == 1
    page = index.search(RunQuery())
    assert [run.id for run in page.runs] == [good.id]
    assert page.errors[bad.id] == 'RUN_CORRUPT'
    assert path.exists(), 'damaged evidence must be preserved'


@pytest.mark.parametrize('legacy', [False, True])
def test_concurrent_first_history_reads_migrate_index_once(tmp_path, monkeypatch, legacy):
    """Two real SQLite connections must not race an old-schema column upgrade."""
    import sqlite3
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, BrokenBarrierError
    from ankiplusmcp.run_index import RunIndex, RunQuery
    m = api()
    store = m.RunStore(tmp_path)
    run = store.start('lecture1', selection(), 1)
    index = RunIndex(store)
    if legacy:
        with sqlite3.connect(index.path) as db:
            db.execute('CREATE TABLE runs (id TEXT PRIMARY KEY, source_hash TEXT, label TEXT, updated TEXT, sequence INTEGER, snapshot TEXT NOT NULL)')
    # Hold each reader's actual old-schema result until both have inspected it.
    # A serialized implementation cannot reach the second inspection yet; the
    # bounded barrier then releases the first reader to finish its transaction.
    inspected = Barrier(2)
    original_connect = sqlite3.connect
    class CoordinatedConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            cursor = super().execute(sql, *args, **kwargs)
            if sql == 'PRAGMA table_info(runs)':
                rows = list(cursor)
                try:
                    inspected.wait(timeout=0.5)
                except BrokenBarrierError:
                    pass
                return rows
            return cursor
    def connect(*args, **kwargs):
        return original_connect(*args, factory=CoordinatedConnection, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', connect)
    def search(_):
        return [item.id for item in RunIndex(m.RunStore(tmp_path)).search(RunQuery()).runs]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(search, range(2)))
    assert results == [[run.id], [run.id]]
    assert store.read(run.id).events == run.events
