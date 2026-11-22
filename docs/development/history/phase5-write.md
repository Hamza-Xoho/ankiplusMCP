# Phase 5: automatic gate, write plan and report

Q-1 contains no successful probe result. Direct mode is therefore absent, including its module and flag. No approval step or bypass option exists.

The gate selects the latest review round, checks both closing summaries and section reports, binds them to the apply log's report and resulting draft hashes, checks outstanding findings, and reruns validation. It records hashes of review, target and source inputs. Write refuses changed drafts or changed review/validation inputs. Rerunning unchanged commands preserves artifacts except the command log and freshly measured usage.

Native batch arguments and updates contain no metadata keys. `write/provenance.json` records tool/version/time and artifact hashes. Native Anki import headers begin at byte zero. The first deck/type group uses `import.txt`; further groups use `import-02.txt`, etc. Fields use quoted TSV, preserving embedded tabs, newlines and HTML. Update operations stay in `updates.json` and do not become import duplicates.

`cards report` requires recorded successful writes and counts matching `expected.json`. Inline callers record actual read-back counts in `build.json.write` (`created`, `updated`, `suspended`, `errors`) and complete P6 with `cards state phase`; a plan alone never represents a completed write. The existing `state set` remains restricted to documented facts. Current-session metering uses `CLAUDE_SESSION_ID` or the meter's latest-project-session resolver, with all usage output under the build. Missing/unreadable usage refuses to produce a successful report. Only a matching `.current` pointer is removed. Report output ends with the usage line.

## L006 demonstration

`builds/phase5-l006-demo/` uses the converted v1 L006 notes, preserving card fields. **Synthetic PASS summaries and simulated write counts are demonstration data, not evidence of independent review or Anki read-back.** `DEMO.txt` records this limitation. Its sample usage comes from the clean synthetic transcript, not the Codex development session.

- Created: 40 cloze notes, updated: 0; one `write/batches/01.json` with exactly the AnkiMCP arguments.
- Tier counts: 29 / 9 / 2; suspend: 2 tier-3 notes.
- `write/import.txt`, `updates.json`, `suspend.json`, `expected.json`, and `provenance.json` accompany the batch.
- `report.md` is the requested sample, ending with the usage line.

The Phase 5 tests were first run against missing subcommands: 18 failures, 14 setup errors caused by absent commands, and one passing unknown-flag rejection. Regression tests also caught malformed-draft tracebacks, import-header injection, and stale-report inputs before their fixes.

The owner still runs `bash .codex/tools/gate.sh 5`, imports the fallback into a scratch Anki profile, then freezes and commits. Phase 6 runtime files and hooks were not changed. The existing repository has no commit and substantial staged/untracked work from earlier phases; this checkpoint remains uncommitted for the owner’s freeze.

## Verification and auditors

Phase 5 contracts plus edge regressions: **42 passed** (34 contract cases, 8 edge cases). Contract, boundary and token auditor final verdicts: **OK**. Findings were fixed for malformed records, optional-input presence changes, incomplete new review rounds, native import header injection, missing test coverage, and multiline report metadata. Native `write --help` has no direct/bypass flag. L006 sample report has 15 file lines including provenance; fallback has five headers plus 40 rows.

Full repository regression run: **298 passed in 213.92s**. The final Phase 5/edge run separately includes the added eighth edge regression (**42 passed**). `compileall` also passes. No Anki profile import, direct write, developer gate, freeze, or commit was performed; those remain the specified manual handoff.
