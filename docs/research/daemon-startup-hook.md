# DAEMON_STARTUP Hook Event

> **Owning task:** #624 — Add DAEMON_STARTUP hook event
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #624 proposes adding a `DAEMON_STARTUP` hook event emitted once in
`run_daemon()` after signal handler installation and before the receive loop.
This would let hooks perform one-time initialization (health checks, boot
messages, metric zeroing) at daemon start.

**Key questions:** Is a startup hook the right pattern? Where exactly should it
fire? Does `run_daemon()` need a new parameter or can it use `agent.hooks`?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | FastAPI lifespan events | <https://fastapi.tiangolo.com/advanced/events/> | .90 |
| 2 | Starlette lifespan | <https://starlette.dev/lifespan/> | .85 |
| 3 | Django signals (request_started) | <https://docs.djangoproject.com/en/5.0/ref/signals/> | .70 |
| 4 | OwlBear `hooks.py` | `src/owlbear/core/hooks.py` | 1.0 |
| 5 | OwlBear `daemon.py` | `src/owlbear/daemon.py` | 1.0 |
| 6 | OwlBear `bootstrap.py` | `src/owlbear/bootstrap.py` | .95 |

## 3. Analysis

### 3.1 Prior art patterns

| Framework | Mechanism | When fired | Payload | Async? |
|-----------|-----------|-----------|---------|--------|
| FastAPI (deprecated `on_event`) | `@app.on_event("startup")` | Before first request | None | Yes |
| FastAPI (lifespan) | `async with lifespan(app)` | Before first request (pre-yield) | App instance | Yes |
| Starlette | `lifespan` context manager | Before serving starts | App, yields state dict | Yes |
| Django | `request_started` signal | Per-request (no startup signal) | Handler class, environ | Sync |

**Consensus:** All modern Python server frameworks fire a startup event once,
after infrastructure setup completes but before the main serve loop begins.
FastAPI/Starlette both evolved from simple event hooks to context-manager
lifespan — but we only need the simple startup event, not a full lifespan
(YAGNI). Django lacks a process-level startup signal, relying on `AppConfig.ready()` instead.

### 3.2 OwlBear current state

| Aspect | Current status |
|--------|---------------|
| `HookEvent` enum | 9 events, no daemon-lifecycle events |
| `daemon.py` hooks usage | **None** — no HookRegistry import or emit calls |
| Hook access in `run_daemon` | Available via `agent.hooks` (OwlBearAgent.hooks) |
| `BootstrapResult.hooks` | Same registry instance, also available in CLI caller |
| Signal setup location | Lines 558–560 in `run_daemon()` |
| Loop entry point | Line 563 (`logger.info("Daemon started...")`) |

### 3.3 Implementation options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Emit via `agent.hooks` | `await agent.hooks.emit(DAEMON_STARTUP, ...)` inside `run_daemon` | Zero new params, uses existing wiring | Couples daemon to agent internals |
| B. New `hooks` param on `run_daemon` | Pass `HookRegistry` explicitly | Clean separation, daemon doesn't reach into agent | Changes `run_daemon` signature |
| C. Emit in CLI `_run()` | Fire in `bearclaw/cli.py` after bootstrap, before `run_daemon` | No daemon changes | Violates SRP — daemon lifecycle belongs in daemon |

### 3.4 Recommendation: Option A (.85 confidence)

Use `agent.hooks` directly. Rationale:

- `run_daemon` already depends on `OwlBearAgent` which publicly exposes `.hooks`
- Adding a parameter for a single emit call violates YAGNI — the daemon already
  has 7 keyword params (at `PLR0913` suppression)
- Option B is the right move if/when we add `DAEMON_SHUTDOWN` too, but that's a
  separate task (YAGNI for now)
- Option C breaks SRP

### 3.5 Fire point

```
run_daemon():
    shutdown_event = asyncio.Event()
    ...
    signal.signal(SIGINT, handler)     # line 559
    signal.signal(SIGTERM, handler)    # line 560
    try:
        logger.info("Daemon started")  # line 563
        # >>> HERE: await agent.hooks.emit(HookEvent.DAEMON_STARTUP, {...})
        if settings.autonomous_mode:
            ...  # TaskGroup with channel_loop + poll_loop
        else:
            await channel_loop(...)
```

**After** signal handlers, **before** any loop starts. This matches
FastAPI/Starlette semantics: infrastructure ready, not yet serving.

### 3.6 Payload

Minimal payload following existing conventions (`{"prompt": ...}`, `{"tool_name": ...}`):

```python
{"channel": channel.name, "config_dir": str(config_dir)}
```

Channel name and config dir are the most useful context for startup hooks.

### 3.7 Testing strategy

Existing `test_daemon.py` tests mock `channel` and `agent`. A new test:

1. Register a mock handler on `agent.hooks` for `DAEMON_STARTUP`
2. Run `run_daemon()` with a channel that returns `None` immediately (EOF)
3. Assert handler was called exactly once with expected payload
4. Verify it fires before the first `channel.receive()` call (ordering)

This is straightforward — no new test infrastructure needed.

## 4. Recommendation (.85 confidence)

Add `DAEMON_STARTUP = "daemon_startup"` to `HookEvent`, emit it in
`run_daemon()` via `agent.hooks` after signal setup. Minimal change: ~3 lines
in `hooks.py`, ~2 lines in `daemon.py`, ~15 lines in `test_daemon.py`.

Risk: Low. Hook emission is fire-and-forget (errors swallowed). No new
dependencies. No signature changes.

## 5. Follow-up Tasks

See kanban commands below.

## 6. Refined Acceptance Criteria

- [ ] `DAEMON_STARTUP = "daemon_startup"` added to `HookEvent` enum
- [ ] `run_daemon()` imports `HookEvent` and emits `DAEMON_STARTUP` via
      `agent.hooks.emit()` after signal setup, before loop entry
- [ ] Payload contains `{"channel": channel.name, "config_dir": str(config_dir)}`
- [ ] `test_hooks.py`: `test_has_daemon_startup` asserts enum value
- [ ] `test_daemon.py`: new test verifies `DAEMON_STARTUP` emitted exactly once
      with correct payload when daemon starts and immediately shuts down
- [ ] ruff clean, all existing tests pass
