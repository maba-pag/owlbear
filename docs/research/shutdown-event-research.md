# Replace module-level _shutdown flag with asyncio.Event

> **Owning task:** #509 — Replace module-level _shutdown flag with asyncio.Event
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`daemon.py` uses a module-global `_shutdown: bool` toggled by a `signal.signal()` handler. Two `global _shutdown` statements (PLW0603 suppressed). The signal handler mutating asyncio-visible state is technically unsafe without `loop.call_soon_threadsafe`. How should we refactor this?

**Constraint:** `loop.add_signal_handler()` is Unix-only — our daemon must run on Windows.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python docs — `loop.add_signal_handler` | https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler | Confirms Unix-only; shows idiomatic asyncio signal pattern |
| 2 | Python docs — `signal.signal` | https://docs.python.org/3/library/signal.html#signal.signal | Signal handler execution semantics; Windows limitations |
| 3 | Python docs — `loop.call_soon_threadsafe` | https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_soon_threadsafe | "safe to be called from a reentrant context or signal handler" |
| 4 | Python docs — `asyncio.Event` | https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event | "Not thread-safe" caveat; `set()`/`is_set()`/`wait()` API |

## 3. Analysis

### Option comparison

| Criterion | A: `asyncio.Event` + `call_soon_threadsafe` (.90) | B: `loop.add_signal_handler` (.30) | C: Status quo (.20) |
|---|---|---|---|
| Cross-platform | Yes (signal.signal + threadsafe callback) | No (Unix only) | Yes |
| Global state | None — event is local to `run_daemon()` | None — uses loop API | Module-level `_shutdown` + `global` |
| Thread safety | Safe — `call_soon_threadsafe` schedules `set()` on loop thread | Safe — loop handles it | Unsafe — signal handler writes bool without loop notification |
| Ruff compliance | No PLW0603 suppressions needed | No PLW0603 | Two PLW0603 noqa comments |
| Complexity | ~20 LOC changed | ~10 LOC but breaks Windows | N/A |
| Future: `await event.wait()` | Enables replacing polling loop with await | Same | Not possible |

### How it works

1. `run_daemon()` creates `shutdown_event = asyncio.Event()` and gets `loop = asyncio.get_running_loop()`
2. Signal handler closure captures `loop` and `shutdown_event`, calls `loop.call_soon_threadsafe(shutdown_event.set)`
3. Loop condition becomes `while not shutdown_event.is_set():`
4. Post-receive recheck becomes `if shutdown_event.is_set(): break`
5. `_make_signal_handler()` factory takes `loop` and `event` as parameters instead of using `global`
6. Module-level `_shutdown` variable and both `global` statements are removed

### Thread-safety proof

`asyncio.Event` is "not thread-safe" — it must not be mutated from multiple threads simultaneously. But `call_soon_threadsafe` schedules `event.set()` to execute **on the event loop thread**, never from the signal handler thread directly. The event is only ever read/written from the loop thread. Safe.

## 4. Recommendation (.90 confidence)

**Option A: `asyncio.Event` + `call_soon_threadsafe`.** Simplest correct approach. Cross-platform. Eliminates all module-level mutable state. Enables future `await event.wait()` upgrade (out of scope). KISS-aligned — ~20 LOC diff.

**Risk:** `loop.call_soon_threadsafe` raises `RuntimeError` if the loop is closed. Mitigation: wrap in try/except in the signal handler (the loop closing means shutdown is already happening).

## 5. Follow-up Tasks

No new tasks needed — #509 covers the full implementation. Updated AC below.

### Refined AC for #509

1. No module-level `_shutdown` variable exists in `daemon.py`
2. No `global` statements in `daemon.py` (no PLW0603 noqa comments)
3. `run_daemon()` creates an `asyncio.Event` for shutdown signaling
4. Signal handler uses `loop.call_soon_threadsafe(event.set)` — not bare `event.set()`
5. `while not _shutdown:` replaced with `while not shutdown_event.is_set():`
6. Signal handler still uses `signal.signal()` (not `loop.add_signal_handler()`) for cross-platform support
7. Existing tests updated and passing; ruff clean
