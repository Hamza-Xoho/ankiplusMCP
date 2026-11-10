"""block_local_http.py — PreToolUse on Bash. Spec D-7, TRD C-6, waste check W-5.

In L006, when a deck couldn't be created, Claude tried curl on three ports,
lsof, AppleScript and Python against 127.0.0.1, all blocked, at full context
each time. Anki is reached only through the mcp__anki__* tools; on a hard
error the skill stops and reports.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _guard import block, guarded, load_payload  # noqa: E402

LOCAL = re.compile(r"(127\.0\.0\.1|\blocalhost:|\b0\.0\.0\.0:|\[::1\])", re.IGNORECASE)

MSG = """BLOCKED: shell access to local ports is not used here.
Anki is reached only through the mcp__anki__* tools. If one failed with a hard error, stop:
tell the owner what failed and what he can do (e.g. open Anki), and offer the import file from cards write."""


def main():
    p = load_payload()
    if p.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = str((p.get("tool_input") or {}).get("command") or "")
    if LOCAL.search(cmd):
        block(MSG)
    sys.exit(0)


if __name__ == "__main__":
    guarded(main, "block_local_http")
