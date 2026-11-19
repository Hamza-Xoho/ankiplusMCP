"""Explicit cleanup of reproducible workspace previews, never permanent evidence."""
from pathlib import Path
from uuid import uuid4
from .coordinator import sha
from .store import DomainError,digest


class DerivedCleanup:
    def __init__(self,service):self.s=service

    def _files(self,workspace):
        root=self.s.store.path(workspace,'previews')
        if root.is_symlink():raise DomainError('PATH','Preview cleanup refuses symbolic links.')
        files=[]
        for raw in sorted(root.rglob('*')):
            if raw.is_symlink():raise DomainError('PATH','Preview cleanup refuses symbolic links.')
            if not raw.is_file():continue
            path=self.s.store.path(workspace,str(raw.relative_to(root.parent)))
            files.append({'artifact':str(path.relative_to(root.parent)),'sha256':digest(path),'size':path.stat().st_size})
            if len(files)>5000:raise DomainError('LIMIT','Too many preview files for one cleanup; retain them for manual inspection.')
        pointer=self.s.store.path(workspace,'latest-preview.json')
        if pointer.exists():files.append({'artifact':'latest-preview.json','sha256':digest(pointer),'size':pointer.stat().st_size})
        # Protect any preview unusually referenced as sole media by a local draft.
        referenced={m['path'] for c in self.s._cards(workspace) for m in c.get('media',[])}
        return [f for f in files if f['artifact'] not in referenced]

    def run(self,workspace,apply=False,expected_digest=None):
        with self.s.store.lock(workspace):
            files=self._files(workspace);version=sha(files)
            if apply:
                if expected_digest!=version:raise DomainError('STALE','Preview files changed; inspect a new cleanup preview.')
                for path in self.s.store.path(workspace,'jobs').glob('*.json'):
                    if self.s.jobs.get(workspace,path.stem)['status'] in ('queued','running'):
                        raise DomainError('BUSY','Wait for active workspace jobs before removing previews.')
                # Retain the exact deletion manifest before any unlink; interruption
                # leaves an inspectable partial cleanup and cannot touch history.
                self.s.store.write_json(workspace,'maintenance/cleanup-'+uuid4().hex+'.json',{'digest':version,'files':files})
                for f in files:self.s.store.path(workspace,f['artifact']).unlink()
            return {'applied':apply,'digest':version,'files':files[:10],'file_count':len(files),
                    'bytes':sum(f['size'] for f in files),'retention':'Sources, cards, media, jobs, reviews, quality packets and run history are retained.'}
