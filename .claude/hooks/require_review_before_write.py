"""require_review_before_write.py — PreToolUse on the Anki write tools. Spec D-5, CON-9, TRD C-6.

No card reaches Anki without passing review. There is no human gate (ADR-9),
so this hook and `cards write` are the gate.

While an /anki2 build is active (builds/.current exists), a write is allowed only if
build.json has gate.status == "passed" AND drafts.jsonl's SHA-256 still equals
gate.drafts_sha256. With no active build (manual use of the Anki tools), it allows.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _guard import active_build, block, guarded, load_payload, project_dir, sha256_file  # noqa: E402

WRITE_TOOLS = {"add_notes", "add_note", "update_note_fields", "update_notes"}

NOT_PASSED = """BLOCKED: this /anki2 build has not passed its review gate (build.json gate.status = {status}).
Run: .venv/bin/cards gate --build {build}. If it fails, fix the findings and re-review; never write unreviewed cards."""

STALE = """BLOCKED: drafts.jsonl changed after the gate passed, so the cards about to be written are not the reviewed ones.
Re-run: .venv/bin/cards check, the review round if needed, then .venv/bin/cards gate --build {build}."""


def main():
    p = load_payload()
    tool = str(p.get("tool_name") or "")
    if not (tool.startswith("mcp__") and tool.rsplit("__", 1)[-1] in WRITE_TOOLS):
        sys.exit(0)
    build = active_build(project_dir(p))
    if build is None:
        sys.exit(0)
    state_path = os.path.join(build, "build.json")
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    gate = state.get("gate") or {}
    status = gate.get("status") or "pending"
    name = os.path.basename(build)
    if status != "passed":
        block(NOT_PASSED.format(status=status, build=f"builds/{name}"))
    drafts = os.path.join(build, "drafts.jsonl")
    if not os.path.exists(drafts) or sha256_file(drafts) != gate.get("drafts_sha256"):
        block(STALE.format(build=f"builds/{name}"))
    sys.exit(0)


if __name__ == "__main__":
    guarded(main, "require_review_before_write")
