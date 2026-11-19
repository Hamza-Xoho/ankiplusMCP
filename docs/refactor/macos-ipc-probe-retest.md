# Mac probe: Desktop-owned registration retest

Run this from Claude Desktop's local Code session on the existing probe folder.
The agent performs configuration/evidence work; the owner performs necessary app
restart and sample UI clicks. Zero Anki operations. Keep the same sample server,
HTML bundle, model, command, arguments and data-root for this registration comparison.

## Evidence and hypothesis

The owner supplied a screenshot of the embedded synthetic UI and later copied
the exact status `IPC not available for MCP tool call` after clicking Save.
The Mac agent independently reported revision 0/original samples, no state.json,
and no save call in the server observation log. Initial rendering passed; the
widget-to-tool path failed in that Code-managed registration. This does not
establish that server persistence is broken or that the owner omitted a click.

[Upstream issue 106708](https://github.com/anthropics/claude-code/issues/106708)
reports the same symptom. Contributors on November 9 and 12 report successful
widget calls when the same local stdio server is started from Desktop's config,
including in the Code tab. Those are other users' results, not a confirmed fix on
this Mac. [Official Desktop documentation](https://code.claude.com/docs/en/desktop#mcp-servers-from-the-claude-desktop-chat-app)
confirms that Desktop-config servers are available in local Code sessions.

Test the Desktop-owned route once before changing probe/runtime code. Preserve
the failed Code-owned result as a separate row; repeated clicks on that unchanged
route add no compatibility evidence.

## Agent: prepare the scoped change

1. Record actual app/bundled runtime versions where readable, source SHA/dirty
   status, model, exact current project path and current probe state/log hashes.
   Use timestamped evidence under the existing probe directory. Keep the owner's
   UI error and observed server results separate from inferred cause.
2. Read this folder's `registration.json` and `.mcp.json`. Verify the fragment
   contains only `ankiplus-compat-probe` and points to the intended absolute venv,
   probe script and existing data-root. Preserve the folder, samples and logs.
3. Back up the project `.mcp.json` and Desktop's
   `~/Library/Application Support/Claude/claude_desktop_config.json`, recording
   hashes. Preserve JSON structure, permissions and all unrelated values. Refuse
   malformed config. Never include credentials or whole host configs in summaries.
4. Prepare and apply an atomic JSON merge adding only the fragment's probe key
   to Desktop's `mcpServers`. If that key already matches, retain it. If it differs,
   report the exact non-secret mismatch and preserve it for diagnosis.
5. After the Desktop entry is verified, remove only the identical probe key from
   the project `.mcp.json`, retaining other entries/settings and the original
   backup. This prevents the Code-managed definition shadowing the route under
   test. If another Code-scoped definition of this name exists, diagnose its
   origin; preserve unknown/user-owned entries rather than broadly deleting them.
6. Confirm the Desktop entry is identical to `registration.json`, project-local
   duplicate is absent, and unrelated `anki`, `ankiplusmcp` and top-level settings
   match the backup. Record the changed registration origin and new config hashes;
   the earlier generated `.mcp.json` hash is historical evidence, not current state.
7. Save a short resume note in the probe folder with the next checks. Tell the
   owner to fully quit and reopen Claude Desktop, then start a fresh Local Code
   session on this exact folder, with Worktree off. No Terminal action is required.

## Owner and agent: verify the result

1. The agent verifies actual probe tool discovery in the fresh session and calls
   `open_sample_review`. The owner confirms whether the embedded view renders.
   Directly launching another stdio client is supplementary evidence only.
   **If Desktop displays a widget-load error and text fallback, stop the sample
   edit/save instructions.** Record rendering as failed on this registration,
   inspect the selected probe's resource response/logs, and follow the diagnostic
   continuation below. A successful opener tool call does not establish rendering.
2. The owner changes sample-a to `Mac test edit`, unchecks sample-b and clicks
   Save once. Capture the exact widget status before Reload, including any error.
3. The agent reads actual server state and observations. A save pass requires the
   selected data-root's state.json to contain those decisions at the next revision
   and a received `save_sample_decisions` call. A displayed revision alone is not
   enough. The agent must not simulate the click by calling the save tool or
   editing state files.
4. If saved, the owner clicks Reload and verifies the same text/selection. Only
   then test full-app restart persistence and later stale-view refusal from the
   main packet. Record whether the click caused a model turn, when observable.
5. If Code still has the bridge error, record that failed result without changing
   the server. Test the same Desktop-managed probe in a fresh **Chat** conversation
   inside the Desktop app and repeat the sample click/readback check. Record this
   as a separate surface; a Chat pass is not a Code pass or a proven combined
   reviewer/UI workflow.

Update `host-evidence.json` and `connection-check.json` with registration origin,
exact error/status, actual state/log evidence and only observed results. Preserve
earlier failed observations. Keep quality reviewers, companion operations and
production approval/recovery unverified until their own acceptance steps run.

If no tested route works, report the concrete matrix and stop production UI
implementation at Task 3's gate. Any change to the chosen experience needs an
evidence-based decision. Keep the sample transport local stdio and existing tool
visibility/quality rules intact.

## Widget-load diagnostic continuation

The owner supplied a screenshot after Desktop-owned registration/restart showing
`Couldn't load this widget, so its result is shown as text.` The opener returned
revision 0, but this view has no editable sample controls. Rendering failed in
that attempt; save/reload/restart persistence cannot be exercised there. Preserve
the earlier Code-managed rendered/IPC-failed result separately.

First, the Mac agent collects the failing Desktop probe's resource-read errors
from its own server logs and verifies `resources/list`/`resources/read` with a
proper MCP client and bounded timeout. Save only relevant non-secret evidence:
the expected URI, MIME type, HTML byte count/hash, and actual errors. A separate
client success is a server check, not a host-rendering pass.

The official SDK's [registerAppTool implementation](https://github.com/modelcontextprotocol/ext-apps/blob/main/src/server/index.ts)
normalizes the modern nested resource URI and deprecated flat alias together.
The probe initially supplied only the modern form. Its generator now supplies
both while preserving app-only save visibility. This is a verified metadata
compatibility correction; its relevance to this Mac loading error is unproven.

The Mac agent can refresh only the existing generated `probe_server.py` from the
latest generator's `SERVER` constant, keeping the registered path and data-root:

1. Fetch the source revision identified in the handoff; inspect the generator
   change and use that exact committed source, preserving the checkout branch.
2. Compare the existing server hash with `experiment.json`'s original generated
   server hash and any documented refresh evidence. If it differs unexpectedly,
   preserve it and diagnose. If it already equals the new source, leave it alone.
3. Back up the current generated server, then atomically write only the new
   `SERVER` string to that same file, retaining its permissions. Preserve the
   bundle, all registrations, data and prior logs. Record old/new hashes and
   source revision in the host evidence; the original manifest remains history.
4. Validate the refreshed server with the actual registration command in a
   bounded MCP client: the opener and app-only save have matching nested/flat
   resource URIs; save visibility remains app-only; the HTML resource is readable.
5. Save a resume note and ask the owner for one full Desktop quit/reopen. In a
   fresh Local Code session, inspect actual discovery/opening again. If rendering
   fails, record that error and try the already-registered probe in a fresh **Chat**
   conversation within Desktop. No project folder is selected in Chat. Ask there
   to open the probe's sample review; the owner checks the view and, only if it
   renders, performs the sample save. The Code agent subsequently verifies the
   same data-root's state/logs.

Record each surface/registration/server revision separately. Neither a metadata
correction nor a Chat result proves a working Code view. Keep the production gate
open until the actual combined host/reviewer/companion requirements are met.
