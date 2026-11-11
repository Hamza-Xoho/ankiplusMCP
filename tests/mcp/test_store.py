import threading
from pathlib import Path
import pytest
from ankiplusmcp.store import Store, DomainError
from ankiplusmcp.jobs import Jobs


def test_revisions_paths_and_imports(tmp_path):
    sources = tmp_path/'sources'; sources.mkdir()
    (sources/'lecture.txt').write_text('hello')
    store = Store(tmp_path/'work', [sources])
    w = store.create('lecture', source_path=str(sources/'lecture.txt'))
    assert store.get(w['id'])['revision'] == 0
    with store.edit(w['id'], 0) as manifest:
        manifest['title'] = 'changed'
    with pytest.raises(DomainError, match='revision'):
        with store.edit(w['id'], 0): pass
    with pytest.raises(DomainError): store.path(w['id'], '../outside')
    (store.directory(w['id'])/'escape').symlink_to(sources, target_is_directory=True)
    with pytest.raises(DomainError): store.path(w['id'], 'escape/lecture.txt')
    with pytest.raises(DomainError): store.import_file(w['id'], '/etc/passwd')
    assert Path(w['source']['path']).read_text() == 'hello'
    with pytest.raises(DomainError): store.get('../sources')


def test_two_stores_serialize_mutations(tmp_path):
    a = Store(tmp_path/'work', [tmp_path]); w = a.create('cards')
    b = Store(tmp_path/'work', [tmp_path])
    def increment(store):
        for _ in range(10):
            with store.edit(w['id']) as m: m['counter'] = m.get('counter', 0)+1
    threads = [threading.Thread(target=increment, args=(s,)) for s in (a,b)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert a.get(w['id'])['counter'] == 20


def test_jobs_cancel_and_restart(tmp_path):
    store = Store(tmp_path/'work', [tmp_path]); w = store.create('cards')
    jobs = Jobs(store, workers=1)
    entered = threading.Event(); release = threading.Event()
    def operation(cancel, report):
        entered.set(); release.wait(5)
        if cancel(): raise DomainError('CANCELLED', 'cancelled', 'submit again')
        return {'done':True}
    first = jobs.submit(w['id'], 'test', operation)
    assert entered.wait(2)
    queued = jobs.submit(w['id'], 'queued', operation)
    jobs.cancel(w['id'], queued['id']); jobs.cancel(w['id'], first['id']); release.set()
    jobs.close()
    assert jobs.get(w['id'], first['id'])['status'] == 'cancelled'
    assert jobs.get(w['id'], queued['id'])['status'] == 'cancelled'
    store.write_json(w['id'], 'jobs/interrupted.json', {'id':'interrupted','status':'running','operation':'test','owner':'dead'})
    recovered = Jobs(store)
    assert recovered.get(w['id'], 'interrupted')['status'] == 'interrupted'
    recovered.close()


def test_cross_process_lock(tmp_path):
    import subprocess
    import sys
    import os
    store=Store(tmp_path/'work',[tmp_path]); w=store.create('cards')['id']
    script='''import sys
from ankiplusmcp.store import Store
s=Store(sys.argv[1],[])
for _ in range(12):
    with s.edit(sys.argv[2]) as m: m['counter']=m.get('counter',0)+1
'''
    processes=[subprocess.Popen([sys.executable,'-c',script,str(store.root),w],env=os.environ.copy()) for _ in range(2)]
    assert all(p.wait(timeout=10)==0 for p in processes)
    assert store.get(w)['counter']==24


def test_live_job_owner_not_recovered_by_second_server(tmp_path):
    store=Store(tmp_path/'work',[tmp_path]); w=store.create('cards')['id']
    first=Jobs(store); second=Jobs(store)
    entered=threading.Event(); release=threading.Event()
    def callback(cancel, report): entered.set(); release.wait(3); return {}
    job=first.submit(w,'test',callback); assert entered.wait(2)
    assert second.get(w,job['id'])['status']=='running'
    second.cancel(w,job['id']); release.set(); first.close(); second.close()
    assert store.read_json(w,f'jobs/{job["id"]}.json')['status']=='cancelled'
