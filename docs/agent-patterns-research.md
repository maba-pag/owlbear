# Agent Patterns Research

> **Owning task:** #22 — P3-07: Research agent patterns from external repos
> **Date:** 2026-02-26
> **Status:** Complete

## 1. Repos Studied

| Repo | Language | Scale | Focus |
|------|----------|-------|-------|
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | TypeScript | ~430k LOC, 6800 files | Always-on chatbot, multi-platform comms, plugin ecosystem |
| [HKUDS/nanobot](https://github.com/HKUDS/nanobot) | Python | ~4k LOC, 35 files | Lean agent framework, message bus, subagent spawning |
| [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) | Python/MD | ~50 files | Claude Code hook patterns, builder/validator team, session management |

---

## 2. Architecture Comparisons

### 2.1 Agent Loop

| Aspect | OpenClaw | Nanobot | OwlBear Recommendation |
|--------|----------|---------|----------------------|
| **Loop structure** | Two-layer: outer retry/failover + inner attempt | Single loop with MessageBus async queues | **Two-layer.** Outer loop handles retries, provider failover, session persistence. Inner loop handles single turn: parse → route → execute → respond. |
| **Provider abstraction** | Auth profile rotation with cooldown timers, multi-provider | LiteLLM wrapper (~270 LOC for 20+ providers) | **LiteLLM-style.** Single provider interface via `httpx` to Copilot API. Keep the abstraction even though we start with one provider — it costs nothing and future-proofs. |
| **Error handling** | Exponential backoff, auth profile swap on 429/401, graceful degradation | tenacity decorators, fallback messages | **tenacity** with exponential backoff + jitter. Provider swap not needed initially (single Copilot endpoint), but design the retry layer to accept a provider list. |
| **Context management** | Compaction via LLM summarization when context window fills | Two-layer memory: MEMORY.md (always-loaded ~500 tokens) + HISTORY.md (grep-searchable) | **Two-layer memory.** MEMORY.md equivalent as system prompt context. HISTORY.md equivalent as searchable session log. Add LLM-based compaction later. |

### 2.2 Communication Gateway

| Aspect | OpenClaw | Nanobot | OwlBear Recommendation |
|--------|----------|---------|----------------------|
| **Abstraction** | `ChannelPlugin` interface (Python Protocol/ABC). 12+ adapters: Slack, Discord, Teams, WhatsApp, Telegram, etc. | WhatsApp via Node.js bridge process (subprocess) | **ChannelPlugin ABC.** Define `Protocol` with `send()`, `receive()`, `connect()`, `disconnect()`. Start with CLI adapter only. Add Teams adapter later. |
| **Teams path** | Bot Framework SDK (Azure Bot Service registration) | N/A | **Bot Framework** is the most capable path (rich cards, adaptive cards, proactive messages). Alternative: Composio MCP if we want zero-infra. Research both in a dedicated task. |
| **Message format** | Internal canonical message type, adapters translate to/from platform-specific formats | Raw text strings | **Canonical Message model.** Pydantic model with `role`, `content`, `metadata`, `channel`, `timestamp`. Adapters serialize to/from platform-specific formats. |

### 2.3 Skill / Tool System

| Aspect | OpenClaw | Nanobot | Disler | OwlBear Recommendation |
|--------|----------|---------|--------|----------------------|
| **Registration** | 24+ hook events, plugins register callbacks | `Tool` ABC + `ToolRegistry` (dict-based) | Markdown frontmatter agent definitions, `settings.json` hook config | **Tool ABC + Registry.** `Tool` base class with `name`, `description`, `execute()`. `ToolRegistry` for registration and lookup. Export tool schemas as JSON for LLM function-calling. |
| **Loading** | Eager load all plugins at startup | Progressive: SKILL.md summary loaded first, full skill on demand | Agents loaded by delegation based on `description` field | **Progressive loading.** Each skill has a summary (1-2 lines) loaded into context; full instructions loaded only when invoked. Keeps base context small. |
| **Boundaries** | Hook matchers scope hooks to specific tools/events | Subagent spawning with restricted tool sets | `disallowedTools` in agent frontmatter (validator can't write) | **Restricted tool sets per agent role.** Builder gets read+write+execute. Validator gets read-only. Planner gets read+create-task. Define as sets in agent config. |

### 2.4 Session & Memory

| Aspect | OpenClaw | Nanobot | Disler | OwlBear Recommendation |
|--------|----------|---------|--------|----------------------|
| **Transcript** | JSONL per session, stored on disk | HISTORY.md (markdown log, grep-searchable) | JSONL transcript, `pre_compact` hook backs up before compaction | **JSONL session log.** One `.jsonl` file per session. Each line: `{role, content, timestamp, tool_calls, metadata}`. Backed up before compaction. |
| **Persistent memory** | SQLite + sqlite-vec for long-term knowledge | MEMORY.md (always-loaded, ~500 tokens, hand-curated) | Per-session JSON files in `.claude/data/sessions/` | **MEMORY.md equivalent.** A `context.md` file per project/domain that's always injected into system prompt. Curated by the user or by a "memory curator" agent. |
| **Compaction** | LLM summarizes old turns, replaces them | Manual editing of HISTORY.md | `pre_compact.py` hook backs up transcript before auto-compaction | **LLM compaction.** When context approaches limit, summarize older turns and replace. Keep the backup. This is a later-phase feature. |

### 2.5 Hook / Event System

| Aspect | OpenClaw | Disler | OwlBear Recommendation |
|--------|----------|--------|----------------------|
| **Events** | 24+ hook events (message, command, reaction, join, leave, etc.) | 13 hook types: Setup, SessionStart, SessionEnd, PreToolUse, PostToolUse, PostToolUseFailure, PreCompact, Stop, SubagentStart, SubagentStop, Notification, UserPromptSubmit, PermissionRequest | **Start with 5-8 hooks.** `on_session_start`, `on_session_end`, `pre_tool_use`, `post_tool_use`, `on_message`, `on_error`, `on_task_complete`. Add more as needed. |
| **Implementation** | Plugin classes register callbacks on events | Python scripts invoked as subprocesses, receive JSON on stdin, exit codes control flow (0=pass, 2=block) | **Python callables.** Register hook functions (not subprocess scripts — we're a Python project, no need for the subprocess overhead). Use a simple `HookRegistry` with `register(event, callable)` and `emit(event, data)`. |
| **Safety** | N/A | `pre_tool_use.py` blocks `rm -rf` and `.env` access, exit code 2 = block | **Safety hooks in pre_tool_use.** Validate commands before execution. Block dangerous operations. Log all tool invocations. |

### 2.6 Build Pipeline (Multi-Step Task Execution)

| Aspect | OpenClaw | Nanobot | Disler | OwlBear Recommendation |
|--------|----------|---------|--------|----------------------|
| **Orchestration** | Cron-based heartbeat checks pending work, spawns subagents | Subagent spawning with restricted tools + message bus routing | Builder/Validator two-agent team pattern; meta-agent generates new agent configs | **Orchestrator + Builder + Validator.** We already have this pattern in our kanban agents. Extend it: orchestrator reads kanban board → spawns builder for each task → spawns validator to verify → advances task status. |
| **Human-in-the-loop** | Approval gates in build pipeline, user confirms before publish | N/A | N/A | **Approval gates.** Before any destructive or publishing action, pause and notify user. Use the comms channel (CLI initially, Teams later) for approval prompts. |
| **Quality gates** | Multi-stage review (tests, lint, human review) | Tests as part of tool execution | PostToolUse hooks run ruff + ty validators after every Write/Edit | **Automated quality gates.** After every code change: ruff check, pytest, type check. Block merge/advance if gates fail. This maps to our existing review → docs → done pipeline. |

### 2.7 Voice / TTS Integration

| Aspect | Disler | OwlBear Recommendation |
|--------|--------|----------------------|
| **TTS output** | Priority chain: ElevenLabs → OpenAI → pyttsx3 (local). Used in `stop.py` to announce task completion and in `work-completion-summary` agent. | **pyttsx3 for local TTS** (zero-cost, works offline). Add ElevenLabs/OpenAI later. Use for task completion announcements and status updates. |
| **Voice input** | Not implemented (spec file `subagent-tts-summary-queue.md` describes a queue system) | **Local Whisper STT** as primary input. Microphone → Whisper → text → parse intent → execute. This is a later-phase feature. |
| **Architecture** | Separate TTS utility scripts in `hooks/utils/tts/`, called by hooks | **Voice module** with STT and TTS adapters behind a common interface. Keep separate from core agent loop — voice is an I/O adapter, not core logic. |

---

## 3. Key Patterns to Adopt

### 3.1 Progressive Skill Loading (from Nanobot)

Each skill has a one-line summary stored in a registry. When the LLM decides to use a skill, the full instructions are loaded on demand. This keeps the base system prompt small (~2k tokens) while supporting dozens of skills.

**Implementation:** `SkillRegistry` class with `register(name, summary, loader_fn)`. The `loader_fn` lazily reads the full skill file. The LLM sees only summaries in its system prompt; when it invokes a skill, the full instructions are injected into the next turn.

### 3.2 Canonical Message Model (from OpenClaw)

All communication — CLI input, Teams messages, voice transcriptions — goes through a single `Message` Pydantic model. Channel adapters translate platform-specific formats to/from this canonical form.

```python
class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    channel: str = "cli"
    metadata: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
```

### 3.3 Builder/Validator Team (from Disler)

Separate agent roles with different tool permissions:

- **Builder** (read+write+execute): Does the work. After every file write, validation hooks run (ruff, type checker).
- **Validator** (read-only, `disallowedTools: Write, Edit`): Inspects the work against acceptance criteria. Cannot modify files.

This prevents "Ralph Wiggum" failures where the agent marks its own homework as complete without actually verifying.

### 3.4 Hook-Based Safety Guards (from Disler)

The `pre_tool_use` hook pattern — intercept every tool call, check for dangerous patterns (`rm -rf`, `.env` access), block with exit code 2 — is an excellent safety net. In our Python context, this becomes a `@pre_tool_use` decorator or hook function that validates tool arguments before execution.

### 3.5 Session Persistence with Pre-Compaction Backup (from Disler)

Before LLM compaction discards old context, back up the full transcript. This preserves the complete history for debugging and auditing while allowing the active context to stay within token limits.

### 3.6 Two-Layer Memory (from Nanobot)

- **Layer 1: Context file** (always loaded, ~500 tokens). Contains project identity, current goals, key constraints. Equivalent to `MEMORY.md`.
- **Layer 2: Session log** (searchable, not loaded by default). Contains full conversation history. Equivalent to `HISTORY.md`. Grep-searchable for retrieval.

This gives the agent stable identity across sessions without bloating context.

---

## 4. Architecture Recommendations for OwlBear

### 4.1 Module Structure

```
src/owlbear/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent.py          # Agent loop (two-layer: outer retry + inner turn)
│   ├── message.py        # Canonical Message model
│   ├── hooks.py          # HookRegistry + built-in hooks
│   └── config.py         # Pydantic Settings config
├── skills/
│   ├── __init__.py
│   ├── registry.py       # SkillRegistry (progressive loading)
│   └── base.py           # Skill ABC
├── tools/
│   ├── __init__.py
│   ├── registry.py       # ToolRegistry
│   └── base.py           # Tool ABC
├── channels/
│   ├── __init__.py
│   ├── base.py           # ChannelPlugin Protocol
│   ├── cli.py            # CLI adapter (stdin/stdout)
│   └── teams.py          # Teams adapter (later)
├── memory/
│   ├── __init__.py
│   ├── context.py        # Layer 1: always-loaded context
│   ├── session.py        # Layer 2: JSONL session log
│   └── compaction.py     # LLM-based compaction (later)
├── providers/
│   ├── __init__.py
│   ├── base.py           # Provider Protocol
│   └── copilot.py        # GitHub Copilot API provider
└── voice/                # Later phase
    ├── __init__.py
    ├── stt.py            # Whisper STT adapter
    └── tts.py            # TTS adapter (pyttsx3 → ElevenLabs)

src/bearclaw/
├── __init__.py
└── cli.py                # Typer CLI entry point
```

### 4.2 Data Flow

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
    │   ├── Provider.complete(messages)  ──→  LLM API
    │   ├── Parse response (text / tool_call)
    │   ├── if tool_call:
    │   │   ├── HookRegistry.emit("pre_tool_use", tool)
    │   │   ├── ToolRegistry.execute(tool)
    │   │   └── HookRegistry.emit("post_tool_use", result)
    │   └── Session.append(turn)
    ├── Retry / failover on error
    └── Session.save()
    │
    ▼
ChannelPlugin.send(response)
```

### 4.3 Recommended Phase Structure

Based on the research findings, here's how the expanded vision maps to implementation phases:

| Phase | Name | Focus | Key Deliverables |
|-------|------|-------|-----------------|
| P1 | Bootstrap | Project skeleton, config, CLI stub | pyproject.toml, src layout, bearclaw CLI, config module |
| P2 | Agent Core | Agent loop, provider, tools, memory | Two-layer agent loop, Copilot provider, Tool ABC, SkillRegistry, JSONL sessions, Message model |
| P3 | Quality & Hooks | Safety, validation, build pipeline | HookRegistry, pre_tool_use safety, builder/validator pattern, automated quality gates |
| P4 | Comms Gateway | Channel abstraction, Teams research | ChannelPlugin Protocol, CLI adapter, Teams adapter research & impl |
| P5 | Knowledge Pipeline | Vector DB, browser automation, scraping | ChromaDB/sqlite-vec integration, Playwright browser, intranet scraping pipeline |
| P6 | Voice & Doc Gen | STT/TTS, document generation | Whisper STT, pyttsx3 TTS, document templates, compliance form generation |

---

## 5. Anti-Patterns to Avoid

1. **Monolithic agent loop.** OpenClaw's 430k LOC is a warning. Keep modules small, interfaces clean. The agent loop itself should be <100 LOC.
2. **Eager skill loading.** Loading all skills into context wastes tokens. Use progressive loading.
3. **Self-validating agents.** Never let the builder verify its own work. Always use a separate validator with restricted permissions.
4. **Subprocess hooks in a Python project.** Disler uses subprocess calls because Claude Code hooks require external scripts. We're building a Python library — use native callables, not subprocess overhead.
5. **Skipping transcript backup before compaction.** Always back up the full transcript before LLM summarization discards detail.
6. **Platform-specific message types leaking into core.** Keep the canonical Message model as the only type the agent loop sees. Adapters handle translation.

---

## 6. Follow-up Tasks

Each task below should be created on the kanban board. They replace the current Phase 3-4 scaffolding tasks with architecture-informed implementations.

1. **Implement canonical Message model** — Priority: high, Depends: P1 done. AC: `src/owlbear/core/message.py` with `Message` Pydantic model (role, content, channel, metadata, timestamp). 100% test coverage. See §3.2.

2. **Implement HookRegistry** — Priority: high, Depends: #1. AC: `src/owlbear/core/hooks.py` with `HookRegistry` class: `register(event, callable)`, `emit(event, data)`. Built-in events: `on_session_start`, `on_session_end`, `pre_tool_use`, `post_tool_use`, `on_message`, `on_error`. Tests cover register, emit, ordering. See §2.5.

3. **Implement Tool ABC + ToolRegistry** — Priority: high, Depends: #1. AC: `src/owlbear/tools/base.py` with `Tool` ABC (name, description, parameters_schema, execute). `src/owlbear/tools/registry.py` with `ToolRegistry` (register, get, list, export_schemas). Tests cover registration, lookup, schema export. See §2.3.

4. **Implement SkillRegistry with progressive loading** — Priority: high, Depends: #3. AC: `src/owlbear/skills/registry.py` with `SkillRegistry` (register with summary + lazy loader, get_summaries, load_full). Tests verify lazy loading behavior. See §3.1.

5. **Implement JSONL session persistence** — Priority: high, Depends: #1. AC: `src/owlbear/memory/session.py` with `Session` class: create, load, append, save, backup. JSONL format. Tests cover round-trip persistence and backup before compaction. See §2.4.

6. **Implement two-layer memory (context + session)** — Priority: medium, Depends: #5. AC: `src/owlbear/memory/context.py` with `ContextManager` that loads a `context.md` file into system prompt. Integrates with Session for Layer 2. See §3.6.

7. **Implement ChannelPlugin Protocol + CLI adapter** — Priority: high, Depends: #1. AC: `src/owlbear/channels/base.py` with `ChannelPlugin` Protocol (send, receive, connect, disconnect). `src/owlbear/channels/cli.py` with CLI adapter using stdin/stdout. Tests cover the adapter. See §2.2.

8. **Implement Copilot API provider** — Priority: high, Depends: P1 OAuth port. AC: `src/owlbear/providers/copilot.py` with `CopilotProvider` implementing `Provider` Protocol. Uses httpx + truststore. Supports chat completion with function calling. Tests with mocked responses. See §2.1.

9. **Implement two-layer agent loop** — Priority: high, Depends: #2, #3, #5, #7, #8. AC: `src/owlbear/core/agent.py` with `Agent` class: outer_loop (retry, session management) + inner_turn (LLM call, tool execution, hook emission). <100 LOC for core loop. Integration test with mocked provider. See §2.1.

10. **Implement pre_tool_use safety hook** — Priority: medium, Depends: #2. AC: Built-in hook registered on `pre_tool_use` that validates tool arguments. Blocks dangerous file operations. Logs all tool invocations. See §3.4.

11. **Research Teams integration path** — Priority: low, Depends: none. AC: Research doc comparing Bot Framework SDK vs Composio MCP vs direct Graph API for Teams integration. Recommend one path. Create follow-up implementation tasks. Tag: `research`. See §2.2.

12. **Implement builder/validator agent roles** — Priority: medium, Depends: #3, #4, #9. AC: Builder agent config with full tool access. Validator agent config with read-only tools. Tests verify validator cannot write. See §3.3.

13. **Design voice I/O module** — Priority: low, Depends: none. AC: Research doc on local Whisper STT integration (model size, latency, accuracy tradeoffs) + pyttsx3 TTS for output. Recommend architecture. Tag: `research`. See §2.7.
