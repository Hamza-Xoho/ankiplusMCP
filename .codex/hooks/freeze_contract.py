"""freeze_contract.py — Codex PreToolUse on apply_patch|Bash.

Invariant INV-1 (design spec §1, test contract): frozen contract tests are never
edited, deleted, moved, skipped or marked xfail, and the agent never changes its
own guardrails in .codex/ or .agents/.

Frozen = listed in .codex/contract.sha256, which only the owner writes (by running
.codex/tools/freeze_contract.sh at a phase gate). Unfrozen contract tests (this
phase's, before its gate) may be edited, but may never contain skip/xfail.

Backstop: the phase gate re-checks every frozen file's SHA-256, so a change this
hook cannot see (e.g. a script that edits files) still fails the gate.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _patch import CONTRACT_DIR, PROTECTED, block, load_payload, parse_patch, rel, repo_root  # noqa: E402

SKIP_RE = re.compile(r"(pytest\.mark\.(skip|skipif|xfail)|pytest\.skip\(|pytest\.xfail\(|importorskip|unittest\.skip)")
WRITE_VERBS = re.compile(
    r"(\brm\b|\bmv\b|\bcp\b|\bsed\s+-i|\bperl\s+-p?i|\btee\b|\btruncate\b|\bunlink\b|\bln\b|\bchmod\b|\binstall\b|"
    r"\bgit\s+(rm|mv|checkout|restore|stash|reset|clean|apply)\b|\s-delete\b|\bpython3?\s+-c\b|write_text|write_bytes)"
)
GUARDED = re.compile(r"(tests/contract|\.codex/|\.agents/)")
REDIRECT_INTO = re.compile(r">>?\s*['\"]?[^\s;&|]*(tests/contract|\.codex/|\.agents/)")
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\|")

FROZEN_MSG = """BLOCKED: {path} is a frozen contract test (listed in .codex/contract.sha256).
Frozen tests encode the acceptance criteria, so a red test means the implementation is wrong, not the test.
Fix the code under src/cards/. If the requirement itself is wrong: stop, report it, and let the owner change the docs and unfreeze."""

GUARD_MSG = """BLOCKED: {path} is under .codex/ or .agents/. These are the owner’s build guardrails and repo skills.
Do not change them. If one is wrong, stop and report what and why."""

SKIP_MSG = """BLOCKED: contract tests may not be skipped or marked xfail ({path}).
A contract test must fail until the implementation is right. Write the test so it fails now, then make the code pass it."""

BASH_MSG = """BLOCKED: this shell command could modify tests/contract/ or .codex/.
Edit unfrozen contract tests with apply_patch only. Frozen tests and .codex/ are never changed by the agent.
Reading and running them (cat, rg, pytest) is fine."""


def frozen_set(root):
    path = os.path.join(root, ".codex", "contract.sha256")
    out = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    out.add(parts[1].lstrip("*").strip().replace(os.sep, "/"))
    return out


def main():
    p = load_payload()
    tool = p.get("tool_name", "")
    cwd = p.get("cwd") or os.getcwd()
    root = repo_root(cwd)
    command = (p.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str):
        command = " ".join(map(str, command))

    if tool == "apply_patch":
        frozen = frozen_set(root)
        for op in parse_patch(command):
            paths = [rel(op["path"], cwd, root)]
            if op["move_to"]:
                paths.append(rel(op["move_to"], cwd, root))
            for path in paths:
                if path.startswith(PROTECTED):
                    block(GUARD_MSG.format(path=path))
                if path in frozen:
                    block(FROZEN_MSG.format(path=path))
            src = paths[0]
            if src.startswith(CONTRACT_DIR) and any(SKIP_RE.search(l) for l in op["added"]):
                block(SKIP_MSG.format(path=src))
        sys.exit(0)

    if tool == "Bash":
        if REDIRECT_INTO.search(command):
            block(BASH_MSG)
        for segment in SEGMENT_SPLIT.split(command):
            if GUARDED.search(segment) and WRITE_VERBS.search(segment):
                block(BASH_MSG)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        block(f"HOOK ERROR: freeze_contract could not check this action ({type(e).__name__}: {e}). Blocking rather than passing.")
