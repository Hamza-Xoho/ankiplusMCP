"""Shared helpers for Codex hooks: read the payload, parse apply_patch text, find the repo root."""
import json
import os
import sys

CONTRACT_DIR = "tests/contract/"
PROTECTED = (".codex/", ".agents/")


def load_payload():
    """Read the hook payload from stdin. Any failure is a hard error (caller exits 2)."""
    raw = sys.stdin.read()
    return json.loads(raw)


def repo_root(start):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(start or os.getcwd())
        d = parent


def rel(path, cwd, root):
    """Path relative to the repo root, with forward slashes."""
    p = path if os.path.isabs(path) else os.path.join(cwd, path)
    p = os.path.normpath(p)
    try:
        r = os.path.relpath(p, root)
    except ValueError:
        r = p
    return r.replace(os.sep, "/")


def parse_patch(text):
    """Return a list of ops: {op: add|update|delete, path, move_to, added: [lines]}.

    apply_patch format:
      *** Begin Patch
      *** Add File: path        (following lines start with '+')
      *** Update File: path     (optional '*** Move to: new'), hunks with '+'/'-'/' ' lines
      *** Delete File: path
      *** End Patch
    """
    ops = []
    cur = None
    for line in text.splitlines():
        if line.startswith("*** Add File: "):
            cur = {"op": "add", "path": line[len("*** Add File: "):].strip(), "move_to": None, "added": []}
            ops.append(cur)
        elif line.startswith("*** Update File: "):
            cur = {"op": "update", "path": line[len("*** Update File: "):].strip(), "move_to": None, "added": []}
            ops.append(cur)
        elif line.startswith("*** Delete File: "):
            cur = {"op": "delete", "path": line[len("*** Delete File: "):].strip(), "move_to": None, "added": []}
            ops.append(cur)
        elif line.startswith("*** Move to: ") and cur is not None:
            cur["move_to"] = line[len("*** Move to: "):].strip()
        elif line.startswith("*** "):
            continue
        elif cur is not None and line.startswith("+"):
            cur["added"].append(line[1:])
    return ops


def block(message):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(2)
