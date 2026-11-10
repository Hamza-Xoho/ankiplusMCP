# Phase 4 review handoff

Implements packets, apply, verbatim review templates and JSONL report formats. No runtime reviewers, gate, write, runtime SKILL.md or contract freeze were run. Existing pinned agents match C-7 and were not edited.

## Validation

Initial Phase 4 contracts: 30 failed, 5 passed (the pinned-agent/global error checks already existed). Final Phase 4 contracts plus review edge tests: 59 passed. Auditor findings were fixed; contract_auditor, boundary_auditor and token_auditor returned OK on re-check. Final full regression: `.venv/bin/python -m pytest -q` — **257 passed** in 185.84 seconds, with no warnings. `git diff --check` also passed.

Image token costs are excluded: text estimates use ceil(chars/4). Packet files include provenance. PNG provenance is represented by the packet manifest/header context; no disallowed sidecars are added.

## L006 packets

### maintainer

Path: `builds/phase4-l006/review/round1/maintainer`. 15 files; 13,418 estimated text tokens; PROMPT 191 tokens.

| File | Estimated text tokens |
|---|---:|
| `PROMPT.md` | 191 |
| `brief.md` | 198 |
| `check.json` | 620 |
| `drafts.jsonl` | 6169 |
| `house-style.md` | 1905 |
| `map.md` | 500 |
| `objectives.json` | 105 |
| `pages/p04.png` | image |
| `pages/p11.png` | image |
| `pages/p14.png` | image |
| `pages/p17.png` | image |
| `reconcile.md` | 150 |
| `report-format.md` | 325 |
| `rubric.md` | 1062 |
| `source_slices.md` | 2198 |

Exact PROMPT.md:

```text
<!-- cards packets 0.1.0 2026-11-05T22:53:04.627682Z -->
Use anki-maintainer. Read brief.md, rubric.md and report-format.md. Read drafts.jsonl, source_slices.md, map.md, objectives.json, check.json, house-style.md and reconcile.md.
The brief placeholders mean drafts.jsonl, source_slices.md, objectives.json and house-style.md. Run reconcile.md searches instead of existing.jsonl.
Open all images named by pages/p04.png, pages/p11.png, pages/p14.png, pages/p17.png in one turn using parallel reads, once only. Commit front answers before judging backs. This image instruction takes precedence over the brief's reading sequence.

Write only JSONL to /home/<name>/projects/anki-v2/builds/phase4-l006/review/round1/maintainer_report.jsonl. Return at most 5 lines.
```

### student

Path: `builds/phase4-l006/review/round1/student`. 15 files; 1,579 estimated text tokens; PROMPT 153 tokens.

| File | Estimated text tokens |
|---|---:|
| `PROMPT.md` | 153 |
| `brief.md` | 285 |
| `report-format.md` | 339 |
| `rubric.md` | 461 |
| `sheets/01_backs.png` | image |
| `sheets/01_fronts.png` | image |
| `sheets/02_backs.png` | image |
| `sheets/02_fronts.png` | image |
| `sheets/03_backs.png` | image |
| `sheets/03_fronts.png` | image |
| `sheets/04_backs.png` | image |
| `sheets/04_fronts.png` | image |
| `sheets/05_backs.png` | image |
| `sheets/05_fronts.png` | image |
| `sheets.json` | 343 |

Exact PROMPT.md:

```text
<!-- cards packets 0.1.0 2026-11-05T22:53:04.628052Z -->
Use anki-student. Read brief.md, rubric.md and report-format.md. Read sheets.json; it names every sheet and preview. Use only this packet.
The brief manifest path means sheets.json in this packet.
Open all images named by sheets.json in one turn using parallel reads, once only. Commit front answers before judging backs. This image instruction takes precedence over the brief's reading sequence.
Sheet pairs omitted: none.
Write only JSONL to /home/<name>/projects/anki-v2/builds/phase4-l006/review/round1/student_report.jsonl. Return at most 5 lines.
```

## Review behavior and limits

- Missing flagged cited page images refuse with the exact `cards source --page-image` remedy, keeping packet reads within the build.
- More than 80 notes creates section packets; the main maintainer packet covers the set. Every section report is required by apply.
- Apply is idempotent for unchanged reports/drafts. Once a round has been applied, edited reports/drafts require explicit resolution in the next round; the backup and log are preserved.
- No automated command invokes Claude or Anki. Handwritten report fixtures cover fix, reject, conflict, CSS pattern and malformed input.
- L006 packet copies preserve all 40 source notes. No report is fabricated for the manual runtime check.

## Files changed

- `src/cards/cli.py`
- `src/cards/review/{__init__,packets,apply}.py`
- `.claude/skills/anki2/templates/review/PROMPT.md`
- `.claude/skills/anki2/templates/review/house-style.md`
- `.claude/skills/anki2/templates/review/{maintainer,student}/{brief,rubric,report-format}.md`
- `tests/contract/test_p4_review.py`
- `tests/unit/test_review_edges.py`
- `tests/fixtures/reports/{fix,reject,conflict,css-pattern,malformed}/{maintainer,student}.jsonl`
- `README.md`, `docs/phase4-review.md`

## Manual handoff

The owner runs `bash .codex/tools/gate.sh 4`, then the real independent reviewer/meter check in Claude Code, then freeze and commit. The workspace has no existing commit and contains substantial staged/untracked earlier work; it is left unfrozen and uncommitted for that checkpoint.
