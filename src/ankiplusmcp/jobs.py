"""Persistent, cancellable jobs; owner leases distinguish restart from concurrency."""
from concurrent.futures import ThreadPoolExecutor
import uuid
from filelock import FileLock, Timeout
from .store import DomainError

class Jobs:
    def __init__(self, store, workers=2):
        self.store = store
        self.owner = uuid.uuid4().hex
        self.lease_path = store.root/f'.owner-{self.owner}.lock'
        self.lease = FileLock(self.lease_path)
        self.lease.acquire()
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='ankiplus')

    def submit(self, workspace, operation, callback):
        ident = uuid.uuid4().hex
        record = {'id':ident,'owner':self.owner,'operation':operation,'status':'queued','progress':'queued','cancel_requested':False}
        self.store.write_json(workspace, f'jobs/{ident}.json', record)
        self.pool.submit(self._run, workspace, ident, callback)
        return record

    def _update(self, workspace, ident, **changes):
        with self.store.lock(workspace, 'jobs'):
            record = self.store.read_json(workspace, f'jobs/{ident}.json')
            record.update(changes)
            self.store.write_json(workspace, f'jobs/{ident}.json', record)
        return record

    def _run(self, workspace, ident, callback):
        cancelled = lambda: self.store.read_json(workspace, f'jobs/{ident}.json')['cancel_requested']
        if cancelled():
            self._update(workspace, ident, status='cancelled', progress='cancelled before start'); return
        self._update(workspace, ident, status='running', progress='operation running')
        report = lambda text: self._update(workspace, ident, progress=text)
        try:
            result = callback(cancelled, report)
            committed=result.pop('_committed',False) if isinstance(result,dict) else False
            stopped=cancelled() and not committed
            self._update(workspace, ident, status='cancelled' if stopped else 'completed',
                         result=None if stopped else result, progress='finished')
        except Exception as exc:
            error = {'code':getattr(exc,'code','OPERATION'), 'message':str(exc),
                     'remedy':getattr(exc,'remedy','Inspect workspace artifacts and retry explicitly.')}
            self._update(workspace, ident, status='cancelled' if cancelled() else 'failed', error=error, progress='stopped')

    def get(self, workspace, ident):
        if not ident or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in ident):
            raise DomainError('JOB', 'Invalid job ID.')
        record = self.store.read_json(workspace, f'jobs/{ident}.json')
        if record['status'] in ('queued','running') and record['owner'] != self.owner:
            lease_path = self.store.root/f'.owner-{record["owner"]}.lock'
            if not lease_path.exists(): alive = False
            else:
                probe = FileLock(lease_path)
                try:
                    probe.acquire(timeout=0)
                    probe.release()
                    alive = False
                except Timeout: alive = True
            if not alive:
                record = self._update(workspace, ident, status='interrupted', progress='owner stopped; retry explicitly')
        return record

    def cancel(self, workspace, ident):
        record = self.get(workspace, ident)
        if record['status'] in ('running','queued'):
            return self._update(workspace, ident, cancel_requested=True)
        return record

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=False)
        self.lease.release()
        self.lease_path.unlink(missing_ok=True)
