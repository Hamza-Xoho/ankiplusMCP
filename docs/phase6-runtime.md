# Phase 6: /anki2 and runtime guards

The skill core has **9,499 characters**. It pins claude-sonnet-5-5 / medium, routes HARVEST and REPAIR to v1, loads house style only at P2, launches the pinned reviewers with packet paths, and uses the shipped stage-1 inline write flow. Q-1 has no successful direct-mode probe; no unsupported direct command is prescribed.

Files added: `SKILL.md`, `phases/draft.md`, `phases/occlusion.md`, `phases/write.md`, and `tests/contract/test_p6_runtime.py`. Runtime `CLAUDE.md` routes PDF builds/resume to `/anki2` and replaces the human review gate with ADR-9. Existing v1 content is untouched.

## Phase map

| Phase | Entry condition | Exact commands / actions | What to read | Exit condition | Phase file to load |
|---|---|---|---|---|---|
| P0 Preflight | Source supplied; resume rule checked | `.venv/bin/cards state init "<PDF>"`; `mcp__anki__model_names` and `mcp__anki__list_decks`; `.venv/bin/cards state set --build <build> facts.anki_reachable=true facts.note_type_exists=true` | `build.json` first; small MCP results | Anki available; ColdRecall Cloze exists; save deck list to `<build>/existing-decks.json` | None; core only |
| P1 Extract + target | P0 complete | `.venv/bin/cards extract --build <build>` (add `--slides N-M` for requested range); `.venv/bin/cards target --build <build> --existing-decks <build>/existing-decks.json`; create missing target deck with `mcp__anki__create_deck`; `.venv/bin/cards state set --build <build> facts.deck_exists=true` | `source/map.md`, `source/objectives.json`, `target.json` | Confident flat target deck exists; model HTML/CSS saved under `<build>/model/` | None; core only |
| P2 Draft | Source and target ready | `.venv/bin/cards source --build <build> --all` once; for flagged slides `.venv/bin/cards source --build <build> --page-image N`; write `drafts.jsonl` and `skipped.jsonl` in one Write each; optional `.venv/bin/cards figures --build <build> --fig <fig_id>` | `phases/draft.md`; source text; only required flagged PNGs | Drafts cover objectives; deliberate omissions recorded; IO previews checked | `phases/draft.md`; `phases/occlusion.md` only for IO |
| P3 Check + render | Draft files ready | `.venv/bin/cards check --build <build>`; `.venv/bin/cards render --build <build>` | Findings summary only; specific check entries if needed | No schema/coverage blockers; renders exist | None; core only |
| P4 Review | Checks and renders ready | `.venv/bin/cards packets --build <build> --round 1`; launch `anki-maintainer` and `anki-student` in one message, each prompt = its `PROMPT.md` path only; `.venv/bin/cards apply --build <build> --round 1` | Apply summary and conflicts only; never reviewer templates | Both reports applied; changes rechecked/reviewed, at most 2 rounds | None; core and round rules below |
| P5 Automatic gate | Latest review round applied | `.venv/bin/cards gate --build <build>` | Gate summary | Gate passed on current drafts; continue without asking | `phases/write.md` |
| P6 Write + verify | Gate passed; hash unchanged | `.venv/bin/cards write --build <build>`; `mcp__anki__add_notes` straight from each batch file's content (stage 1 inline); updates, media, suspend and verify via MCP per `expected.json` | `write/expected.json`, `write/suspend.json`, `write/updates.json`; each batch once | Actual writes and suspend/verify searches match expected counts; evidence recorded | `phases/write.md` |
| P7 Report | P6 done with verified counts | `.venv/bin/cards report --build <build>` | Report output once | Short report delivered with usage line and sync reminder; mark P7 done, then `.venv/bin/cards state phase --build <build> done start` | `phases/write.md` |

## Settings diff

All six pre-existing top-level settings keys and their values are unchanged after JSON parsing, including Phase 1 exclusions and permissions. The added keys are `model`, `env` and `hooks`. The merged `settings.hooks.json` fragment is deleted. The four guard Python files gained executable permissions, as required by the wiring contract; their bytes and run.sh are unchanged.

```diff
--- .claude/settings.json (before Phase 6)
+++ .claude/settings.json (Phase 6)
@@ -153,5 +153,49 @@
       "serverName": "terminal"
     }
   ],
-  "enabledPlugins": {}
+  "enabledPlugins": {},
+  "model": "claude-sonnet-5-5",
+  "env": {
+    "CARDS_PDF_GUARD": "build"
+  },
+  "hooks": {
+    "PreToolUse": [
+      {
+        "matcher": "Agent",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh\" block_fork.py"
+          }
+        ]
+      },
+      {
+        "matcher": "Read",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh\" block_pdf_read.py"
+          }
+        ]
+      },
+      {
+        "matcher": "Bash",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh\" block_local_http.py"
+          }
+        ]
+      },
+      {
+        "matcher": "mcp__anki__add_notes|mcp__anki__add_note|mcp__anki__update_note_fields|mcp__anki__update_notes",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/run.sh\" require_review_before_write.py"
+          }
+        ]
+      }
+    ]
+  }
 }
```

## Verification

- Initial Phase 6 run: **7 failed, 41 passed**. Missing wiring/core/phase files and old runtime gate caused the expected failures; existing guards passed immediately as allowed by the phase prompt.
- Phase 6 after implementation and auditor fix: **49 passed**. The extra test executes the terminal commands from the map against the real CLI; it first reproduced the rejected `done done` instruction, then passed when documentation ended at `done start`.
- Hook verifier: **42/42 passed**. Protected guard bytes and v1 SKILL.md hashes match the pre-edit snapshot.
- Earlier-phase baseline: **299 passed**.
- Full Phase 0–6 contracts + unit run: **347 passed in 186.53s** (collected before the added terminal regression). Final Phase 6 rerun: **49 passed**, including that new test; earlier-phase baseline is **299 passed**. All current cases have passing evidence across these runs.
- No new subcommands were added, so Phase 6 has no additional G-test parametrisations. Existing G-tests run in regression.
- `contract_auditor`: **OK** for all 19 named clauses. Its additional terminal-transition finding was fixed with a red/green regression test.
- `token_auditor`: **OK**. Core 9,499 chars; L006 source ≈2,316 tokens; map ≈485; maintainer/student prompts ≈187/150. Normal command output maximum 5 lines/268 characters; report 15 lines/637 characters. Auditor used only temporary copies and repaired an existing demo state's missing schema keys only in that copy.

## Handoff limitations

No real Claude Code session or Anki collection was exercised here. The owner runs `bash .codex/tools/gate.sh 6`, the five fresh-session hook checks, then freeze and commit. This checkout has no HEAD and earlier staged/untracked work, so no commit was made. Phase 7 was not started and CARDS_PDF_GUARD remains `build`.

The existing MCP `permissions.ask` entries were preserved as requested. Claude Code can therefore still prompt for tool permissions; the skill adds no human review/approval question after gate success. This distinction needs checking in the fresh runtime session.

## Live checks (Claude Code)

Run 2026-11-06 in a live Claude Code session in this folder (hooks wired, `anki` MCP live). All five were blocked by the hook, not a permission prompt.

1. **PDF Read after `cards state init`: PASS.** `BLOCKED: lecture PDFs are not read directly (every page becomes an image in context). Use: .venv/bin/cards extract --build <build>, then .venv/bin/cards source --build <build> --all (once) or --slides N. For a slide whose figure you must see: cards source --build <build> --page-image N, then Read that PNG.`
2. **Fork subagent: PASS.** `BLOCKED: forked subagents are not used in this workspace (they copy the whole conversation). For card review use subagent_type "anki-maintainer" or "anki-student" with the packet's PROMPT.md path. For anything else, use a fresh agent type such as "Explore" or "general-purpose".`
3. **Shell request to the local Anki port: PASS.** `BLOCKED: shell access to local ports is not used here. Anki is reached only through the mcp__anki__* tools. ...`
4. **`mcp__anki__add_notes` to `ZZ hook test`: PASS.** `BLOCKED: this /anki2 build has not passed its review gate (build.json gate.status = pending). Run: .venv/bin/cards gate --build builds/2026-11-06_MED241-L006. ...` No note was written.
5. **`rm builds/.current` then Read `README.md`: PASS.** Nothing fired.

Finding: `cards state init` globbed every `builds/*/build.json` and failed (E12) on Codex's old scratch builds (Linux paths, old schema), so one stale build blocked all inits. I moved those to `~/Code/anki-v2-archive/builds-codex/`. A tolerant glob in `state.init` is a possible hardening, not done.
