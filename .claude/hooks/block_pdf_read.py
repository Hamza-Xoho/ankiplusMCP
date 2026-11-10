"""block_pdf_read.py — PreToolUse on Read. Spec D-7, TRD C-6, waste check W-2.

Reading a lecture PDF directly loads every page as an image (~33k tokens for
24 slides in L006) and keeps them in context. The cards CLI extracts text once.

Scope: CARDS_PDF_GUARD=build (default) blocks only while an /anki2 build is
active (builds/.current exists), so the old /anki keeps working during the
build. Phase 7 sets CARDS_PDF_GUARD=always in .claude/settings.json "env".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _guard import active_build, block, guarded, load_payload, project_dir  # noqa: E402

MSG = """BLOCKED: lecture PDFs are not read directly (every page becomes an image in context).
Use: .venv/bin/cards extract --build <build>, then .venv/bin/cards source --build <build> --all (once) or --slides N.
For a slide whose figure you must see: cards source --build <build> --page-image N, then Read that PNG."""


def main():
    p = load_payload()
    if p.get("tool_name") != "Read":
        sys.exit(0)
    path = str((p.get("tool_input") or {}).get("file_path") or "")
    if not path.lower().endswith(".pdf"):
        sys.exit(0)
    mode = os.environ.get("CARDS_PDF_GUARD", "build").strip().lower()
    if mode == "always" or active_build(project_dir(p)) is not None:
        block(MSG)
    sys.exit(0)


if __name__ == "__main__":
    guarded(main, "block_pdf_read")
