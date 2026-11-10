"""block_fork.py — PreToolUse on Agent. Spec D-7, TRD C-6, waste check W-3.

A forked subagent copies this whole conversation. In L006 the two forked
reviewers inherited ~141k tokens each and judged the cards against the author's
own summary. Reviewers must be the pinned project agents instead.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _guard import block, guarded, load_payload  # noqa: E402

MSG = """BLOCKED: forked subagents are not used in this workspace (they copy the whole conversation).
For card review use subagent_type "anki-maintainer" or "anki-student" with the packet's PROMPT.md path.
For anything else, use a fresh agent type such as "Explore" or "general-purpose"."""


def main():
    p = load_payload()
    if p.get("tool_name") != "Agent":
        sys.exit(0)
    agent_type = str((p.get("tool_input") or {}).get("subagent_type") or "").strip().lower()
    if agent_type == "fork":
        block(MSG)
    sys.exit(0)


if __name__ == "__main__":
    guarded(main, "block_fork")
