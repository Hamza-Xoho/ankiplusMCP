# Desktop compatibility experiment

This is Task 3 of the approved student-workflow plan. It prepares the remaining
implementation decisions; it does not complete onboarding or deliver a production
review interface. The launcher lifecycle has separately passed on the reported
Mac at `d5c345f`; retain that working registration and its backups.

## Start from the Desktop app

The owner uses the Claude Desktop app. An agent in its **local Code** surface can
perform the internal commands below; the owner need not open Terminal. Use the
existing Mac checkout, preserve its branch/local artifacts, and record the exact
commit and dirty status before proceeding. Fetch the authorized
`refactor/student-workflows` branch and fast-forward the Mac test branch only if
clean and a fast-forward is possible. Preserve a divergent branch and report it.
Never reset, clean, replace the existing wheel, or reinstall the working product
just to run this experiment.

Paste into a local Code session opened on the checkout:

> Run `docs/refactor/desktop-compatibility-experiment.md` from this checkout.
> Prepare its disposable sample UI and reviewer packets, verify them locally,
> then guide me through the actual Desktop checks. Use the Desktop app throughout;
> you may run internal build/test commands. Preserve my working AnkiPlus/Anki
> registrations and backups. Register only the separately named synthetic probe
> after backing up configuration. Zero Anki operations in the sample/UI/reviewer
> stages. Companion inspection is discovery-only; no collection writes are
> authorized. Save raw evidence under the experiment directory, mark unavailable
> checks blocked or not_run, and return the sanitized summary. Do not implement
> production interfaces from a partial result.

Record Desktop app version, bundled Code runtime version, macOS/architecture,
subscription, selected model/effort and whether each tested surface executes
locally or remotely. The earlier CLI version is not proof of the app's bundled
runtime. Use the frozen reviewers' configured models/efforts; report an unavailable
model rather than substituting one or adding API credentials.

## Prepare and verify

Choose a fresh directory, e.g. `.artifacts/compatibility/desktop-probe-<timestamp>`.
The following commands are for the agent, from the repository root. Replace
`<probe>` and `<checks>` with distinct absolute paths in that ignored directory:

```sh
.venv/bin/python scripts/prepare-desktop-experiment.py --output <probe> --build-ui --reviewers
.venv/bin/python scripts/check-desktop-experiment.py --root <probe> --output <checks>
.venv/bin/python <probe>/probe_server.py --check
```

Use the existing frozen Python dev environment (`uv sync --frozen --extra dev`
if missing), not the system Python 3.15 or an unpinned remote package. The generated
npm project pins the official MCP Apps SDK 2.0.4 and esbuild 0.28.2 with a separate
lockfile. Node 20+ is required for this experiment; production launcher dependencies
are unchanged. Rendering resolves the installed preview browser through doctor,
including system Google Chrome. A failed build is a failed prerequisite, not an
embedding failure. Outputs are exclusive: select a new directory on retry.

The check uses a real stdio client and the actual bundled App SDK in a local
JSON-RPC iframe host emulator. It exercises edit/exclude, persistence after a new
handshake, stale revision refusal, reload, inert text and 390px layout. It opens
no HTTP listener and blocks browser network requests. This establishes **local
probe correctness only**, not Desktop support or model context behavior.

`experiment.json` records source revision/dirty status and generated hashes.
Copy `HOST-RESULTS.template.json` to `host-evidence.json` and fill observed results;
never turn missing evidence into a pass. Keep local-check output and screenshots.

## Register the separate sample server

`registration.json` contains only `mcpServers.ankiplus-compat-probe`, using the
absolute venv Python and generated script/data paths. Back up Desktop's config
and record hashes/settings before adding that one key. If the key already exists,
preserve it and diagnose rather than overwrite it. Use the supported local MCP
registration path for each surface. Do not assume Desktop Chat registration is
automatically available in Code or Cowork; record how each actually connects.

For a project-local Code registration, the generated experiment folder may hold
a `.mcp.json` copied from `registration.json`. Open that folder as the local Code
project for the reviewer stage so its `.claude/agents/` definitions are discovered.
Keep repository `.claude/` files frozen. Project MCP enablement/restart prompts are
normal host interactions for the owner to accept in the app.

Quit/reopen as needed and confirm the **probe** lists four tools and its single
`ui://ankiplus-probe/review.html` resource. The working product remains a separate
36-tool server; neither count proves the view rendered.

## Actual embedded view: each surface separately

Use a new conversation on each locally available Chat/Code/Cowork surface.
Invoke `open_sample_review` through the probe, then have the owner:

1. Confirm an interactive view renders **inside that Desktop surface**; save a
   screenshot, resource/permission errors and exact surface/version. A browser
   screenshot, JSON result or generated HTML file does not satisfy this check.
2. Change sample-a text, uncheck sample-b, and press **Save sample decisions**.
   Read back state and confirm the edited text, excluded sample and new revision.
   Record whether clicking caused a model turn, using visible conversation/usage
   evidence. Server logs alone cannot establish model activity.
3. Close/reopen the conversation/view and fully restart the app once. Invoke the
   sample again and confirm server-side selection/text survives. Keep the same
   data directory. If the host cannot restore the view, record that distinction.
4. Open two views at the same revision. Save one; saving the other must show
   `STALE` and leave the first result intact. Reload and confirm the latest state.

If no embedded view is available in a surface, capture the actual failure and
mark it blocked. Do not expose a public Anki endpoint or substitute an external
web page and call it an embedded pass. A Chat UI pass plus a Code reviewer pass
still needs an explicit, demonstrated handoff before a combined workflow is
supported. Cloud Cowork is not evidence of access to local stdio/files.

## Fresh reviewer execution

The generator renders two synthetic ColdRecall cloze notes and builds packets
with the existing engine. `reviewer-packets.json` gives the absolute packet paths.
Rubric, brief and report format bytes and agent instruction bodies are preserved.
Only the experimental agent names/descriptions/tool envelope change: aliases
`compat-maintainer` and `compat-student` allow this sample-only invocation outside
the legacy `/anki2` workflow. The maintainer gets supplied synthetic collection
context and no Anki tools. This proves execution/isolation feasibility, **not**
real collection searching or representative card-quality acceptance.

In a fresh local Code session opened on `<probe>`, explicitly ask it to run the
two named custom agents, each with only its own packet's absolute `PROMPT.md`
path. Use separate fresh contexts without author history. Permit those two
reviewer subagents for this experiment; no extra reviewers are needed. Preserve
the definitions' Sonnet 5.5 / high maintainer and medium student settings and turn
limits. Capture actual agent IDs, model/effort, invocation inputs and transcripts.

Each agent reads its packet and writes only its named report. The student sees
contact sheets without source/draft answers and must commit front answers before
judging backs. Verify actual image reads and answer sequence from the transcript.
Separate filenames or the main agent saying it used reviewers are insufficient.
If the runtime cannot load these agents, enforce their settings or provide fresh
contexts, report the precise limitation. A main-agent self-review is not a pass.

After both reports exist, the evaluating session can read `EXPECTATIONS.md` and
check the seeded source-fidelity defect. Never provide that file or expected
verdict to the reviewers. Save report/provenance hashes. Findings remain findings;
success at launching the reviewers does not mean both cards passed quality.

## Content channels and loading cost

Use another fresh conversation/context that has not read the probe source,
answer key, channel-result artifact or this section's raw tool output. Ask it:

> Call only the probe's `observe_content_channels` once. Quote every marker and
> value you can actually see in that tool result, identify its visible channel
> if available, and say when a channel is unavailable. Do not inspect files.

Retain the exact prompt, tool result and model response per surface. Compare
against the raw stdio `channel-result.json` only afterward. A screenshot of raw
JSON is not proof that both channels reached the model. If the host flattens or
hides channel provenance, record the observation and the inference limit. Do not
remove either production channel based on a tool inspector alone.

The local checker saves full schemas and **UTF-8 byte counts** of compact JSON
tools arrays: record those alongside installed host/tool-loading settings. They
are not token counts or proof that every schema enters every model turn. If the
host exposes context/usage data, save the actual measurement and tokenizer/model
identity; otherwise keep those fields `not_measured`.

## Installed companion discovery

Run this independently of UI failures. Identify the actual local Anki companion
or add-on and version, transport and authentication mechanism from installed
metadata plus actual discovery. Inspect tool schemas only, using the host's
discovery or an existing supported authenticated local connection. **Do not call
collection read/search/write tools in this stage.** Zero Anki operations remains
the target. Never print credentials, personal card content or full host configs
in the handoff. Store sanitized schemas locally, with a hash and discovery method.

Fill a capability matrix with exact tool names, argument/result schemas and
known limits for: collection identity; note/card search and readback; note type
fields/templates/CSS; media input/receipt; create/update; suspension; duplicate
handling; partial responses; errors. Distinguish **documented**, **advertised by
installed schema**, and **experimentally executed**. None are interchangeable.
Use the [official tool reference](https://ankimcp.ai/docs/reference/addon/tools/)
and installed version/source as applicable; the separate CLI, AnkiConnect and
the add-on must not be conflated.

An isolated-profile mutation test is a **later, explicitly authorized stage**.
Before it, prepare a reviewable operation list: synthetic deck/note-type/media
names, profile identity, create/readback/card-ID/suspension checks, deliberate
partial batch, duplicate retry, and interruption after acceptance before local
receipt. It must prove ambiguity stays pending and there is no blind second
create. No mutation or profile switching is authorized by this packet. Leave
these results `not_run` and request that separate authorization with the concrete
list when ready. Production approval/recovery cannot be declared verified yet.

## Finish and decision

Remove only an unchanged probe registration if the owner wants cleanup; compare
against the saved fragment. Preserve a changed entry and report it for resolution.
Keep experiment data and backups. Record whether the working product/Anki entries
and unrelated settings are intact; attribute unrelated host state drift honestly.

Return the source SHA/dirty status, host versions/surfaces, filled result JSON,
artifact paths, reviewer provenance, sanitized companion matrix and exact
failures. Report the combined workflow as verified only with demonstrated local
UI, independent reviewers and a supported handoff; companion mutation/recovery
and private acceptance remain separate gates. Do not mark the full product ready.

The implementer then updates the approved plan's exact transport/UI contracts
and tests from this evidence before Tasks 7–10. If the combination is unsupported,
present the observed limitation and concrete alternatives for the owner's choice.
Do not silently change apps, reviewers, quality policy or subscription requirements.

## Development-host evidence, 2026-11-19

The disposable preparation, stdio/resource checks and SDK iframe emulator ran
locally with zero Anki operations. Eight focused tests pass; the reviewer packets
contain actual rendered PNGs, preserved templates and isolated inputs, but no AI
reviewer has executed on this host for product acceptance. Schema measurements
are 1,668 bytes / four probe tools and 30,142 bytes / 36 production tools using
the serialization above. Raw evidence is ignored under
`.artifacts/compatibility-local/`; build hashes/revision/dirty status accompany it.
Actual Desktop embedding, model-channel forwarding, independent Mac reviewers
and installed companion operations remain unverified.
