---
name: claude-code-runtime
description: Facts about the Claude Code runtime that /anki2 runs in. Covers the transcript format the cards meter parses, hook payloads and blocking, subagent and skill frontmatter, and the AnkiMCP tools and their limits. Use when building cards meter (phase 1), cards write (phase 5) or anything under .claude/ (phases 4-7). Verified 2026-11-05.
---

# Claude Code runtime facts (verified 2026-11-05)

You (Codex) are building for a different agent. Don't assume Codex behaviour applies to Claude Code. Use these facts.

## Session transcripts (for `cards meter`)

Location: `~/.claude/projects/<cwd with / replaced by ->/<session-id>.jsonl`, e.g. `~/.claude/projects/-path-to-project/02b30a03-….jsonl`. Subagents are in `<session-id>/subagents/agent-<id>.jsonl`, with `agent-<id>.meta.json` holding `{"agentType": "fork", "isFork": true, "description": …}`.

- One JSON object per line. `type` ∈ `assistant`, `user`, `attachment`, `system`, `queue-operation`, `custom-title`, `api-request`, ….
- **Assistant rows:**
  - `message.id` (one API call can span several rows with the same id; count usage once per id)
  - `message.model`
  - `message.usage.{input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens}`
  - `message.content[]` with `{type: "tool_use", name, input, id}`, `text` and `thinking`
- **Context of a call** = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.
- **Tool results:** `type: user`, `message.content[] = {type: "tool_result", tool_use_id, content}`. `content` is a string or a list. An `{"type": "image"}` element means an image entered context. A failed tool has `is_error: true` or text starting `Error`.
- **Compaction:** `type: system, subtype: compact_boundary, compactMetadata: {trigger, preTokens, postTokens}`.
- Not a stable interface. Fail loudly on a missing field.

L006 baseline (fixture `tests/fixtures/private/transcripts/l006/`):
- 76 unique main-agent message ids
- first context 79,270; peak 166,115
- 2 compactions
- subagents `abf410fc9ef5df4b0` and `aa8e0bb0754f0eaeb`, both `isFork: true`, first context 141,689
- `mcp__anki__add_notes` input of 14,879 characters sent twice (plus a 38-note batch)
- 9 `Edit` calls on `drafts.jsonl`
- 10 `Read` calls on `renders/sheets/*.png` in the main session
- `Bash` with `curl … 127.0.0.1:3141` and `:8765`
- `Read` of the lecture PDF returning 14 and 10 images

## Hooks (`.claude/settings.json` → `hooks.PreToolUse[]`)

- The payload arrives on stdin as JSON: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id`.
- `tool_input` by tool:
  - `Agent` → `subagent_type`, `prompt`, `description`, `model`, `effort`
  - `Read` → `file_path`
  - `Bash` → `command`
  - MCP tools → their arguments
- MCP tool names look like `mcp__anki__add_notes`.
- **Exit 2 blocks**, and stderr is shown to Claude, so say what to do instead. Any other non-zero exit does **not** block, which is why `run.sh` converts failures to exit 2.
- `$CLAUDE_PROJECT_DIR` is the project root. Matchers are regexes on the tool name (`Write|Edit`).
- The four runtime guards already exist in `.claude/hooks/` and pass `.codex/tools/verify_hooks.py`. Phase 6 wires them by merging `.claude/settings.hooks.json` into `.claude/settings.json`.

## Subagents (`.claude/agents/<name>.md`, YAML frontmatter + body)

- **Fields:**
  - `name` and `description` (required)
  - `tools` (comma list; a typo that leaves zero tools = launch failure)
  - `model` (`sonnet`, `opus`, `haiku`, `fable`, a full id such as `claude-sonnet-5-5`, or `inherit`)
  - `effort` (`low`, `medium`, `high`, `xhigh`, `max`)
  - `permissionMode` (`dontAsk` refuses unapproved actions)
  - `maxTurns`
  - `omitClaudeMd: true` (no CLAUDE.md in the agent's context; needs v2.1.271+)
  - `mcpServers`, `skills`, `hooks`
- The main agent launches one with the `Agent` tool and `subagent_type: <name>`. `fork` copies the whole conversation, which is banned here.

## Skills (`.claude/skills/<name>/SKILL.md`)

- **Frontmatter:**
  - `name` (sets the `/name` command)
  - `description` + `when_to_use` (≤ 1,536 characters combined)
  - `model` and `effort` (apply for the rest of the turn that invokes the skill)
  - `allowed-tools`, `disallowed-tools`
  - `disable-model-invocation`
- The body stays in context for the rest of the session, so it is a recurring cost. Keep the core small and put phase detail in files read only when needed.

## AnkiMCP (add-on 124672614, 127.0.0.1:3141)

- **Tool names seen in L006:** `mcp__anki__list_decks`, `model_names`, `find_notes`, `notes_info`, `create_deck`, `add_notes`, `add_note`, `card_suspend`, `card_unsuspend`, `model_templates`, `model_styling`.
- **Limits:**
  - `create_deck` ≤ 2 levels (flat decks avoid this)
  - `add_notes`: one deck + one note type per call, ≤ 100 notes, deck must exist, duplicate check on the first field
  - `find_notes` returns note ids; suspend/unsuspend take **card** ids (from `notes_info`)
- In Claude Code auto mode, Bash calls to 127.0.0.1 were blocked. Q-1 tests whether a project allow rule changes that.
