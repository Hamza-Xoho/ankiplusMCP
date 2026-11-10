# Phase 3: Drafts in → `cards check`, `cards render`, `cards figures`

> Paste into a **new T3 thread** (GPT-6.1 Sol · High · Auto) on branch `anki-v2`. Self-contained.

## Not in this phase

- No review packets or report applying (Phase 4).
- No gate or write (Phase 5).
- Don't write card text yourself: drafts come from fixtures. You validate, lint and render; you don't author.
- Don't change the ColdRecall note type's CSS. Render with it as it is.

## Goal

Given `drafts.jsonl`:
- validate, lint and check coverage against the slides and objectives
- render phone-width contact sheets through the real note type
- build image-occlusion drafts from extracted figures

## Requirements in scope

- **FR-11**: check
- **FR-12**: render
- **FR-10**: figures / IO
- **FR-8**: the D-6 draft schema, proven on real v1 drafts

## Read first

- `docs/anki-v2-trd.md` T-5, T-6, T-11
- `docs/design-spec.md` §3.4, §3.5 (lint table), §4.1 (`check`, `render`, `figures` rows)
- `docs/test-contract.md`: the Phase 3 table
- v1 code to port: `.claude/skills/anki/scripts/render_cards.py` (renderer + its lint), `build_occlusion.py`
- Note-type assets: `.claude/skills/anki/assets/coldrecall-cloze/`. Copy them to `.claude/skills/anki2/assets/coldrecall-cloze/` (this is the one `.claude/` write allowed here).

## Build

1. `src/cards/check/`: schema (S01–S09), lint (L01–L13), coverage, stats. Then `cards check`.
2. `src/cards/render/` and `cards render`. Default model: `.claude/skills/anki2/assets/coldrecall-cloze/`.
3. `src/cards/figures.py` and `cards figures`.
4. `tests/fixtures/drafts_broken.jsonl`: one fault per lint and schema code.
5. A converter test helper: v1 L006 drafts (`private_fixture("l006_v1_drafts.jsonl")`) → D-6.

Write the Phase 3 contract tests first, show red, then implement.

## Definition of done

1. These pass, and failed before:
   - `test_fr11_clean_one_line`, `test_fr11_lint_detects[L01..L13]`, `test_fr11_schema_errors_located`
   - `test_fr11_uncovered_slide`, `test_fr11_objective_without_t1`, `test_fr11_enumeration_objective_below_t1`
   - `test_fr11_tier3_share_warning`, `test_fr11_foreign_tag_blocker`
   - `test_fr8_v1_l006_drafts_convert_and_validate`
   - `test_fr12_l006_sheet_pairs`, `test_fr12_only_rerenders_listed`, `test_fr12_scripts_stripped`, `test_fr12_default_model_from_assets`
   - `test_fr10_occlusion_record_d6`, `test_fr10_repeated_labels_share_index`
   - the G-tests re-applied to this phase's new subcommands (see the test-contract header)
   - all earlier phases still pass
2. Run `contract_auditor` (phase 3), `boundary_auditor` and `token_auditor`; fix their findings.
3. Report: `cards check` stdout on the converted v1 L006 drafts, and the sheet paths.

## Gate (the owner runs this)

```
bash .codex/tools/gate.sh 3
```

Then, by hand:

1. Open `renders/sheets/sheet_01_backs.png` for the converted L006 drafts. Check that cards look like your ColdRecall cards on the phone (colours, bold, Extra), with no raw HTML.
2. Open one IO preview from L007: check that the masks sit on the labels.
3. Freeze and commit.

## Stop

Stop at the definition of done and report. Don't begin Phase 4.
