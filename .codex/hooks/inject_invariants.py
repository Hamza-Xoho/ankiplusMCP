"""inject_invariants.py — Codex SessionStart (startup|resume|clear|compact).

Re-states the build invariants deterministically, so they survive compaction.
Never blocks a session from starting (wrapper runs it with NONBLOCKING=1).
"""
import json

TEXT = """BUILD INVARIANTS (hook-enforced; if a hook blocks you, your change is wrong, do not route around it):
- INV-1 Frozen contract tests (listed in .codex/contract.sha256) are never edited, deleted, moved, skipped or xfailed. .codex/ and .agents/ are never changed by you.
- INV-2 No network import in src/cards/ except src/cards/write/direct.py.
- Every cards subcommand: stdout line 1 is OK|FINDINGS|ERROR, then <=40 lines/2000 chars; exit 0/1/2/3 (spec section 6). Never write outside the build folder.
- One phase per thread. Work only on the phase prompt you were given; stop at its gate and report. Do not start the next phase.
Where things are: docs/design-spec.md (how), docs/test-contract.md (named tests), docs/anki-v2-trd.md (tool requirements), docs/anki-v2-brief.md (why/what)."""

print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": TEXT}}))
