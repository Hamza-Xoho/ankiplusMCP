from pathlib import Path
from ankiplusmcp.store import Store
from ankiplusmcp.jobs import Jobs

SRC = Path(__file__).parents[2]/'src/ankiplusmcp'


def test_no_posix_only_locking():
    assert all('fcntl' not in p.read_text() for p in SRC.glob('*.py'))


def test_dead_owner_marks_job_interrupted_and_live_owner_does_not(tmp_path):
    store = Store(tmp_path, [tmp_path]); w = store.create('cards')['id']
    a, b = Jobs(store), Jobs(store)
    store.write_json(w, 'jobs/j1.json', {'id':'j1','owner':a.owner,'operation':'x','status':'running','progress':'','cancel_requested':False})
    assert b.get(w, 'j1')['status'] == 'running'
    a.close()
    assert not (tmp_path/f'.owner-{a.owner}.lock').exists()
    assert b.get(w, 'j1')['status'] == 'interrupted'
    b.close()
