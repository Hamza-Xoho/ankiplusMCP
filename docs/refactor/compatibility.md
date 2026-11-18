# Desktop compatibility investigation

Status: documentation and repository inspection only, 2026-11-18. This is not a completed compatibility spike or a claim of tested Desktop support.

## Established locally

The existing product is a stdio MCP server. No internal sampling/create-message implementation was found in `src/`. Two independent reviewer definitions exist in `.claude/agents/`, and the legacy skill requires the host to launch them. Installing the newer MCP in Desktop alone does not establish those reviewers will execute.

The owner's documented add-on is AnkiMCP on local port 3141. The first-party tool reference documents collection search/read, note creation/update, templates/CSS and media operations. It distinguishes partial batch success. No live companion connection was opened and no collection was mutated.

## Primary documentation

- MCP Apps testing: https://apps.extensions.modelcontextprotocol.io/api/documents/testing-mcp-apps.html — reference-host and actual conversational-host testing are separate; local stdio is listed as a supported connection route.
- AnkiMCP tool reference: https://ankimcp.ai/docs/reference/addon/tools/ — use actual capabilities/version to map operations rather than assume AnkiConnect semantics.
- Add-on source: https://github.com/ankimcp/anki-mcp-server-addon — identify transport/version/authentication and inspect actual result schemas before writing an adapter.
- Claude connector networking: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp — remote connectors originate from the cloud; local stdio connections are separate. Local-device Cowork and cloud Cowork must not be treated as equivalent.
- Cowork plugin guide: https://claude.com/resources/guides/claude-cowork-product-guide/extending-claude-cowork-with-plugins — plugin subagents have distinct contexts. This is evidence for an investigation route, not proof that the current reviewers and embedded UI work together locally.

Documentation can change; record the installed host/add-on versions in actual acceptance evidence.

## Required real-host experiment

1. On a Mac, use the supported Pro Desktop mode; record exact Chat/Cowork/Code surface and local/cloud execution.
2. Connect sample stdio MCP App and demonstrate select/edit/exclude followed by a server-side decision. Reconnect and confirm the same proposal version survives.
3. Run fresh maintainer/student contexts with the existing packet rules, check/render artifacts and no author conversation inheritance. Verify neither separate API credentials nor an unapproved weaker review are needed.
4. In an isolated Anki profile, discover companion capabilities, create synthetic notes, resolve distinct card IDs, inspect duplicate/partial-success responses and verify suspension state.
5. Interrupt the host after a write is accepted and inspect available readback evidence before selecting retry semantics.
6. Record whether text and structured content both enter model context, and whether direct UI selection invokes the model.

## Gate

No Mac/Desktop session or isolated live Anki is available on this development host. Consequently the combined local interactive UI + independent reviewer + companion path is unverified. Do not freeze production transport/UI implementation from documentation alone, expose Anki publicly as a workaround, or replace the quality process silently. Durable records and other transport-independent work may proceed without claiming this gate passed.
