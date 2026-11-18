"""Workspace containment, atomic persistence and cross-process revisions."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from datetime import datetime, timezone
from filelock import FileLock, Timeout
from cards.common.files import atomic_write

MAX_FILE = 64 * 1024 * 1024

class DomainError(Exception):
    def __init__(self, code, message, remedy='Correct the input and retry.'):
        self.code, self.message, self.remedy = code, message, remedy
        super().__init__(f'{code}: {message}')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Store:
    def __init__(self, root, source_roots):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        # None means "not resolved yet": the server asks the client on the first tool call.
        self.source_roots = None
        self.source_roots_origin = 'unresolved'
        if source_roots is not None:
            self.set_source_roots(source_roots, 'flags')

    def set_source_roots(self, paths, origin):
        self.source_roots = tuple(Path(p).expanduser().resolve() for p in paths)
        self.source_roots_origin = origin

    def directory(self, ident):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', ident):
            raise DomainError('PATH', 'Invalid workspace ID.')
        raw = self.root / ident
        if raw.is_symlink() or not raw.is_dir():
            raise DomainError('WORKSPACE', 'Workspace not found.', 'Use list_workspaces or create_workspace.')
        return raw

    def path(self, ident, relative):
        root = self.directory(ident)
        if not relative or Path(relative).is_absolute():
            raise DomainError('PATH', 'Use a relative artifact ID.')
        raw = root / relative
        if '..' in Path(relative).parts or any(p.is_symlink() for p in [raw, *raw.parents] if p != self.root):
            raise DomainError('PATH', 'Artifact path or symlink is outside the allowed boundary.')
        resolved = raw.resolve()
        if not resolved.is_relative_to(root):
            raise DomainError('PATH', 'Artifact escapes the workspace.')
        return resolved

    def source(self, filename):
        raw = Path(filename).expanduser()
        if not raw.is_absolute():
            raise DomainError('SOURCE', 'Source path must be absolute.')
        resolved = raw.resolve()
        roots = self.source_roots or ()
        if not roots:
            raise DomainError('SOURCE', 'No readable source roots are configured.', 'Launch with --source-root <directory> or set ANKIPLUS_SOURCE_ROOTS.')
        if not any(resolved.is_relative_to(root) for root in roots):
            raise DomainError('SOURCE', 'Source is outside configured readable roots.', 'Launch with --source-root for the intended directory.')
        if not resolved.is_file() or resolved.stat().st_size > MAX_FILE:
            raise DomainError('SOURCE', 'Source missing or larger than 64 MiB.')
        return resolved

    def write_json(self, ident, relative, value):
        atomic_write(self.path(ident, relative), json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n')

    def read_json(self, ident, relative):
        try:
            return json.loads(self.path(ident, relative).read_text())
        except (OSError, ValueError) as exc:
            raise DomainError('ARTIFACT', f'Cannot read {relative}.', 'List artifacts and use an existing JSON artifact.') from exc

    @contextmanager
    def lock(self, ident, name='workspace', *, timeout=5):
        # A new FileLock per call: two threads in one process must still exclude each other.
        try:
            with FileLock(self.path(ident, f'.{name}.lock'), timeout=timeout):
                yield
        except Timeout as exc:
            raise DomainError('BUSY', 'Workspace is busy.', 'Retry after the active operation releases its lock.') from exc

    @contextmanager
    def edit(self, ident, expected_revision=None, *, artifact=False):
        with self.lock(ident):
            manifest = self.get(ident)
            if expected_revision is not None and manifest['revision'] != expected_revision:
                raise DomainError('STALE', f'Expected revision {expected_revision}; current revision is {manifest["revision"]}.', 'Read get_workspace and rebase the change.')
            yield manifest
            key = 'artifact_revision' if artifact else 'revision'
            manifest[key] = manifest.get(key, 0) + 1
            manifest['updated'] = datetime.now(timezone.utc).isoformat()
            self.write_json(ident, 'workspace.json', manifest)

    @contextmanager
    def artifact_work(self, ident, *, inputs=(), source=None, cancel=None, publish=None):
        """Snapshot inputs, release the lock for native work, validate on publication."""
        with self.lock(ident):
            state = self.get(ident)
            original_source = state.get('source')
            if source is not None and source != original_source:
                raise DomainError('SOURCE_CHANGED', 'Source changed before artifact work started.')
            fingerprints = {name: digest(self.path(ident, name)) for name in inputs}
        if cancel and cancel():
            raise DomainError('CANCELLED', 'Cancelled before artifact work.')
        yield state
        with self.lock(ident):
            current = self.get(ident)
            if cancel and cancel():
                raise DomainError('CANCELLED', 'Cancelled before artifact publication.')
            if current.get('source') != original_source:
                raise DomainError('SOURCE_CHANGED', 'Source changed during artifact work.')
            if original_source and digest(Path(original_source['path'])) != original_source['sha256']:
                raise DomainError('SOURCE_CHANGED', 'Source snapshot changed during artifact work.')
            if any(digest(self.path(ident, name)) != sha for name, sha in fingerprints.items()):
                raise DomainError('ARTIFACT_CHANGED', 'Artifact input changed during native work.')
            if publish is not None:
                publish()
            current['artifact_revision'] = current.get('artifact_revision', 0) + 1
            current['updated'] = datetime.now(timezone.utc).isoformat()
            self.write_json(ident, 'workspace.json', current)

    def get(self, ident):
        manifest = self.read_json(ident, 'workspace.json')
        manifest.setdefault('created', None)
        manifest.setdefault('updated', None)
        source = manifest.get('source') or {}
        manifest.setdefault('label', source.get('name') or ('Cards' if manifest.get('mode')=='cards' else 'Lecture'))
        return manifest

    def create(self, mode, source_path=None, text=None):
        if mode not in ('lecture', 'cards'):
            raise DomainError('MODE', 'Mode must be lecture or cards.')
        source = self.source(source_path) if source_path else None
        if source and source.suffix.lower() not in ('.pdf','.txt','.md','.markdown'):
            raise DomainError('SOURCE', 'Use PDF, text or Markdown.')
        if source and text is not None:
            raise DomainError('SOURCE', 'Supply source_path or text, not both.')
        if text is not None and (not isinstance(text, str) or len(text.encode()) > MAX_FILE):
            raise DomainError('SOURCE', 'Text must be a string under 64 MiB.')
        ident = uuid.uuid4().hex
        (self.root/ident).mkdir()
        now = datetime.now(timezone.utc).isoformat()
        manifest = {'id':ident, 'mode':mode, 'revision':0, 'source':None,
                    'created':now, 'updated':now, 'label':source.name if source else ('Pasted text' if text is not None else 'Cards')}
        if source or text is not None:
            local = self.path(ident, 'input/source'+(source.suffix.lower() if source else '.txt'))
            local.parent.mkdir(parents=True)
            local.write_bytes(source.read_bytes() if source else text.encode())
            local.chmod(0o444)
            manifest['source'] = {'path':str(local), 'original':str(source) if source else None,
                                  'name':source.name if source else 'pasted.txt', 'sha256':digest(local)}
        self.write_json(ident, 'workspace.json', manifest)
        return manifest

    def list(self, offset=0, limit=20):
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:
            raise DomainError('LIMIT','Use a nonnegative offset and a limit between 1 and 100.')
        ids = sorted(p.name for p in self.root.iterdir() if p.is_dir() and not p.is_symlink() and (p/'workspace.json').is_file())
        items=sorted((self.get(ident) for ident in ids),key=lambda item:(item.get('updated') or item.get('created') or '', item['id']),reverse=True)
        end=offset+limit
        return {'workspaces':items[offset:end], 'total':len(items), 'next_offset':end if end<len(items) else None}

    def import_file(self, ident, filename):
        source = self.source(filename)
        suffix = source.suffix.lower()
        if suffix not in ('.png','.jpg','.jpeg','.webp'):
            raise DomainError('IMAGE', 'Import a PNG, JPEG or WebP image.')
        from PIL import Image
        try:
            with Image.open(source) as im:
                if im.width*im.height > 20_000_000: raise ValueError('too many pixels')
                im.verify()
        except Exception as exc:
            raise DomainError('IMAGE', 'Image invalid or exceeds 20 million pixels.') from exc
        relative = f'media/{uuid.uuid4().hex}{suffix}'
        path = self.path(ident, relative); path.parent.mkdir(exist_ok=True)
        path.write_bytes(source.read_bytes())
        return relative
