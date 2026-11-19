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


def test_shutdown_is_bounded_and_retains_owner_lease_until_running_work_stops(tmp_path):
    from threading import Event
    import time
    started=Event();release=Event()
    store=Store(tmp_path,[tmp_path]);w=store.create('cards')['id'];jobs=Jobs(store);observer=Jobs(store)
    def slow(cancel,progress):
        started.set();release.wait(5);return {'synthetic':True}
    job=jobs.submit(w,'slow',slow);assert started.wait(2)
    try:
        before=time.monotonic();jobs.close(timeout=.05)
        assert time.monotonic()-before<.5
        assert observer.get(w,job['id'])['status']=='running'
        assert observer.get(w,job['id'])['cancel_requested'] is True
    finally:
        release.set()
        for _ in range(200):
            if not jobs.lease_path.exists():break
            time.sleep(.01)
        observer.close()
    assert not jobs.lease_path.exists()
    assert jobs.get(w,job['id'])['status']=='cancelled'
