"""Workspace containment, atomic persistence and cross-process revisions."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from filelock import FileLock
from cards.common.files import _write

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
        self.source_roots = tuple(Path(p).expanduser().resolve() for p in source_roots)

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
        if not any(resolved.is_relative_to(root) for root in self.source_roots):
            raise DomainError('SOURCE', 'Source is outside configured readable roots.', 'Launch with --source-root for the intended directory.')
        if not resolved.is_file() or resolved.stat().st_size > MAX_FILE:
            raise DomainError('SOURCE', 'Source missing or larger than 64 MiB.')
        return resolved

    def write_json(self, ident, relative, value):
        _write(self.path(ident, relative), json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n')

    def read_json(self, ident, relative):
        try:
            return json.loads(self.path(ident, relative).read_text())
        except (OSError, ValueError) as exc:
            raise DomainError('ARTIFACT', f'Cannot read {relative}.', 'List artifacts and use an existing JSON artifact.') from exc

    @contextmanager
    def lock(self, ident, name='workspace'):
        # A new FileLock per call: two threads in one process must still exclude each other.
        with FileLock(self.path(ident, f'.{name}.lock')):
            yield

    @contextmanager
    def edit(self, ident, expected_revision=None):
        with self.lock(ident):
            manifest = self.get(ident)
            if expected_revision is not None and manifest['revision'] != expected_revision:
                raise DomainError('STALE', f'Expected revision {expected_revision}; current revision is {manifest["revision"]}.', 'Read get_workspace and rebase the change.')
            yield manifest
            manifest['revision'] += 1
            self.write_json(ident, 'workspace.json', manifest)

    def get(self, ident):
        return self.read_json(ident, 'workspace.json')

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
        manifest = {'id':ident, 'mode':mode, 'revision':0, 'source':None}
        if source or text is not None:
            local = self.path(ident, 'input/source'+(source.suffix.lower() if source else '.txt'))
            local.parent.mkdir(parents=True)
            local.write_bytes(source.read_bytes() if source else text.encode())
            local.chmod(0o444)
            manifest['source'] = {'path':str(local), 'original':str(source) if source else None,
                                  'name':source.name if source else 'pasted.txt', 'sha256':digest(local)}
            self.write_json(ident, 'engine/build.json', {'source':{'path':str(local),'sha256':digest(local),'kind':'pdf' if local.suffix=='.pdf' else 'text'}})
        self.write_json(ident, 'workspace.json', manifest)
        return manifest

    def list(self, offset=0, limit=20):
        ids = sorted(p.name for p in self.root.iterdir() if p.is_dir() and not p.is_symlink() and (p/'workspace.json').is_file())
        return {'workspaces':[self.get(i) for i in ids[offset:offset+limit]], 'total':len(ids)}

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
