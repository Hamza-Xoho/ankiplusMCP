from threading import Event

from ankiplusmcp.jobs import Jobs
from ankiplusmcp.store import Store


def test_workspace_list_has_labels_dates_recency_and_pagination(tmp_path):
    store = Store(tmp_path / 'work', [tmp_path])
    first = store.create('lecture', text='# Histology\nCells')
    second = store.create('cards')
    with store.edit(first['id']) as current:
        current['label'] = 'Histology chapter 2'
    listed = store.list(limit=1)
    assert listed['workspaces'][0]['id'] == first['id']
    assert listed['workspaces'][0]['label'] == 'Histology chapter 2'
    assert listed['workspaces'][0]['created']
    assert listed['workspaces'][0]['updated'] >= listed['workspaces'][0]['created']
    assert listed['next_offset'] == 1
    assert store.list(offset=1)['workspaces'][0]['id'] == second['id']


def test_older_workspace_creation_date_is_unknown_not_fabricated(tmp_path):
    store = Store(tmp_path / 'work', [tmp_path])
    workspace = store.create('cards')['id']
    store.write_json(workspace, 'workspace.json', {'id': workspace, 'mode': 'cards', 'revision': 0, 'source': None})
    old = store.get(workspace)
    assert old['created'] is None
    assert old['updated'] is None
    assert old['label'] == 'Cards'


def test_job_ids_are_discoverable_after_caller_loses_them(tmp_path):
    store = Store(tmp_path / 'work', [tmp_path])
    workspace = store.create('cards')['id']
    jobs = Jobs(store)
    entered, release = Event(), Event()
    def work(cancel, report):
        entered.set()
        release.wait(3)
        return {'secret_large_artifact': 'not needed in a job listing'}
    try:
        submitted = jobs.submit(workspace, 'render_cards', work)
        assert entered.wait(2)
        found = jobs.list(workspace, status='running')
        assert found['jobs'][0]['id'] == submitted['id']
        assert found['jobs'][0]['created']
        assert 'result' not in found['jobs'][0]
    finally:
        release.set()
        jobs.close()


def test_damaged_job_does_not_hide_other_jobs_or_leak_its_contents(tmp_path):
    store = Store(tmp_path / 'work', [tmp_path])
    workspace = store.create('cards')['id']
    jobs = Jobs(store)
    try:
        store.write_json(workspace, 'jobs/good.json', {
            'id': 'good', 'owner': jobs.owner, 'operation': 'render_cards',
            'status': 'completed', 'progress': 'finished'})
        broken = store.path(workspace, 'jobs/broken.json')
        broken.write_text('{"credential": "private-do-not-echo"')
        before = broken.read_bytes()
        found = jobs.list(workspace)
        assert [job['id'] for job in found['jobs']] == ['good']
        assert found['errors'] == [{'id': 'broken', 'code': 'JOB_RECORD',
                                   'message': 'Cannot read job record; original retained.'}]
        assert 'private-do-not-echo' not in str(found)
        assert broken.read_bytes() == before
    finally:
        jobs.close()


def test_damaged_job_errors_are_bounded_and_discoverable_across_pages(tmp_path):
    store = Store(tmp_path / 'work', [tmp_path])
    workspace = store.create('cards')['id']
    jobs = Jobs(store)
    try:
        for ident in ('a', 'b', 'c'):
            store.write_json(workspace, f'jobs/{ident}.json', [])
        first = jobs.list(workspace, limit=2)
        second = jobs.list(workspace, offset=first['next_offset'], limit=2)
        assert first['jobs'] == second['jobs'] == []
        assert [item['id'] for item in first['errors']] == ['a', 'b']
        assert [item['id'] for item in second['errors']] == ['c']
        assert first['error_total'] == second['error_total'] == 3
        assert second['next_offset'] is None
    finally:
        jobs.close()


def test_invalid_job_owner_is_refused_before_lease_probe(tmp_path):
    import pytest
    from ankiplusmcp.store import DomainError

    store = Store(tmp_path / 'work', [tmp_path])
    workspace = store.create('cards')['id']
    jobs = Jobs(store)
    try:
        record = {'id': 'bad', 'owner': '../outside', 'operation': 'render_cards',
                  'status': 'running', 'progress': 'working'}
        store.write_json(workspace, 'jobs/bad.json', record)
        with pytest.raises(DomainError, match='Invalid job record'):
            jobs.get(workspace, 'bad')
        assert store.read_json(workspace, 'jobs/bad.json') == record
    finally:
        jobs.close()
