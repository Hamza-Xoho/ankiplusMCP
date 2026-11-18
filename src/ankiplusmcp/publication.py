"""Short-lock publication of captured inputs; multiple renames are not a transaction."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import uuid
from .store import DomainError, digest

@dataclass(frozen=True)
class ArtifactTicket:
    workspace: str
    manifest: dict
    expected_revision: int | None
    inputs: tuple[tuple[str,str,str], ...]
    bind_source: bool

class ArtifactPublisher:
    def __init__(self, store): self.store=store

    def capture(self, workspace, *, inputs=None, expected_revision=None, bind_source=True):
        with self.store.lock(workspace):
            return self.capture_locked(workspace,inputs=inputs,expected_revision=expected_revision,bind_source=bind_source)

    def capture_locked(self, workspace, *, inputs=None, expected_revision=None, bind_source=True):
        state=self.store.get(workspace)
        if expected_revision is not None and state['revision']!=expected_revision: raise DomainError('STALE','Card revision changed.')
        if bind_source: self._source(state.get('source'))
        fingerprints=[]
        for path,code in (inputs or {}).items():
            try: sha=digest(self.store.path(workspace,path))
            except OSError as exc: raise DomainError(code,'Captured input is missing.') from exc
            fingerprints.append((path,sha,code))
        return ArtifactTicket(workspace,state,expected_revision,tuple(fingerprints),bind_source)

    def _source(self, source):
        if source:
            try: valid=digest(Path(source['path']))==source['sha256']
            except OSError: valid=False
            if not valid: raise DomainError('SOURCE_CHANGED','Source snapshot changed.')

    def _destination(self, workspace, relative):
        path=self.store.path(workspace,relative)
        if Path(relative).parts[0]=='input' or relative=='workspace.json':
            raise DomainError('PATH','Publication cannot replace source input or workspace manifest.')
        return path

    @contextmanager
    def temporary(self, workspace, target):
        path=self._destination(workspace,target)
        relative=str(Path(target).with_name('.'+path.stem+'-'+uuid.uuid4().hex+path.suffix))
        temporary=self.store.path(workspace,relative); temporary.parent.mkdir(parents=True,exist_ok=True)
        try: yield relative
        finally: temporary.unlink(missing_ok=True)

    def publish(self, ticket, *, replacements=None, json_records=None, manifest_changes=None, cancel=None):
        w=ticket.workspace; replacements=replacements or {}; json_records=json_records or {}; changes=manifest_changes or {}
        if set(changes)-{'source_engine'}: raise DomainError('PUBLICATION','Unsupported manifest changes.')
        with self.store.lock(w):
            state=self.store.get(w)
            if cancel and cancel(): raise DomainError('CANCELLED','Cancelled before publication.')
            if ticket.expected_revision is not None and state['revision']!=ticket.expected_revision: raise DomainError('STALE','Card revision changed.')
            if ticket.bind_source:
                if state.get('source')!=ticket.manifest.get('source'): raise DomainError('SOURCE_CHANGED','Source identity changed.')
                self._source(state.get('source'))
            for path,sha,code in ticket.inputs:
                try: valid=digest(self.store.path(w,path))==sha
                except OSError: valid=False
                if not valid: raise DomainError(code,'Captured input changed.')
            pairs=[(self.store.path(w,src),self._destination(w,dst)) for src,dst in replacements.items()]
            for src,_ in pairs:
                if not src.is_file(): raise DomainError('ARTIFACT','Staged input is missing.')
            for relative in json_records: self._destination(w,relative)
            # Validate JSON before the first side effect.
            import json
            for value in json_records.values(): json.dumps(value,allow_nan=False)
            for src,dst in pairs:
                dst.parent.mkdir(parents=True,exist_ok=True); os.replace(src,dst)
            for relative,value in json_records.items(): self.store.write_json(w,relative,value)
            state.update(changes); state['artifact_revision']=state.get('artifact_revision',0)+1
            state['updated']=datetime.now(timezone.utc).isoformat()
            self.store.write_json(w,'workspace.json',state)
