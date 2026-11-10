# AnkiPlus MCP verification

Verified locally on 2026-11-07, Python 3.14/Linux. Source branch:
`feat/ankiplusmcp`, based on upstream `5bb2530`; implementation is uncommitted
because Git author identity is not configured. Container builds are labelled
`5bb2530-dirty`, not a clean upstream revision.

- 177 tests passed: 27 new MCP/service/regression tests, 122 original unit tests,
  and 28 synthetic foundational contract tests.
- Every frozen contract checksum in `.codex/contract.sha256` passed. Existing
  `src/cards/`, `.claude/`, `.agents/`, `.codex/` and contract tests are unchanged.
- Real SDK stdio discovery and calls exercised 33 tools, source extraction,
  structured cards/checks, rendering, MCP image content, domain errors and payloads.
- The same synthetic smoke workflow passed from a separately installed wheel
  outside the checkout and inside the non-root/read-only/network-disabled Compose
  container. The image built successfully and Compose configuration validated.
- The companion skill passed the skill-creator validator.
- An independent reviewer identified six material issues. Regression tests first
  reproduced them; fixes now cover supplied-HTML invalidation, staged/cancel-safe
  extraction, pre-allocation PDF raster bounds, media-filename conflicts,
  duplicate-note update conflicts, and every cloze/native occlusion mask.
- Additional tests cover multi-process locking, revision/snapshot consistency,
  live job ownership vs interrupted jobs, source caching and source-root symlinks.

Reproduce with `./scripts/check-mcp.sh` and
`.venv/bin/python scripts/smoke-mcp.py`. For a built image use
`.venv/bin/python scripts/smoke-mcp.py --command ./scripts/run-container.sh REVISION`.
The container wrapper requires an existing image and never builds on MCP stdout.

Limits: private lecture fixtures were unavailable, so the remaining private-data
contract cases were not run. No live Anki collection or interactive Codex,
Claude Code or OpenCode client was used. The independent reviewer did not judge
factual accuracy, live Anki execution, client UX, or non-Linux support; these
remain explicit limits, not implicit success claims. AnkiPlus performs no Anki
network calls. Windows needs POSIX support through WSL or the Linux container.
