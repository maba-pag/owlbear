# ErrorJournal Async-Safety Research

> **Owning task:** #541 — Make ErrorJournal async-safe for daemon event loop
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

ErrorJournal (extending JsonlStore) uses blocking file I/O — `path.open('a')`,
`path.read_text()`, and `path.open('w')` for rotation. The daemon calls
`_log_to_journal()` (sync) from async `_recover_from_error()` at 5 call sites,
blocking the event loop. At 10K entries, rotation reads + rewrites the entire
file synchronously. What is the simplest way to make this non-blocking?

### Blocking I/O paths identified

| Method | Operations | Severity |
|--------|-----------|----------|
| `JsonlStore.append()` | `mkdir` + `open("a")` + `write` | Low (single line) |
| `JsonlStore.load()` | `exists()` + `read_text()` + deserialize all | High at 10K entries |
| `ErrorJournal._maybe_rotate()` | `load()` + `open("w")` + rewrite all | High (full read + write) |
| `ErrorJournal.log()` | `append()` + `_maybe_rotate()` | High (combines both) |
| `ErrorJournal.query()` | `load()` | Medium (agent-initiated, less frequent) |

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Python docs — `asyncio.to_thread` | <https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread> | 1.0 — stdlib API for offloading blocking I/O to thread pool |
| aiofiles library (v25.1.0) | <https://github.com/Tinche/aiofiles> | 0.7 — async file API; internally uses `loop.run_in_executor()` |
| OwlBear codebase — existing `to_thread` usage | `src/owlbear/voice/tts.py`, `tools/web_search.py`, `core/context_hook.py` | 1.0 — established internal pattern |

## 3. Analysis

### Option comparison

| Criterion | A: `asyncio.to_thread` at call site (.85) | B: `aiofiles` library (.40) | C: Async wrapper methods on ErrorJournal (.65) |
|-----------|-------|---------|--------|
| New dependencies | 0 (stdlib) | 1 (`aiofiles`) | 0 (stdlib) |
| Diff size | ~15 lines (daemon.py only) | ~100+ lines across JsonlStore + 3 subclasses | ~30 lines (error_journal.py + daemon.py) |
| KISS | High — callers wrap, internals untouched | Low — rewrites base class API | Medium — dual sync/async API |
| YAGNI | High — only fixes the hot path | Low — converts all stores unnecessarily | Medium — adds API surface |
| Codebase precedent | 3 existing uses of `asyncio.to_thread` | 0 uses of `aiofiles` | 0 precedent for dual-API stores |
| Sync callers unaffected | Yes — ErrorJournal stays sync | No — all callers must become async | Yes — sync API preserved |
| Mechanism | `run_in_executor` under the hood | `run_in_executor` under the hood | `run_in_executor` under the hood |

### Key insight

Both `asyncio.to_thread` and `aiofiles` use the same underlying mechanism
(`loop.run_in_executor` with the default thread pool). The difference is
granularity: aiofiles wraps each file operation individually, while
`asyncio.to_thread` wraps an entire function call. For ErrorJournal's
coarse-grained operations (log = serialize + append + maybe rotate), wrapping
the whole method is simpler and equally effective.

### Scope decision

Only ErrorJournal's `log()` is called from the daemon event loop. EventStore
and UsageTracker have the same theoretical issue but are separate tasks (the
ObservabilityHook also calls `store.append()` synchronously from an async
handler). Fixing all JsonlStore subclasses is out of scope for #541.

## 4. Recommendation (.85 confidence)

**Option A: `asyncio.to_thread` at call site** — Make `_log_to_journal` in
`daemon.py` async and wrap `journal.log(...)` in `asyncio.to_thread()`.

Implementation sketch (daemon.py):

```python
async def _log_to_journal(journal, *, error_type, exc, action_taken, attempt, resolved, agent):
    if journal is None:
        return
    try:
        await asyncio.to_thread(
            journal.log, ts=..., error_type=error_type, ...
        )
    except Exception:
        logger.warning("Failed to write error journal entry", exc_info=True)
```

**Risk:** Thread safety — concurrent `to_thread` calls could interleave writes.
Mitigation: ErrorJournal is append-only, and `_log_to_journal` is only called
from `_recover_from_error` which runs sequentially in the daemon loop. No
concurrent writes in practice.

**Not recommended:** Adding `asyncio.Lock` — YAGNI given sequential call pattern.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Wrap ErrorJournal.log() calls in asyncio.to_thread in daemon" --status backlog --priority nice-to-have --tags "resilience,scope:core" --body "Make _log_to_journal async in daemon.py. Wrap journal.log() in asyncio.to_thread(). This is the only async call site. Keep ErrorJournal/JsonlStore sync for CLI/test callers. AC: (1) _log_to_journal is async, (2) journal.log() runs in thread pool, (3) existing tests pass, (4) new test verifies non-blocking behavior. See docs/research/error-journal-async.md §4."
```
