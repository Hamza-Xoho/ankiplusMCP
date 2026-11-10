"""Shared helpers for the /anki2 runtime guards (Claude Code PreToolUse hooks)."""
import hashlib
import json
import os
import sys


def load_payload():
    return json.loads(sys.stdin.read())


def project_dir(payload):
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def active_build(proj):
    """Return the active build folder path, or None when no /anki2 build is running."""
    pointer = os.path.join(proj, "builds", ".current")
    if not os.path.exists(pointer):
        return None
    with open(pointer, encoding="utf-8") as f:
        name = f.read().strip()
    if not name:
        return None
    return os.path.join(proj, "builds", name)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def block(message):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(2)


def guarded(main, name):
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        block(f"HOOK ERROR: {name} could not check this call ({type(e).__name__}: {e}). Blocking rather than passing.")
