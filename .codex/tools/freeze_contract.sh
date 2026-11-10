#!/usr/bin/env bash
# freeze_contract.sh — freeze every contract test that exists now. YOU run this,
# after a phase's gate passes. Writes .codex/contract.sha256, which Codex cannot
# edit, and which its freeze hook and gate.sh both read.
#
# Unfreezing a test (only when the owner changed the requirement in the docs):
#   delete its line from .codex/contract.sha256 by hand, let the agent fix the
#   test in a thread, gate, then run this again.
set -eu
cd "$(git rev-parse --show-toplevel)"
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
"$PY" -m pytest -q tests/contract > /dev/null 2>&1 || { echo "Refusing to freeze: contract tests are not all green. Run the gate first."; exit 1; }
"$PY" - <<'EOF'
import glob, hashlib
lines = []
for path in sorted(glob.glob("tests/contract/**/*.py", recursive=True)):
    lines.append(f"{hashlib.sha256(open(path, 'rb').read()).hexdigest()}  {path}")
open(".codex/contract.sha256", "w").write("\n".join(lines) + "\n")
print(f"Frozen {len(lines)} contract files -> .codex/contract.sha256")
EOF
git add .codex/contract.sha256 tests/contract >/dev/null 2>&1 || true
echo "Commit it with the phase: git commit -m 'freeze: phase contract'"
