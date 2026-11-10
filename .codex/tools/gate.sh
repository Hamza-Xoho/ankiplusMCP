#!/usr/bin/env bash
# gate.sh <phase> — the phase gate. YOU run this (in T3's terminal), not the agent.
# It lives in .codex/, which Codex cannot edit under workspace-write, so the
# agent cannot weaken it.
#
#   bash .codex/tools/gate.sh 2
#
# Checks, in order:
#   1. frozen contract tests are byte-identical to the freeze manifest
#   2. no contract test is skipped or xfailed
#   3. every hook script still behaves (verify_hooks.py)
#   4. contract tests for phases 0..N pass, plus unit tests
# Prints GATE PASS or GATE FAIL. Then do the phase prompt's manual check.
set -u
N="${1:?usage: gate.sh <phase number>}"
cd "$(git rev-parse --show-toplevel)" || exit 2
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
fail=0
say() { printf '%s\n' "$*"; }

say "== 1. contract freeze"
if [ -f .codex/contract.sha256 ]; then
  if "$PY" - <<'EOF'
import hashlib, sys
bad = 0
for line in open(".codex/contract.sha256"):
    parts = line.strip().split(None, 1)
    if len(parts) != 2:
        continue
    want, path = parts[0], parts[1].lstrip("*")
    try:
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    except FileNotFoundError:
        print(f"   MISSING  {path}"); bad += 1; continue
    if got != want:
        print(f"   CHANGED  {path}"); bad += 1
sys.exit(1 if bad else 0)
EOF
  then say "   ok: frozen tests unchanged"; else say "   FAIL: a frozen contract test was changed or removed"; fail=1; fi
else
  say "   (nothing frozen yet)"
fi

say "== 2. no skipped contract tests"
if grep -rnE "pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|importorskip|unittest\.skip" tests/contract 2>/dev/null; then
  say "   FAIL: contract tests may not skip or xfail"; fail=1
else
  say "   ok"
fi

say "== 3. hook self-test"
if "$PY" .codex/tools/verify_hooks.py > /tmp/verify_hooks.out 2>&1; then
  say "   ok: $(tail -1 /tmp/verify_hooks.out)"
else
  grep FAIL /tmp/verify_hooks.out; say "   FAIL: a hook misbehaves"; fail=1
fi

say "== 4. contract tests p0..p$N + unit tests"
files=()
for i in $(seq 0 "$N"); do
  for f in tests/contract/test_p${i}_*.py; do [ -e "$f" ] && files+=("$f"); done
done
if [ "${#files[@]}" -eq 0 ]; then
  say "   FAIL: no contract tests for phases 0..$N"; fail=1
else
  [ -d tests/unit ] && files+=(tests/unit)
  "$PY" -m pytest -q "${files[@]}" > /tmp/gate_pytest.out 2>&1
  rc=$?
  tail -15 /tmp/gate_pytest.out
  [ "$rc" -eq 0 ] || { say "   FAIL: tests failing"; fail=1; }
fi

if [ "$fail" -eq 0 ]; then
  say ""; say "GATE PASS (phase $N). Now do the manual check in prompts/phase-$(printf '%02d' "$N")-*.md, then freeze:"
  say "   bash .codex/tools/freeze_contract.sh"
  exit 0
fi
say ""; say "GATE FAIL (phase $N). The phase is not done. Report the failure back to the thread; do not start the next phase."
exit 1
