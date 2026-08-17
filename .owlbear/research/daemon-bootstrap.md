# Daemon Bootstrap Research — Wiring PydanticAI Agent Loop

> **Owning task:** (new — daemon bootstrap research)
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear has ~15 individually tested modules that have never run together. How do we wire them into an autonomous PydanticAI agent daemon? Specifically: model bridge, tool registration, daemon loop, assembly pattern, and channel integration.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI docs — Agents | <https://ai.pydantic.dev/agents/> | .95 | Agent construction, `run()`, `iter()`, `message_history`, `instructions`, `toolsets` |
| PydanticAI docs — OpenAI Models | <https://ai.pydantic.dev/models/openai/> | .95 | `OpenAIChatModel` + `OpenAIProvider(openai_client=...)` for custom endpoints |
| PydanticAI docs — Toolsets | <https://ai.pydantic.dev/toolsets/> | .90 | `FunctionToolset`, `CombinedToolset`, `FilteredToolset`, toolsets at run-time |
| PydanticAI docs — Multi-Agent | <https://ai.pydantic.dev/multi-agent-applications/> | .85 | Agent delegation, programmatic hand-off, deep agents pattern |
| tool.graphicator `agents/__init__.py` | Local project | .90 | Working `create_agent()` factory: `OpenAIChatModel` + `OpenAIProvider(openai_client=copilot_client)` |
| OwlBear `pydantic-ai-integration.md` | `docs/research/pydantic-ai-integration.md` | .85 | Confirmed OpenAIProvider pattern, FunctionToolset, PydanticAI provides agent loop |
| pydantic-deepagents (prior art) | <https://github.com/vstorm-co/pydantic-deepagents> | .70 | Skills, hooks, memory patterns; anti-pattern: 855-line factory function |

## 3. Analysis

### 3.1 Model Bridge — How to Wire Copilot to PydanticAI

Current `OwlBearAgent.__init__` takes `model: str` and passes it to `Agent(model, ...)`. PydanticAI accepts both a string name and a model instance. To use Copilot, we need an `OpenAIChatModel` with our custom `AsyncOpenAI` client.

**Pattern (confirmed working in tool.graphicator):**

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

client = await create_copilot_client(settings)  # existing module
provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel(settings.chat_model, provider=provider)
agent = Agent(model, instructions=..., toolsets=[...])
```

**Change required:** `OwlBearAgent.__init__` should accept `model: str | OpenAIChatModel` instead of just `str`. PydanticAI `Agent` already accepts both — zero adaptation on its side.

| Option | Change | KISS Score |
|--------|--------|------------|
| A. Accept `str \| Model` in OwlBearAgent | 1-line type hint change | High |
| B. Always construct model externally, pass instance | Cleaner separation | High |
| C. Build model inside OwlBearAgent from settings | Couples agent to auth | Low |

**Recommendation (.90):** Option B — construct the model in the bootstrap function, pass the instance to `OwlBearAgent`. Keeps auth concerns out of the agent. Matches tool.graphicator prior art.

### 3.2 Tool Registration — What Tools Does the Agent Need?

PydanticAI supports multiple registration paths. Current OwlBear toolsets (`BrowserToolset`, `SkillRegistry`) already extend `FunctionToolset`. They can be passed directly via `toolsets=[...]` at Agent construction or at run-time.

**Tools needed for autonomous dev work:**

| Tool | Purpose | Implementation |
|------|---------|----------------|
| `file_read` | Read file contents | New `DevToolset(FunctionToolset)` |
| `file_write` | Write/create files | New `DevToolset` |
| `file_edit` | Edit existing files | New `DevToolset` |
| `execute_command` | Run shell commands | New `DevToolset` — requires safety guard |
| `list_directory` | List directory contents | New `DevToolset` |
| `kanban_list` | List kanban board tasks | New `DevToolset` |
| `kanban_show` | Show task details | New `DevToolset` |
| `kanban_move` | Move task between statuses | New `DevToolset` |
| `list_skills` | List available skills | Existing `SkillRegistry` |
| `load_skill` | Load a skill by name | Existing `SkillRegistry` |
| `browser_*` | 6 browser tools | Existing `BrowserToolset` |

**Composition pattern (from PydanticAI docs):**

```python
agent = Agent(
    model,
    instructions=context.instructions,
    toolsets=[dev_toolset, skill_registry, browser_toolset],
)
```

PydanticAI also supports `CombinedToolset` for explicit grouping and `FilteredToolset` for role-based access — which maps directly to our existing `apply_role_policy()`.

**Recommendation (.85):** Create a single `DevToolset(FunctionToolset)` in `src/owlbear/tools/dev/toolset.py` with file and shell tools. Compose all toolsets via PydanticAI's native `toolsets=` parameter. Use `FilteredToolset` for role policies instead of our custom `apply_role_policy`.

### 3.3 Daemon Loop Pattern — How to Run Continuously

PydanticAI agents are **stateless per-run**. They don't run continuously. The daemon loop must be external.

| Pattern | Description | Complexity | Fit |
|---------|-------------|------------|-----|
| A. Simple `while True` receive-turn-send | Channel.receive() → Agent.run() → Channel.send() | Low | Best for MVP |
| B. asyncio task + signal handlers | Pattern A + SIGINT/SIGTERM graceful shutdown | Medium | Production-ready |
| C. pydantic-graph FSM | Full graph-based state machine | High | Over-engineered for now |

**Key requirements:**

- **Error recovery:** Wrap `agent.run()` in try/except, log errors, keep looping
- **Token refresh:** Copilot tokens expire. Catch auth errors, re-run `create_copilot_client()`, rebuild model. Tenacity retry on 401/403.
- **Graceful shutdown:** `asyncio.Event` for shutdown signal, `signal.signal(SIGINT, ...)` handler
- **Session persistence:** Already handled by `SessionStore` — `agent.turn()` loads/saves history

**Pseudocode for the daemon loop:**

```python
async def run_daemon(settings: OwlBearSettings, channel: ChannelPlugin) -> None:
    hooks = HookRegistry()
    # ... register hooks ...

    model = await create_copilot_model(settings)
    toolsets = build_toolsets(settings)
    session = SessionStore(settings.config_dir / "daemon.jsonl")
    context = ContextManager(Path.cwd())

    agent = OwlBearAgent(model=model, session=session, context=context, hooks=hooks, channel=channel, toolsets=toolsets)

    await hooks.emit(HookEvent.SESSION_START, {})
    shutdown = asyncio.Event()
    # ... install signal handlers ...

    try:
        while not shutdown.is_set():
            user_input = await channel.receive()
            if user_input is None:
                continue
            try:
                response = await agent.turn(user_input)
                await channel.send(response)
            except AuthError:
                model = await create_copilot_model(settings)  # refresh
                agent.update_model(model)
            except Exception as exc:
                await channel.send(f"Error: {exc}")
    finally:
        await hooks.emit(HookEvent.SESSION_END, {})
```

**Recommendation (.85):** Pattern B — simple loop with signal handlers. Implement in `src/owlbear/daemon.py` (~80 LOC). Add `bearclaw run` CLI command that calls it.

### 3.4 Assembly/Bootstrap — Wiring Pattern

| Pattern | Description | LOC | KISS |
|---------|-------------|-----|------|
| A. Procedural `bootstrap()` | Sequential function: settings → auth → model → tools → hooks → channel → agent → loop | ~60 | High |
| B. Builder/fluent API | `OwlBearBuilder().with_model(...).with_channel(...).build()` | ~150 | Medium |
| C. DI container | Pydantic DI or custom registry | ~200+ | Low |
| D. God factory (deepagents anti-pattern) | Single function with 50+ params | 855 | Anti-pattern |

**Prior art comparison:**

- **tool.graphicator:** Simple `create_agent()` factory (94 LOC) — works well
- **pydantic-deepagents:** `create_deep_agent()` at 855 LOC — explicitly identified as anti-pattern in our prior research
- **OpenClaw:** Procedural bootstrap with async resource cleanup

**Recommendation (.90):** Option A — procedural `bootstrap()`. One async function, ~60 LOC. The `bearclaw run` command calls it. No abstraction until we need it (YAGNI).

### 3.5 Channel Integration — Where Does the Loop Live?

Current state: `OwlBearAgent` stores `channel` but never uses it. `turn()` takes a string and returns a string.

| Option | Description | Coupling |
|--------|-------------|----------|
| A. Loop outside agent | Daemon calls `channel.receive()` → `agent.turn()` → `channel.send()` | Low — agent stays pure |
| B. Loop inside agent | `agent.run_forever(channel)` method | Medium |
| C. Channel as dependency | PydanticAI `deps_type` includes channel, tools can send messages | High |

**Recommendation (.90):** Option A — loop lives outside the agent, in `daemon.py`. The agent stays a pure turn-based processor. Channel is only used by the loop. Remove `channel` from `OwlBearAgent.__init__` (or keep it as optional metadata only). This matches PydanticAI's design: agents process runs, not manage I/O.

### 3.6 Architecture: Single Agent vs. Orchestrator

| Approach | Description | Complexity |
|----------|-------------|------------|
| Single agent with all tools | One PydanticAI Agent with `toolsets=[dev, skills, browser]` | Low |
| Orchestrator + sub-agents | Orchestrator dispatches to builder/validator agents via tool delegation | Medium |

Both are viable. PydanticAI supports agent delegation (calling an agent from within a tool). But we already have role policies (`BUILDER_POLICY`, `VALIDATOR_POLICY`) and `FilteredToolset` that can restrict tools per role.

**Recommendation (.85):** Start with a single agent for MVP. Add orchestrator delegation later when we have clear multi-role needs. The existing `apply_role_policy` + `FilteredToolset` pattern handles tool restriction. YAGNI — don't build an orchestrator until we need one.

## 4. Recommendation (.88 confidence)

**Minimal bootstrap approach — 4 deliverables:**

1. **`src/owlbear/tools/dev/toolset.py`** — `DevToolset(FunctionToolset)` with file_read, file_write, file_edit, execute_command, list_directory, kanban_list, kanban_show, kanban_move (~120 LOC)
2. **`src/owlbear/daemon.py`** — `run_daemon()` async function: settings → model → toolsets → agent → channel loop with signal handling and error recovery (~80 LOC)
3. **Update `OwlBearAgent`** — Accept `model: str | OpenAIChatModel`, add `toolsets` parameter forwarded to inner `Agent` (~10 LOC diff)
4. **`bearclaw run` CLI command** — Typer command that loads settings, selects channel (CLI or Slack), calls `run_daemon()` (~30 LOC)

Total estimated effort: ~240 LOC of new code, ~20 LOC of changes to existing code.

**Risks and mitigations:**

- **Copilot token expiry mid-session:** Catch 401 → re-run auth flow → rebuild model. Tenacity for retry.
- **Tool safety:** `execute_command` must pass through `PreToolUse` safety hook (already exists in #19).
- **Token budget:** Long conversations exceed context window. Mitigation: PydanticAI's `HistoryProcessor` or manual session truncation. Defer to a follow-up task.

## 5. Follow-up Tasks

1. **Create DevToolset** — `src/owlbear/tools/dev/toolset.py` with file and shell tools
2. **Test DevToolset** — Unit tests for each tool function
3. **Update OwlBearAgent** — Accept model instance + toolsets parameter
4. **Test OwlBearAgent changes** — Updated unit tests
5. **Create daemon module** — `src/owlbear/daemon.py` with `run_daemon()`
6. **Test daemon module** — Mock channel, mock agent, test loop lifecycle
7. **Create `bearclaw run` command** — Typer command wiring CLI/Slack channel to daemon
8. **Test `bearclaw run` command** — CLI integration test
9. **Create `create_copilot_model()` helper** — Bridge between existing `create_copilot_client()` and PydanticAI's `OpenAIChatModel`
10. **Test Copilot model helper** — Verify OpenAIProvider wrapping
