# macOS host lifecycle evidence and launcher fixes

Current status: **launcher lifecycle passed on the reported Mac at `d5c345f`**, without manual config edits. Evidence is user-reported; raw Mac artifacts have not been independently inspected on this development host. Earlier workaround-dependent observations below are retained as history.

## Report supplied from the real Mac

The user reported the following at `94aa1c3` on `test/macos-compatibility`. These are real-host observations supplied in conversation; the development host has not independently read the Mac's artifact files.

- macOS 15.6.1 (24G90), arm64; Claude Code 2.1.227; Python venv 3.12.12 (system Python 3.15.2); Node 25.2.1, npm 11.6.2, uv 0.10.2.
- Frozen sync/lock checks, wheel and launcher build/install, doctor, and all five synthetic rehearsal scenarios passed. The rehearsal reported `local_refactor_verified` and zero Anki operations. Full `check-mcp.sh` was not run on the Mac.
- Unicode/Arabic paths were exercised. Tesseract 5.5.4 has eng/osd only: Arabic OCR was not exercised. Doctor identified system Google Chrome, not independently demonstrated bundled Chromium use.
- Desktop registration used `npx -y file:<absolute local tarball> serve` and a synthetic workspace. Manual `ANKIPLUSMCP_PY_SPEC` and `ANKIPLUSMCP_UV` entries were required. After correcting the nonstandard uv location, two restarts connected successfully and tools/list answered. A separate stdio client using the exact registered command/environment listed 36 tools. Later logs showed no remote Git package fetch.
- Uninstall returned 0 but kept the manually edited server entry and deleted its receipt. The user removed only that key, confirmed unrelated Anki/top-level settings matched the backup, then reinstalled with the same manual overrides. Desktop remains running with that registration.
- A Claude Code state-file hash changed during the session. Its origin was not established; it must not be described as a proven unchanged host-state check.
- Raw Mac evidence is retained there in `.artifacts/premacos/host-lifecycle/` (including `SUMMARY.md`), `.artifacts/premacos/host-backups/`, and `.artifacts/premacos/mac-*`. Config backups remain user-owned; these fixes do not delete them.

The initial unpinned `--version` call had cached the released v0.3.0 Python package through uv. Subsequent commands explicitly used the local wheel; this was not a global installation. Cache deletion is unnecessary for testing a correctly pinned entry.

## Defects reproduced and fixed locally

1. Init persists the explicitly supplied `ANKIPLUSMCP_PY_SPEC` and resolved uv executable in the server environment. It copies no unrelated environment variables. Native host adapters carry these two values through their respective config/CLI formats.
2. Local launcher references are normalized to absolute `file:` specs, including Unicode/space paths. Registry/Git references and remote URLs remain unchanged.
3. Uninstall preserves modified/non-JSON config, returns 3 for incomplete removal (2 for failed host commands), and retains only unresolved installation records for retry. Already-absent entries count as gone. It never silently deletes manually changed server entries.
4. Re-init can refresh an existing owned JSON receipt when the live config exactly matches the requested registration, supporting the previous manual-env workaround. It does not adopt ownership of an untracked pre-existing entry.

These launcher changes require a new Mac lifecycle run. They do not retroactively turn the workaround-dependent run into a clean installer pass. Local RED/GREEN logs live under ignored `.artifacts/macos-launcher-fixes/`.

## Retest on the Mac

Fetch `refactor/student-workflows` and check out the fix commit recorded in the handoff. Preserve the working config, install receipt, existing test data and backups before proceeding. Build a new launcher archive in a fresh artifact directory to distinguish it from the previous archive. The Python implementation is unchanged; the current local wheel remains usable.

Run init with `ANKIPLUSMCP_NPX_REF` pointing to the new local archive, `ANKIPLUSMCP_PY_SPEC` pointing to the absolute local wheel, and `ANKIPLUSMCP_UV` pointing to the actual uv binary. Preview with `--dry-run`; replacing the previous archive reference needs the explicitly scoped `--force` option. Require the generated entry/receipt to contain both env values without manual config editing.

Fully quit/reopen Desktop twice and verify connection/tools, then run `uninstall --host claude-desktop --yes`. Require successful removal of only the owned entry, preserved unrelated settings, then reinstall and restart again. Also test a deliberately changed synthetic entry: uninstall must return 3 and retain its receipt; restore the recorded value and retry successfully. Do not weaken ownership checks to remove a changed entry automatically.

Record exact revision, package paths/hashes, commands, exits and config differences. Do not delete user backups or the uv cache as part of this test. Anki operations remain zero.

## Remaining gates

The local stdio/Desktop connection and workaround-dependent lifecycle have evidence. Embedded review UI, actual independent maintainer/student reviewer execution, companion capability/write recovery, onboarding integration and private-quality acceptance remain not_run. The reports do not establish these product integrations or release readiness. See `macos-test-packet.md` and `compatibility.md` for the remaining experiment.

## Local fix verification (2026-11-19)

`npm test`: **42 passed**, including all lifecycle regressions and a packed-archive execution through real offline `npx` with spaces/Unicode. Regression-first failures are retained in `red.log`, `adapters-red.log`, `migration-red.log` and `refs-red.log`; final results are in `npm.log` under `.artifacts/macos-launcher-fixes/`.

`./scripts/check-mcp.sh`: **382 passed, 1 existing system-Chrome skip**, all 12 frozen contract hashes intact, wheel build, version/privacy guards, **42/42** host hook checks, and **IDENTICAL (66 files, 14 commands)** Linux golden. The Python engine/MCP source and frozen files are unchanged by these launcher fixes. No container rebuild was needed: the image does not include this Node launcher, and its Python implementation/dependencies are unchanged. No Mac revalidation is claimed for the new launcher until the lifecycle retest above runs.

## Clean Mac lifecycle retest (user report, 2026-11-19)

The dedicated `test/macos-compatibility` checkout fast-forwarded from `94aa1c3` to `d5c345f` and was clean. `npm test` passed **42/42** on the Mac. The fresh archive is `.artifacts/premacos/launcher-d5c345f-20261119-030234/ankiplusmcp-0.3.0.tgz`; its reported abbreviated SHA-256 is `8531956a…3418`. The unchanged Python implementation still uses `dist/ankiplusmcp-0.3.0-py3-none-any.whl`, reported abbreviated SHA-256 `22a4b4d9…9b74`. These abbreviated hashes are identification notes, not complete hashes independently verified here.

Before changes, backups were saved under `.artifacts/premacos/host-backups/d5c345f-retest-20261119-030227/`.

- Init dry run without force correctly refused the changed archive reference with exit 3; force dry run planned the replacement with exit 0.
- `init --force --yes` exited 0 and populated both `ANKIPLUSMCP_PY_SPEC` and `ANKIPLUSMCP_UV` in the live entry and install receipt without hand editing.
- Two complete Desktop restarts connected successfully and answered tools/list; the reported stdio listing contained 36 tools.
- With Desktop quit, uninstall exited 0 and removed the owned entry and receipt. The unrelated Anki entry and top-level settings were identical to the pre-change backup.
- Reinstall exited 0 with both runtime env values present in entry and receipt. A third Desktop restart connected and listed 36 tools. Desktop remains running with this registration.
- A deliberately changed entry in a synthetic config under an isolated test home produced exit 3, preserving the entry and receipt. Restoring its recorded value and retrying produced exit 0 and removed the receipt. This negative test did not modify the real Desktop config.
- No remote Git package fetch appeared in the Desktop logs. **Anki operations: 0. No blockers for this stage.**

Raw evidence summary remains on the Mac at `.artifacts/premacos/launcher-d5c345f-20261119-030234/SUMMARY.md`. Five launcher backup files beside the real Desktop config were retained; no cleanup was requested or performed by the development host.

This closes the reported launcher registration/restart/scoped-uninstall/reinstall stage. It supersedes the pending-retest status in the earlier local-fix checkpoint. It does not close embedded review UI, independent reviewer execution, companion operations/recovery, onboarding integration, the unrun full Mac suite, bundled-Chromium/Arabic-OCR checks, or private-quality acceptance.
