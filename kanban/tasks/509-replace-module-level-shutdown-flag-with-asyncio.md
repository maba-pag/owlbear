---
id: 509
title: Replace module-level _shutdown flag with asyncio.Event
status: archived
priority: important
created: 2026-03-04T07:38:20.7731329+01:00
updated: 2026-03-07T18:07:59.4981393+01:00
started: 2026-03-06T20:59:36.3486253+01:00
completed: 2026-03-07T18:07:59.4981393+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

## Research Complete
See [docs/research/shutdown-event.md](docs/research/shutdown-event.md) for full analysis.

### Summary
Replace module-level `_shutdown: bool` + `global` statements with `asyncio.Event` created locally in `run_daemon()`. Signal handler calls `loop.call_soon_threadsafe(shutdown_event.set)` -- documented as safe from signal handlers, works cross-platform (keeps `signal.signal()`, does NOT use Unix-only `loop.add_signal_handler()`). Confidence: .90.

### Acceptance Criteria

1. No module-level `_shutdown` variable exists in `daemon.py`
2. No `global` statements in `daemon.py`; zero PLW0603 noqa comments remain
3. `run_daemon()` creates `shutdown_event = asyncio.Event()` and captures `loop = asyncio.get_running_loop()`
4. `_make_signal_handler(loop, shutdown_event)` accepts loop and event as parameters -- no global state access
5. Signal handler body calls `loop.call_soon_threadsafe(shutdown_event.set)` wrapped in `try/except RuntimeError` (loop may be closed during shutdown race)
6. Main loop condition: `while not shutdown_event.is_set():` ; post-receive recheck: `if shutdown_event.is_set(): break`
7. Signal registration still uses `signal.signal()` (cross-platform) -- NOT `loop.add_signal_handler()`
8. `TestSignalHandler.test_signal_handler_sets_shutdown_flag` adapted to verify event-based shutdown (simulated signal triggers `call_soon_threadsafe` path; loop exits cleanly)
9. `TestSignalHandler.test_signal_handlers_restored_after_run` still passes (assertions unchanged)
10. All existing daemon tests pass; `ruff check` clean on `src/owlbear/daemon.py` and `tests/test_daemon.py`

### Implementation Notes
- `_make_signal_handler()` becomes `_make_signal_handler(loop, event)` -- closure captures params, no global
- Wrap `call_soon_threadsafe` in `try/except RuntimeError` in handler (loop may be closed during teardown)
- ~20 LOC diff, no new dependencies
- Follow existing daemon.py patterns: factory function returns closure, `try/finally` for signal restore
