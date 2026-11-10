#!/usr/bin/env bash
# run.sh — launches a Codex hook script and FAILS CLOSED.
#
# Only exit 2 blocks in Codex. If python3 is missing (127) or the script
# crashes (1), Codex would let the tool call through and the invariant would
# silently stop being enforced. This wrapper turns every unexpected outcome
# into exit 2 with a message, except for non-blocking hooks (SessionStart),
# which are called with NONBLOCKING=1.
#
# Usage (from .codex/hooks.json):
#   bash "$(git rev-parse --show-toplevel)/.codex/hooks/run.sh" freeze_contract.py [args]
set -u
here="$(cd "$(dirname "$0")" && pwd)"
script="$here/$1"; shift
py="$(command -v python3 || true)"
if [ -z "$py" ]; then
  [ "${NONBLOCKING:-0}" = "1" ] && exit 0
  echo "HOOK ERROR: python3 not found, so $(basename "$script") could not check this action. Blocking rather than passing." >&2
  exit 2
fi
"$py" "$script" "$@"
rc=$?
if [ "$rc" -eq 0 ] || [ "$rc" -eq 2 ]; then exit "$rc"; fi
[ "${NONBLOCKING:-0}" = "1" ] && exit 0
echo "HOOK ERROR: $(basename "$script") exited $rc and could not complete its check. Blocking rather than passing." >&2
exit 2
