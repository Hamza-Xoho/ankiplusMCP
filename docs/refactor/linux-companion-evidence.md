# Linux companion source and isolated compatibility evidence

The GitHub access retry succeeded on 2026-11-19. The repository reports public,
standalone (`fork=false`, parent/source null). No visibility or repository settings
were changed. Branch local/collection-identity matched c4cad4a6d41063f14611566b92ce5f6349141f97;
its upstream main matched 278f5e9, with no drift. A dedicated Linux clone preserves
the Mac worktree, installation, registrations and real collection. Its local Git
identity reuses the configured primary project's hamza identity.

Reviewed actual source and tests, not a pasted patch description. Tool discovery
uses pkgutil import and the normal Tool registry; the identity tool is read-only.
Upstream v0.41.1..278f5e9 changes version/Nix/docs only: primitive and transport
source are unchanged. This supports source-derived contract investigation for the
reported installed version without claiming a captured live handshake.

Original c4cad4a reproduces 839 passing unit tests; unchanged 278f5e9 under the same
Python 3.13.18/vendor environment reproduces 825. The repaired/extended branch
passes 867 tests with no skips/failures. Existing pytest-asyncio unset-loop-scope
warnings remain. Failing-first regressions cover missing/invalid attributes,
legitimate profile name unknown, lifecycle/object freshness, and bounded byte
readback. Missing identity never receives a hash/session binding.

Standalone rootless containers pass packaged imports against Linux Anki/aqt
26.9.2 and real synthetic collection operations through MCP memory streams:
stock two-cloze creation, actual note/card mapping, selective suspend, unsuspend,
full note reads, media storage plus exact byte/hash readback, and same-profile
close/open freshness. Both textual and numeric add-on package directory names
pass. No host mounts, ports, network, real profiles, credentials or real companion
connections are present. Tests dispatch directly on the single collection thread;
they do not prove Qt queue/HTTP authentication or real Desktop integration.

Raw source/package/image/environment/results are retained in the companion clone's
ignored .artifacts/identity-review directory. The initial build was labelled
c4cad4a-dirty. Failed harness attempts (permissions, missing Qt library, missing UID
record and unsupported FastMCP constructor argument) are retained and corrected.
The final image and archive hashes are in provenance.json; exact pip environments
are retained separately. The standalone source configuration and procedure are
versioned under tests/isolated in the companion repository. The reported Mac
IDENTITY-LIMITS/matrix/E2E-plan/log/checksum attachments were not present in Git;
these independently reproduced Linux results do not claim to inspect those files.

## Safety implications

Complete profile/path/creation evidence, explicit intended-profile binding,
runtime session freshness and fresh exact target reads are complementary checks.
Fingerprint numerical uniqueness is not a requirement. Session changes detect
observed close/reopen and replacement collection objects. An in-place restoration
without either signal can remain invisible; matching exact intended targets is
therefore still required. A separate preflight read and later write have a race.
The current companion mutation tools have no atomic expected-session/target-state
precondition. A narrow conditional-dispatch enhancement must close that race
before the coordinator can claim enforced changed-profile/target conflicts.
This is an implementation requirement, not a request to accept the gap.

The new media operation resolves byte-readback at source/Linux-test level only;
it is absent from the installed Mac add-on. No Mac installation/restart/change is
authorized here. ColdRecall type compatibility, live HTTP/auth attribution,
production apply/recovery and Desktop staged continuation remain open. Successful
Linux probes and 867 unit tests do not finish the student product.

## Checkpoint revisions and engineering review

Companion commits: c86403b (identity/freshness/media) and bcde97d (isolated packaged
checks). A clean bcde97d image also passed import and both synthetic package-name
runs. Image ID: sha256:167afa2561ae1b16e9bbe52d3f9bbbe4fcd798bbd2e331b90e63d8094ddca6bf.
The clean image records bcde97d in its OCI source label. Archive hashes and
complete dependency environments are retained with the raw evidence.

One fresh whole-branch engineering reviewer inspected primary b0f4233..4963722
and companion278f5e9..bcde97d, independently passing105primary and42companion
focused tests. It found one Important implementation defect: concurrent first
history reads could race SQLite schema migration and crash with duplicate column
name journal_token. Two real-connection regressions reproduced it for fresh and
legacy indexes, then passed after schema inspection/DDL were serialized inside
BEGIN IMMEDIATE. Failed connections are closed, not silently ignored.

Post-fix full AnkiPlus public-mode suite:644passed25existing skips; check-mcp:
411passed1existing skip, frozenhashes12/12, hooks42/42, wheel/version/privacy and
unchanged66artifact14command golden. Launcher42/42 and lockfile checks passed in
this session; their inputs were unchanged by the index fix. NoCritical/Minor
implementation finding was reported, and no re-review was substituted for the
regression-tested fix. The reviewer explicitly retains all missing product scope
and real-platform/private-quality acceptance as required work.

Companion push was attempted with the configured GitHub credential and refused
403: account binaryzer0 has pull:true/push:false on that repository. The two
commits remain local pending repository write access; no authorization bypass,
visibility change, fork or alternate repository was attempted. The same account
has push:true on the primary repository.

The post-fix AnkiPlus container build and smoke also passed, labelled
4963722-dirty because the index fix was uncommitted when the build started (now
committed as b41580c). The smoke uses a disposable no-network/no-mount container,
non-root/read-only/cap-drop/no-new-privileges/resource limits; real Tesseract,
Chromium and history-index migration/search pass. No project data volume is
mounted. Build/image/smoke logs are retained in the ignored follow-up workspace.
Canonical upstream fetches also confirmed no drift: AnkiPlus main b0f4233 and
ankimcp/anki-mcp-server-addon main278f5e94c8eb5faedff272c505310e55c540b26f.

This checkpoint does not complete original Tasks7–10 or14, the remaining audit
register, private/representative quality or first-release acceptance. No Mac
add-on install, profile switch, registration change, real-collection access,
service deployment, fork, visibility change, package publication or PR occurred.
The exact Mac host-support action is macos-staged-host-action.md. The implementer
still owns the missing product work; the owner's necessary external actions do
not substitute for that implementation.
