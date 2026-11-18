# Pre-macOS readiness evidence

Status: local source verification passed; hardened container verification recorded below; ready for a real macOS investigation only, no release claim. No push, publication, deployment, Anki endpoint or collection mutation is authorized or performed.

| Architecture candidate | Implementation | Evidence |
|---|---|---|
| Source ownership | `ffca529` | Catalog and existing evidence/source/card/review/protocol tests: 59 passed, 1 existing skip |
| Artifact publication | `ae3cfdd`, `dccad94` | Publisher/native migration tests: 49 passed/1 skip, then 65 passed |
| Run discovery | `3ba5e2a` | Discovery/run/migration/history tests: 26 passed |
| Coverage batches | `4fc6766` | 42 passed; measured adoption gate passed (79.05%/97.98% repeated snapshot bytes) |

Measurement report: `coverage-recording-measurement.md`; raw RED/GREEN logs and task ledger are retained under ignored `.superpowers/sdd/2026-11-18-final-premacos-refactor/`. Raw measurements and final gate logs live under ignored `.artifacts/premacos/`.

The exact tested source and checks are appended below. Real macOS/Desktop compatibility, independent host reviewer execution, companion/coordinator integration, onboarding/guide integration, hosted CI and private-quality acceptance remain outstanding. The original audit register is not closed by this pass. See `compatibility.md`, `acceptance.md` and `macos-test-packet.md`.

## Final reviewed source and actual local checks

Tested source: **`290b246144851e78f2bb3ab75415afb053765c57`, clean**. This includes the single fresh whole-branch review of `b0f4233..d8a5960` and one material fix pass (`290b246`). All three Important findings were reproduced RED and fixed GREEN: uncommitted extraction discovery, dead-marker replacement races, and missing acknowledged journal tails. The focused fix suite passed **89 tests**. No Critical or Minor findings remain reported; no second review was substituted for tests.

| Actual command | Result / retained log |
|---|---|
| `.venv/bin/uv sync --frozen --extra dev` | Passed; `uv-sync.log` |
| `.venv/bin/uv lock --check` | Passed; `uv-lock.log` |
| `CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract` | **615 passed, 25 skipped**; `final-full-suite.log` |
| `./scripts/check-mcp.sh` | **382 passed, 1 skipped**, all **12** frozen hashes, wheel build, **42/42** hooks, version/privacy guards; **IDENTICAL (66 files, 14 commands)**; `final-check-mcp.log` |
| `npm test` | **29 passed**; launcher source unchanged by review fixes; `npm-test.log` |
| `npm pack --pack-destination .artifacts/premacos` | Passed; local tarball only, no publication; `npm-pack.log` |
| `.venv/bin/python scripts/smoke-premacos.py --output .artifacts/premacos/final-smoke.json` | All five scenarios passed; `local_refactor_verified`, **zero Anki operations** |
| `.venv/bin/python tests/tools/coverage_recording_benchmark.py --output .artifacts/premacos/coverage-final.json` | All nine cases reconstructed identical decisions, one snapshot/event per batch; `coverage-final.log` |

Every listed log is under ignored `.artifacts/premacos/`. The full-suite skips are the existing 24 unavailable private-fixture cases and one unavailable system-Google-Chrome case; real bundled Chromium ran successfully. No new skip was introduced. No frozen/legacy engine source changed from plan commit `e7d26d1`. Existing setuptools license deprecation warnings remain. Hosted CI was not run.

Final dependency environment: Linux x86_64, Python 3.14.4, Node 22.22.1, Tesseract 5.5.0, PyMuPDF 2.1, Pillow 13.0.0, Playwright 1.65.0, bundled Chromium 158.0.8127.18. The rehearsal JSON records its exact clean source revision and dependency versions. Local wheel: `dist/ankiplusmcp-0.3.0-py3-none-any.whl`; local launcher archive: `.artifacts/premacos/ankiplusmcp-0.3.0.tgz`. Set `ANKIPLUSMCP_PY_SPEC` to that absolute wheel path when testing the local launcher.

## Recovery limitations and remaining gates

No architecture candidate was deferred: coverage batching met the measured gate. No deferred minor findings. Pre-marker legacy extraction folders retain hash-checked compatibility because their publication provenance cannot be retroactively established. Old headless journals remain readable; new appends establish acknowledged sequence heads. Existing index watermarks detect shortened legacy history across repeated searches. If an old headless tail and its index evidence are both already missing, a rebuild cannot infer that missing history; restore from backup. These limits are not independent-integrity guarantees.

The reviewer declined unsupported external source-manifest replacement during export: no supported source-replacement operation exists, while actual copied-source byte changes are checked. A future replacement API must capture identity atomically. Desktop/macOS, independent host reviewers, companion/coordinator recovery, full onboarding/guide integration and private-quality acceptance remain **not_run**. Full original-plan and audit work follows the real-host experiment; none is implicitly waived. Use the ordered `macos-test-packet.md` and retain `compatibility.md` as unpassed.

Documentation-only handoff updates after the tested source do not change the native implementation these results cover. The final branch is retained locally; nothing was pushed, published, deployed or connected to a collection.

## Hardened container

At clean source `290b246`, `ANKIPLUS_REVISION=290b246 docker compose -p ankiplusmcp config --quiet` and `docker compose -p ankiplusmcp build` passed. `docker compose -p ankiplusmcp run --rm --no-deps --entrypoint python mcp -c "$(cat .artifacts/premacos/container-smoke.py)"` passed: **nonroot real OCR/render; no Anki operations**, semantic revision remained 1. The exact script and logs are retained in `.artifacts/premacos/`: `container-smoke.py`, `final-container-build.log`, `final-container-smoke.log`, `final-image.txt` and `final-container-revision.txt`. The existing read-only rootfs, network disabled, dropped capabilities, no-new-privileges, CPU/RAM/PID limits were retained; no public route or host endpoint was added.
