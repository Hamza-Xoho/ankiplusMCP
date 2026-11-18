# AnkiPlus student workflows refactor design

Status: product design approved in conversation on 2026-11-18 after requirements interview and grill-me review. Native implementation is in progress; see `docs/refactor/implementation-checkpoint.md` for the tested subset and remaining gates.

Reference implementation: public repository `Hamza-Xoho/ankiplusMCP`, revision `b0f4233`, version 0.3.0. The existing local checkout is older and contains unrelated uncommitted work. These documents do not establish that it matches the reference implementation.

## Purpose

Make the existing card specialist usable by nontechnical students with different source materials, without degrading its current card selection or design. Preserve the combination of existing-card coverage and carefully selected new cards, rather than creating one card per fact.

Lecture-based and textbook-based study are examples, not fixed personas or exhaustive presets. Users can start with no premade decks. Existing user-generated cards must still be searched for overlapping coverage.

AnkiPlus owns making, selecting, unsuspending and maintaining cards. Study scheduling, backlog management, exam planning and chat watchers remain outside it.

## Approaches considered

1. Extend the existing MCP and add a companion review interface. Selected by the user: retain the working engine and add configuration, onboarding, traceability and a preferably embedded Claude review experience.
2. Build the main experience around PDFCraft. Useful for optional source inspection, but introduces another application and does not meet the preferred in-conversation review experience by itself.
3. Build a standalone AnkiPlus application. Offers control over the whole interface but adds unnecessary implementation and maintenance for the agreed first direction.

Direct coordination with the separate Anki MCP is approved as an architectural direction. This supersedes the previous prohibition on connection code only for the new, explicitly scoped adapter. It does not authorize network code in the legacy `cards` engine, weakening frozen tests, or modifying any live collection during development.

## Delivery and platform constraints

- Target Claude Pro and Claude Desktop, with installation initiated by pasting a repository link or setup prompt into Claude Code. No separate model API subscription is required by the proposed workflow.
- macOS is the first supported release platform. Immediate Mac access is unavailable. Develop portable components and CI checks elsewhere, but do not claim complete Mac support or release until real Mac acceptance passes.
- Windows support follows its own complete validation. Correcting a Windows path is not evidence of Windows support.
- The first release includes all agreed product features and all verified required fixes. Internal phases are not permission to publish an incomplete subset.
- Maintain a disposition for every architecture-audit finding. Recommendations and hypotheses are not automatically mandatory changes.
- Do not publish packages, push branches, deploy services, or change the user's live Anki collection as part of writing this plan.

## Preserve the working quality process

Trace which runtime the owner actually uses: legacy `/anki2`, newer MCP guidance, hooks and external maintainer files may contribute different behaviour. Do not infer the canonical workflow from the README alone.

Preserve the current house style, selection and combination principles, tiering, tag conventions, rendering and AI reviewer requirements of that actual workflow. User approval does not bypass technical or existing quality checks. Automatic mode skips user review, not quality review.

Preservation has two checks: deterministic CLI/artifact contracts and representative source-to-card evaluations. Model-generated wording is not guaranteed byte-identical. Include real OCR and rendering checks as well as deterministic synthetic CI cases. Never regenerate a golden snapshot merely to hide a regression.

## Configuration and onboarding

Keep a validated, versioned configuration separate from installed code. Store source habits, relevant deck IDs, card profile, data folder, user-review preference and explicit automatic-mode matching policy. Do not replace the existing card-design rules with simplified persona rules.

Setup helps install Anki and the required companion/tools, registers the relevant host connections without erasing unrelated configuration, and explains permission or restart steps in plain language. A missing dependency gets a specific diagnosis; an OCR timeout is not described as proof that OCR is uninstalled.

Ask about existing decks instead of assuming board decks. No premade deck is a valid setup. Recommend user review strongly, explain the bulk-processing alternative, and recommend leaving uncertain matches pending in automatic mode.

Persist `onboarding_complete`, `onboarding_version`, `config_version` and completed health checks. The completion flag is set only after the required setup is verified; a guide or flag alone is not success. An interrupted installation can resume without duplicate registration or discarded user choices. Product updates ask only newly relevant questions.

Users can request preference changes in ordinary language. Show a plain-language diff and require explicit confirmation before saving a lasting preference. In-run choices default to the current run only. Saved changes affect future decisions and invalidate affected staged proposals, not past records or already applied actions.

Generate a local guide named `Start here — AnkiPlus` with these sections:

1. Your AnkiPlus setup.
2. Make your first cards, with source-appropriate steps and a copyable prompt.
3. Check what AnkiPlus proposes, adapted to the selected review mode.
4. What happens after approval, including required running applications and incomplete outcomes.
5. Everyday requests.
6. Find your files and history, with the actual chosen locations.
7. Change your setup or get help.

Each section explains what to do and why it matters. Avoid developer terminology and unsupported features. Save the guide in the chosen data folder and tell the user its exact location. Regenerate affected sections after confirmed configuration changes without losing user-authored notes. Private paths and user records never enter the public repository.

## Source identity and card evidence

Retain immutable source snapshots and their hashes. A source document, a selected chapter/page range and a run are distinct identities. Reusing a document does not collapse separate chapter selections or reruns into one history entry. Revised source bytes retain an explicit relationship to earlier versions without silently reusing stale extraction.

For each proposed card or existing-card coverage decision, store supporting source references: source version/hash, physical PDF page number, printed page label when available, exact extracted quote and extraction origin. Multiple passages can support one card. Display OCR-derived quotations as such; do not invent a quote where only an image is available.

Offer a rendered source page or crop when useful. The reviewer sees a citation such as `Intro to connective tissue, PDF page 7`, its quoted LM bullets and optionally the original slide. Page numbering must not silently confuse physical pages with printed book numbering.

Source references stay in the external record; adding fields or tags to existing card output is not necessary for this feature. Persist evidence after approval so records remain inspectable. Original documents are never annotated in place; use copies or overlays.

## Coverage and repeat runs

Search the user-approved relevant decks and previously generated notes before generating gaps. Record queries, returned IDs and decisions; this supports inspection but does not prove semantic completeness. Use the same current card-design principles for the remaining gaps.

Distinguish `already_covered`, `propose_unsuspend`, `propose_create`, `explicit_update` and `pending`. Already-active suitable cards remain unchanged. Recognise prior successful actions before proposing creates on repeated runs. Reconcile uncertain prior writes first. Semantic duplicate prevention is an evaluated goal, not an unconditional exact-match guarantee.

Uncertain matches and source contradictions appear in review with card text and source evidence. Automatic mode defaults to leaving them pending, processes unrelated work and records that outcome. Other automatic policies require an explicit configuration choice. The user can resolve pending work during a later run or revisit the original run without losing its history.

## User review and approval

Prefer an interactive MCP App review inside Claude Desktop. A compatibility experiment must validate the actual local connection, UI state and installed host support; a browser/WASM build alone is not proof of embeddability. The existing CLI/text tools remain usable, but are not a substitute for the agreed first-release interactive capability without a user decision.

Display card text, proposed actions, source evidence, existing coverage and unresolved findings. Permit keep, exclude, edit new drafts, resolve matches and approve. Rendered card fronts/backs are not required for the user's interface; preserve the existing AI visual review separately.

Existing premade notes are protected by default. Editing displayed existing text proposes an adapted new draft unless the user explicitly chooses to modify the existing note. Explain that a cloze note can generate several cards. Suspension/unsuspension must name actual card IDs, not note IDs.

User edits affect this run only and trigger relevant validation/review before final approval. Bind approval to the complete proposal digest: fields, actions, target notes/cards, media content hashes, source evidence, relevant configuration and quality-review evidence. Any affected change before application invalidates that approval. Automatic mode records configuration-based authorization rather than fabricating a human approval event.

## Anki coordination and recovery

Add a narrow adapter to the separate Anki MCP for the required reads, searches, templates, media operations, approved note creation/explicit update, suspension/unsuspension and readback. Validate actual operation names, transport, authentication and capabilities before freezing adapter details. Do not add a general proxy or direct database mutation.

The coordinator enforces quality checks and exact proposal authorization immediately before application. It rereads relevant collection state: changed fields, missing records or changed collection/profile identity become conflicts; already-unsuspended cards are recorded as unchanged. Never silently overwrite or substitute.

Journal operation intent durably before an external write, record per-operation acknowledgements, and read back relevant fields/media/card states. Keep note IDs separate from generated card IDs. Report confirmed success only for the portion actually verified.

There is no distributed transaction across the local journal and Anki. A timeout or process death after sending produces an uncertain outcome. Reconcile by known IDs and available collection evidence before retry; if reconciliation is inconclusive, require resolution instead of blindly resending. No unsupported exactly-once guarantee or automatic destructive rollback.

This protects the AnkiPlus coordinator path, not unrelated tools or users calling Anki directly. Legacy host hooks remain documented guardrails, not portable enforcement. Offlining Anki leaves a resumable staged run, not a falsely completed one.

## Run records and index

One user-selected data root, outside installed source, holds source workspaces with multiple runs. Retain immutable events and versioned proposal/review snapshots. Record source selection, extraction, quality checks, coverage decisions, user edits/exclusions, configuration versions, approval, operation intent, results, verification and unresolved work.

Record IDs and explicit units: notes created, cards generated, cards suspended/unsuspended and unchanged records. Results accumulate without overwriting earlier batch evidence. Preserve caller-supplied evidence labels when importing old receipts; migration must not manufacture independent verification or missing lecture-to-card relationships.

Use a rebuildable SQLite index over file records for sources, runs, note/card IDs, stages and outcomes. SQLite is an implementation choice, not a requirement expressed by the user. Loss of the index must not lose history. Expose history through separate CLI/search exports and readable summaries, not a new history screen in the card-review interface.

Logging is mechanical where possible, with no generated rationale required. User feedback is historical evidence, not automatic preference learning. Preserve records indefinitely by default; explicit cleanup may remove reproducible previews/caches but not audit history or the only source copy. Do not log credentials, transport secrets or unrelated user data.

## First-release acceptance

- One clean Mac setup completes through the supported Claude Pro Desktop workflow without a separate model API subscription.
- A novice can follow their tailored guide and review text/source evidence before applying changes.
- Lecture, selected textbook chapter, no-premade-deck and premade-deck scenarios pass.
- Repeat source and overlapping topics reuse coverage; uncertain matches stay pending or follow explicitly saved policy.
- Existing quality checks remain enforced, including after user edits.
- Approval invalidates when its bound proposal changes; unrelated configuration edits do not alter prior history.
- Confirmed create/unsuspend results contain real note/card IDs and readback evidence in an isolated Anki profile.
- Interrupted installation, interrupted writing and lost host context can resume without blind duplicate writes or lost results.
- Legacy contracts and representative card-quality checks pass; missing private fixtures are explicitly resolved for acceptance.
- All required audit fixes have evidence, and every deferred/out-of-scope audit item has an explicit reason.

## Remaining technical decisions

Resolve experimentally: embedded UI transport and local file access; independent reviewer execution under the actual Desktop/Pro host; exact Anki companion identity and capabilities; cross-process locks and durable publication strategy; safe reconciliation with actual duplicate behaviour; token transmission by each supported host. These are investigation deliverables, not promises of compatibility.

The implementation plan must stop at the compatibility gate if the target experience cannot preserve the approved constraints, report evidence and present alternatives. It must not quietly replace reviewers, require a separate API key or require a different app.
