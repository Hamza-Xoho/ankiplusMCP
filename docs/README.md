# Documentation

Start with the [project README](../README.md) for an introduction to AnkiPlus MCP.
The guides in this directory describe the current product. Development records
live separately below; their proposals and historical results are not necessarily
current behaviour.

## Using AnkiPlus

| Guide | Read it when you want to… |
| --- | --- |
| [Installation and configuration](setup.md) | Register a host, choose profiles/browsers, configure folders or troubleshoot. |
| [Worked study workflow](study-workflow.md) | Reuse existing cards, draft gaps, inspect previews and approve an Anki handoff. |
| [All 33 tools](tools.md) | Look up inputs, outputs, examples, limits and implementation paths. |

## Understanding and contributing

| Guide | Purpose |
| --- | --- |
| [Developer guide](developer-guide.md) | Current architecture, storage, jobs, development setup and checks. |
| [Capability mapping](capabilities.md) | How original CLI capabilities map to current independent MCP tools. |

## Legacy tools and development records

- [Legacy Lecture2Cards guide](legacy/README.md): using the original `cards` CLI and skill.
- [Legacy architecture](legacy/architecture.md): the original pipeline and design rationale.
- [Development records](development/README.md): design proposals, implementation plans, handoffs, decisions and dated verification evidence.

The four specification links at this directory's root (`anki-v2-brief.md`,
`anki-v2-trd.md`, `design-spec.md`, `test-contract.md`) preserve paths used by frozen
agent tooling. Their documents live under `development/specs/legacy/`; start with
the guides above for current product usage.

This layout separates audiences, not access permissions: development records
remain visible in the public repository. Keep private lectures, credentials,
conversation exports and local diagnostics out of versioned documentation.
