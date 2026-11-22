# Development records

[Documentation index](../README.md) · [Current developer guide](../developer-guide.md)

These files record how the project was designed, built and checked. They are
reference material for contributors, not installation instructions or a statement
that every proposal was implemented. Dates, unfinished checkboxes and recorded
limitations belong to the stage of development described by each document.

## Designs and requirements

Current-product design records live in [specs/](specs/):

- [Independent MCP toolkit](specs/2026-11-07-ankiplusmcp-design.md)
- [Launcher and host registration](specs/2026-11-10-npx-launcher-design.md)
- [Efficacy and performance work](specs/2026-11-10-efficacy-design.md)
- [Student documentation](specs/2026-11-22-student-documentation-design.md)

The original CLI requirements live in [specs/legacy/](specs/legacy/):

- [Product brief](specs/legacy/anki-v2-brief.md)
- [Technical requirements](specs/legacy/anki-v2-trd.md)
- [Design specification](specs/legacy/design-spec.md)
- [Test contract](specs/legacy/test-contract.md)

Those four historical specifications retain their original contents. Compatibility
links at `docs/` preserve references from frozen hooks and agent definitions.
Historical prose may name other original paths; use the record links below to
find relocated handoffs and measurements.

## Implementation plans

[plans/](plans/) contains task breakdowns from individual development sessions.
They can explain why a change was made; use the current code and developer guide
to determine what is implemented now. The documentation work and its subsequent
organisation are tracked in the [student documentation plan](plans/2026-11-22-student-documentation.md).

## Handoffs, decisions and measurements

| Record | Contents |
| --- | --- |
| [Development history](history/development-history.md) | Original CLI setup and phase-by-phase implementation history. |
| [Decisions and measurements](history/decisions.md) | Probe results, implementation decisions and historical usage measurements. |
| [Lean workspace notes](history/lean-workspace.md) | Historical runtime inventory, configuration and measurement notes. |
| [Phase 4 handoff](history/phase4-review.md) | Review packets and phase-specific validation. |
| [Phase 5 handoff](history/phase5-write.md) | Gate, payload planning and report work. |
| [Phase 6 handoff](history/phase6-runtime.md) | Original runtime skill and guard verification. |
| [Verification record](verification.md) | Dated test/build results and explicit untested limitations. |

New development-only records belong here: designs in `specs/`, plans in `plans/`,
and completed handoffs/measurements in `history/`. Keep maintained user/developer
guides one level up and legacy usage guidance in `../legacy/`.
