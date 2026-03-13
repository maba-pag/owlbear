# BoardContextProvider Implementation Research

> **Owning task:** #770 — Implement BoardContextProvider with TTL caching
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

Task #770 requires a `BoardContextProvider` service that runs
`kanban-md list --compact --status in-progress --status review --status todo`,
caches the result with configurable TTL (default 60s), and degrades gracefully
on subprocess failure. The parent research (docs/research/compact-board-context.md)
chose Option C. This doc covers the implementation approach.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| cachetools TTLCache docs | <https://cachetools.readthedocs.io/en/latest/> | .75 |
| Python `time.monotonic()` docs | <https://docs.python.org/3/library/time.html#time.monotonic> | .90 |
| OwlBear `ContextInjectionHook` | `src/owlbear/core/context_hook.py` | .95 |
| PydanticAI runtime instructions | <https://ai.pydantic.dev/agents/#instructions> | .85 |
| Mission Control generate-context | <https://github.com/MeisnerDan/mission-control> | .70 |

## 3. Analysis

### 3.1 Caching Strategy: stdlib vs cachetools

| Criterion | stdlib `time.monotonic()` | `cachetools.TTLCache` |
|-----------|--------------------------|----------------------|
| New dependency? | No | Yes (not a direct dep) |
| LOC needed | ~5 lines | ~3 lines |
| Complexity | Minimal — 2 attrs | MutableMapping with eviction |
| Fit for single value | Perfect | Overkill (designed for many keys) |
| Thread-safety | Manual (not needed — asyncio) | Manual |
| KISS/YAGNI | **High** | Low — adds dep for 1 cached value |

**Verdict (.85):** Use stdlib `time.monotonic()` with `_cached_value` /
`_cached_at` attributes. Adding `cachetools` as a direct dependency for a
single cached string violates YAGNI.

### 3.2 File Placement

The service belongs in `src/owlbear/core/board_context.py` alongside
`context_hook.py` (both deal with context injection for agents). It's a core
service consumed by `agent.turn()` (wired in #771).

### 3.3 Interface Design

```
class BoardContextProvider:
    __init__(kanban_cmd, ttl, timer)  # configurable command, TTL, timer
    async get_context() -> str        # returns cached or refreshed output
    invalidate() -> None              # force refresh on next call
```

Follow the `ContextInjectionHook._run_kanban()` pattern for subprocess execution:
`asyncio.create_subprocess_exec` with stdout/stderr capture, graceful degradation
(return empty string on `OSError` or non-zero exit), log warnings.

### 3.4 Key Design Decisions

1. **Async `get_context()`** — subprocess exec is I/O, must be async.
2. **`timer` parameter** — injectable for testing (avoids `time.sleep` in tests).
3. **Empty string on failure** — matches `ContextInjectionHook` degradation pattern.
   Caller can concatenate without null checks.
4. **No header/formatting** — provider returns raw `kanban-md` output. Formatting
   is the consumer's concern (#771).

## 4. Recommendation (.85 confidence)

Implement `BoardContextProvider` in `src/owlbear/core/board_context.py` using:

- `time.monotonic()` for TTL tracking (no new dependency)
- `asyncio.create_subprocess_exec` for subprocess (existing pattern)
- Graceful degradation: return `""` on failure, log warning
- ~40 LOC total

### Testing Strategy

| Category | Tests |
|----------|-------|
| Happy path | `get_context()` returns subprocess output |
| Caching | Second call within TTL returns cached value (no subprocess) |
| TTL expiry | After TTL, `get_context()` re-runs subprocess |
| Graceful degradation | `OSError` → returns `""`, logs warning |
| Non-zero exit | rc≠0 → returns `""`, logs warning |
| `invalidate()` | Next `get_context()` re-runs subprocess |
| Custom timer | Injectable timer for deterministic tests |
| Custom command | Configurable `kanban_cmd` parameter |

Mock `asyncio.create_subprocess_exec` — no real subprocess in unit tests.

## 5. Follow-up Tasks

Task #770 already exists. No additional tasks needed — #771 (wiring) and #772
(hook fix) were already created by the parent research. The architect gates
these before `todo`.
