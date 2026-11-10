# P5–P7: gate, write, verify and report

Load at P5 or on resume in P5–P7; do not load draft.md or reviewer templates.

## P5: automatic gate

Use `cards build --continue`; it runs `.venv/bin/cards gate --build <build>` internally. Passed means continue without asking
for approval. Failure means no writes: follow the findings and return to P4
if a review round remains; otherwise stop with blockers. Never bypass a
stale hash, edit gate evidence, or add a force flag.

## P6: stage 1 inline

At the P6 pause the controller has already run `.venv/bin/cards write --build <build>`
after gate passes. Use those generated plans/import files; they have **not written to Anki**. Q-1 has no successful direct
probe: the shipped CLI has no `--direct`. Do not attempt it or shell HTTP.

1. Read `write/expected.json`, `write/suspend.json`, `write/updates.json` and
   `write/provenance.json`. Enumerate `write/batches/*.json` paths without
   dumping their contents. Track actual per-call receipts in
   `<build>/write/receipts.json` (batch path/hash, returned note ids, success or
   failure). On resume, reconcile receipts with Anki; never resubmit a successful
   or ambiguously completed batch.
2. For IO, discover `media` entries with a local script that reads drafts and
   outputs only unique `{path,filename}` pairs to `<build>/write/media.json`.
   Read that small list, then use `mcp__anki__store_media_file` by absolute local
   path and matching filename before adding IO notes. Never send base64. Record
   success. If media upload/access is unavailable, stop and report.
3. Read each batch file once; pass **its content directly as the arguments to
   `mcp__anki__add_notes`**. Do not reconstruct notes, retype fields or re-echo
   payloads in Bash. Each batch already has one deck/type and at most 100 notes.
   Record actual returned ids and failures immediately; never count attempts as
   successful writes. For entries in `updates.json`, call
   `mcp__anki__update_note_fields` with the shipped `note_id` and `fields`.
4. Resolve draft ids from `suspend.json` to the actual note ids (batch order and
   receipts; existing nids for updates), using a local script that reads files
   and emits only the id mapping. `mcp__anki__notes_info` returns **card** ids.
   Suspend every card belonging to the listed tier-3/unresolved notes with
   `mcp__anki__card_suspend`. Do not assume a note has only one card. Verify all
   intended cards are suspended; count suspended notes separately from cards.
5. Run `mcp__anki__find_notes` with each search in `expected.json.verify` exactly,
   and inspect `notes_info` for ids/fields and suspension. The first search must
   yield the intended source notes (account for existing notes from preflight);
   the active-suspension search must yield no unintentionally suspended notes.
   An explicitly flagged unresolved note is an allowed suspended exception:
   confirm its identity through `suspend.json`, not by ignoring search results.
   Read back three actual notes, or all if fewer, comparing their fields to
   batch/update files with a local comparison, never a full drafts dump.
6. If explicitly carding ahead, suspend all source cards, record that extra
   action separately, and explain the expected nonempty active-suspension search.
   Do not silently unsuspend anything. AnKing matches remain proposals unless
   the user has explicitly requested their unsuspension; use their **card** ids.
7. Only after actual writes and read-back match `expected.json`, run
   `cards build --continue`. The CLI auto-records receipts, runs P7 (report)
   and closes the build. Never edit `build.json` or run phase commands by hand.

A hard MCP/Anki error or permission refusal stops the run. Say what failed,
which batches succeeded, and how to resume safely. Offer `write/import.txt`
(and further numbered import files if present) for manual import; updates stay
in `updates.json`, not import duplicates. Never report an import file as an
imported deck. Do not retry via ports, curl or another connector.

## P7: report

Use the report from the P6 continuation: it already writes the report, closes
the build and removes `.current`. Do not continue again after closure. If
resuming an unfinished P7, use `cards build --continue --build <build>`.
No manual phase commands.
