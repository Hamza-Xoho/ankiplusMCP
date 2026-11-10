"""Launch-time defaults: where workspaces live and which directories may be read."""
import os
from pathlib import Path
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
