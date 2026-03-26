# OwlBear Architecture

> **Version:** 0.3 (codebase-aligned rewrite)
> **Date:** 2026-03-06
> **Previous:** v0.2 (2026-02-28, post-implementation audit)
> **Based on:** Full code audit of all modules, bootstrap.py wiring verification, [architecture-rewrite.md](architecture-rewrite.md)

## 1. Vision

OwlBear is an always-on, laptop-resident AI development system. The user describes intent (via CLI, Slack, or voice), and OwlBear extracts intent, plans work, executes it autonomously, and delivers results — with human approval gates for destructive or publishing actions. It owns the full build pipeline (ideation → spec → code → test → review → deliver) and operates as a standalone daemon process. VS Code remains the user's IDE for interactive work; OwlBear and VS Code share the filesystem as the integration point.

**Key constraints:**

- Runs on user's corporate Windows laptop (Ryzen 8840U, 16 GB RAM, no discrete GPU)
- No admin access — Edge locked by IT, no extension sideloading
- GitHub Copilot API as LLM provider (OAuth device-flow)
- Python 3.12+, managed by `uv`
- PydanticAI as the agent framework (handles agent loop, tool calling, structured output)
- Quality over speed: ≥ 90% test coverage per phase gate

## 2. System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             OwlBear System                                  │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ CLI Channel  │  │   Slack     │  │   Voice     │                         │
│  │ (stdin/out)  │  │  Channel    │  │  Channel    │                         │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                 │                │                                │
│         └────────┬────────┴────────────────┘                                │
│                  ▼                                                           │
│         ┌─────────────────┐                                                 │
│         │ ChannelPlugin   │  Protocol: name, send(), receive()              │
│         │   Protocol      │                                                 │
│         └────────┬────────┘                                                 │
│                  ▼                                                           │
│         ┌─────────────────┐     ┌──────────────────┐                        │
│         │  OwlBearAgent   │────▶│   PydanticAI     │                        │
│         │   (turn-based)  │     │   Agent.run()    │──▶ Copilot API         │
│         │                 │     │   (manages loop) │                        │
│         └────────┬────────┘     └──────────────────┘                        │
│                  │                                                           │
│    ┌─────────────┼──────────────┬──────────────┬──────────────┐              │
│    ▼             ▼              ▼              ▼              ▼              │
│ ┌────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐        │
│ │Toolsets│ │  Hooks   │ │  Skills   │ │  Memory  │ │Agent Registry│        │
│ │        │ │          │ │           │ │          │ │+ Delegation  │        │
│ │File    │ │Command   │ │Progressive│ │Session   │ │              │        │
│ │Terminal│ │  Guard   │ │ loading   │ │ (JSONL)  │ │8 agent defs  │        │
│ │AskUser │ │Lint      │ │           │ │Context   │ │(architect,   │        │
│ │GitHub  │ │Context   │ │           │ │ (.md)    │ │builder,      │        │
│ │Git     │ │Notify    │ │           │ │Usage     │ │closer,       │        │
│ │Browser │ │Observe   │ │           │ │ tracker  │ │kanban-planner│        │
│ │Kanban  │ │Subagent  │ │           │ │          │ │orchestrator, │        │
│ │Knowledge│ │Test      │ │           │ │Knowledge │ │researcher,   │        │
│ │Web     │ │Screenshot│ │           │ │ pipeline │ │reviewer,     │        │
│ │MCP     │ │Progress  │ │           │ │          │ │writer)       │        │
│ │Hooked  │ │          │ │           │ │          │ │              │        │
│ └────────┘ └──────────┘ └───────────┘ └──────────┘ └──────────────┘        │
│                                                                             │
│  ┌─ Auth ─────────────────┐  ┌─ Config ──────────────┐                     │
│  │ Copilot OAuth          │  │ OwlBearSettings        │                     │
│  │ (device-flow, token    │  │ (pydantic-settings,    │                     │
│  │  cache, proxy-ep)      │  │  env vars)             │                     │
│  └────────────────────────┘  └────────────────────────┘                     │
│                                                                             │
│  ┌─ Daemon ───────────────┐  ┌─ CLI (BearClaw) ──────┐                     │
│  │ PID file, logging,     │  │ auth, chat, run, stop, │                     │
│  │ signal handling, OTEL  │  │ browser, slack, voice,  │                     │
│  │                        │  │ usage                   │                     │
│  └────────────────────────┘  └────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Package Structure (actual)

```text
src/owlbear/                          # Main Python package (v0.1.0)
├── __init__.py                       # Version: 0.1.0
├── bootstrap.py                      # Procedural assembly of all components (~940 LOC)
├── config.py                         # OwlBearSettings (pydantic-settings)
├── daemon.py                         # PidFile, logging, OTEL, run_daemon()
├── py.typed                          # PEP 561 type marker
│
├── auth/
│   ├── __init__.py
│   └── copilot.py                    # OAuth device-flow, token cache, proxy-ep
│
├── core/
│   ├── __init__.py
│   ├── agent.py                      # OwlBearAgent (wraps PydanticAI Agent)
│   ├── agent_def.py                  # AgentDefinition (parsed from markdown YAML)
│   ├── agent_registry.py             # AgentRegistry (scan .md, lazy-build agents)
│   ├── command_guard.py              # CommandSafetyGuard (PRE_TOOL_USE hook)
│   ├── context_hook.py               # ContextInjectionHook (SESSION_START)
│   ├── delegation.py                 # DelegationToolset (delegate_to_agent tool)
│   ├── deps.py                       # OwlBearDeps (shared dependency injection)
│   ├── errors.py                     # Custom exception hierarchy
│   ├── hooks.py                      # HookEvent enum, HookRegistry
│   ├── lint_hook.py                  # AutoLintHook (POST_TOOL_USE)
│   ├── notification_hook.py          # NotificationHook (console/winsound)
│   ├── observability.py              # ObservabilityHook + EventStore (JSONL)
│   ├── progress.py                   # ProgressReporter (periodic channel updates)
│   ├── roles.py                      # AgentRole, RolePolicy, apply_role_policy()
│   ├── subagent_hook.py              # SubagentVerificationHook
│   └── test_hook.py                  # TestVerificationHook (SESSION_END)
│
├── channels/
│   ├── __init__.py
│   ├── base.py                       # ChannelPlugin Protocol (name, send, receive)
│   ├── cli.py                        # CLIChannel (stdin/stdout, send_file)
│   ├── slack.py                      # SlackChannel (SocketMode + AsyncWebClient)
│   ├── slack_mrkdwn.py               # Markdown → Slack mrkdwn converter
│   └── slack_templates.py            # Block Kit builders (proposal, status, approval)
│
├── memory/
│   ├── __init__.py
│   ├── context.py                    # ContextManager (context.md → instructions)
│   ├── error_journal.py              # ErrorJournal (append-only JSONL, rotation)
│   ├── session.py                    # SessionStore (JSONL persistence)
│   ├── usage.py                      # UsageRecord, UsageTracker (JSONL)
│   ├── usage_cost.py                 # calc_estimated_cost (genai_prices)
│   └── knowledge/                    # Knowledge pipeline (21 files)
│       ├── __init__.py
│       ├── bookmark.py               # BookmarkStore (URL+scope dedup CRUD)
│       ├── bookmark_pipeline.py      # BookmarkPipeline (extract→evaluate→ingest)
│       ├── bookmark_toolset.py       # BookmarkToolset (bookmark_source, list_bookmarks)
│       ├── chunker.py                # TextChunker (token-level splits)
│       ├── embeddings.py             # EmbeddingProvider protocol + BgeM3EmbeddingProvider (idle-timeout)
│       ├── evaluator.py              # SourceEvaluator (relevance scoring 0–1)
│       ├── extractor.py              # LLM-based entity extraction
│       ├── graph.py                  # GraphStore (entity/edge CRUD)
│       ├── graph_builder.py          # GraphBuilder (batch entity/edge construction)
│       ├── ingest.py                 # IngestPipeline orchestrator
│       ├── intake.py                 # File/URL/text readers
│       ├── inter_doc_graph_builder.py # InterDocGraphBuilder (embedding similarity + LLM)
│       ├── models.py                 # Entity, Edge, Document Pydantic models
│       ├── protocol.py               # KnowledgeStore protocol (query interface)
│       ├── qdrant.py                 # QdrantVectorStore (hybrid search, temporal decay)
│       ├── query_service.py          # KnowledgeQueryService (per-turn context injection)
│       ├── refresh.py                # RefreshOrchestrator (url_list, crawl, file_glob)
│       ├── retrieval.py              # GraphAugmentedRetriever (graph-neighbor expansion)
│       ├── schema.py                 # SQLite DDL, migrations (v1-v7)
│       └── source_store.py           # KnowledgeSourceStore (source CRUD)
│
├── planning/
│   ├── __init__.py
│   ├── extractor.py                  # Plan extractor from LLM output
│   ├── markdown.py                   # Markdown plan formatter
│   └── models.py                     # Plan, Step Pydantic models
│
├── projects/
│   ├── __init__.py
│   ├── models.py                     # Project model
│   ├── store.py                      # ProjectStore (JSON file CRUD)
│   ├── toolset.py                    # ProjectToolset (switch, list, create)
│   └── workspace.py                  # ProjectWorkspace (scaffold templates)
│
├── providers/
│   ├── __init__.py
│   ├── copilot.py                    # create_copilot_model() → OpenAIChatModel
│   └── copilot_multipliers.py        # Premium request multipliers per model
│
├── safety/
│   ├── __init__.py
│   ├── gate.py                       # ApprovalGateToolset (wraps destructive tools)
│   └── policy.py                     # ApprovalPolicy, ApprovalRule, ApprovalSession
│
├── skills/
│   ├── __init__.py
│   └── registry.py                   # SkillRegistry (FunctionToolset, progressive)
│
├── tools/
│   ├── __init__.py
│   ├── ask_user.py                   # AskUserToolset (via ChannelPlugin)
│   ├── filesystem.py                 # FileToolset (read/write/create/list/search)
│   ├── git_local.py                  # GitLocalToolset (git CLI wrapper)
│   ├── github_api.py                 # GitHubToolset (REST: PRs, issues)
│   ├── hooked.py                     # HookedToolset (WrapperToolset, PRE/POST hooks)
│   ├── kanban.py                     # KanbanToolset (list, show, create, move, edit, pick, context)
│   ├── knowledge.py                  # KnowledgeToolset (query, ingest, list_sources)
│   ├── knowledge_source.py           # KnowledgeSourceToolset (add, list, refresh sources)
│   ├── mcp_registry.py               # MCPServerRegistry (lifecycle, health check)
│   ├── mcp_servers.py                # Factory: github, git, fetch servers
│   ├── screenshot.py                 # ScreenshotService (capture/save/deliver)
│   ├── screenshot_hook.py            # ScreenshotOnErrorHook (auto-capture on ON_ERROR)
│   ├── terminal.py                   # TerminalToolset (run_command, timeout)
│   ├── visual_feedback.py            # VisualFeedbackToolset (share_screenshot, share_terminal_output)
│   ├── web_search.py                 # WebSearchToolset (web_search, web_read via ddgs + trafilatura)
│   └── browser/                      # Browser automation (12 files, ~1200 LOC)
│       ├── __init__.py
│       ├── actions.py                # 6 browser actions (navigate, click, type, ...)
│       ├── config.py                 # BrowserConfig (URL allow/block, CDP, viewport)
│       ├── content_extractor.py      # trafilatura-based extraction
│       ├── crawler.py                # WebCrawler (async BFS, robots.txt)
│       ├── crawl_config.py           # CrawlConfig model
│       ├── integration.py            # crawl_and_ingest bridge
│       ├── launcher.py               # Edge CDP launcher (find/launch/probe/kill)
│       ├── manager.py                # BrowserManager (launch/CDP modes, Playwright)
│       ├── safety.py                 # URLSafetyGuard (blocklist/allowlist)
│       ├── toolset.py                # BrowserToolset (FunctionToolset wrapping)
│       └── url_utils.py              # URL normalize, discover_links, robots checker
│
├── voice/
│   ├── __init__.py
│   ├── channel.py                    # VoiceChannel (quick + brainstorm modes)
│   ├── streaming_stt.py              # StreamingSTT (moonshine-voice MicTranscriber)
│   ├── stt.py                        # STTEngine (moonshine-voice batch mode)
│   └── tts.py                        # TTSEngine (pyttsx3)
│
└── agents/                           # Agent definitions (markdown + YAML frontmatter)
    ├── architect.md                  # Validator role, gate: backlog → todo
    ├── builder.md                    # Builder role, TDD workflow
    ├── closer.md                     # Builder role, gate: done → archived
    ├── kanban-planner.md             # Builder role, task decomposition
    ├── orchestrator.md               # Builder role, delegation, depth=5
    ├── researcher.md                 # Validator role, read-only, browser
    ├── reviewer.md                   # Validator role, read-only, depth=0
    └── writer.md                     # Builder role, filesystem only, depth=0

src/bearclaw/                         # CLI package
├── __init__.py
└── cli.py                            # Typer app: auth, chat, run, stop,
                                      # status, browser, slack, voice, usage,
                                      # knowledge-source, project
```

## 4. Core Components

### 4.1 OwlBearAgent (PydanticAI wrapper)

Wraps `pydantic_ai.Agent` with OwlBear-specific lifecycle:

```python
class OwlBearAgent:
    def __init__(self, model, session, context, hooks, channel, toolsets, ...):
        self._agent = Agent(model, instructions=..., toolsets=toolsets)

    async def turn(self, prompt: str) -> str:
        await hooks.emit(SESSION_START, ...)
        history = session.load()
        result = await self._agent.run(prompt, message_history=history)
        session.save(result.all_messages())
        tracker.record(result.usage())
        return result.output
```

PydanticAI manages the inner loop (LLM call → tool dispatch → repeat). OwlBearAgent manages the outer lifecycle (session load/save, hook emit, usage tracking, premium request recording).

### 4.2 HookRegistry

Event-driven system for cross-cutting concerns. 9 event types:

| Event | When | Hook implementations |
|-------|------|---------------------|
| `SESSION_START` | Before first turn | ContextInjectionHook |
| `SESSION_END` | After last turn | TestVerificationHook |
| `PRE_TOOL_USE` | Before any tool call | CommandSafetyGuard |
| `POST_TOOL_USE` | After any tool call | AutoLintHook, ObservabilityHook |
| `ON_MESSAGE` | On user message | _(none yet)_ |
| `ON_ERROR` | On exception | _(none yet)_ |
| `SUBAGENT_COMPLETE` | After sub-agent finishes | SubagentVerificationHook |
| `TASK_COMPLETE` | After kanban task done | `reconcile_tasks` (daemon.py) |
| `QUESTION_PENDING` | User question queued | _(reserved — not currently emitted)_ |

### 4.3 Toolsets (PydanticAI FunctionToolset-based)

All toolsets extend `pydantic_ai.toolsets.FunctionToolset`. Composed at run-time in `bootstrap.py` via `build_toolsets()`. Non-delegation toolsets are wrapped in `HookedToolset` for PRE/POST hook emission. Destructive toolsets (`GitLocalToolset`, `TerminalToolset`, `GitHubToolset`) are optionally wrapped in `ApprovalGateToolset`.

| Toolset | Tools | Status |
|---------|-------|--------|
| FileToolset | read_file, write_file, create_file, list_directory, search_files | ✅ Wired |
| TerminalToolset | run_command | ✅ Wired |
| AskUserToolset | ask_user | ✅ Wired |
| SkillRegistry | list_skills, load_skill | ✅ Wired (conditional) |
| GitLocalToolset | git_status, git_diff, git_add, git_commit, git_branch, git_log, git_push | ✅ Wired |
| GitHubToolset | create_pr, list_prs, list_issues, get_issue | ✅ Wired (conditional) |
| BrowserToolset | navigate, click, type_text, select_option, read_page_text, screenshot | ✅ Wired |
| KanbanToolset | kanban_list, kanban_show, kanban_create, kanban_move, kanban_edit, kanban_pick, kanban_context | ✅ Wired |
| KnowledgeToolset | query_knowledge, ingest_document, list_knowledge_sources | ✅ Wired (conditional) |
| KnowledgeSourceToolset | add_source, list_sources, refresh_source | ✅ Wired (conditional) |
| BookmarkToolset | bookmark_source, list_bookmarks | ✅ Wired (conditional) |
| WebSearchToolset | web_search, web_read | ✅ Wired (conditional) |
| VisualFeedbackToolset | share_screenshot, share_terminal_output | ✅ Wired |
| ProjectToolset | switch_project, list_projects, workspace_create_project | ✅ Wired (conditional) |
| DelegationToolset | delegate_to_agent | ✅ Wired (unwrapped) |
| HookedToolset | _(wraps any toolset with PRE/POST hooks)_ | ✅ Wired |
| ApprovalGateToolset | _(wraps destructive toolsets)_ | ✅ Wired (conditional) |
| MCPServerRegistry | _(dynamic MCP tools)_ | ✅ Wired (conditional) |
| ScreenshotService | capture, save, deliver _(internal, used by VisualFeedbackToolset)_ | ✅ Wired |

### 4.4 Agent Framework (multi-agent)

PydanticAI-based multi-agent system:

- **AgentDefinition**: Parsed from markdown files with YAML frontmatter (name, role, tools, model, system_prompt)
- **AgentRegistry**: Scans `.md` agent definitions, lazily builds PydanticAI Agents with resolved toolsets and role policies
- **DelegationToolset**: `delegate_to_agent` tool allows one agent to spawn another with depth-limited recursion (max 5)
- **RolePolicy**: BUILDER (full access) vs VALIDATOR (read-only, denied: write_file, create_file)
- **OwlBearDeps**: Shared dependency object injected into every agent run (hooks, tracker, registry, delegation depth)

8 agent definitions: architect (validator, gate: backlog → todo), builder (builder, TDD), closer (builder, gate: done → archived), kanban-planner (builder, task decomposition), orchestrator (builder, delegation), researcher (validator, browser), reviewer (validator, read-only), writer (builder, filesystem).

### 4.5 Channels

`ChannelPlugin` Protocol with 3 implementations:

- **CLIChannel**: stdin/stdout with optional stream injection for testing
- **SlackChannel**: SocketMode WebSocket + AsyncWebClient, DM-only
- **VoiceChannel**: STT (moonshine-voice) + TTS (pyttsx3), quick + brainstorm modes

### 4.6 Memory System

**Layer 1 — Context**: `ContextManager` reads `context.md` from workspace root, injected as agent `instructions` property.

**Layer 2 — Session**: `SessionStore` persists PydanticAI `ModelMessage` objects as JSONL. Load/save/append/backup per session.

**Usage tracking**: `UsageTracker` records per-turn usage (tokens, cost, premium requests) as JSONL.

**Knowledge pipeline** (21 modules): chunking → entity extraction → graph store → vector embeddings → ingest pipeline. Uses SQLite (graph schema v7) + Qdrant (hybrid vector search) + BGE-M3 (embeddings with idle-timeout model unloading). Subsystems: `BookmarkStore` + `BookmarkPipeline` (URL evaluate→ingest with dedup), `KnowledgeSourceStore` (source CRUD), `RefreshOrchestrator` (url_list, crawl, file_glob dispatch), `KnowledgeQueryService` (per-turn context injection, token-budgeted), `GraphAugmentedRetriever` (graph-neighbor expansion to vector results), `InterDocGraphBuilder` (cross-document edge inference via embedding similarity + LLM, opt-in).

### 4.7 Auth

GitHub Copilot OAuth device-flow: `request_device_code()` → user authorizes → `poll_for_access_token()` → `exchange_for_copilot_token()`. Token cached as JSON, `derive_base_url()` from proxy endpoint.

### 4.8 Daemon

`PidFile` context manager with stale detection. `setup_logging()` with RotatingFileHandler. `configure_otel()` for Logfire. `run_daemon()` async loop: receive → turn → send, with sentinel-file shutdown and signal handlers.

### 4.9 Browser Module

12 files (~1200 LOC) for browser automation on a corporate-locked Windows laptop:

- **BrowserManager**: Launch mode (new Playwright browser) or CDP mode (attach to existing Edge via `--remote-debugging-port`)
- **Edge CDP launcher**: Finds Edge executable, launches with debugging port, probes readiness
- **URLSafetyGuard**: Domain blocklist/allowlist for security
- **WebCrawler**: Async BFS with robots.txt compliance and rate limiting
- **content_extractor**: trafilatura-based main content extraction

**Why custom** (see [browser-automation.md](browser-automation.md) for full analysis):

1. **No OSS library handles the Edge CDP lifecycle.** Our ~100 LOC launcher performs find → probe → launch → connect for a corporate-locked Edge browser. browser-use and crawl4ai both support `connect_over_cdp()` but assume CDP is already running — they cannot discover, launch, or probe Edge readiness.
2. **browser-use conflicts with PydanticAI agent architecture.** browser-use brings its own AI agent loop that decides which elements to click and type. This creates a double-agent problem: our PydanticAI agent would delegate to browser-use's agent, doubling inference cost and splitting control flow. Our `BrowserToolset` is a `FunctionToolset` subclass where PydanticAI remains the single intelligence layer.
3. **KISS — 1200 LOC vs 15–20k LOC alternatives.** browser-use (~15k LOC) and crawl4ai (~20k LOC) include features we'll never use: AI element selection, cloud browsers, proxy rotation, stealth mode. Our module does exactly what we need with an order of magnitude less code.

## 5. Data Flow

### 5.1 Current (bearclaw chat)

```text
User types in CLI
    │
    ▼
CLIChannel.receive() → prompt string
    │
    ▼
OwlBearAgent.turn(prompt)
    ├── SessionStore.load() → message_history
    ├── Agent.run(prompt, message_history=...)     ← PydanticAI manages tool loop
    │   ├── LLM call → Copilot API (via model string)
    │   ├── Tool call? → FunctionToolset.call_tool() → result → loop
    │   └── Text response → return
    ├── SessionStore.save(result.all_messages())
    ├── UsageTracker.record(result.usage())
    └── returns result.output string
    │
    ▼
CLIChannel.send(response)
```

### 5.2 Current (after bootstrap)

```text
User Input (CLI / Slack / Voice)
    │
    ▼
ChannelPlugin.receive()
    │
    ▼
HookRegistry.emit(SESSION_START, data)    ← Context injection, bootstrap files
    │
    ▼
OwlBearAgent.turn(prompt)
    ├── SessionStore.load()
    ├── PydanticAI Agent.run(prompt, message_history=..., deps=OwlBearDeps)
    │   ├── Copilot API (OpenAIProvider + OpenAIChatModel)
    │   ├── Tool call → HookedToolset (PRE/POST hooks)
    │   │   ├── CommandSafetyGuard checks
    │   │   ├── Tool executes (FileToolset, TerminalToolset, BrowserToolset, ...)
    │   │   ├── AutoLintHook, ObservabilityHook
    │   │   └── Result → loop back to LLM
    │   ├── delegate_to_agent? → AgentRegistry → child Agent.run()
    │   └── Text response → return
    ├── SessionStore.save()
    ├── UsageTracker.record()
    └── returns response
    │
    ▼
HookRegistry.emit(SESSION_END, data)      ← TestVerificationHook, SubagentHook
    │
    ▼
ChannelPlugin.send(response)
```

## 6. Bootstrap Layer

`bootstrap.py` (~940 LOC) provides procedural assembly of all OwlBear components into a working `BootstrapResult`. The main entry point is the async `bootstrap()` function, which wires everything in sequence:

1. **Project resolution** — reads `config_dir/active_project`, derives workspace path from the active `Project`
2. **Channel creation** — `create_channel()` dispatches to CLI, Slack, or Voice adapter
3. **Hook assembly** — `build_hooks()` registers all hooks: CommandSafetyGuard, AutoLintHook, SubagentVerificationHook, TestVerificationHook, ContextInjectionHook, NotificationHook, ObservabilityHook, ProgressReporter
4. **Model creation** — `create_copilot_model()` produces an OpenAIChatModel for all agents
5. **Toolset assembly** — `build_toolsets()` creates all toolsets, wraps non-delegation ones in `HookedToolset`, optionally wraps destructive toolsets in `ApprovalGateToolset`
6. **Knowledge infrastructure** — `_build_knowledge_infra()` + `_build_knowledge_toolset()` + `_build_bookmark_toolset()` wire SQLite, Qdrant, BGE-M3, ingest pipeline, query service, and bookmark pipeline (all conditional, failure-tolerant)
7. **MCP registry** — `build_mcp_registry()` registers configured MCP servers
8. **Agent registry** — `build_agent_registry()` scans 8 agent definitions with alias-based tool resolution
9. **Session / context / tracker** — per-project or per-workspace JSONL stores
10. **Agent construction** — `OwlBearAgent` with all toolsets, hooks, knowledge service, and agent registry wired

Each `build_*` helper is independently testable. Conditional subsystems (knowledge, bookmarks, web search, GitHub, MCP) fail gracefully with warning logs — the system starts without them.

## 7. Implementation Phases

| Phase | Name | Kanban Tasks | Status | Focus |
|-------|------|-------------|--------|-------|
| P1 | Bootstrap | #1-12 | ✅ Done | Project skeleton, config, CLI stub |
| P2 | Agent Core | #37-45 | ✅ Done | HookRegistry, SkillRegistry, Session, ChannelPlugin, Agent loop |
| P2.5 | Docs & Config | #13-15 | ✅ Done | sources.md, attribution, inventory |
| P3 | Quality & Hooks | #16-28, #46, #48 | ✅ Done | VS Code hooks, safety hooks, agent roles, prompts |
| P4 | Auth & Comms | #30-36, #44, #47 | ✅ Done | Copilot OAuth, auth CLI, Slack integration |
| P5 | Browser | #49-68 | ✅ Done | BrowserConfig, BrowserManager, 6 tools, BrowserToolset, URL safety |
| P6 | CDP Browser | #69-90 | ✅ Done | Edge launcher, CDP connect, tab naming |
| P7 | Daemon & Core Tools | #120-126 | ✅ Done | FileToolset, TerminalToolset, chat REPL, ask_user, daemon |
| P8 | Agent Framework | #127-132, #149-162 | ✅ Done | PydanticAI multi-agent, agent def/registry/delegation, observability |
| P9 | Knowledge Pipeline | #133-136, #247-262 | ✅ Done | Ingestion pipeline, Qdrant hybrid search, BGE-M3 embeddings |
| P10 | External Connectors | #137-140 | ✅ Done | MCP client built |
| P10.5 | Voice | #240-246 | 📋 Planned | Moonshine migration (research done) |
| PX | Bootstrap/Assembly | #263+ | ✅ Done | bootstrap.py wires all modules into working system |
| P11 | Observability & UI | #141-144 | 📋 Planned | Admin dashboard, kanban replacement |
| P12 | Advanced | #145-148 | 📋 Planned | Council system, self-improvement, cron |

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | PydanticAI | Structured output, dependency injection, managed agent loop, FunctionToolset |
| LLM provider | Copilot API only | YAGNI — PydanticAI's `OpenAIChatModel` + `OpenAIProvider` wraps our copilot client |
| Async | Async throughout | httpx, Playwright, channel adapters all async |
| Hook implementation | Python callables | HookRegistry with async emit, error-isolated |
| Tool system | PydanticAI FunctionToolset | Not custom Tool ABC — PydanticAI handles schema export, validation, dispatch |
| Memory persistence | JSONL files | Session stores PydanticAI ModelMessage. Knowledge pipeline uses SQLite (schema) + Qdrant (vectors) + BGE-M3 (embeddings) |
| Skill loading | Progressive (lazy) | Frontmatter at scan time, full content on demand |
| Channel abstraction | Protocol (structural typing) | ChannelPlugin with name, send(), receive() |
| CLI | Typer (BearClaw) | Entry point for all user commands |
| Config | pydantic-settings | Env vars (OWLBEAR_ prefix), validated at startup |
| Browser | Custom (Playwright + CDP) | No OSS tool handles Edge CDP lifecycle; browser-use conflicts with PydanticAI agent loop; KISS 1200 LOC vs 15–20k ([research](browser-automation.md)) |
| Agent definitions | Markdown + YAML frontmatter | Human-readable, parsed by AgentDefinition model |
| Role policies | BUILDER/VALIDATOR with FilteredToolset | Validator denied write_file, create_file |

### Package-root lazy exports

OwlBear defaults to **direct imports or eager re-exports** for ordinary package roots.
A cached module-level `__getattr__` import map (`_LAZY_IMPORTS` + `__getattr__` caching
into `globals()`) is allowed only when a deliberate public package root has at least one
of:

- **Measured eager-import side effects** — the cost of importing the submodule eagerly
  is visible (slow startup, heavy transitive pull).
- **Optional-dependency pressure** — a symbol's submodule has an optional install that
  must not be imported until the symbol is accessed.
- **Import-cycle pressure** — a circular dependency cannot be broken by restructuring
  alone, and lazy importing is the least-invasive escape hatch.

**`__all__` is the supported public contract.** It is always explicit and limited to the
intended public surface. The lazy import map and `__getattr__` are implementation details:
private machinery that consumers must never depend on directly.

**Lazy-loader (the third-party package) is out of scope** for OwlBear's current small
fixed public surfaces. `owlbear.tools` (10 names) and `owlbear.memory.knowledge`
(14 names) use an inline `importlib`-based map, which is lower cost than adding
`lazy-loader` and its stub or packaging overhead.

**`__dir__` is optional ergonomics** — not required alongside `__getattr__`. The two
existing examples omit it by design; it can be added in a later targeted task if
interactive-shell discoverability becomes a practical need.

**Lazy exports must not be used to hide illegal dependency edges.** If a circular import
only disappears by deferring it to access time, that is a layering problem — fix the
layering first, then apply lazy imports only if import-cycle pressure remains.

Current repo examples:

- `src/owlbear/tools/__init__.py` — 10 public toolset symbols deferred to avoid eager
  loading of heavy submodules (e.g. `owlbear.tools.github_api` pulls
  `owlbear.core.retry`).
- `src/owlbear/memory/knowledge/__init__.py` — 14 public knowledge-graph symbols
  deferred to break a circular-import chain
  (`ingest → intake → core.retry → core.errors → tools → core.retry`).

## 9. Nanobot Influence

OwlBear draws architectural patterns from [nanobot](https://github.com/HKUDS/nanobot) (MIT, ~15K LOC, very active — PRs to #1325+). Key differences:

| Aspect | Nanobot | OwlBear |
|--------|---------|---------|
| Agent framework | LiteLLM (raw OpenAI messages) | PydanticAI (managed loop, DI, structured output) |
| Tool system | Custom Tool ABC + ToolRegistry | PydanticAI FunctionToolset |
| Channel routing | MessageBus (async queue) + ChannelManager | ChannelPlugin Protocol (direct) |
| Memory | MEMORY.md + HISTORY.md + LLM consolidation | SessionStore (JSONL) + ContextManager (.md) |
| Skill system | SkillsLoader (similar progressive) | SkillRegistry (FunctionToolset-based) |
| Agent delegation | SubagentManager (spawn tool) | DelegationToolset (delegate_to_agent tool) |
| Config | YAML schema | pydantic-settings (env vars) |

**Patterns to adopt** (per task #263 research):

- Wiring pattern: how AgentLoop.**init** composes all tools/contexts/sessions
- ContextBuilder approach: bootstrap files loaded at startup
- ChannelManager concept for multi-channel routing (when needed)

**Not applicable:** LiteLLM loop (PydanticAI manages this), raw Tool ABC, most channel adapters (we need CLI + Slack only).
