# Phase 4: Review loop (`cards packets`, `cards apply`, templates, reviewer agents)

> Paste into a **new T3 thread** (GPT-6.1 Sol · High · Auto) on branch `anki-v2`. Self-contained.

## Not in this phase

- Don't run the reviewers. They are Claude Code agents, used at run time. You build their inputs and the code that applies their outputs, and test with hand-written report fixtures.
- No gate or write (Phase 5). No SKILL.md (Phase 6).
- Don't change the rubric's *meaning* when porting it. Only the report format changes, to JSONL.
- `.claude/agents/anki-maintainer.md` and `anki-student.md` already exist. Don't edit them unless `test_fr28_agent_frontmatter` shows a mismatch with TRD C-7; if so, report the mismatch before changing anything.

## Goal

Packets that give each reviewer everything and nothing more, and one command that applies both reports.

## Requirements in scope

- **FR-13**: packets
- **FR-15**: apply
- **FR-16**: reconcile searches
- **C-3**: templates
- **C-8**: student subset
- **FR-28**: pinned agents
- **CON-6**: independence

## Read first

- `docs/anki-v2-trd.md` T-7, T-8, D-9, D-10, D-11, C-3, C-7, C-8
- `docs/design-spec.md` §3.6, §4.1 (`packets`, `apply` rows), §5 (round counter, note status)
- `docs/test-contract.md`: the Phase 4 table
- **Source for the templates:** the current v1 skill `.claude/skills/anki/SKILL.md`. Its sections "Maintainer brief", "Rubric — the maintainer, per note", "Rubric — the maintainer, the set", "Report format — the maintainer", "Student brief", "Rubric — the student" and "Report format — the student" are what you port.

## Build

1. **Templates:** `.claude/skills/anki2/templates/review/{maintainer,student}/{brief,rubric,report-format}.md`, and `house-style.md` (the v1 House style section, as-is).
   - Briefs and rubrics are ported verbatim.
   - Report formats are rewritten to spec §3.6 JSONL.
2. **`PROMPT.md` template:** ≤ 300 tokens. It names the files, says to open all images in one turn, and gives the exact report path.
3. **Packets:** `src/cards/review/packets.py` and `cards packets`, including the C-8 subset rule and `reconcile.md`.
4. **Apply:** `src/cards/review/apply.py` and `cards apply`.
5. **Report fixtures:** `tests/fixtures/reports/` holds fix, reject, conflict, CSS-pattern and malformed cases.

Write the Phase 4 contract tests first, show red, then implement.

## Definition of done

1. These pass, and failed before:
   - `test_fr13_refuses_with_blockers`, `test_fr13_maintainer_slices_cover_citations`
   - `test_fr13_packet_allowlist_only`, `test_fr13_student_has_no_text_sources`
   - `test_fr13_prompt_small`, `test_fr13_prompt_single_turn_images`, `test_fr13_prompt_names_pinned_agent`, `test_fr13_round2_scope`
   - `test_c8_student_subset_rule`, `test_fr16_reconcile_searches`
   - `test_fr15_applies_rewrites_and_rejections`, `test_fr15_conflict_untouched`, `test_fr15_v2_escalates_to_a2`
   - `test_fr15_css_findings_flagged`, `test_fr15_malformed_report_exit2`, `test_fr15_round2_threshold`
   - `test_fr15_unresolved_after_round2`, `test_fr15_previous_drafts_kept`
   - `test_fr28_agent_frontmatter`, `test_c3_templates_complete`
   - the G-tests re-applied to this phase's new subcommands (see the test-contract header)
   - all earlier phases still pass
2. Run `contract_auditor` (phase 4), `boundary_auditor` and `token_auditor`; fix their findings.
3. Report: the file list and estimated tokens of the L006 maintainer packet and student packet, plus the two `PROMPT.md` texts.

## Gate (the owner runs this)

```
bash .codex/tools/gate.sh 4
```

Then, by hand:

1. **Real check of independence and cost.** In a Claude Code session in `this repository`, ask: "Launch anki-maintainer with the packet at builds/<L006>/review/round1/maintainer/ and anki-student with …/student/, in parallel."
2. Afterwards run `.venv/bin/cards meter --latest this repository --out /tmp/m4`. W-3 and W-8 must pass, and both reports must exist and be accepted by `cards apply`.
3. Freeze and commit.

## Stop

Stop at the definition of done and report. Don't begin Phase 5.
