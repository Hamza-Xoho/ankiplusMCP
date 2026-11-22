---
id: TESTS-anki-v2
title: /anki v2 — Test Contract
derived_from: [docs/anki-v2-brief.md 0.2.0, docs/anki-v2-trd.md 0.2.0, docs/design-spec.md 0.1.0]
created: 2026-11-05
---

# Test Contract

Every acceptance clause, as a named test. **The phase prompt cites these names. Implement exactly these names.**

**Where tests live:** `tests/contract/test_p<phase>_<area>.py`, one file per phase area. Unit tests go in `tests/unit/` and are free to change.

**Order of work:** a phase's contract tests are written first and must fail (red). Then the implementation makes them pass. Then, at the gate, the owner freezes them with `bash .codex/tools/freeze_contract.sh`.

**Once frozen, a test is never edited, deleted, skipped or marked xfail.** A Codex hook blocks it, and the gate re-checks the frozen files' SHA-256. If a frozen test is wrong, stop and report it. The owner changes the docs, re-runs the kit generator, and unfreezes by hand.

**Private fixtures** live in `tests/fixtures/private/` (gitignored). Setup in HANDOVER copies them in. A test that needs a missing private fixture **fails** with `missing fixture <name>: see HANDOVER §Setup`. It never skips.

Fixture files keep their **original filenames**, because `cards target` parses the lecture id from the filename:

| Fixture | What it is |
|---|---|
| `MED241_L006_2026-09-13_endoplasmic-reticulum-mitochondria-and-golgi-apparatus.pdf` | L006 PDF (the tests call it "L006") |
| `MED241_L007_2026-09-14_anatomy-of-the-pectoral-region.pdf` | L007 PDF |
| `transcripts/l006/` | The 2–3 Nov session `.jsonl` plus its `subagents/` folder |
| `l006_v1_drafts.jsonl` | `builds/2026-11-02_MED241-L006/drafts.jsonl` from the v1 run |
| `l007_labels.json` | the owner’s ground-truth labels for one L007 figure |

Small synthetic fixtures (`tests/fixtures/*.jsonl`, tiny PDFs made by the tests themselves) are committed.

**Global rules for every phase.** Each later phase's contract file re-applies the G-tests to that phase's new subcommands: the same base names (`test_g3_status_line_first`, `test_g3_stdout_budget`, `test_g4_exit_codes_mapped`, `test_g5_rerun_identical`, `test_g6_no_writes_outside_build`, `test_g7_provenance_present`, `test_g10_help_short`), parametrised by subcommand. Phase 0 can't foresee every later subcommand's fixtures.

**Tiers:**
- **inv**: an invariant, also enforced by a hook or by code that refuses
- **beh**: behavioural
- **char**: characterisation, named now and pinned once observed; the gate's manual check covers it

Asserts are in EARS form.

---

## Phase 0: foundations

| Req | Test | Asserts | Tier |
|---|---|---|---|
| G-3 | `test_g3_status_line_first` | WHEN any implemented subcommand runs THE SYSTEM SHALL print `OK`, `FINDINGS` or `ERROR` as stdout line 1 | inv |
| G-3 | `test_g3_stdout_budget` | WHEN any subcommand other than `source` and `report` runs THE SYSTEM SHALL print ≤ 40 lines and ≤ 2,000 characters | inv |
| G-4 | `test_g4_exit_codes_mapped` | WHEN a command finishes, finds issues, errors or is refused THE SYSTEM SHALL exit 0, 1, 2 or 3 respectively | inv |
| G-4 | `test_g4_unknown_flag_exit2` | WHEN a subcommand receives an unknown flag THE SYSTEM SHALL exit 2, not ignore it | beh |
| G-5 | `test_g5_rerun_identical` | WHEN a subcommand is re-run on unchanged inputs THE SYSTEM SHALL produce byte-identical outputs, apart from `_meta.created` | inv |
| G-6 | `test_g6_no_writes_outside_build` | WHEN any subcommand runs with a read-only source directory THE SYSTEM SHALL ALWAYS leave every path outside the build folder unchanged | inv |
| G-7 | `test_g7_provenance_present` | WHEN a subcommand writes a file THE SYSTEM SHALL include tool, version and created time | beh |
| G-8 | `test_g8_errors_name_file_line_field` | WHEN input fails validation THE SYSTEM SHALL name the file, line and field | beh |
| G-9 | `test_g9_spaces_and_unicode_paths` | WHEN paths contain spaces and non-ASCII THE SYSTEM SHALL run normally | beh |
| G-10 | `test_g10_help_short` | WHEN `--help` is passed THE SYSTEM SHALL print ≤ 20 lines | beh |
| G-10 | `test_g10_log_line_per_run` | WHEN a subcommand runs with `--build` THE SYSTEM SHALL append one line to `log.jsonl` | beh |
| FR-2 | `test_fr2_init_creates_state_and_pointer` | WHEN `state init` runs on a new source THE SYSTEM SHALL create the build folder, `build.json` and `builds/.current` | beh |
| FR-2 | `test_fr2_init_same_source_resumes` | WHEN `state init` runs on a source whose hash matches an existing build THE SYSTEM SHALL reuse that build and report its phase | beh |
| FR-2 | `test_fr2_next_after_interrupt` | WHEN a phase was started but not finished THE SYSTEM SHALL name that phase from `state next` | beh |
| FR-2 | `test_fr2_illegal_phase_transition_exit2` | WHEN `state phase` is asked to skip forward THE SYSTEM SHALL exit 2 and leave `build.json` unchanged | inv |
| FR-2 | `test_fr2_set_rejects_unknown_key` | WHEN `state set` gets a key outside `facts.*` THE SYSTEM SHALL exit 2 | beh |
| FR-2 | `test_fr2_corrupt_state_backed_up` | WHEN `build.json` is not valid JSON THE SYSTEM SHALL keep a backup and exit 2 | beh |
| INV-2 | `test_inv2_no_network_imports` | THE SYSTEM SHALL ALWAYS have no network-library import in `src/cards/` outside `write/direct.py` (AST scan) | inv |

## Phase 1: measurement

| Req | Test | Asserts | Tier |
|---|---|---|---|
| FR-24 | `test_fr24_usage_counted_once_per_message_id` | WHEN several rows share a `message.id` THE SYSTEM SHALL count their usage once | beh |
| FR-24 | `test_fr24_reproduces_l006_baseline` | WHEN metering the L006 fixture THE SYSTEM SHALL report 76 main calls, first context 79,270 ±1%, peak 166,115 ±1%, 2 compactions, 2 fork subagents | beh |
| FR-24 | `test_fr24_l006_fails_every_waste_check` | WHEN metering the L006 fixture THE SYSTEM SHALL fail each of W-1 to W-8 with non-empty evidence | beh |
| FR-24 | `test_fr24_clean_session_passes` | WHEN metering the synthetic clean transcript THE SYSTEM SHALL pass W-1 to W-8 | beh |
| FR-24 | `test_fr24_waste_check_detects[W-1..W-8]` | WHEN a synthetic transcript contains exactly one waste pattern THE SYSTEM SHALL fail only that check | beh |
| FR-24 | `test_fr24_unknown_price_not_guessed` | WHEN the model has no price in `prices.toml` THE SYSTEM SHALL report cost as unknown, not zero or an estimate | inv |
| FR-24 | `test_fr24_missing_field_exit2` | WHEN a transcript lacks a required usage field THE SYSTEM SHALL exit 2 naming it, not report zeros | beh |
| FR-27 | `test_fr27_line_mode_one_line` | WHEN `meter --line` runs THE SYSTEM SHALL print one line in the §3.9 format | beh |
| FR-25 | `test_fr25_cards_settings_lean` | WHEN `.claude/settings.json` is read THE SYSTEM SHALL find `disableClaudeAiConnectors: true`, `claudeMdExcludes` covering `~/.claude/CLAUDE.md`, and `deniedMcpServers` naming claude-flow and flow-nexus, and SHALL NOT deny `anki` | beh |
| FR-25 | `char_fr25_first_call_drop` | First-call context in a fresh Cards session drops ≥ 10k tokens versus 79k (measured with the meter) | char |

## Phase 2: source and target

| Req | Test | Asserts | Tier |
|---|---|---|---|
| FR-3 | `test_fr3_l006_slide_count` | WHEN extracting L006 THE SYSTEM SHALL produce 24 slide records numbered 1–24 | beh |
| FR-3 | `test_fr3_reading_order_two_columns` | WHEN a slide has two text columns THE SYSTEM SHALL emit the left column before the right | beh |
| FR-3 | `test_fr3_flags_image_only_and_repeated_title` | WHEN slides are image-only or repeat the previous title THE SYSTEM SHALL flag them | beh |
| FR-3 | `test_fr3_source_unchanged` | THE SYSTEM SHALL ALWAYS leave the source file's bytes and mtime unchanged | inv |
| FR-3 | `test_fr3_unreadable_source_exit2` | WHEN the source can't be read THE SYSTEM SHALL exit 2 with E2x and a remedy | beh |
| FR-3 | `test_fr3_objectives_never_invented` | WHEN no objectives slide exists THE SYSTEM SHALL emit an empty list and `no_objectives` | inv |
| FR-3 | `test_fr3_l006_objectives_found` | WHEN extracting L006 THE SYSTEM SHALL find its objectives with slide numbers | beh |
| FR-3 | `char_fr3_l007_label_recall` | OCR finds ≥ 85% of the labels in `l007_labels.json` | char |
| FR-4 | `test_fr4_map_one_line_per_slide` | WHEN the map is written THE SYSTEM SHALL have one line ≤ 110 characters per slide, after a header | beh |
| FR-4 | `test_fr4_l006_map_small` | WHEN extracting L006 THE SYSTEM SHALL write a `map.md` ≤ 2,500 estimated tokens | beh |
| FR-5 | `test_fr5_slice_exact` | WHEN slides 10–12 are requested THE SYSTEM SHALL print exactly slides 10, 11, 12 | beh |
| FR-5 | `test_fr5_out_of_range_exit2` | WHEN a slide number is out of range THE SYSTEM SHALL exit 2 | beh |
| FR-5 | `test_fr5_grep_slide_refs` | WHEN grepping a term THE SYSTEM SHALL print ≤ 20 hits, each with its slide number | beh |
| FR-5 | `test_fr5_all_l006_small` | WHEN `source --all` runs on L006 THE SYSTEM SHALL print ≤ 6,000 estimated tokens | beh |
| FR-5 | `test_fr5_page_image_small` | WHEN `--page-image` renders a slide THE SYSTEM SHALL write a PNG ≤ 1,000 px on its long side | beh |
| FR-6 | `test_fr6_cache_hit` | WHEN extracting an unchanged source a second time THE SYSTEM SHALL skip extraction and say so | beh |
| FR-7 | `test_fr7_text_source_sections` | WHEN the source is a markdown or text file THE SYSTEM SHALL split it on headings into slide records | beh |
| FR-1 | `test_fr1_deck_from_slide1_title` | WHEN slide 1 has a title THE SYSTEM SHALL use it as the deck name | beh |
| FR-1 | `test_fr1_deck_fallback_filename_topic` | WHEN slide 1 has no usable title THE SYSTEM SHALL use the humanised filename topic | beh |
| FR-1 | `test_fr1_deck_never_nested` | THE SYSTEM SHALL ALWAYS produce a deck name without `::` | inv |
| FR-1 | `test_fr1_collision_suffix` | WHEN a same-named deck holds another lecture THE SYSTEM SHALL append ` (<COURSE> L<nnn>)` | beh |
| FR-1 | `test_fr1_rerun_reuses_own_deck` | WHEN the same-named deck already holds this lecture's source tag THE SYSTEM SHALL reuse it unchanged | beh |
| FR-1 | `test_fr1_unparseable_filename_asks` | WHEN the filename can't be parsed and no manual flags are given THE SYSTEM SHALL exit 1 and print one question | beh |

## Phase 3: check, render, figures

| Req | Test | Asserts | Tier |
|---|---|---|---|
| FR-11 | `test_fr11_clean_one_line` | WHEN drafts are clean THE SYSTEM SHALL print `OK` plus one stats line | beh |
| FR-11 | `test_fr11_lint_detects[L01..L13]` | WHEN a draft breaks one lint rule THE SYSTEM SHALL report that code with the right severity | beh |
| FR-11 | `test_fr11_schema_errors_located` | WHEN a record breaks the D-6 schema THE SYSTEM SHALL report S-code, file, line and field | beh |
| FR-11 | `test_fr11_uncovered_slide` | WHEN a slide has neither a note nor a skip record THE SYSTEM SHALL list it | beh |
| FR-11 | `test_fr11_objective_without_t1` | WHEN an objective has no tier-1 note THE SYSTEM SHALL list it | beh |
| FR-11 | `test_fr11_enumeration_objective_below_t1` | WHEN an "enumerate" objective's notes sit at tier 2 THE SYSTEM SHALL flag it | beh |
| FR-11 | `test_fr11_tier3_share_warning` | WHEN tier 3 is under 5% of notes THE SYSTEM SHALL warn | beh |
| FR-11 | `test_fr11_foreign_tag_blocker` | WHEN a tag sits outside `#ColdRecall::` THE SYSTEM SHALL report a blocker | inv |
| FR-8 | `test_fr8_v1_l006_drafts_convert_and_validate` | WHEN the v1 L006 drafts are converted to D-6 THE SYSTEM SHALL validate all 40 records | beh |
| FR-12 | `test_fr12_l006_sheet_pairs` | WHEN rendering 40 notes at 8 per sheet THE SYSTEM SHALL write 5 fronts and 5 backs sheets and `sheets.json` | beh |
| FR-12 | `test_fr12_only_rerenders_listed` | WHEN `--only n007,n015` is given THE SYSTEM SHALL render only those notes | beh |
| FR-12 | `test_fr12_scripts_stripped` | WHEN a template contains `<script>` THE SYSTEM SHALL ALWAYS omit it from renders | inv |
| FR-12 | `test_fr12_default_model_from_assets` | WHEN no `model/` folder exists THE SYSTEM SHALL use `.claude/skills/anki2/assets/coldrecall-cloze/` and say so | beh |
| FR-10 | `test_fr10_occlusion_record_d6` | WHEN `cards figures` builds an occlusion THE SYSTEM SHALL append one valid `io` record with media and preview | beh |
| FR-10 | `test_fr10_repeated_labels_share_index` | WHEN a label appears twice on a figure THE SYSTEM SHALL give both masks one cloze index | beh |

## Phase 4: review loop

| Req | Test | Asserts | Tier |
|---|---|---|---|
| FR-13 | `test_fr13_refuses_with_blockers` | WHEN `check.json` has blockers THE SYSTEM SHALL exit 3 and build no packet | inv |
| FR-13 | `test_fr13_maintainer_slices_cover_citations` | WHEN building the maintainer packet THE SYSTEM SHALL include every cited slide ±1 in `source_slices.md` | beh |
| FR-13 | `test_fr13_packet_allowlist_only` | THE SYSTEM SHALL ALWAYS put only the spec §3.6 files in each packet | inv |
| FR-13 | `test_fr13_student_has_no_text_sources` | WHEN building the student packet THE SYSTEM SHALL include no drafts, source text or HTML | inv |
| FR-13 | `test_fr13_prompt_small` | WHEN `PROMPT.md` is written THE SYSTEM SHALL keep it ≤ 300 estimated tokens | beh |
| FR-13 | `test_fr13_prompt_single_turn_images` | WHEN `PROMPT.md` lists images THE SYSTEM SHALL instruct opening them all in one turn | beh |
| FR-13 | `test_fr13_prompt_names_pinned_agent` | WHEN packets are built THE SYSTEM SHALL print `anki-maintainer` and `anki-student` as the agents to use, and never `fork` | inv |
| FR-13 | `test_fr13_round2_scope` | WHEN `--only` is given THE SYSTEM SHALL include those notes plus their group siblings, nothing else | beh |
| C-8 | `test_c8_student_subset_rule` | WHEN there are > 6 sheet pairs THE SYSTEM SHALL include every pair with a tier-1 note plus one note per group, and list what it left out | beh |
| FR-16 | `test_fr16_reconcile_searches` | WHEN building the maintainer packet THE SYSTEM SHALL write `reconcile.md` with the source tag, legacy tag and AnKing searches | beh |
| FR-15 | `test_fr15_applies_rewrites_and_rejections` | WHEN reports contain fixes and rejects THE SYSTEM SHALL apply them and record them in `apply_log.json` | beh |
| FR-15 | `test_fr15_conflict_untouched` | WHEN both reviewers rewrite one note differently THE SYSTEM SHALL leave it unchanged, list it as a conflict and exit 1 | beh |
| FR-15 | `test_fr15_v2_escalates_to_a2` | WHEN the student reports a V2 alternative answer THE SYSTEM SHALL treat it as an A2 blocker | beh |
| FR-15 | `test_fr15_css_findings_flagged` | WHEN the same layout fault hits ≥ 3 notes THE SYSTEM SHALL flag `css_fix_needed` and not patch the notes | beh |
| FR-15 | `test_fr15_malformed_report_exit2` | WHEN a report line is invalid THE SYSTEM SHALL exit 2 naming the reviewer and line | beh |
| FR-15 | `test_fr15_round2_threshold` | WHEN ≤ 8 notes changed THE SYSTEM SHALL say round 2 is a self-review; when > 8, that it needs agents | beh |
| FR-15 | `test_fr15_unresolved_after_round2` | WHEN a blocker is open after round 2 THE SYSTEM SHALL mark the note `unresolved` and add the flag tag | beh |
| FR-15 | `test_fr15_previous_drafts_kept` | WHEN applying round k THE SYSTEM SHALL keep `drafts.r<k>.jsonl` | beh |
| FR-28 | `test_fr28_agent_frontmatter` | WHEN reading `.claude/agents/anki-*.md` THE SYSTEM SHALL find exactly the model, effort, tools, `permissionMode`, `omitClaudeMd` and `maxTurns` of TRD C-7 | inv |
| C-3 | `test_c3_templates_complete` | WHEN reading `templates/review/` THE SYSTEM SHALL find brief, rubric and report-format for both reviewers, with every rubric code A1–A13, S1–S9, V1–V9 | beh |

## Phase 5: gate, write, report

| Req | Test | Asserts | Tier |
|---|---|---|---|
| FR-17 | `test_fr17_gate_passes` | WHEN both latest summaries pass and no blocker is open THE SYSTEM SHALL set `passed` and store the drafts hash | beh |
| FR-17 | `test_fr17_gate_fails_on_fail_verdict` | WHEN a summary is `FAIL` THE SYSTEM SHALL set `failed` and exit 1 with the reason | beh |
| FR-17 | `test_fr17_gate_fails_on_open_blocker` | WHEN a non-dropped, non-unresolved note has an open blocker THE SYSTEM SHALL fail | beh |
| FR-17 | `test_fr17_gate_no_bypass` | THE SYSTEM SHALL ALWAYS refuse to pass a failing build, whatever flags or `CARDS_*` environment variables are set | inv |
| FR-18 | `test_fr18_write_refused_before_gate` | WHEN `write` runs without a passed gate THE SYSTEM SHALL exit 3 and write nothing | inv |
| FR-18 | `test_fr18_write_refused_after_drafts_change` | WHEN drafts changed after the gate THE SYSTEM SHALL exit 3 | inv |
| FR-18 | `test_fr18_batches_shape` | WHEN planning writes THE SYSTEM SHALL emit batches of ≤ 100 notes, one deck and note type each, with only `fields` and `tags` per note | beh |
| FR-18 | `test_fr18_suspend_list` | WHEN planning THE SYSTEM SHALL list tier-3 and `unresolved` notes to suspend | beh |
| FR-18 | `test_fr18_expected_counts` | WHEN planning THE SYSTEM SHALL write `expected.json` with counts and verify searches | beh |
| FR-20 | `test_fr20_import_file_format` | WHEN planning THE SYSTEM SHALL write `import.txt` with the five header lines and tab-separated rows | beh |
| FR-20 | `char_fr20_imports_into_anki` | `import.txt` imports into a scratch Anki profile with no configuration | char |
| FR-21 | `test_fr21_report_short` | WHEN `report` runs THE SYSTEM SHALL print ≤ 25 lines and remove `builds/.current` | beh |
| FR-27 | `test_fr27_report_usage_line` | WHEN `report` runs THE SYSTEM SHALL end `report.md` with the usage line | beh |
| FR-19 | `char_fr19_direct_mode` | Only if Q-1 passed: `write --direct` writes, verifies and records results | char |

## Phase 6: runtime skill and guards

| Req | Test | Asserts | Tier |
|---|---|---|---|
| C-6 | `test_c6_fork_blocked` | WHEN an Agent call has `subagent_type: fork` THE SYSTEM SHALL block (exit 2, instruction on stderr) | inv |
| C-6 | `test_c6_reviewers_allowed` | WHEN an Agent call uses `anki-maintainer`, `anki-student` or `Explore` THE SYSTEM SHALL allow it | beh |
| C-6 | `test_c6_pdf_read_blocked_during_build` | WHEN Read targets `*.pdf` (any case) while `builds/.current` exists THE SYSTEM SHALL block | inv |
| C-6 | `test_c6_pdf_read_blocked_always_mode` | WHEN `CARDS_PDF_GUARD=always` THE SYSTEM SHALL block every `*.pdf` Read | inv |
| C-6 | `test_c6_pdf_read_allowed_without_build` | WHEN no build is active and the mode is `build` THE SYSTEM SHALL allow (v1 `/anki` keeps working) | beh |
| C-6 | `test_c6_png_read_allowed` | WHEN Read targets a PNG THE SYSTEM SHALL allow it | beh |
| C-6 | `test_c6_local_http_blocked` | WHEN a Bash command contains `127.0.0.1`, `localhost:`, `0.0.0.0:` or `[::1]` THE SYSTEM SHALL block | inv |
| C-6 | `test_c6_plain_bash_allowed` | WHEN a Bash command is `.venv/bin/cards check --build …` THE SYSTEM SHALL allow it | beh |
| C-6 | `test_c6_write_blocked_before_gate` | WHEN `builds/.current` names a build without a passed gate THE SYSTEM SHALL block `mcp__anki__add_notes` | inv |
| C-6 | `test_c6_write_blocked_stale_gate` | WHEN the drafts hash no longer matches THE SYSTEM SHALL block | inv |
| C-6 | `test_c6_write_allowed_after_gate` | WHEN the gate passed and the hash matches THE SYSTEM SHALL allow | beh |
| C-6 | `test_c6_write_allowed_without_build` | WHEN no `builds/.current` exists THE SYSTEM SHALL allow (manual use) | beh |
| C-6 | `test_c6_fail_closed` | WHEN a hook gets malformed JSON THE SYSTEM SHALL ALWAYS exit 2 | inv |
| C-6 | `test_c6_settings_wiring` | WHEN reading `.claude/settings.json` THE SYSTEM SHALL find each hook under `PreToolUse` with its matcher, and each script existing and executable | inv |
| §4b | `test_skill_core_size` | WHEN reading `anki2/SKILL.md` THE SYSTEM SHALL find ≤ 10,000 characters | beh |
| §4b | `test_skill_frontmatter_pins` | WHEN reading the frontmatter THE SYSTEM SHALL find `model: claude-sonnet-5-5` and `effort: medium` | inv |
| §4b | `test_skill_core_no_rubric` | WHEN reading SKILL.md THE SYSTEM SHALL find none of the rubric tables (A1–A13, S1–S9, V1–V9 definitions) | beh |
| §4b | `test_skill_phase_map_complete` | WHEN reading SKILL.md THE SYSTEM SHALL find every `cards` subcommand used in P0–P7, and each referenced phase file existing | beh |
| FR-9 | `test_fr9_house_style_only_in_phase_file` | WHEN reading SKILL.md THE SYSTEM SHALL find no house-style rules, only a pointer to `phases/draft.md` | beh |

## Phase 7: acceptance (run by the owner in Claude Code)

| Req | Check | Tier |
|---|---|---|
| SC-1 | `cards meter --latest this repository` on the `/anki2` L006 session: W-1 to W-8 pass | char |
| SC-4 | `report.md`: every objective has a tier-1 note; tier-3 share shown; no active note with an open blocker | char |
| SC-5 | the owner compares the v1 and v2 L006 decks: no category worse | char |
| SC-6 | No Anki write error in the transcript; deck created in P1 | char |
| SC-7 | Kill the session at P4, start a new chat with `/anki2` + the same PDF: it resumes from `build.json` without `source --all` | char |
| SC-8 | Transcript shows `anki-maintainer` and `anki-student`, no fork; W-8 passes | char |
| DoD | All of the above repeated on L007 (with occlusions) | char |
