# AnkiPlus architecture audit disposition

Reference: user-supplied Claude audit of `b0f4233` (0.3.0). This is a planning register, not an independently reproduced audit. Every item requires code/test evidence at execution. “Required” means fix a verified defect in the retained workflow before release; it does not mean implement the auditor's exact suggested mechanism.

Plan task numbers refer to `2026-11-18-student-workflows.md`.

| Audit ID | Disposition | Owner task and acceptance |
| --- | --- | --- |
| A1 | Required if reproduced | 11: count mismatch remains recoverable before P6 completion. |
| A2 | Required | 5: artifact publication does not stale unrelated card edits. |
| A3 | Required | 5: native work does not hold unbounded exclusive locks; stale/cancelled publication rejected. |
| A4 | Required if retained CLI affected | 11: concurrent continue refuses cleanly. |
| A5 | Investigate then scope | 1, 11: new user-review edits must work; changing legacy round limits/amend policy needs an explicit compatibility decision. |
| A6 | Required if reproduced | 11: target/deck collision logic sees actual preflight inputs. |
| A7 | Required defects; verify each subclaim | 1, 11, 13: corrupt-state containment, slides support claim, timeout diagnosis, reviewer subset and unused logic each get a recorded result. Do not change reviewer sampling silently. |
| B1 | Required safe retention | 4, 12: timestamps, abandoned-temp recovery and explicit derived cleanup; never auto-prune permanent history. |
| B2 | Required | 4: labels, timestamps, stage and recency query. A list can resume with IDs even if metadata is poor; avoid overstating the original defect. |
| B3 | Required recovery; measure shutdown | 5, 12: jobs discoverable after lost context, bounded shutdown and explicit cooperative cancellation limits. |
| B4 | Required durable publication | 4, 5, 8: recover interrupted state/event writes; no claim several file renames form a transaction. |
| B5 | Required consistent reads | 5: concurrent snapshots/reports/checks tested with a documented locking order. |
| C1 | Required | 6, 8: valid source references, quotes, media digests and retained external provenance without new output tags. |
| C2 | Required coverage records | 6: collection queries/hits/dispositions logged. New evidence does not itself prove semantic coverage; do not require legacy query evidence retroactively. |
| C3 | Required honest docs and displayed distinctions | 6, 13: rejected omissions distinct from coverage. Turning legacy warnings into blockers is not approved automatically. |
| C4 | Required surfacing | 6, 9: show/log reviewer set findings. Do not change their severity or rubric silently. |
| D1 | Required for new coordinator | 8: exact authorization, durable outcomes and readback. Document legacy limits separately. |
| D2 | Required | 8, 11: per-batch state and no blind retries; unresolved tier/suspension failures visible. |
| D3 | Required | 4, 8: cumulative receipts, stable draft/batch IDs and reconciliation before repeated creates. |
| D4 | Required new-path control; legacy guardrails documented | 7, 8, 13: validate planned actions/targets and collection state. No claim that a token prevents external tools bypassing AnkiPlus. Recheck conflicting audit descriptions of Codex hooks. |
| D5 | Required if explicit updates support tier changes | 6, 8: keep note/card state consistent with approved actions. Any tag/output change must be explicit and regression-tested. |
| D6 | Required truthful provenance | 3, 8: preserve actual independent quality process; never equate report filenames with verified independence. |
| E1 | Required efficiency | 12: stable-ID partial edits preserve untouched drafts. |
| E2 | Required bounded responses | 12: pagination and null/default compatibility checks. |
| E3 | Measurement before change | 3, 12: inspect host forwarding; do not remove structured results on speculation. |
| E4 | Measure, then proportionate change | 3, 12: schema/token budget with host loading behaviour; no arbitrary tool-count target or forced consolidation. |
| E5 | Measure; quality-sensitive changes deferred pending evidence | 2, 12: summary structure/format changes must preserve selection and tier suggestions; A/B test if reviewer inputs change. |
| E6 | Required drift control; wording changes need evaluation | 2, 13: repair broken references and compare duplicated templates. Do not trim reviewer instructions as routine deduplication. |
| E7 | Required if verified wasted repeat work | 12: shared OCR cache with complete identity and identical labels. |
| E8 | Optional measured optimisation | 12: image resolution/encoding change only after legibility and token measurements. |
| F1 | Required | 2: committed normalized baseline in CI plus real OCR/render quality acceptance. Stubbed OCR is only one test lane. |
| F2 | Required | 2, 14: public synthetic coverage and explicitly completed private acceptance; no frozen-test skip manipulation. |
| F3 | Required supported claims | 2, 13: checks and version-independent package discovery. Windows CI is not full Windows support. |
| F4 | Required freeze verification | 2, 13: verify hashes and protect sensitive test infrastructure. CODEOWNERS only claims enforcement if matching repo branch protections exist. No blanket permission to edit .codex/.agents. |
| F5 | Required targeted gaps | 2, 5, 9: config/roots negotiation, concurrency, image bounds and actual session tests. Coverage percentage is diagnostic, not a release goal alone. |
| G1 | Required path defect | 10, 13: Windows APPDATA logic tested without advertising Windows as supported yet. |
| G2 | Outside first-release promise | 13: no new Cursor/Hermes support required; preserve documented existing support without false compatibility claims. |
| G3 | Required reproducible installation; registry publication conditional | 10, 13: pin/test install provenance and package identity. npm/PyPI publishing needs separate authorization; no automatic account or release operations. |
| G4 | Investigate namespace collision | 13: do not rename/remove legacy `cards` command speculatively; document and test chosen packaging. |
| G5 | Required coherent configuration | 5, 13: one validated user configuration path; inert historical files clearly labelled/removed only after usage checks. |
| G6 | Required portable new path | 3, 10, 13: new coordinator independent of POSIX host hooks; document retained legacy assumptions. |
| G7 | Required if shipping container | 13: rootless build and actual render smoke; review dependency reproducibility rather than equating absent hashes with a demonstrated vulnerability. |
| G8 | Required | 13: metadata tests derive version rather than hard-code it. |

## Conflicts and cautions

- The audit groups A1/A2/A3/A4/A6, B1–B5 and several new validations as “behaviour-neutral.” They can change errors, timing, accepted inputs and user records; verify compatibility individually.
- Enforcing new search-evidence or source-reference requirements may reject previously accepted work. Migrate or retain explicit legacy mode rather than silently breaking source-free card workspaces.
- “No network in AnkiPlus” is historical intent superseded only for the approved narrow companion adapter. Preserve the network-free shared engine and truthful evidence labels.
- Existing test failures attributed to missing OCR/browser remain unverified checks until rerun with compatible dependencies. The reported totals are supplied evidence, not results from this planning session.
- Card-quality preservation is not established by CLI byte snapshots alone. Model outputs, OCR fidelity, coverage judgements and visual review need representative evaluation.

## Closure record format

For each item record: ID, verified revision, reproduction/test, actual impact, chosen fix or reason for deferral, compatibility effect, quality-baseline result and acceptance evidence. “Needs investigation” items affecting a release requirement must resolve before release; optional optimisations may close as explicitly deferred.

## Verified continuation evidence (2026-11-19)

These are scoped updates, not closure of the full register:

| IDs | Source | Reproduction and disposition | Compatibility / acceptance boundary |
| --- | --- | --- | --- |
| A7 (corrupt-state containment), B3 (job discovery), E2 (bounded response) | `8d068fa` | Three failed-first regressions reproduced unreadable-job list failure, non-object-record crash and invalid owner acceptance. Damaged records now remain intact; valid jobs and bounded error pages remain discoverable. Discovery/locking/store suite: 13 passed. | Clean listing shape retained; optional error summaries and continuation apply when damage exists. Broader corrupt-state, shutdown and response-budget requirements remain open. |
| G8 | `758dd18` | Version expectations now derive from declared/installed metadata. A complete disposable launcher+skills copy at manifest version 9.9.9 failed with old assertions and passed 29/29 with corrected assertions; actual repository Python checks passed 19/19 and launcher 42/42. | No package version/runtime changed. Synthetic fake-child version stays an arbitrary forwarding control. Registry publication and real-host acceptance remain separate. |
| B4, D3 (caller-receipt read recovery only) | `510c1e4` | The fresh whole-branch reviewer reproduced lost visibility of durable journal evidence after interrupted projection. Four restart/report/import regressions and a legacy-wrapper preservation regression failed first, then passed. Shared read-only folding now preserves all saved caller receipts without a second recording call. | Full suite 634 passed/25 existing skips; no original JSON mutation, independent Anki verification or collection retry. Production intent/apply/reconciliation requirements remain open. |
| D6, E3, E4 | Existing Mac reports, not freshly inspected raw evidence | Reviewer provenance, complete sheet inspection, active companion schemas and text-channel forwarding remain unresolved. The subsequent supplied response describes instructions read from origin, not their execution results. | Do not close these from report filenames, installed candidates, synthetic UI results or estimated tokens. Both response channels retained. |

Raw logs, including the corrected disposable-copy attempt and its initial missing
skill-folder failure, remain ignored in the original plan's workspace. No private
Mac transcripts, credentials or collection data were committed. The current
whole-branch engineering review is distinct from the still-required independent
product-quality reviewers and real-platform acceptance.

## Received Mac evidence assessment

The later seven-file intake is assessed in
`docs/refactor/macos-evidence-assessment.md`; hashes and copied originals remain
ignored. D6 advances from names/configuration alone to supplied per-request
model/effort, packet-input and template/image inspection evidence, with local
source-hash checks. Blind recall and representative quality remain unresolved.
D1–D5 are not closed by stock-Cloze synthetic operations or caller-journal recovery.
Actual identity binding, media content, unsuspend and live loss-of-receipt recovery
still need supported contracts and acceptance. The bounded follow-up plan retains
these requirements and forbids guessing or weakening them. E3 forwarding remains
unverified; both response channels stay unchanged.
