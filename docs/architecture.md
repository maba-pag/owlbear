# OwlBear Architecture

> **Version:** 0.2 (post-implementation audit)
> **Date:** 2026-02-28
> **Previous:** v0.1 (2026-02-26, pre-implementation)
> **Based on:** Full code audit of all ~50 modules, [agent-patterns-research.md](agent-patterns-research.md), [daemon-bootstrap-research.md](daemon-bootstrap-research.md)

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
│ │Terminal│ │  Guard   │ │ loading   │ │ (JSONL)  │ │5 agent defs  │        │
│ │AskUser │ │Lint      │ │           │ │Context   │ │(coder,       │        │
│ │GitHub  │ │Context   │ │           │ │ (.md)    │ │orchestrator, │        │
│ │Git     │ │Notify    │ │           │ │Usage     │ │researcher,   │        │
│ │Browser │ │Observe   │ │           │ │ tracker  │ │reviewer,     │        │
│ │MCP     │ │Subagent  │ │           │ │          │ │writer)       │        │
│ │Hooked  │ │Test      │ │           │ │Knowledge │ │              │        │
│ └────────┘ └──────────┘ └───────────┘ │ pipeline │ └──────────────┘        │
│                                        │(not wired│                         │
│                                        │  yet)    │                         │
│                                        └──────────┘                         │
│                                                                             │
│  ┌─ Auth ─────────────────┐  ┌─ Config ──────────────┐                     │
│  │ Copilot OAuth          │  │ OwlBearSettings        │                     │
│  │ (device-flow, token    │  │ (pydantic-settings,    │                     │
│  │  cache, proxy-ep)      │  │  env + TOML)           │                     │
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
│   ├── deps.py                       # OwlBearDeps (shared dependency injection)
│   ├── hooks.py                      # HookEvent enum, HookRegistry
│   ├── roles.py                      # AgentRole, RolePolicy, apply_role_policy()
│   ├── delegation.py                 # DelegationToolset (delegate_to_agent tool)
│   ├── command_guard.py              # CommandSafetyGuard (PRE_TOOL_USE hook)
│   ├── context_hook.py               # ContextInjectionHook (SESSION_START)
│   ├── lint_hook.py                  # AutoLintHook (POST_TOOL_USE)
│   ├── notification_hook.py          # NotificationHook (console/winsound)
│   ├── observability.py              # ObservabilityHook + EventStore (JSONL)
│   ├── subagent_hook.py              # SubagentVerificationHook
│   └── test_hook.py                  # TestVerificationHook (SESSION_END)
│
├── channels/
│   ├── __init__.py                   # ⚠ Unconditional SlackChannel import (bug)
│   ├── base.py                       # ChannelPlugin Protocol (name, send, receive)
│   ├── cli.py                        # CLIChannel (stdin/stdout)
│   └── slack.py                      # SlackChannel (SocketMode + AsyncWebClient)
│
├── memory/
│   ├── __init__.py
│   ├── context.py                    # ContextManager (context.md → instructions)
│   ├── session.py                    # SessionStore (JSONL persistence)
│   ├── usage.py                      # UsageRecord, UsageTracker (JSONL)
│   ├── usage_cost.py                 # calc_estimated_cost (genai_prices)
│   └── knowledge/                    # Knowledge pipeline (11 files, ~2500 LOC)
│       ├── __init__.py
│       ├── schema.py                 # SQLite + sqlite-vec DDL, migrations
│       ├── vectors.py                # VectorStore (temporal decay, bridge table)
│       ├── embeddings.py             # EmbeddingProvider + FastEmbedProvider
│       ├── graph.py                  # GraphStore (entity/edge CRUD)
│       ├── models.py                 # Entity, Edge, Document Pydantic models
│       ├── extractor.py              # LLM-based entity extraction
│       ├── reranker.py               # BGE reranker (cross-encoder)
│       ├── chunker.py                # TextChunker (token-level splits)
│       ├── dedup.py                  # Entity deduplication
│       ├── ingest.py                 # IngestPipeline orchestrator
│       └── intake.py                 # File/URL/text readers
│
├── providers/
│   ├── __init__.py
│   ├── copilot.py                    # create_copilot_client() → AsyncOpenAI
│   └── copilot_multipliers.py        # Premium request multipliers per model
│
├── skills/
│   ├── __init__.py
│   └── registry.py                   # SkillRegistry (FunctionToolset, progressive)
│
├── tools/
│   ├── __init__.py
│   ├── hooked.py                     # HookedToolset (WrapperToolset, PRE/POST hooks)
│   ├── ask_user.py                   # AskUserToolset (via ChannelPlugin)
│   ├── filesystem.py                 # FileToolset (read/write/create/list/search)
│   ├── terminal.py                   # TerminalToolset (run_command, timeout)
│   ├── github_api.py                 # GitHubToolset (REST: PRs, issues)
│   ├── git_local.py                  # GitLocalToolset (git CLI wrapper)
│   ├── mcp_registry.py              # MCPServerRegistry (lifecycle, health check)
│   ├── mcp_servers.py                # Factory: github, git, fetch servers
│   └── browser/                      # Browser automation (12 files, ~1200 LOC)
│       ├── __init__.py
│       ├── config.py                 # BrowserConfig (URL allow/block, CDP, viewport)
│       ├── manager.py                # BrowserManager (launch/CDP modes, Playwright)
│       ├── actions.py                # 6 browser actions (navigate, click, type, ...)
│       ├── toolset.py                # BrowserToolset (FunctionToolset wrapping)
│       ├── safety.py                 # URLSafetyGuard (blocklist/allowlist)
│       ├── launcher.py               # Edge CDP launcher (find/launch/probe/kill)
│       ├── content_extractor.py      # trafilatura-based extraction
│       ├── crawler.py                # WebCrawler (async BFS, robots.txt)
│       ├── crawl_config.py           # CrawlConfig model
│       ├── url_utils.py              # URL normalize, discover_links, robots checker
│       └── integration.py            # crawl_and_ingest bridge
│
├── voice/
│   ├── __init__.py
│   ├── stt.py                        # STTEngine (moonshine-voice batch mode)
│   ├── streaming_stt.py              # StreamingSTT (moonshine-voice MicTranscriber)
│   ├── tts.py                        # TTSEngine (pyttsx3)
│   └── channel.py                    # VoiceChannel (quick + brainstorm modes)
│
└── agents/                           # Agent definitions (markdown + YAML frontmatter)
    ├── coder.md                      # Builder role, TDD workflow
    ├── orchestrator.md               # Builder role, delegation, depth=5
    ├── researcher.md                 # Validator role, read-only, browser
    ├── reviewer.md                   # Validator role, read-only, depth=0
    └── writer.md                     # Builder role, filesystem only, depth=0

src/bearclaw/                         # CLI package
├── __init__.py
└── cli.py                            # Typer app (~860 LOC): auth, chat, run, stop,
                                      # status, browser, slack, voice, usage
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
| `TASK_COMPLETE` | After kanban task done | _(none yet)_ |
| `QUESTION_PENDING` | User question queued | NotificationHook |

### 4.3 Toolsets (PydanticAI FunctionToolset-based)

All toolsets extend `pydantic_ai.toolsets.FunctionToolset`. Composed at run-time via `toolsets=[...]` parameter.

| Toolset | Tools | Status |
|---------|-------|--------|
| FileToolset | read_file, write_file, create_file, list_directory, search_files | ✅ Wired in `bearclaw chat` |
| TerminalToolset | run_command | ✅ Wired in `bearclaw chat` |
| AskUserToolset | ask_user | ✅ Wired in `bearclaw chat` |
| SkillRegistry | list_skills, load_skill | ✅ Wired in `bearclaw chat` |
| GitLocalToolset | git_status, git_diff, git_add, git_commit, git_branch, git_log, git_push | ✅ Wired in `bearclaw chat` |
| GitHubToolset | create_pr, list_prs, list_issues, get_issue | ✅ Conditionally wired |
| DelegationToolset | delegate_to_agent | ⚠ Built, not wired |
| BrowserToolset | navigate, click, type_text, select_option, read_page_text, screenshot | ⚠ Built, not wired |
| HookedToolset | _(wraps any toolset)_ | ⚠ Built, not wired |
| MCPServerRegistry | _(dynamic MCP tools)_ | ⚠ Built, not wired |

### 4.4 Agent Framework (multi-agent)

PydanticAI-based multi-agent system:

- **AgentDefinition**: Parsed from markdown files with YAML frontmatter (name, role, tools, model, system_prompt)
- **AgentRegistry**: Scans `.md` agent definitions, lazily builds PydanticAI Agents with resolved toolsets and role policies
- **DelegationToolset**: `delegate_to_agent` tool allows one agent to spawn another with depth-limited recursion (max 5)
- **RolePolicy**: BUILDER (full access) vs VALIDATOR (read-only, denied: write_file, create_file)
- **OwlBearDeps**: Shared dependency object injected into every agent run (hooks, tracker, registry, delegation depth)

5 agent definitions: coder (builder, TDD), orchestrator (builder, delegation), researcher (validator, browser), reviewer (validator, read-only), writer (builder, filesystem).

### 4.5 Channels

`ChannelPlugin` Protocol with 3 implementations:

- **CLIChannel**: stdin/stdout with optional stream injection for testing
- **SlackChannel**: SocketMode WebSocket + AsyncWebClient, DM-only
- **VoiceChannel**: STT (moonshine-voice) + TTS (pyttsx3), quick + brainstorm modes

### 4.6 Memory System

**Layer 1 — Context**: `ContextManager` reads `context.md` from workspace root, injected as agent `instructions` property.

**Layer 2 — Session**: `SessionStore` persists PydanticAI `ModelMessage` objects as JSONL. Load/save/append/backup per session.

**Usage tracking**: `UsageTracker` records per-turn usage (tokens, cost, premium requests) as JSONL.

**Knowledge pipeline** (built, not wired to agent): 11 modules covering chunking → entity extraction → graph store → vector embeddings → reranking → ingest pipeline. Currently uses sqlite-vec + FastEmbed; planned migration to Qdrant + bge-m3 (#247-#261).

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

**Why custom** (see [browser-automation-research.md](browser-automation-research.md) for full analysis):

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

### 5.2 Target (after bootstrap, task #263)

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

## 6. Assembly Gap (blocking issue)

As of v0.2, all individual modules are built and tested (1608 tests, 2 SSL-env failures), but **no bootstrap layer wires them into a working system**. The `bearclaw chat` command manually wires ~40% of components; the `bearclaw run` daemon wires ~10%.

**What's wired today** (in `bearclaw chat`): FileToolset, TerminalToolset, AskUserToolset, SkillRegistry, GitLocalToolset, GitHubToolset (conditional), CommandSafetyGuard.

**What's NOT wired:**

1. AgentRegistry + agent definitions (5 .md files, never loaded)
2. DelegationToolset (never instantiated)
3. BrowserToolset (never added to any agent)
4. MCP servers (configured, never started)
5. HookedToolset (never wraps toolsets)
6. 6 of 7 hooks (only CommandSafetyGuard wired)
7. Knowledge pipeline (no tool interface to agent)
8. Daemon (creates toolset-less agent)
9. create_copilot_client() → OpenAIChatModel bridge (orphaned)

**Blocking task: #263** — Research bootstrap/assembly layer using nanobot patterns adapted for PydanticAI.

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
| P9 | Knowledge Pipeline | #133-136, #247-262 | 🔄 Active | Ingestion pipeline built; Qdrant+bge-m3 migration in research |
| P10 | External Connectors | #137-140 | ✅ Done | MCP client built |
| P10.5 | Voice | #240-246 | 📋 Planned | Moonshine migration (research done) |
| **PX** | **Bootstrap/Assembly** | **#263** | **🚨 Critical** | **Wire all modules into working system** |
| P11 | Observability & UI | #141-144 | 📋 Planned | Admin dashboard, kanban replacement |
| P12 | Advanced | #145-148 | 📋 Planned | Council system, self-improvement, cron |

**Critical path:** PX (Bootstrap) unblocks everything. Without it, individual modules remain disconnected despite being individually tested.

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | PydanticAI | Structured output, dependency injection, managed agent loop, FunctionToolset |
| LLM provider | Copilot API only | YAGNI — PydanticAI's `OpenAIChatModel` + `OpenAIProvider` wraps our copilot client |
| Async | Async throughout | httpx, Playwright, channel adapters all async |
| Hook implementation | Python callables | HookRegistry with async emit, error-isolated |
| Tool system | PydanticAI FunctionToolset | Not custom Tool ABC — PydanticAI handles schema export, validation, dispatch |
| Memory persistence | JSONL files | Session stores PydanticAI ModelMessage. Knowledge pipeline uses sqlite-vec (migrating to Qdrant) |
| Skill loading | Progressive (lazy) | Frontmatter at scan time, full content on demand |
| Channel abstraction | Protocol (structural typing) | ChannelPlugin with name, send(), receive() |
| CLI | Typer (BearClaw) | Entry point for all user commands |
| Config | pydantic-settings | Env vars (OWLBEAR_ prefix) + TOML, validated at startup |
| Browser | Custom (Playwright + CDP) | No OSS tool handles Edge CDP lifecycle; browser-use conflicts with PydanticAI agent loop; KISS 1200 LOC vs 15–20k ([research](browser-automation-research.md)) |
| Agent definitions | Markdown + YAML frontmatter | Human-readable, parsed by AgentDefinition model |
| Role policies | BUILDER/VALIDATOR with FilteredToolset | Validator denied write_file, create_file |

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
| Config | YAML schema | pydantic-settings (env + TOML) |

**Patterns to adopt** (per task #263 research):

- Wiring pattern: how AgentLoop.**init** composes all tools/contexts/sessions
- ContextBuilder approach: bootstrap files loaded at startup
- Memory consolidation: LLM-based MEMORY.md + HISTORY.md archiving
- ChannelManager concept for multi-channel routing (when needed)

**Not applicable:** LiteLLM loop (PydanticAI manages this), raw Tool ABC, most channel adapters (we need CLI + Slack only).
