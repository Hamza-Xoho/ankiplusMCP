"""Append-only run records; the search index is a disposable projection."""
import json
import hashlib
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from .run_models import EventRecord, Run, RunEvent, RunSnapshot, SourceSelection
from .store import DomainError


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise DomainError('RUN', 'Invalid run or workspace identifier.')
    return value


def _encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def _sync_directory(directory: Path) -> None:
    # Windows does not expose the POSIX directory fsync operation.
    if os.name != 'nt':
        fd = os.open(directory, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _publish(path: Path, value: dict) -> None:
    data = _encoded(value)
    fd, temporary = tempfile.mkstemp(prefix='.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


class RunStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.directory = self.root / 'runs'
        if self.directory.is_symlink():
            raise DomainError('RUN', 'Run root cannot be a symbolic link.')
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        path = self.directory / _identifier(run_id)
        if path.is_symlink() or not path.resolve().is_relative_to(self.directory):
            raise DomainError('RUN', 'Run directory escapes the data root.')
        if not path.is_dir():
            raise DomainError('RUN', 'Run does not exist.')
        return path

    def _lock(self, path: Path):
        return FileLock(path / '.events.lock', timeout=5)

    def _records(self, path: Path) -> list[EventRecord]:
        try:
            records = []
            for number, file in enumerate(sorted(path.glob('[0-9]' * 20 + '.json')), 1):
                if file.is_symlink():
                    raise ValueError('event is a symbolic link')
                record = EventRecord.model_validate_json(file.read_bytes())
                if record.sequence != number or file.stem != f'{number:020d}':
                    raise ValueError('noncontiguous event history')
                records.append(record)
            if not records or records[0].kind != 'run_started':
                raise ValueError('missing run start')
            return records
        except (OSError, ValueError) as exc:
            raise DomainError('RUN_CORRUPT', 'Run history is invalid; preserve it for recovery.') from exc

    def start(self, workspace: str, selection: SourceSelection, config_version: int) -> Run:
        if type(config_version) is not int or config_version < 1:
            raise DomainError('RUN', 'A new run requires a positive configuration version.')
        return self._start(workspace, selection, config_version, uuid4().hex)

    def _start(self, workspace, selection, config_version, ident):
        workspace = _identifier(workspace)
        selection = SourceSelection.model_validate(selection)
        event = EventRecord(sequence=1, kind='run_started', payload={
            'workspace': workspace, 'selection': selection.model_dump(), 'config_version': config_version})
        snapshot = RunSnapshot(id=ident, workspace=workspace, selection=selection,
                               config_version=config_version, events=[event])
        staging = self.directory / ('.staging-' + ident)
        staging.mkdir()
        try:
            _publish(staging / f'{1:020d}.json', event.model_dump())
            os.replace(staging, self.directory / ident)
            _sync_directory(self.directory)
        except BaseException:
            # A killed process may leave staging. It is never indexed as a run.
            if staging.exists():
                for child in staging.iterdir():
                    child.unlink()
                staging.rmdir()
            raise
        return snapshot

    def import_legacy(self, workspace: str, directory: Path) -> list[RunSnapshot]:
        """Copy supplied evidence without changing or upgrading the legacy record."""
        _identifier(workspace)
        directory = Path(directory).resolve()
        def read(path):
            if path.is_symlink() or not path.resolve().is_relative_to(directory):
                raise DomainError('RUN', 'Legacy artifact escapes its workspace.')
            return json.loads(path.read_bytes())
        manifest = read(directory / 'workspace.json')
        if manifest.get('id') != workspace:
            raise DomainError('RUN', 'Legacy workspace identity does not match.')
        source = manifest.get('source') or {}
        selected = SourceSelection(source_hash=source.get('sha256'), label=workspace)
        plans = sorted((directory / 'write').glob('*/plan.json')) or [None]
        imported = []
        with FileLock(self.directory / '.imports.lock', timeout=5):
            for path in plans:
                plan = read(path) if path else None
                results_path = path.parent / 'external-results.json' if path else None
                results = read(results_path) if results_path and results_path.exists() else None
                evidence = {'workspace': workspace, 'manifest': manifest, 'plan': plan, 'results': results,
                            'legacy_plan_id': path.parent.name if path else None}
                key = hashlib.sha256(_encoded(evidence)).hexdigest()
                ident = 'legacy-' + key
                if not (self.directory / ident).exists():
                    self._start(workspace, selected, None, ident)
                run = self.read(ident)
                timestamp = run.events[0].timestamp
                self.save_snapshot(ident, 'legacy-evidence', evidence)
                self.append(ident, RunEvent(id='import-' + key, timestamp=timestamp, kind='legacy_import',
                                           payload={'legacy_plan_id': evidence['legacy_plan_id'],
                                                    'config_version_known': False,
                                                    'evidence_origin': 'caller_supplied',
                                                    'independently_verified': False}))
                for number, result in enumerate((results or {}).get('results', [])):
                    self.append(ident, RunEvent(id=f'result-{number}', timestamp=timestamp, kind='legacy_result',
                                               payload={**result, 'evidence_origin': 'caller_supplied',
                                                        'independently_verified': False}))
                imported.append(self.read(ident))
        return imported

    def append(self, run_id: str, event: RunEvent) -> int:
        path = self._path(run_id)
        event = RunEvent.model_validate(event)
        with self._lock(path):
            records = self._records(path)
            for previous in records:
                if previous.id == event.id:
                    prior = previous.model_dump(exclude={'sequence'})
                    if prior != event.model_dump():
                        raise DomainError('CONFLICT', 'Conflicting reuse of an event identifier.')
                    return previous.sequence
            record = EventRecord(**event.model_dump(), sequence=len(records) + 1)
            _publish(path / f'{record.sequence:020d}.json', record.model_dump())
            return record.sequence

    def read(self, run_id: str) -> RunSnapshot:
        path = self._path(run_id)
        with self._lock(path):
            records = self._records(path)
            initial = records[0].payload
            try:
                return RunSnapshot(id=run_id, workspace=initial['workspace'],
                                   selection=SourceSelection.model_validate(initial['selection']),
                                   config_version=initial['config_version'], events=records)
            except (KeyError, ValueError) as exc:
                raise DomainError('RUN_CORRUPT', 'Invalid initial run record.') from exc

    def save_snapshot(self, run_id: str, name: str, value: dict) -> str:
        path = self._path(run_id)
        _identifier(name)
        with self._lock(path):
            directory = path / 'snapshots'
            if directory.is_symlink():
                raise DomainError('RUN', 'Snapshot directory cannot be a symbolic link.')
            directory.mkdir(exist_ok=True)
            target = directory / (name + '.json')
            data = _encoded(value)
            if target.exists() or target.is_symlink():
                if target.is_symlink() or target.read_bytes() != data:
                    raise DomainError('CONFLICT', 'Snapshot version already exists with different content.')
            else:
                _publish(target, value)
            return str(target.relative_to(self.root))
