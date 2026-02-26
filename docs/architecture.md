# OwlBear Architecture

> **Version:** 0.1 (pre-implementation)
> **Date:** 2026-02-26
> **Based on:** [docs/agent-patterns-research.md](agent-patterns-research.md)

## 1. Vision

OwlBear is an always-on, laptop-resident AI development system. The user describes intent (via CLI, Teams, or voice), and OwlBear extracts intent, plans work, executes it autonomously, and delivers results — with human approval gates for destructive or publishing actions.

**Key constraints:**

- Runs on the user's laptop (needs user session for intranet browsing, credential entry)
- Uses GitHub Copilot API as the LLM provider (OAuth device-flow)
- Python 3.12+, managed by `uv`
- Quality over speed: every feature must be well-tested and maintainable

## 2. System Overview

```text
┌──────────────────────────────────────────────────────────┐
│                      OwlBear System                      │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ CLI (stdin) │  │   Teams    │  │   Voice    │         │
│  │  Adapter    │  │  Adapter   │  │  Adapter   │         │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
│        │               │               │                 │
│        └───────────┬────┴───────────────┘                 │
│                    ▼                                      │
│           ┌────────────────┐                              │
│           │ ChannelPlugin  │  Canonical Message in/out    │
│           │   Protocol     │                              │
│           └───────┬────────┘                              │
│                   ▼                                       │
│           ┌────────────────┐                              │
│           │   Agent Loop   │  Two-layer: outer + inner    │
│           │                │                              │
│           │  ┌──────────┐  │                              │
│           │  │ Provider  │──┼──→ GitHub Copilot API       │
│           │  └──────────┘  │                              │
│           │  ┌──────────┐  │                              │
│           │  │  Tools    │  │  ToolRegistry + Tool ABC    │
│           │  └──────────┘  │                              │
│           │  ┌──────────┐  │                              │
│           │  │  Skills   │  │  Progressive loading        │
│           │  └──────────┘  │                              │
│           │  ┌──────────┐  │                              │
│           │  │  Hooks    │  │  HookRegistry (events)      │
│           │  └──────────┘  │                              │
│           └───────┬────────┘                              │
│                   ▼                                       │
│           ┌────────────────┐                              │
│           │    Memory      │  Context (L1) + Session (L2) │
│           │   (JSONL)      │                              │
│           └────────────────┘                              │
│                                                           │
│  Future modules:                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │ Vector DB│ │ Browser  │ │ Doc Gen  │                   │
│  │ Pipeline │ │Automation│ │ Engine   │                   │
│  └──────────┘ └──────────┘ └──────────┘                   │
└──────────────────────────────────────────────────────────┘
```

## 3. Package Structure

```
src/owlbear/                    # Main Python package
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent.py                # Agent loop (two-layer)
│   ├── message.py              # Canonical Message model
│   ├── hooks.py                # HookRegistry + built-in hooks
│   └── config.py               # Pydantic Settings config
├── skills/
│   ├── __init__.py
│   ├── registry.py             # SkillRegistry (progressive loading)
│   └── base.py                 # Skill ABC
├── tools/
│   ├── __init__.py
│   ├── registry.py             # ToolRegistry
│   └── base.py                 # Tool ABC
├── channels/
│   ├── __init__.py
│   ├── base.py                 # ChannelPlugin Protocol
│   ├── cli.py                  # CLI adapter (stdin/stdout)
│   └── teams.py                # Teams adapter (later)
├── memory/
│   ├── __init__.py
│   ├── context.py              # Layer 1: always-loaded context
│   ├── session.py              # Layer 2: JSONL session log
│   └── compaction.py           # LLM-based compaction (later)
├── providers/
│   ├── __init__.py
│   ├── base.py                 # Provider Protocol
│   └── copilot.py              # GitHub Copilot API provider
└── voice/                      # Later phase
    ├── __init__.py
    ├── stt.py                  # Whisper STT adapter
    └── tts.py                  # TTS adapter (pyttsx3 → ElevenLabs)

src/bearclaw/                   # CLI package
├── __init__.py
└── cli.py                      # Typer CLI entry point
```

## 4. Core Components

### 4.1 Message Model

Single canonical type for all communication across the system.

```python
class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    channel: str = "cli"
    metadata: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
```

All channel adapters translate platform-specific formats to/from `Message`. The agent loop only sees `Message` objects — never platform-specific types.

### 4.2 Agent Loop (Two-Layer)

**Outer loop** — session lifecycle:

1. Load or create session
2. Inject Layer 1 context (system prompt + context.md)
3. Run inner turn
4. On error: retry with backoff (tenacity), log error
5. Save session

**Inner turn** — single LLM interaction:

1. Prepare messages (system prompt + history + new message)
2. Call `Provider.complete(messages, tools=tool_schemas)`
3. Parse response:
   - Text → return as assistant message
   - Tool call → emit `pre_tool_use` hook → execute tool → emit `post_tool_use` hook → loop back to step 2 with tool result
4. Append turn to session log

Target: <100 LOC for the core loop.

### 4.3 Provider Protocol

```python
class Provider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> ProviderResponse: ...
```

Initial implementation: `CopilotProvider` using httpx + truststore against `api.individual.githubcopilot.com`. OAuth device-flow for authentication (ported from Graphicator).

### 4.4 ToolRegistry + Tool ABC

```python
class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def parameters_schema(self) -> dict: ...

    @abstractmethod
    async def execute(self, **kwargs) -> Any: ...
```

`ToolRegistry`: register, get, list, `export_schemas()` → list of JSON schemas for LLM function calling.

### 4.5 SkillRegistry (Progressive Loading)

Each skill registered with:

- `name`: unique identifier
- `summary`: 1-2 line description (loaded into system prompt)
- `loader_fn`: callable that returns full instructions (lazy)

The LLM sees only summaries. When it invokes a skill, `load_full(name)` injects the complete instructions into the next turn.

### 4.6 HookRegistry

Event-driven system for cross-cutting concerns.

```python
class HookRegistry:
    def register(self, event: str, callback: Callable) -> None: ...
    async def emit(self, event: str, data: dict) -> list[Any]: ...
```

**Built-in events:** `on_session_start`, `on_session_end`, `pre_tool_use`, `post_tool_use`, `on_message`, `on_error`, `on_task_complete`.

**Pre-tool-use safety hook:** validates tool arguments, blocks dangerous operations (file deletion patterns, env file access), logs all tool invocations.

### 4.7 ChannelPlugin Protocol

```python
class ChannelPlugin(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def send(self, message: Message) -> None: ...
    async def receive(self) -> AsyncIterator[Message]: ...
```

Initial adapter: CLI (stdin/stdout). Later: Teams (Bot Framework or Composio MCP).

### 4.8 Memory System

**Layer 1 — Context** (always loaded, ~500 tokens):

- Project identity, current goals, key constraints
- Loaded from `context.md` file
- Injected as part of system prompt

**Layer 2 — Session** (searchable, on-demand):

- JSONL file per session
- Each line: `{role, content, timestamp, tool_calls, metadata}`
- Backed up before compaction
- Full history available for grep-based retrieval

## 5. Data Flow

```
User Input (CLI / Teams / Voice)
    │
    ▼
ChannelPlugin.receive()  ──→  Message(canonical)
    │
    ▼
HookRegistry.emit("on_message", msg)
    │
    ▼
Agent.outer_loop()
    ├── Session.load() / Session.create()
    ├── Context.inject()  (Layer 1 memory)
    ├── Agent.inner_turn(msg)
    │   ├── Provider.complete(messages)  ──→  Copilot API
    │   ├── Parse response (text or tool_call)
    │   ├── if tool_call:
    │   │   ├── HookRegistry.emit("pre_tool_use", tool)
    │   │   ├── ToolRegistry.execute(tool)
    │   │   └── HookRegistry.emit("post_tool_use", result)
    │   └── Session.append(turn)
    ├── Retry / failover on error (tenacity)
    └── Session.save()
    │
    ▼
ChannelPlugin.send(response)
```

## 6. Implementation Phases

| Phase | Name | Kanban Tasks | Focus |
|-------|------|-------------|-------|
| P1 | Bootstrap | #1-12 | Project skeleton, config, CLI stub, rename from Graphicator |
| P2 | Agent Core | #37-45 | Message model, HookRegistry, ToolRegistry, SkillRegistry, Session, ChannelPlugin, Provider, Agent loop |
| P2.5 | Docs & Config | #13-15 | sources.md, attribution, inventory updates |
| P3 | Quality & Hooks | #16-28, #46, #48 | VS Code hooks, safety hooks, agent roles (builder/validator), prompts |
| P4 | Auth & Comms | #30-36, #44, #47 | Copilot OAuth port, auth CLI, Teams research |
| P5 | Knowledge Pipeline | (future tasks) | Vector DB, Playwright browser automation, intranet scraping |
| P6 | Voice & Doc Gen | #49, (future tasks) | Whisper STT, TTS, document templates |

**Dependencies:** P1 must complete first. P2 depends on P1. P3 and P4 can partially overlap. P5 and P6 depend on P2 completion.

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Single provider initially | Copilot API only | YAGNI — but Provider Protocol allows adding more later |
| Sync vs async | Async throughout | httpx is async, channel adapters need async iteration, hooks need async emit |
| Hook implementation | Native Python callables | We're a Python library — no subprocess overhead like Claude Code hooks |
| Memory persistence | JSONL files | Simple, human-readable, grep-friendly. SQLite/vector DB added later for knowledge pipeline |
| Skill loading | Progressive (lazy) | Keeps base context small while supporting many skills |
| Channel abstraction | Protocol (structural typing) | No registration ceremony — any class implementing the protocol works |
| CLI framework | Typer (BearClaw) | Already decided in project setup |
| Config | pydantic-settings | Environment variables + TOML config file, validated at startup |
