# Phase 6 runtime implementation plan

Spec: phase-06-runtime-skill prompt; brief §4/§4b; design §4.2/§5/§6; TRD orchestration/C-6/C-7; test-contract Phase 6.

Work in the supplied anki-v2 checkout. It has no HEAD and contains earlier-phase staged/untracked work; do not move or commit that work. The owner owns gate, fresh-Claude manual verification, freeze and commit.

1. Add tests/contract/test_p6_runtime.py with every named Phase 6 contract. Execute shipped guards via run.sh with isolated project payloads; test malformed input, stale gates and all write tool variants. Parse settings and skill structure. Run before implementation: guards may pass, skill/wiring must fail.
2. Add .claude/skills/anki2/SKILL.md and phases/{draft,occlusion,write}.md. Keep core <=10,000 characters, required ordered sections and six-column P0–P7 map. Keep source/style/schema detail in P2 files and write verification in write.md. Use only currently shipped CLI flags. No new subcommands: Phase 6 has no additional G-test parametrisations; earlier-phase G-tests remain in the full run.
3. Merge settings.hooks.json into settings.json without changing existing keys/values; delete the fragment. Preserve guard bytes and v1. Update CLAUDE.md routing and ADR-9 rule, removing contradictory human review-gate language.
4. Run Phase 6 contracts, earlier contracts/unit tests, verify_hooks.py, protected-file hashes and diff checks. Run contract_auditor (Phase 6) and token_auditor read-only, address findings, then rerun affected checks. Record character count, exact phase map, settings diff and manual limitations in docs/phase6-runtime.md.

Interface calls: build.json is authoritative for resume; do not follow state next's older advisory phase filenames (no source changes in this phase). Read it before loading any phase file. Drafts are written once per file, IO tools append their generated notes. P4 agents receive PROMPT.md paths only; reports are applied by cards apply. P6 records real write/read-back evidence in build.json.write; cards state set permits facts only. Direct mode is absent pending Q-1, so stage 1 inline is used.

Verification: .venv/bin/python -m pytest -q tests/contract/test_p6_runtime.py; .venv/bin/python -m pytest -q tests/contract/test_p[0-6]_*.py tests/unit; .venv/bin/python .codex/tools/verify_hooks.py. Do not run the owner’s gate or begin Phase 7.

## Execution record

Complete: initial contracts 41 pass / 7 fail; implementation 48 pass; auditor terminal-transition regression RED then fixed; final Phase 6 49 pass. Full regression 347 pass (before new terminal test was collected); final Phase 6 rerun includes it. Hook verifier 42/42, guard/v1 hashes unchanged, all original settings values preserved. Contract/token auditor verdicts OK. No scope changes or deferred code findings. Gate, fresh runtime checks, freeze and commit remain the owner’s handoff.
