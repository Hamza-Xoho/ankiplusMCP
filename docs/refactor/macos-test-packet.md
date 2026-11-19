> Historical checkpoint/evidence. Current connected-product scope, exact tested
> revisions and ordered Mac acceptance are in [macos-acceptance.md](macos-acceptance.md)
> and [t3-requirement-evidence.md](t3-requirement-evidence.md). Preserve the evidence
> below; do not execute superseded host probes or treat old unfinished-scope lists
> as the current implementation status. The known reviewer-control gate remains.

# macOS compatibility test packet

This packet prepares an investigation, not a release. Read `compatibility.md` and the approved student-workflows design first. Record exact Git SHA and clean/dirty status from `premacos-readiness.md`; use that reviewed source and its locally built wheel/npm tarball, never assume the remote v0.3.0 default includes these changes.

## 1. Record prerequisites and isolate data

Record macOS version/architecture, Python (>=3.12), Node (>=18), npm, uv, Tesseract version/languages, Playwright and its Chromium build, Claude Desktop version, Pro subscription and exact Chat/Cowork/Code surface. Record local versus cloud execution. No separate model API subscription is required or an acceptable silent substitution.

Use a new temporary data directory named `Study notes — اختبار` and synthetic inputs only. Preserve unrelated host configuration. Record host configuration hashes before and after install/uninstall; any registration must be explicitly scoped and preserve unrelated entries. Do not use a real collection.

## 2. Build and install the reviewed revision locally

From a clean checkout of the recorded SHA:

```sh
uv sync --frozen --extra dev
uv lock --check
.venv/bin/python -m build --wheel
npm pack --pack-destination .artifacts/premacos
```

Record filenames/hashes and install the resulting local npm tarball into a disposable npm prefix. Set `ANKIPLUSMCP_PY_SPEC` to the absolute local wheel path before running the launcher; do not accept its default remote Git tag. Consult `node launcher/cli.mjs --help` and the README for supported entry points. Use an explicit disposable data root/source root for server commands. Actual launcher init/setup registration is a separate host integration investigation: back up and compare config, obtain any platform permissions, restart and confirm registration, interrupt/resume without duplicate entries, then test scoped uninstall without removing unrelated entries.

Run the local rehearsal with a fresh output filename:

```sh
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/smoke-premacos.py --output .artifacts/premacos/mac-smoke.json
```

Require all five named scenarios to pass with zero Anki operations. Repeat after a process restart with retained disposable data: select chapter one then two, reopen the first citation/page, patch/render a draft without changing semantic revision, delete/rebuild SQLite and recover the note/card searches. Verify source hashes and historical event bytes. Exercise spaces/Unicode in the installation, data and source paths. Use real OCR and rendering checks on macOS; Linux PNG byte identity is not a cross-platform requirement. Missing dependencies are failures with evidence, not skips.

## 3. Execute the real Desktop/Pro experiment

Follow `compatibility.md` in order:

1. Prove a locally connected embedded MCP App prototype supports select/edit/exclude and server-side decisions. Reconnect and preserve proposal version. Record what enters model context (text/structured content) and whether a UI click invokes the model.
2. Execute the existing maintainer and student reviewer rules in genuinely fresh contexts with their check/render packets, without author conversation inheritance. Verify independence and quality requirements; filenames alone do not prove execution. Do not replace reviewers or require an API key as a workaround.
3. Only in an explicitly authorized isolated Anki profile, discover actual companion name/version, transport/authentication and tool/result schemas. Keep the endpoint local. Record exact capabilities before freezing an adapter.
4. Companion mutations await that explicitly authorized isolated-profile session: create synthetic notes, obtain distinct real note/card IDs, inspect partial/duplicate outcomes and suspension/readback. Interrupt after an accepted write and reconcile known IDs before choosing retry semantics. Do not claim distributed atomicity or exactly-once writes.
5. Record each combination as passed or blocked with versions, commands, inputs, logs and observed behavior. A failure is not permission to weaken the approved workflow.

## 4. External acceptance remains open

Desktop review, independent reviewer execution, companion/coordinator write recovery, completed onboarding/guide integration and private-quality acceptance remain `not_run` until real evidence exists. Implement the resulting original-plan integration tasks before running complete first-release lecture/chapter/no-premade/premade/repeat/uncertainty scenarios. Resolve all 24 unavailable private-fixture cases and representative card-quality evaluations. Hosted CI and Windows support require their own authorized execution. Do not publish based on this packet.
