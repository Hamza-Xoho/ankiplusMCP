# Audit implementation dispositions

This closes the executable scope of the original audit register against the
connected student product. Final verification revisions, counts and evidence are
recorded in macos-acceptance.md. Historical checkpoint documents remain evidence
of their stated subsets; they are not overwritten as whole-product passes.

| ID | Disposition and actual evidence | Compatibility / remaining acceptance |
| --- | --- | --- |
| A1 | Fixed: legacy P6 checks expected counts before recording success/finishing. `test_write_recovery.py`. | Mismatches retain recoverable P6; no invented receipt. |
| A2 | Fixed: artifact revision is separate from card revision. `test_artifact_revisions.py`, `test_publication.py`. | Extraction/preview publication does not stale unrelated edits. |
| A3 | Fixed: captured inputs, short publication lock, cooperative cancellation and stale-result refusal. `test_publication.py`, `test_source_catalog.py`. | Native calls are not forcibly interrupted. |
| A4 | Fixed: nonblocking build lock. `test_build_lock.py`. | Established refusal exit 3; successful CLI output unchanged. |
| A5 | Superseded for student editing: production review edits and reruns quality for current immutable content, `test_review_session.py`. | Retained legacy two-round policy is unchanged; no silent amendment policy extension. |
| A6 | Fixed: occupied collision suffixes allocate another free name; cached P1 target rechecks newly available actual deck listing. `test_target_collision.py`, frozen P2 contracts. | Legacy P0 still requests host preflight facts; it does not itself verify Anki. New path reads actual scoped companion evidence. |
| A7 | Corrupt manifests/jobs/runs isolated with retained originals, `test_workspace_damage.py`, `test_discovery.py`, `test_runs.py`; source format and failures in `test_source_errors.py`; full student packet selection retained. | No claim to edit presentation files; supported source types remain PDF/text/Markdown/images. Timeouts retain failure/uncertainty rather than being diagnosed as success. Unused legacy code is retained compatibility, not a new workflow dependency. |
| B1 | Fixed safe retention: timestamps plus explicit digest-confirmed preview cleanup and deletion manifest. `test_derived_cleanup.py`. | Sources, sole media, quality/reviews/history/jobs are protected. Abandoned extraction/journal files retained for inspection, not auto-pruned. |
| B2 | Fixed: labels, timestamps, recency, source/run/note/card/stage/outcome search. `test_run_discovery.py`, `test_history_cli.py`. | CLI discovers actual student root; old standalone root remains explicitly accessible. |
| B3 | Fixed: persistent job discovery, live/dead owner leases, bounded close API and cancellation. `test_discovery.py`, `test_locking.py`. | Close API waits at most 2s; process exit can wait for native work. OCR subprocess limit is 30s. Actual Mac shutdown remains acceptance. |
| B4 | Fixed durable publication/recovery: fsynced immutable journal/head/snapshots, config version/pointer recovery, cumulative legacy receipts. `test_runs.py`, `test_configuration.py`, `test_cumulative_results.py`, `test_run_migration.py`. | Several renames are not called a transaction. Uncommitted temporaries do not manufacture committed results. |
| B5 | Fixed snapshot/publication consistency and lock order. `test_publication.py`, `test_workflow_concurrency.py`, `test_source_catalog.py`, `test_profiles.py`. | Local per-root locks do not control independent external Anki processes. |
| C1 | Fixed exact citations, quote validation, OCR origin, source versions and media hashes. `test_evidence.py`, `test_product_workflow.py`, `test_workflow_quality.py`. | No output-tag changes or invented quotes; production source fidelity still needs representative private evaluation. |
| C2 | Fixed durable queries/hits/decisions and scoped mapping reuse. `test_coverage_batches.py`, `test_coordinator.py`, `test_reconciliation.py`. | Semantic completeness is explicitly unverified judgement, not inferred from hit count. |
| C3 | Fixed displayed disposition distinctions, pending/source contradiction and omitted/excluded decisions. `test_review_session.py`, `test_run_responses.py`; student workflow guide. | Legacy warning severity unchanged. Rejected/excluded is not represented as covered. |
| C4 | Fixed per-note and set-review findings surfaced in production review and retained exact in history. `test_workflow_quality.py`, `test_review_session.py`. | Rubrics/severity unchanged; bounded preview discloses retained full findings. |
| D1 | Implemented exact proposal/config/source/media/quality authorization and conditional per-item readback. `test_coordinator.py`, `test_product_workflow.py`, `test_workflow_concurrency.py`. | Trusted local host presents actual user decisions; state checks alone are not user authorization or persistent identity uniqueness. |
| D2 | Implemented per-operation cumulative outcomes and separate tier-child failures; uncertainty stops sends. `test_reconciliation.py`. | No whole-batch retry; preflight failure explicitly not_sent; prior acknowledgements retained. |
| D3 | Implemented stable operation IDs, durable intent/ack/result, restart recovery and verified mapping reuse. `test_reconciliation.py`; real packaged stdio loss-of-ack experiment. | Inconclusive creates remain uncertain indefinitely without sufficient evidence. |
| D4 | Implemented narrow dispatch, exact complete affected state and non-POSIX local coordinator locks. Companion conditional unit suite; `test_anki_adapter.py`. | Direct external companion use is outside AnkiPlus authorization. Frozen Codex hooks remain untouched/verified. |
| D5 | Retained tier policy: generated tier 3 suspended via real card IDs; tier 1/2 scheduling preserved; explicit reuse unsuspends selected cards. `test_reconciliation.py`. | Field updates preserve existing tags; tag/tier reclassification is not silently performed. Source-linked explicit update and all sibling ownership are checked. |
| D6 | Implemented local evidence binding/invalidation/receipt validation; unsupported actual execution refuses. `test_workflow_quality.py`, `test_staged_student.py`. | Actual independent prescribed reviewers on Mac remain a gate. No author or Linux synthetic pass substitutes. |
| E1 | Fixed stable-ID partial patches preserve untouched drafts and current revision. `test_card_patch.py`. | No whole-set resend required for one field edit. |
| E2 | Fixed bounded run/results/history/field/evidence previews with continuation and complete exact record access. `test_run_responses.py`, `test_review_session.py`, `test_protocol.py`. | Large legacy helper responses may return the existing explicit response-limit remedy; no completed application response is discarded that way. |
| E3 | Measured local schema/response sizes; both MCP channels retained. | Actual host forwarding/token accounting remains Mac measurement, not an executable implementation defect or reason to remove structured results. |
| E4 | 66 exposed tools / 57,866 schema chars measured locally (rough chars/4 estimate 14,466.5; not tokenizer output). | No arbitrary tool-count reduction or unsupported claim about host lazy loading. |
| E5 | Explicitly deferred quality-sensitive summary format changes. Existing summaries/tier suggestions preserved and regression checked. `test_slides_summary.py`, CLI baseline. | Representative model selection/combination evaluations remain private acceptance. |
| E6 | Existing reviewer instructions preserved; source/installed templates compared and guide/package copies kept consistent. `test_review_edges.py`, `test_desktop_experiment.py`, `test_staged_student.py`, packaging checks. | No routine trimming of reviewer wording. Historical mechanics docs now labelled, current guidance points to connected path. |
| E7 | Implemented shared OCR cache with complete image/tool/config identity and unchanged output. `test_ocr_speed.py`, source cache tests. | No OCR pass/resolution/label shortcuts. Real OCR acceptance is separate from deterministic shim lane. |
| E8 | Explicitly deferred optional preview compression/resolution optimization. | Existing image bounds retained; no unmeasured legibility trade. |
| F1 | Committed normalized public/CLI baselines plus actual OCR/Chromium container acceptance. `test_public_baseline.py`, CLI baseline and isolated acceptance. | Actual independent card-quality evaluation remains prescribed external gate. |
| F2 | Public synthetic suite exercised without frozen-test changes. | 25 existing skips retained; missing private fixtures are not waived or called passes. |
| F3 | Supported claims narrowed to tested Linux mechanics and reported historical Mac subsets. Version-independent package name checks cover textual/numeric add-on paths. | Mac product compatibility and Windows support are not claimed. |
| F4 | Frozen hashes and hooks preserved; checks rerun. | No CODEOWNERS/branch-protection enforcement claim; no sensitive infrastructure changes. |
| F5 | Config/root negotiation, live concurrency, image bounds, SDK session/reconnect and actual installed stdio path covered. Relevant MCP suites and isolated acceptance. | Real host/App behavior remains Mac acceptance. |
| G1 | APPDATA/platform paths covered by launcher/settings tests. | Windows remains unaccepted; portable paths are not proof of full support. |
| G2 | Outside first-release promise: no new Cursor/Hermes behavior added. Existing launcher contracts preserved. | Alternative-host readiness not inferred from printed snippets. |
| G3 | Revision-pinned checkout installation, Python lock, launcher lock and real package build are verifiable without publishing. | Registry publication is outside authorized scope. No account/release operation performed. |
| G4 | Existing `cards` CLI entry point retained and golden-checked. | Namespace renaming was speculative; no migration/command removal justified. |
| G5 | Confirmed student preferences govern future defaults and saved roots; explicit run choices separate. `test_profiles.py`, `test_run_preferences.py`, `test_verified_onboarding.py`. | Legacy TOML seeds launch defaults; confirmed student choices take precedence for card defaults. Explicit launch source-root flags remain explicit overrides. |
| G6 | New coordinator uses portable FileLock and SDK APIs, independent of POSIX host hooks. `test_locking.py`, actual installed stdio acceptance. | Retained CLI/runtime assumptions labelled; host controls still require acceptance. |
| G7 | Hardened rootless standalone container: nonroot/read-only/no runtime network, mounts or ports; CPU/RAM/PID limits; actual OCR/Chromium/real-Anki acceptance. | Base OS/transitive Anki packages are captured in evidence; image digest is pinned per run, not claimed byte-reproducible across apt registry changes. Primary Python runtime is locked. |
| G8 | Metadata/version tests derive declared version; synthetic version mutation check retained. `test_packaging_meta.py`, version check, launcher suite. | No release/version bump or publication inferred. |

## Quality and compatibility invariants

Frozen files, successful CLI output, card-selection/design/combination rules,
review rubrics, tier/tag output contracts, rendering and note/card distinctions
remain acceptance invariants. Optional optimizations above are explicit deferrals,
not hidden executable T3 work. The actual Mac/private gates are enumerated in the
revision-pinned packet, separately from completed Linux implementation.
