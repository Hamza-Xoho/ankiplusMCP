"""Explicit versioned preferences; run feedback never implicitly calls this store."""
from pathlib import Path
from typing import Literal
from uuid import uuid4

from filelock import FileLock
from pydantic import Field

from .models import Identifier, Model, Positive
from .runs import _encoded, _identifier, _publish
from .store import DomainError


class UserConfig(Model):
    schema_version: Literal[1] = 1
    config_version: Positive = 1
    onboarding_version: int = Field(default=0, ge=0)
    onboarding_complete: bool = False
    health_checks: dict[str, str] = Field(default_factory=dict)
    data_root: str
    source_roots: list[str] = Field(default_factory=list)
    source_materials: list[str] = Field(default_factory=list)
    selected_decks: list[str] = Field(default_factory=list)
    profile: str = 'default'
    note_type: str = 'Cloze'
    tag_root: str = '#AnkiPlus'
    review_mode: Literal['manual', 'automatic'] = 'manual'
    uncertain_match: Literal['pending', 'reuse', 'create'] = 'pending'


class ConfigChange(Model):
    id: Identifier
    expected_version: Positive
    before: UserConfig
    after: UserConfig
    changed_keys: list[str]


class ConfigStore:
    MUTABLE = {'source_roots', 'source_materials', 'selected_decks', 'profile',
               'note_type', 'tag_root', 'review_mode', 'uncertain_match'}

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.directory = self.root / 'configuration'
        if self.directory.is_symlink():
            raise DomainError('CONFIG', 'Configuration directory cannot be a symbolic link.')
        self.directory.mkdir(parents=True, exist_ok=True)
        for name in ('versions', 'proposals'):
            path = self.directory / name
            if path.is_symlink():
                raise DomainError('CONFIG', 'Configuration files cannot be outside the data root.')
            path.mkdir(exist_ok=True)
        self.pointer = self.directory / 'current.json'
        with self._lock():
            if not self.pointer.exists():
                value = UserConfig(data_root=str(self.root))
                target = self.directory / 'versions/00000000000000000001.json'
                if target.exists() and target.read_bytes() != _encoded(value.model_dump()):
                    raise DomainError('CONFIG', 'Unpublished initial configuration requires recovery.')
                _publish(target, value.model_dump())
                _publish(self.pointer, {'version': 1, 'change_id': None})

    def _lock(self):
        return FileLock(self.directory / '.configuration.lock', timeout=5)

    def _json(self, path):
        import json
        if path.is_symlink():
            raise DomainError('CONFIG', 'Configuration file cannot be a symbolic link.')
        try:
            return json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise DomainError('CONFIG', 'Configuration is unreadable; preserve it for recovery.') from exc

    def _current(self):
        pointer = self._json(self.pointer)
        return self.read_version(pointer['version']), pointer

    def read(self) -> UserConfig:
        with self._lock():
            return self._current()[0]

    def read_version(self, version: int) -> UserConfig:
        if type(version) is not int or version < 1:
            raise DomainError('CONFIG', 'Invalid configuration version.')
        return UserConfig.model_validate(self._json(self.directory / 'versions' / f'{version:020d}.json'))

    def propose(self, changes: dict, expected_version: int) -> ConfigChange:
        if set(changes) - self.MUTABLE:
            raise DomainError('CONFIG', 'Only explicit preferences can be changed here.')
        with self._lock():
            current, _ = self._current()
            if current.config_version != expected_version:
                raise DomainError('STALE', 'Configuration changed; review the current preferences first.')
            # Avoid reusing a version published before an interrupted pointer swap.
            highest = max(int(p.stem) for p in (self.directory / 'versions').glob('[0-9]' * 20 + '.json'))
            after = UserConfig.model_validate({**current.model_dump(), **changes, 'config_version': highest + 1})
            changed = sorted(k for k in changes if getattr(current, k) != getattr(after, k))
            if not changed:
                raise DomainError('CONFIG', 'No preferences changed.')
            proposal = ConfigChange(id=uuid4().hex, expected_version=expected_version,
                                    before=current, after=after, changed_keys=changed)
            _publish(self.directory / 'proposals' / (proposal.id + '.json'), proposal.model_dump())
            return proposal

    def confirm(self, change_id: str) -> UserConfig:
        _identifier(change_id)
        with self._lock():
            current, pointer = self._current()
            if pointer.get('change_id') == change_id:
                return current
            proposal = ConfigChange.model_validate(self._json(self.directory / 'proposals' / (change_id + '.json')))
            if current != proposal.before or current.config_version != proposal.expected_version:
                raise DomainError('STALE', 'Configuration changed since this proposal was shown.')
            target = self.directory / 'versions' / f'{proposal.after.config_version:020d}.json'
            if target.exists() and target.read_bytes() != _encoded(proposal.after.model_dump()):
                raise DomainError('CONFLICT', 'Configuration version was already published with different values.')
            _publish(target, proposal.after.model_dump())
            _publish(self.pointer, {'version': proposal.after.config_version, 'change_id': proposal.id})
            return proposal.after
