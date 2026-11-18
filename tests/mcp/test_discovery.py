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
