#!/usr/bin/env bash
# run.sh — launches a Claude Code runtime guard and FAILS CLOSED.
# Only exit 2 blocks in Claude Code; a missing interpreter (127) or a crash (1)
# would let the tool call through. Every unexpected outcome becomes exit 2.
#
# Usage (from .claude/settings.json):
#   bash "$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh" block_fork.py
set -u
here="$(cd "$(dirname "$0")" && pwd)"
script="$here/$1"; shift
proj="${CLAUDE_PROJECT_DIR:-$(cd "$here/../.." && pwd)}"
py=""
for cand in "$proj/.venv/bin/python" "$(command -v python3 || true)"; do
  if [ -n "$cand" ] && [ -x "$cand" ]; then py="$cand"; break; fi
done
if [ -z "$py" ]; then
  echo "HOOK ERROR: no Python found, so $(basename "$script") could not check this call. Blocking rather than passing." >&2
  exit 2
fi
"$py" "$script" "$@"
rc=$?
if [ "$rc" -eq 0 ] || [ "$rc" -eq 2 ]; then exit "$rc"; fi
echo "HOOK ERROR: $(basename "$script") exited $rc and could not complete its check. Blocking rather than passing." >&2
exit 2
