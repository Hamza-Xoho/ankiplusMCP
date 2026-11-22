# AnkiPlus MCP authoritative release — 2026-11-22

Owner decision: main at b0f423398432708feaab7a157ed7dcbe36bf3b1b (v0.3.0)
is the authoritative implementation. The student-workflows refactor is discontinued.
All subsequent refactor commits, plans, requirements, acceptance gates, Mac retest
packets and incomplete work are historical archives, not outstanding requirements.
Do not merge, cherry-pick, resume or implement that work without a new owner request.
Keep upstream main exactly at the release commit; operational notes belong outside
that revision or on this maintenance branch.

## Recovery and checkout

Active checkout: /home/shakeel/projects/ankiplusmcp-refactor, now on main. Its path
is retained to preserve existing path references; the directory name does not select
an implementation. /home/shakeel/projects/ankiplusmcp is a separate Lecture2Cards
repository with unrelated uncommitted work and was not changed.

Refactor archive (local and GitHub): archive/student-workflows-2026-11-22 at
ea13852c68f04d95fb8670d169715b79be677feb. The original remote refactor branch
was removed only after archive publication, using an explicit SHA lease.
Neither local nor remote main needed movement; GitHub default was already main.

Private recovery folder: /home/shakeel/project-archives/ankiplusmcp/2026-11-22
- checkout-before.tar: full pre-switch checkout including ignored files, excluding
  .git; verified against the live checkout with tar --diff before switching.
- checkout-before.tar.sha256: archive checksum, verified before branch switching.
- repository.bundle: all then-current refs and complete Git history, bundle verified.
- refs-before.txt, status-before.txt, uncommitted.patch: original state; working tree
  was clean, so there was no uncommitted patch or untracked source work to stash.
- inactive-generated/: moved (not deleted) old .superpowers planning/session history,
  build/, dist/, orphan review-ui dependencies, egg-info and orphan tests/isolated
  files (including the companion add-on fixture, never installed or modified).

User data, .artifacts evidence/workspaces, source documents and existing user
configuration remain in their original locations. Full backup is private, not pushed.

## Local configuration inspection

No separate AnkiPlus T3 project is registered on this host; no project scripts select
the refactor. Checked repo .mcp.json (only the separate Anki HTTP server),
.codex/config.toml and .claude/settings.json. No local AnkiPlus launch entry found in
user Codex config, T3 settings, shell startup files or user systemd/config directories.
No active AnkiPlus process/container found. No global instructions, authentication,
source-root permissions, workspace locations or unrelated MCP entries changed.

The release launcher already pins its Python and npx defaults to v0.3.0. The existing
editable .venv was reinstalled from main with --no-deps to refresh release metadata;
the original environment is also in checkout-before.tar. Git fetch refspec/tracking
now selects main and the archive instead of the removed refactor branch.

Other-machine Mac/Claude Desktop configurations could not be inspected and were not
changed. Archived Mac packets and .artifacts retain historical refactor references.
Do not use those packets as active launch instructions or requirements.

## Validation

See adjacent check-mcp.log, npm-test.log, container-build.log and discovery.json.
Discovery uses real stdio initialize and tools/list only, with disposable roots;
requires version 0.3.0 and exactly 33 tools. No collection mutation was requested.
No deployment, package publication or installed Anki add-on change was performed.

Final observed results:
- ./scripts/check-mcp.sh: exit 0; 250 passed, 1 skipped; frozen contract hashes
  verified and ankiplusmcp-0.3.0-py3-none-any.whl built.
- npm test: 28 passed, none skipped or failed.
- Hook verification: 42/42 passed; version agreement and privacy checks exited 0.
- Real stdio discovery: server ankiplusmcp, version 0.3.0, 33 tools; no tools called.
- ANKIPLUS_REVISION=b0f4233 docker compose -p ankiplusmcp config --quiet: passed.
- Same Compose build: failed in the unchanged release Dockerfile because Playwright's
  bundled Node cannot load libatomic.so.1 before browser dependency installation.
  No Dockerfile fix was applied: the owner's exact release source is authoritative.
  No container was started or deployed. The successful wheel and stdio checks use
  the available local dependencies. Original failed no-build-isolation editable
  install was retried with build isolation successfully (setuptools was absent).
