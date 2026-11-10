# Lean Cards workspace

This repository stands in for `this repository` on the owner’s Mac (the imported setup handover). Copy the runtime settings back before the fresh-session manual gate. Existing settings keys and permissions are preserved.

## Project changes
Official JSON shapes verified 2026-11-05 against [Claude Code settings reference](https://code.claude.com/docs/en/settings-reference): connector Boolean, MCP deny objects with `serverName`, memory glob strings, plugin Boolean map.
Connectors disabled; global ruflo CLAUDE.md excluded (both requested tilde spelling and absolute Mac path); every observed non-Anki MCP server denied, plus claude-flow (its connection timed out). Anki remains enabled.
`enabledPlugins` is an empty map: the transcript names the design plugin but does not identify its marketplace. No plugin identifier is invented. The owner must supply the installed plugin ID before setting it false.

## L006 loaded inventory
Source: `tests/fixtures/private/transcripts/l006/02b30a03-0ddf-45fa-b36c-f1d72ad41439.jsonl`. Row numbers below are original JSONL lines; inventories combine repeated attachment rows.

- `deferred_tools_delta`: lines 12, 48, 74, 198, 230, 664, 698, 892, 907
- `agent_listing_delta`: lines 13, 199, 665
- `mcp_instructions_delta`: lines 14, 201, 667
- `skill_listing`: lines 15, 200, 666

MCP server names (all except anki denied):
1a59c906-04da-521d-bda7-7f71b9f9e01c, 221ec88d-c52d-4747-a990-ecfcd5bfa8f6, 28653145-9478-421e-9db2-431d69fb6879, 2d277bd6-49a8-4c81-94db-f4e0914b8244, 4f298f8c-5be2-4bff-84a9-3f895010e477, 5c08f0fb-4448-4e27-b3dd-6ffcb690dd52, 6079fc39-1b75-4d68-a24a-bd4756b18aa5, Claude_Code_iOS_Simulator, Control_Chrome, Control_your_Mac, Desktop_Commander, Figma, anki, ccd_connectors, ccd_directory, ccd_host, ccd_pr, ccd_session, ccd_session_mgmt, ccd_settings, ccd_sidebar, ccd_view, ccd_window, claude-flow, claude-in-chrome, e848792d-9b75-498a-aa7e-be091921f176, edebdeef-5135-44b0-a6bf-2feb75f5c8b3, flow-nexus, mcp-registry, ruv-swarm, scheduled-tasks, terminal

Agent types (87):
Benchmark Suite, Explore, Load Balancing Coordinator, Performance Monitor, Plan, Resource Allocator, Topology Optimizer, adaptive-coordinator, agentic-payments, aidefence-guardian, analyst, api-docs, architecture, backend-dev, base-template-generator, byzantine-coordinator, cicd-engineer, claims-authorizer, claude, claude-code-guide, code-analyzer, code-review-swarm, collective-intelligence-coordinator, consensus-coordinator, crdt-synchronizer, ddd-domain-expert, flow-nexus-app-store, flow-nexus-auth, flow-nexus-challenges, flow-nexus-neural, flow-nexus-payments, flow-nexus-sandbox, flow-nexus-swarm, flow-nexus-user-tools, flow-nexus-workflow, general-purpose, github-modes, gossip-coordinator, hierarchical-coordinator, injection-analyst, issue-tracker, matrix-optimizer, memory-coordinator, mesh-coordinator, ml-developer, mobile-dev, multi-repo-swarm, pagerank-analyzer, perf-analyzer, performance-benchmarker, performance-engineer, performance-optimizer, pii-detector, planner, pr-manager, production-validator, project-board-sync, pseudocode, quorum-manager, raft-manager, reasoningbank-learner, refinement, release-manager, release-swarm, repo-architect, security-architect, security-architect-aidefence, security-manager, smart-agent, sona-learning-optimizer, sparc-coder, sparc-coord, specification, statusline-setup, sublinear-goal-planner, swarm-init, swarm-issue, swarm-memory-manager, swarm-pr, sync-coordinator, system-architect, task-orchestrator, tdd-london-swarm, test-long-runner, trading-predictor, v3-integration-architect, workflow-automation

Skill listing entries (277):
- SKIP only when another provider is being worked on (overrides all triggers): OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama named in the query; OR `grep -rE 'openai|langchain_openai|google.generativeai|genai|mistralai|cohere|ollama'` over the project hits (run this grep FIRST if no provider named — don't Read the file).
- TRIGGER — read BEFORE opening the target file; don't skip because it "looks like a one-liner" — whenever: the prompt names Claude/Anthropic in any form (Claude, Anthropic, Fable, Opus, Sonnet, Haiku, `anthropic`, `@anthropic-ai`, `claude-*`, `us.anthropic.*`, `[1m]`); the user asks about an LLM (pricing/model choice/limits/caching) — never answer from memory; OR the task is LLM-shaped with provider unstated (agent/MCP/tool-definition/multi-agent/RAG/LLM-judge/computer-use; generate/summarize/extract/classify/rewrite/converse over NL; debugging refusals/cutoffs/streaming/tool-calls/tokens).
- agentdb-advanced
- agentdb-learning
- agentdb-memory-patterns
- agentdb-optimization
- agentdb-vector-search
- agents:README
- agents:agent-capabilities
- agents:agent-coordination
- agents:agent-spawning
- agents:agent-types
- agents:health
- agents:list
- agents:logs
- agents:metrics
- agents:pool
- agents:spawn
- agents:status
- agents:stop
- analysis:COMMAND_COMPLIANCE_REPORT
- analysis:README
- analysis:bottleneck-detect
- analysis:performance-bottlenecks
- analysis:performance-report
- analysis:token-efficiency
- analysis:token-usage
- anki
- anthropic-skills:anki
- anthropic-skills:built-in-browser
- anthropic-skills:chrome-browser
- anthropic-skills:codebase-handover
- anthropic-skills:computer-use
- anthropic-skills:consolidate-memory
- anthropic-skills:debugandrefactor
- anthropic-skills:debugging
- anthropic-skills:deep-research
- anthropic-skills:design-council
- anthropic-skills:docs
- anthropic-skills:docx
- anthropic-skills:explain-usage
- anthropic-skills:frontend-design
- anthropic-skills:google-workspace
- anthropic-skills:handoff
- anthropic-skills:idea-validator
- anthropic-skills:import-memory
- anthropic-skills:learning
- anthropic-skills:llm-council
- anthropic-skills:morning
- anthropic-skills:pdf
- anthropic-skills:pptx
- anthropic-skills:prep-for-the-week
- anthropic-skills:project-buildkit
- anthropic-skills:project-charter
- anthropic-skills:project-proposal
- anthropic-skills:setup-claude
- anthropic-skills:skill-creator
- anthropic-skills:xlsx
- artifact-capabilities: Runtime capabilities a published Artifact page can be granted — behavior static HTML cannot provide on its own, such as the page reading live or connected data, remembering what people do on it (a poll, a sign-up sheet, a checklist, a document edited in place — it saves new versions of itself), keeping state shared across viewers, knowing who is viewing, asking Claude a question of its own, storing files people add, handing the viewer a file to save, or using the viewer's camera, microphone, location, screen or device motion. Serves this user's live capability roster and the typed call definitions. Load it whenever any such runtime behavior would make an artifact more useful, before writing the page.
- artifact-design: Design guidance and fundamentals for Artifacts. - Load before writing any artifact, including a skill-instructed Markdown one - Markdown is never a shortcut past the design pass.
- artifact-diagramming: Diagramming know-how for Artifacts - when a picture earns its place, how to draw one that shows the real mechanism, and the inline-SVG mechanics that keep it legible in both themes.
- automation:README
- automation:auto-agent
- automation:self-healing
- automation:session-memory
- automation:smart-agents
- automation:smart-spawn
- automation:workflow-select
- browser
- claude-api: Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration.
- claude-flow-help
- claude-flow-memory
- claude-flow-swarm
- code-review: Review the current diff, or a PR number/branch/path target, for correctness bugs (plus reuse/simplification/efficiency cleanups where the model's review recipe covers them) at the given effort level (low|medium|high|xhigh|max: from few high-confidence findings up to many, some of them uncertain; ultra: deep multi-agent review in the cloud); with no level given, it reuses the level you typed last. Pass --comment to post findings as inline PR comments, or --fix to apply the findings to the working tree after the review. Pass --max-findings <n> to report up to n findings, or --max-findings all for every finding. The choice stays until you pass --max-findings default. For ultra on a GitHub.com PR target, --post asks to post the finished review’s findings to the PR as a single comment from the user’s GitHub account (not a review; the launch dialog still confirms in interactive sessions, while non-interactive mode posts on the flag alone) and --no-post hides that option.
- coordination:README
- coordination:agent-spawn
- coordination:init
- coordination:orchestrate
- coordination:spawn
- coordination:swarm-init
- coordination:task-orchestrate
- cowork-plugin-management:cowork-plugin-customizer
- cowork-plugin-management:create-cowork-plugin
- dataviz: Use this skill whenever you are about to create ANY chart, graph, plot, dashboard, or data visualization, in ANY output medium — an HTML or React artifact, inline SVG, plotting code in any library (matplotlib, plotly, d3, Recharts, …), an image/PNG you will render and upload, or a chart shared into Slack. Read it BEFORE writing the first line of chart code, choosing chart colors, building a stat tile / meter / KPI row, or laying out a dashboard. When the destination is a first-party document connector (host-designated, never self-described) that renders live charts, hand it the rows (inline, or as an uploaded data file the chart cites) rather than a rendered PNG/SVG — a picture of a chart loses hover, data inspection and per-value comments. Produces visualizations that read as one system — elegant, accessible, consistent in light and dark — using a brand-neutral placeholder palette you swap for your own. Teaches a design-system-agnostic method: a form heuristic, a color formula with a runnable validator, mark specs, and interaction rules. A validated default palette is documented in `references/palette.md` — swap that file's values for your brand's. Triggers on: "chart", "graph", "plot", "data viz", "visualization", "dashboard", "analytics", "visualize data", "categorical colors", "sequential / diverging palette", "stat tile", "sparkline", "heatmap", "legend", "axis", "tooltip", "chart colors", "color by series".
- design:accessibility-review
- design:design-critique
- design:design-handoff
- design:design-system
- design:research-synthesis
- design:user-research
- design:ux-copy
- fewer-permission-prompts: Scan your transcripts for common read-only Bash and MCP tool calls, then add a prioritized allowlist to project .claude/settings.json to reduce permission prompts.
- flow-nexus-neural
- flow-nexus-platform
- flow-nexus-swarm
- github-code-review
- github-multi-repo
- github-project-management
- github-release-management
- github-workflow-automation
- github:README
- github:code-review
- github:code-review-swarm
- github:github-modes
- github:github-swarm
- github:issue-tracker
- github:issue-triage
- github:multi-repo-swarm
- github:pr-enhance
- github:pr-manager
- github:project-board-sync
- github:release-manager
- github:release-swarm
- github:repo-analyze
- github:repo-architect
- github:swarm-issue
- github:swarm-pr
- github:sync-coordinator
- github:workflow-automation
- hive-mind:README
- hive-mind:hive-mind
- hive-mind:hive-mind-consensus
- hive-mind:hive-mind-init
- hive-mind:hive-mind-memory
- hive-mind:hive-mind-metrics
- hive-mind:hive-mind-resume
- hive-mind:hive-mind-sessions
- hive-mind:hive-mind-spawn
- hive-mind:hive-mind-status
- hive-mind:hive-mind-stop
- hive-mind:hive-mind-wizard
- hooks-automation
- hooks:README
- hooks:overview
- hooks:post-edit
- hooks:post-task
- hooks:pre-edit
- hooks:pre-task
- hooks:session-end
- hooks:setup
- init
- keybindings-help: Use when the user wants to customize keyboard shortcuts, rebind keys, add chord bindings, or modify ~/.claude/keybindings.json. Examples: "rebind ctrl+s", "add a chord shortcut", "change the submit key", "customize keybindings".
- loop: Run a prompt or slash command on a recurring interval (e.g. /loop 5m /foo). Omit the interval to let the model self-pace. - When the user wants to set up a recurring task, poll for status, or run something repeatedly on an interval (e.g. "check the deploy every 5 minutes", "keep running /babysit-prs"). Do NOT invoke for one-off tasks.
- memory:README
- memory:memory-persist
- memory:memory-search
- memory:memory-usage
- memory:neural
- monitoring:README
- monitoring:agent-metrics
- monitoring:agents
- monitoring:real-time-view
- monitoring:status
- monitoring:swarm-monitor
- optimization:README
- optimization:auto-topology
- optimization:cache-manage
- optimization:parallel-execute
- optimization:parallel-execution
- optimization:topology-optimize
- pair-programming
- pair:README
- pair:commands
- pair:config
- pair:examples
- pair:modes
- pair:session
- pair:start
- plugin-authoring: Make a mod: a change to Claude's own interface or behaviour, such as a panel or pane that stays beside the chat and updates, a band, status line, toast, slash command, or hook on tool calls. Use to make, change or debug a mod or its hooks module.
- project-charter
- reasoningbank-agentdb
- reasoningbank-intelligence
- run: Launch and drive this project's app to see a change working. Use when asked to run, start, or screenshot the app, or to confirm a change works in the real app (not just tests). First looks for a project skill that already covers launching the app; otherwise falls back to built-in patterns per project type (CLI, server, TUI, Electron, browser-driven, library).
- schedule: Create, update, list, or run scheduled cloud agents (routines) that execute on a cron schedule. - When the user wants to schedule a recurring cloud agent, set up automated tasks, create a cron job for Claude Code, or manage their scheduled agents/routines. Also use when the user wants a one-time scheduled run ("run this once at 3pm", "remind me to check X tomorrow").
- security-review
- simplify: Review the changed code for reuse, simplification, efficiency, and altitude cleanups, then apply the fixes. Quality only — it does not hunt for bugs; use /code-review for that.
- skill-builder
- sparc-methodology
- sparc:analyzer
- sparc:architect
- sparc:ask
- sparc:batch-executor
- sparc:code
- sparc:coder
- sparc:debug
- sparc:debugger
- sparc:designer
- sparc:devops
- sparc:docs-writer
- sparc:documenter
- sparc:innovator
- sparc:integration
- sparc:mcp
- sparc:memory-manager
- sparc:optimizer
- sparc:orchestrator
- sparc:post-deployment-monitoring-mode
- sparc:refinement-optimization-mode
- sparc:researcher
- sparc:reviewer
- sparc:security-review
- sparc:sparc
- sparc:sparc-modes
- sparc:spec-pseudocode
- sparc:supabase-admin
- sparc:swarm-coordinator
- sparc:tdd
- sparc:tester
- sparc:tutorial
- sparc:workflow-manager
- startup:startup-competitors
- startup:startup-design
- startup:startup-pitch
- startup:startup-positioning
- stream-chain
- stream-chain:pipeline
- stream-chain:run
- superpowers:brainstorming
- superpowers:diagnosing-superpowers
- superpowers:dispatching-parallel-agents
- superpowers:executing-plans
- superpowers:finishing-a-development-branch
- superpowers:receiving-code-review
- superpowers:requesting-code-review
- superpowers:subagent-driven-development
- superpowers:systematic-debugging
- superpowers:test-driven-development
- superpowers:using-git-worktrees
- superpowers:using-superpowers
- superpowers:verification-before-completion
- superpowers:writing-plans
- superpowers:writing-skills
- swarm-advanced
- swarm-orchestration
- swarm:README
- swarm:analysis
- swarm:development
- swarm:examples
- swarm:maintenance
- swarm:optimization
- swarm:research
- swarm:swarm
- swarm:swarm-analysis
- swarm:swarm-background
- swarm:swarm-init
- swarm:swarm-modes
- swarm:swarm-monitor
- swarm:swarm-spawn
- swarm:swarm-status
- swarm:swarm-strategies
- swarm:testing
- training:README
- training:model-update
- training:neural-patterns
- training:neural-train
- training:pattern-learn
- training:specialization
- truth:start
- update-config: Use this skill to configure the Claude Code harness via settings.json. Automated behaviors ("from now on when X", "each time X", "whenever X", "before/after X") require hooks configured in settings.json - the harness executes these, not Claude, so memory/preferences cannot fulfill them. Also use for: permissions ("allow X", "add permission", "move permission to"), env vars ("set X=Y"), hook troubleshooting, or any changes to settings.json/settings.local.json files. Examples: "allow npm commands", "add bq permission to global settings", "move permission to user settings", "set DEBUG=true", "when claude stops show X". For simple settings like theme/model, suggest the /config command.
- v3-cli-modernization
- v3-core-implementation
- v3-ddd-architecture
- v3-integration-deep
- v3-mcp-optimization
- v3-memory-unification
- v3-performance-optimization
- v3-security-overhaul
- v3-swarm-coordination
- verification-quality
- verify:check
- verify:start
- workflows:README
- workflows:development
- workflows:research
- workflows:workflow-create
- workflows:workflow-execute
- workflows:workflow-export

## User-level steps for the owner (not performed)
No `~/.claude/` directory from the owner’s Mac was supplied. The transcript proves the loaded names but not the file locations or line numbers inside those source files. Exact source lines cannot be truthfully supplied from these inputs. Use the commands below on the Mac to produce them before editing; do not apply changes to the Ubuntu user’s unrelated settings.

1. `~/.claude/settings.json`: remove the ruflo/claude-flow hook entries only, preserving unrelated hooks. Project hook settings merge and cannot selectively subtract these inherited entries. Locate exact lines with `rg -n "ruflo|claude-flow|flow-nexus|hooks|enabledPlugins" ~/.claude/settings.json`.
2. `~/.claude/agents/*.md`: move unwanted user-level definitions outside the discovery directory; preserve anki-maintainer and anki-student project agents. Find actual file names and name lines using `rg -n "^name:|^description:" ~/.claude/agents`. The 87 observed agent types above are attachment evidence, not a claim that 87 particular source files exist.
3. `~/.claude/skills/*/SKILL.md` and `~/.claude/commands/**/*.md`: inspect the observed skill/command list above. Move unused ruflo/flow-nexus entries outside discovery. Locate exact lines with `rg -n "^name:|^description:|ruflo|claude-flow|flow-nexus" ~/.claude/skills ~/.claude/commands`.
4. `~/.claude/settings.json` → `enabledPlugins`: find the full `design@<marketplace>` identifier with the first command, then set that exact key false in the project settings. Do not guess its marketplace from `plugin:design:*` MCP auth entries.
5. `~/.claude/CLAUDE.md`: excluded by project settings; no user-level edit needed. The application-managed `ccd_*` tools may be SDK servers, which the documented denylist exempts. Desktop tools may therefore require disabling them in the client; confirm by a fresh transcript.

## Manual measurement
Fill Sonnet 5.5 prices only at the owner’s gate. Start a fresh Cards session, say hi, close it, then meter --latest. Record `char_fr25_first_call_drop` in docs/decisions.md only after measuring ≥10k below 79k. No reduction is claimed yet.

## Baseline discrepancy
The runtime skill lists 10 main contact-sheet Read calls. The original fixture contains 8 Read tool uses under renders/sheets (2 PDF reads and 3 draft reads make 13 Read calls total). The meter reports the observed 8 rather than manufacturing 10. Both PDF reads returned images, so W-2 and W-7 still fail.
