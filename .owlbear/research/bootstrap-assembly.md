# Bootstrap/Assembly Layer — Nanobot Wiring Patterns for PydanticAI

> **Owning task:** #263 — Research: Bootstrap/assembly layer
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear has 50 individually tested modules (1608 tests pass) but no bootstrap layer wires them into a running system. `bearclaw chat` manually wires ~40% of components; `bearclaw run` wires ~10%. Nine interactions remain unwired (see §3.2). This research maps nanobot's proven startup wiring to PydanticAI and designs a concrete `bootstrap()` function.

**Builds on:** [daemon-bootstrap.md](daemon-bootstrap.md) (model bridge .90, procedural bootstrap .90, loop-outside-agent .90) and [agent-patterns.md](agent-patterns.md) (progressive skill loading, canonical Message, two-layer memory, hook-based safety).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Nanobot v0.1.4.post2 (cloned) | <https://github.com/HKUDS/nanobot> | .95 | Full startup wiring: `gateway` command → MessageBus → AgentLoop → ChannelManager → tools |
| Nanobot ContextBuilder | `nanobot/agent/context.py` | .90 | Bootstrap files + memory + skills → system prompt assembly |
| Nanobot MemoryStore | `nanobot/agent/memory.py` | .85 | Two-layer memory: MEMORY.md + HISTORY.md, LLM consolidation via tool call |
| Nanobot SessionManager | `nanobot/session/manager.py` | .80 | JSONL sessions with `last_consolidated` pointer, append-only for cache efficiency |
| Nanobot ChannelManager | `nanobot/channels/manager.py` | .75 | Config-driven channel init, outbound dispatch by channel name |
| PydanticAI docs — Toolsets | <https://ai.pydantic.dev/toolsets/> | .90 | `FunctionToolset`, `CombinedToolset`, `FilteredToolset`, `WrapperToolset` |
| daemon-bootstrap.md | local | .95 | Model bridge, procedural bootstrap, loop-outside-agent recommendations |
| agent-patterns.md | local | .90 | Progressive loading, canonical Message, builder/validator, hook safety |
| OwlBear architecture.md §6 | local | .95 | Assembly gap inventory: 9 unwired interactions |

## 3. Analysis

### 3.1 Nanobot Startup Sequence (from `gateway` command)

Nanobot's production entry point wires 8 components in this order:

```
1. Config           → load_config()
2. MessageBus       → MessageBus()                    # two async queues
3. LLM Provider     → _make_provider(config)          # LiteLLM wrapper
4. SessionManager   → SessionManager(workspace)       # JSONL + cache
5. CronService      → CronService(store_path)         # scheduled jobs
6. AgentLoop        → AgentLoop(bus, provider, ...)   # internally creates:
                       ├─ ContextBuilder(workspace)    # system prompt assembly
                       ├─ ToolRegistry + 10 tools      # filesystem, shell, web, message, spawn
                       └─ SubagentManager              # restricted tool sets per subagent
7. ChannelManager   → ChannelManager(config, bus)     # lazy-import channels, outbound dispatch
8. Start            → asyncio.gather(agent.run(), channels.start_all())
```

**Key insight:** nanobot's AgentLoop owns the tool iteration (call LLM → execute tools → loop). PydanticAI's `Agent.run()` does this internally. Our bootstrap only needs the **outer** loop (receive → turn → send) and the **component wiring**.

### 3.2 Component Mapping: Nanobot → OwlBear

| Nanobot Component | OwlBear Equivalent | Status | Adaptation |
|---|---|---|---|
| AgentLoop (490 LOC) | OwlBearAgent + daemon.py | Exists, ~10% wired | **NOT adoptable** — PydanticAI manages tool loop |
| MessageBus (40 LOC) | ChannelPlugin.receive()/send() | Exists | **DEFER** — adopt for multi-channel later |
| InboundMessage / OutboundMessage | (no equivalent) | Missing | **DEFER** — current string I/O suffices for single-channel |
| ChannelManager (246 LOC) | Manual if/else in CLI | Partial | **ADOPT** — config-driven registry, ~50 LOC |
| BaseChannel ABC | ChannelPlugin Protocol | Complete | Already equivalent |
| ContextBuilder (150 LOC) | ContextManager (55 LOC) | Exists | **ENHANCE** — add runtime context (timestamp, channel) |
| MemoryStore consolidation | Not built | Missing | **ADOPT** — LLM-driven MEMORY.md + HISTORY.md |
| SessionManager (+consolidation ptr) | SessionStore (JSONL only) | Partial | **ENHANCE** — add `last_consolidated` pointer |
| ToolRegistry + Tool ABC | PydanticAI FunctionToolset | Complete | **NOT needed** — FunctionToolset replaces entirely |
| _make_provider() | create_copilot_client() | Orphaned | **BRIDGE** — add `create_copilot_model()` helper |
| SubagentManager | AgentRegistry + DelegationToolset | Built, unwired | **WIRE** in bootstrap |
| 10 built-in tools | 7 toolsets (File, Terminal, Ask, Skills, Git, GitHub, Browser) | Built, partially wired | **WIRE** all in bootstrap |
| HookedToolset wrapper | HookedToolset (50 LOC) | Built, never used | **WIRE** in bootstrap |
| 6 hook implementations | 6 hooks (Guard, Lint, Obs, Notify, Test, Subagent) | Built, 1/6 wired | **WIRE** all in bootstrap |
| MCP servers | MCPServerRegistry + 3 factories | Built, never started | **WIRE** lifecycle in bootstrap |

### 3.3 Bootstrap Function Design

Following nanobot's proven wiring order, adapted for PydanticAI:

```python
async def bootstrap(
    settings: OwlBearSettings,
    *,
    channel_name: str = "cli",
    workspace_root: Path | None = None,
) -> BootstrapResult:
    """Wire all OwlBear modules into a running system."""
    workspace = workspace_root or Path.cwd()

    # 1. Auth → Model (create_copilot_model helper)
    model = await create_copilot_model(settings)

    # 2. Hooks (all 6 + safety guard)
    hooks = build_hooks(settings)

    # 3. Session + Context + Usage
    session = SessionStore(settings.config_dir / "sessions" / f"daemon-{channel_name}.jsonl")
    context = ContextManager(workspace)
    tracker = UsageTracker(settings.usage_path)

    # 4. Channel
    channel = create_channel(settings, channel_name)

    # 5. Toolsets (all 7 + delegation)
    toolsets = build_toolsets(settings, workspace, hooks, channel)

    # 6. Wrap toolsets with HookedToolset for PRE/POST_TOOL_USE
    hooked = [HookedToolset(wrapped=ts, hooks=hooks) for ts in toolsets]

    # 7. MCP servers (optional)
    mcp_registry = build_mcp_registry(settings) if settings.mcp_servers else None

    # 8. Agent registry (scan .md definitions)
    agent_registry = build_agent_registry(settings, toolsets, mcp_registry)

    # 9. Build agent
    agent = OwlBearAgent(model=model, session=session, context=context, hooks=hooks, tracker=tracker, toolsets=hooked)
    agent._deps.agent_registry = agent_registry

    return BootstrapResult(agent=agent, channel=channel, mcp_registry=mcp_registry, hooks=hooks)
```

**Estimated size:** `bootstrap()` ~40 LOC, helper functions ~80 LOC, total module ~150 LOC.

### 3.4 Decision: MessageBus Adoption

| Criterion | MessageBus | Current ChannelPlugin |
|---|---|---|
| Single-channel (MVP) | Unnecessary overhead | Sufficient |
| Multi-channel (future) | Required | Cannot multiplex |
| Progress messages | Natural (outbound queue) | Requires callback wiring |
| Complexity | +40 LOC, 2 async queues | 0 LOC (already works) |

**Decision (.85): NO for bootstrap MVP, YES as follow-up.** Current `channel.receive()` → `agent.turn()` → `channel.send()` handles single-channel. MessageBus becomes necessary when running CLI + Slack simultaneously. Create as a separate task.

### 3.5 Decision: Memory Consolidation

Nanobot's pattern: append-only messages → periodic LLM tool call → MEMORY.md (long-term facts, always in context) + HISTORY.md (grep-searchable log). The `last_consolidated` pointer tracks progress.

| Criterion | Nanobot Pattern | OwlBear Current |
|---|---|---|
| Long-term memory | MEMORY.md (~500 tokens, always loaded) | ContextManager loads `context.md` (static) |
| Session history | Append-only JSONL + pointer | SessionStore (append-only JSONL, no pointer) |
| Consolidation | LLM summarizes via tool call | Not implemented |
| Token efficiency | Only unconsolidated messages sent to LLM | Full history grows unbounded |

**Decision (.80): YES, adopt — but as a follow-up task, not blocking bootstrap.** The consolidation pattern directly solves the context window exhaustion problem for long-running daemon sessions. Implementation: add `last_consolidated` to SessionStore, create a `MemoryConsolidator` class that uses PydanticAI `Agent.run()` with a specialized prompt.

### 3.6 Token Refresh in Long-Running Daemon

Nanobot doesn't face this (LiteLLM handles auth). OwlBear's approach:

```python
# In daemon loop — catch auth errors, rebuild model
try:
    response = await agent.turn(message)
except Exception as exc:
    if _is_auth_error(exc):
        model = await create_copilot_model(settings)
        agent.update_model(model)  # New method on OwlBearAgent
        response = await agent.turn(message)  # Retry once
    else:
        raise
```

**Requires:** `OwlBearAgent.update_model()` method (~5 LOC) that rebuilds the inner PydanticAI `Agent` with a new model instance.

## 4. Recommendation (.88 confidence)

**Procedural `bootstrap()` in `src/owlbear/bootstrap.py`** — one async function, ~150 LOC total (with helpers). Wires all 9 unwired interactions. The `bearclaw run` and `bearclaw chat` commands both call it, eliminating the current 40%/10% wiring gap.

**Key changes from prior research:** Prior daemon-bootstrap-research recommended ~60 LOC bootstrap + a new `DevToolset`. We already have `FileToolset` + `TerminalToolset` which cover the same ground — no new `DevToolset` needed. The bootstrap is larger (~150 LOC) because it wires hooks, MCP, agent registry, and browser that weren't scoped before.

**Risks:** (1) Browser setup/teardown lifecycle adds complexity — mitigate with `BootstrapResult` holding cleanup callbacks. (2) MCP server startup failures must not block daemon — mitigate with try/except per server (already in MCPServerRegistry). (3) Token refresh requires rebuilding PydanticAI Agent — mitigate with `update_model()` method.

## 5. Follow-up Tasks

See §6 for `kanban-md create` commands. Summary:

1. `create_copilot_model()` bridge function (prerequisite)
2. `OwlBearAgent.update_model()` + accept model instances (prerequisite)
3. `bootstrap()` module — the main deliverable
4. `ChannelManager` — config-driven channel creation
5. Update `bearclaw run` to call `bootstrap()`
6. Update `bearclaw chat` to call `bootstrap()`
7. Token refresh handler in daemon loop
8. Memory consolidation module (nanobot pattern)
9. Integration test: full bootstrap smoke test
