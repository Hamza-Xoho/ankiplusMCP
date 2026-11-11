"""Launch-time defaults: where workspaces live, which directories may be read, and the card profile."""
from dataclasses import dataclass, replace
import os
from pathlib import Path
import tomllib
import platformdirs

APP = 'ankiplusmcp'
SOURCE_ROOTS_ENV = 'ANKIPLUS_SOURCE_ROOTS'


def default_workspace_root() -> Path:
    """Per-user data directory; never the working directory, which the host chooses."""
    return platformdirs.user_data_path(APP) / 'workspaces'


def configured_source_roots(flags, env):
    """Return (roots, origin) from --source-root flags or the environment, else None."""
    if flags:
        return [Path(p) for p in flags], 'flags'
    entries = [p for p in env.get(SOURCE_ROOTS_ENV, '').split(os.pathsep) if p]
    if entries:
        return [Path(p) for p in entries], 'env'
    return None


def safe_cwd_root(cwd: Path, home: Path):
    """The working directory as a source root, unless it would expose the whole disk or home."""
    resolved = Path(cwd).resolve()
    if resolved == Path(resolved.anchor) or resolved == Path(home).resolve():
        return None
    return cwd


@dataclass(frozen=True)
class Profile:
    """The conventions a deployment uses when a card or target does not state its own."""
    name: str
    note_type: str
    tag_root: str


PROFILES = {
    'default': Profile('default', 'Cloze', '#AnkiPlus'),
    'coldrecall': Profile('coldrecall', 'ColdRecall Cloze', '#ColdRecall'),
}
CONFIG_ENV = 'ANKIPLUS_CONFIG'
CONFIG_KEYS = {'profile', 'note_type', 'tag_root', 'browser'}


def default_config_path() -> Path:
    return platformdirs.user_config_path(APP) / 'config.toml'


def _named(name):
    if name not in PROFILES:
        raise ValueError(f'Unknown profile {name!r}; choose one of {", ".join(sorted(PROFILES))}.')
    return PROFILES[name]


def load_profile(profile_flag, config_path, env) -> Profile:
    """A --profile flag wins outright; otherwise the config file; otherwise the default profile."""
    if profile_flag:
        return _named(profile_flag)
    explicit = config_path or (Path(env[CONFIG_ENV]) if env.get(CONFIG_ENV) else None)
    path = explicit or default_config_path()
    if not Path(path).is_file():
        if explicit:
            raise ValueError(f'Config file not found: {explicit}')
        return PROFILES['default']
    try:
        data = tomllib.loads(Path(path).read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f'Config file {path} is not valid TOML: {exc}') from exc
    unknown = sorted(set(data) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f'Unknown config key {unknown[0]!r} in {path}; allowed: {", ".join(sorted(CONFIG_KEYS))}.')
    overrides = {key: data[key] for key in ('note_type', 'tag_root') if key in data}
    if any(not isinstance(value, str) or not value.strip() for value in overrides.values()):
        raise ValueError(f'note_type and tag_root in {path} must be non-empty text.')
    return replace(_named(data.get('profile', 'default')), **overrides)


BROWSER_CHOICES = ('auto', 'chromium', 'chrome')


def _valid_browser(value, origin):
    if isinstance(value, str) and (value in BROWSER_CHOICES or (Path(value).is_absolute() and Path(value).is_file())):
        return value
    raise ValueError(f'Invalid browser {value!r} from {origin}; use auto, chromium, chrome, or the absolute path of an existing browser program.')


def load_browser(browser_flag, config_path, env) -> str:
    """A --browser flag wins outright; otherwise the config file; otherwise `auto`."""
    if browser_flag:
        return _valid_browser(browser_flag, '--browser')
    explicit = config_path or (Path(env[CONFIG_ENV]) if env.get(CONFIG_ENV) else None)
    path = explicit or default_config_path()
    if not Path(path).is_file():
        if explicit:
            raise ValueError(f'Config file not found: {explicit}')
        return 'auto'
    try:
        data = tomllib.loads(Path(path).read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f'Config file {path} is not valid TOML: {exc}') from exc
    return _valid_browser(data['browser'], str(path)) if 'browser' in data else 'auto'
