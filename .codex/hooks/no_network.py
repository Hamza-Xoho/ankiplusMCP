"""no_network.py — Codex PreToolUse (mode 'pre') and PostToolUse (mode 'post') on apply_patch.

Invariant INV-2 (design spec §2): no network library is imported anywhere in
src/cards/ except src/cards/write/direct.py (which exists only if the Q-1 spike passed).

pre:  checks the lines a patch ADDS. Blocks before the change lands.
post: reads every touched file FROM DISK and checks the whole file, which also
      catches imports that were already there or arrived another way.
"""
import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _patch import block, load_payload, parse_patch, rel, repo_root  # noqa: E402

NET_MODULES = {"socket", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp", "websocket", "websockets",
               "ftplib", "smtplib", "telnetlib", "xmlrpc"}
LINE_RE = re.compile(r"^\s*(import|from)\s+(" + "|".join(sorted(NET_MODULES)) + r")\b")
ALLOWED = "src/cards/write/direct.py"

MSG = """BLOCKED: network import in {path} ({what}).
Invariant INV-2: only src/cards/write/direct.py may talk to the network, and only to 127.0.0.1:3141.
Everything else reads and writes files. Remove the import; if Anki access is needed, it belongs in the write step."""


def in_scope(path):
    return path.startswith("src/cards/") and path.endswith(".py") and path != ALLOWED


def scan_file(full):
    with open(full, encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        for line in src.splitlines():
            if LINE_RE.search(line):
                return line.strip()
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in NET_MODULES:
                    return f"import {a.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in NET_MODULES:
                return f"from {node.module} import ..."
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    p = load_payload()
    if p.get("tool_name") != "apply_patch":
        sys.exit(0)
    cwd = p.get("cwd") or os.getcwd()
    root = repo_root(cwd)
    command = (p.get("tool_input") or {}).get("command", "")
    for op in parse_patch(command):
        target = op["move_to"] or op["path"]
        path = rel(target, cwd, root)
        if not in_scope(path) or op["op"] == "delete":
            continue
        if mode == "pre":
            for line in op["added"]:
                if LINE_RE.search(line):
                    block(MSG.format(path=path, what=line.strip()))
        else:
            full = os.path.join(root, path)
            if os.path.exists(full):
                hit = scan_file(full)
                if hit:
                    block(MSG.format(path=path, what=hit))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        block(f"HOOK ERROR: no_network could not check this change ({type(e).__name__}: {e}). Blocking rather than passing.")
