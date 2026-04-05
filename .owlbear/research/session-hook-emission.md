# Emit SESSION_START and SESSION_END Hook Events

> **Owning task:** #711 — Emit SESSION_START and SESSION_END hook events at session boundaries
> **Date:** 2026-03-09 **Status:** Complete

## 1. Context and Question

`HookEvent.SESSION_START` and `SESSION_END` exist in the enum (`core/hooks.py`) and
two hooks register for them — `ContextInjectionHook` (SESSION_START) and
`TestVerificationHook` (SESSION_END) — but **no production code ever emits them**.
The downstream `SessionMemoryHook` (#622) also depends on these events.

**Question:** Where should emission happen, what payload data should be passed,
and are there any ordering/safety concerns?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OpenAI Agents SDK — Lifecycle hooks | <https://openai.github.io/openai-agents-python/ref/lifecycle/> | `.90` — `on_agent_start`/`on_agent_end` with context+agent params |
| 2 | PydanticAI — Agent run lifecycle | <https://ai.pydantic.dev/agents/> | `.75` — No built-in session hooks; events are per-request, not per-session |
| 3 | OwlBear codebase — `daemon.py`, `agent.py`, `bootstrap/hooks.py` | Local | `1.0` — Direct inspection of emission sites and hook consumers |

## 3. Analysis

### 3a. Where to emit — placement options

| Option | Location | Scope | Pros | Cons |
|--------|----------|-------|------|------|
| A. `run_daemon()` | `daemon.py` L823+ / finally | Daemon lifecycle | Brackets entire daemon; symmetric with `DAEMON_STARTUP`; works for both autonomous and non-autonomous | Session ≡ daemon run (correct for current design) |
| B. `channel_loop()` | `daemon.py` L428+ | Per-loop | Could support multiple sessions per daemon | Over-complex; no current use case (YAGNI) |
| C. `OwlBearAgent` methods | `agent.py` new methods | Agent-level | Modular, reusable | Adds API surface; agent doesn't own its lifecycle |
| D. Bootstrap | `bootstrap/__init__.py` | Pre-daemon | Early injection | Can't emit SESSION_END (doesn't own teardown) |

**Recommendation (.90 confidence):** **Option A** — emit in `run_daemon()`. Aligns with
KISS and existing `DAEMON_STARTUP` pattern. A session maps 1:1 to a daemon run.

### 3b. Payload design

Inspecting existing hook consumers to derive required payload fields:

| Consumer | Event | Reads from `data` | Required fields |
|----------|-------|--------------------|-----------------|
| `ContextInjectionHook` | SESSION_START | Injects `data["context"]` | Must be `dict` (already checked) |
| `TestVerificationHook` | SESSION_END | Injects `data["test_results"]` | Must be `dict`; docstring expects `{"session_id": str}` |
| `SessionMemoryHook` (#622) | SESSION_START | `data["session_memory"]` | Must be `dict` with `session_id` |
| `SessionMemoryHook` (#622) | SESSION_END | `data["messages"]` | Needs `session_id` + session messages |

**Recommended payloads:**

```python
# SESSION_START
{"session_id": str(agent.session.path), "workspace_root": str(workspace_root)}

# SESSION_END
{"session_id": str(agent.session.path), "messages": agent.session.load()}
```

- `session_id`: Uses `str(agent.session.path)` — consistent with error journal and usage tracker
- `workspace_root`: Needed by future `SessionMemoryHook` for file I/O
- `messages`: Loaded from SessionStore; needed by `SessionMemoryHook` for summarization

### 3c. Placement within `run_daemon()`

```
run_daemon():
  emit DAEMON_STARTUP           # existing (line ~824)
  emit SESSION_START            # NEW — after DAEMON_STARTUP, before loops
  try:
    channel_loop / TaskGroup    # existing
  finally:
    emit SESSION_END            # NEW — in finally, before signal restore
    signal restore / cleanup    # existing
```

**SESSION_START** goes right after `DAEMON_STARTUP` emit. This ensures hooks and
config are fully wired before session hooks fire.

**SESSION_END** goes in the `finally` block before signal handler restoration.
The `finally` guarantees emission even on SIGINT/SIGTERM or channel EOF.

### 3d. Error isolation

Both `ContextInjectionHook` and `TestVerificationHook` already handle their own
errors internally (`try/except` + logging). The `HookRegistry.emit()` itself
wraps each handler in `try/except` (line ~80 of `hooks.py`). No additional error
handling needed at the emission site.

### 3e. Prior art alignment

OpenAI Agents SDK uses `on_agent_start(context, agent)` / `on_agent_end(context,
agent, output)` — symmetric start/end pairs with context objects. Our
`{session_id, workspace_root}` / `{session_id, messages}` payload follows the
same pattern: identity + context at start, identity + results at end.

## 4. Recommendation (.90 confidence)

Add two `await agent.hooks.emit(...)` calls in `daemon.py:run_daemon()`:

1. **SESSION_START** after `DAEMON_STARTUP` with `{session_id, workspace_root}`
2. **SESSION_END** in `finally` block with `{session_id, messages}`

Risk: `agent.session.load()` in the finally block may I/O-fail if session file
was never created (new daemon, no messages). Mitigation: wrap in try/except —
fall back to empty list on any error.

**No changes needed to `hooks.py`, `context_hook.py`, or `test_hook.py`** — they
already register for these events and will start receiving data automatically.

## 5. Follow-up Tasks

The task #711 itself IS the implementation task. It was created with concrete AC.
The research validates the AC is correct and implementable. No additional tasks
needed beyond #711 (already on the board) and its downstream dependency #622.

```powershell
# No new tasks needed — #711 AC is validated as-is
# #622 (SessionMemoryHook) already exists and depends on #711
```

## 6. Testing Strategy

- Mock `agent.hooks.emit` → verify SESSION_START called with expected payload keys
- Mock `agent.hooks.emit` → verify SESSION_END called in finally (even after exception)
- Integration: register ContextInjectionHook → emit SESSION_START → verify `data["context"]` populated
- Integration: register TestVerificationHook → emit SESSION_END → verify `data["test_results"]` populated
- Edge: SESSION_END when session file doesn't exist → graceful fallback to empty messages
