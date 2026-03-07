---
id: 624
title: Add DAEMON_STARTUP hook event
status: archived
priority: important
created: 2026-03-07T05:21:14.0380965+01:00
updated: 2026-03-07T18:08:25.1312301+01:00
started: 2026-03-07T06:30:14.2347675+01:00
completed: 2026-03-07T18:08:25.1312301+01:00
tags:
    - scope:core
    - hooks
class: standard
---

Add `DAEMON_STARTUP` to `HookEvent` enum and emit it in `run_daemon()` via `agent.hooks` after signal handler installation and before the receive/poll loop starts. This enables bootstrap hooks (boot messages, health checks, metric zeroing) to run at startup.

See `docs/daemon-startup-hook-research.md` for full analysis.

## Acceptance Criteria

- [ ] `DAEMON_STARTUP = 'daemon_startup'` member added to `HookEvent` in `src/owlbear/core/hooks.py` (after `QUESTION_PENDING`)
- [ ] `run_daemon()` in `src/owlbear/daemon.py` imports `HookEvent` from `owlbear.core.hooks`
- [ ] `await agent.hooks.emit(HookEvent.DAEMON_STARTUP, {'channel': channel.name, 'config_dir': str(config_dir)})` called **after** signal handler installation and **before** `logger.info('Daemon started ...')`
- [ ] Payload is exactly `{'channel': channel.name, 'config_dir': str(config_dir)}`  no settings, no autonomous_mode (YAGNI)
- [ ] `tests/test_hooks.py`: `test_has_daemon_startup` asserts `HookEvent.DAEMON_STARTUP.value == 'daemon_startup'` (follows existing pattern at lines 15-39)
- [ ] `tests/test_daemon.py`: new test in `TestRunDaemon` class verifies `agent.hooks.emit` is `await`-ed exactly once with `HookEvent.DAEMON_STARTUP` and payload `{'channel': 'mock', 'config_dir': str(tmp_path)}`
- [ ] `tests/test_daemon.py`: the emit call occurs before the first `channel.receive()` call (assert `mock_agent.hooks.emit` called before `mock_agent.turn`)
- [ ] `uv run ruff check src/owlbear/core/hooks.py src/owlbear/daemon.py tests/test_hooks.py tests/test_daemon.py` clean
- [ ] All existing tests pass (`uv run pytest tests/ -q --tb=short`)

## Architecture Notes

- Follow Option A from research: access hooks via `agent.hooks`  no new `run_daemon` parameters
- Existing pattern: `OwlBearAgent.turn()` emits `ON_MESSAGE` via `self.hooks.emit()` (agent.py L123)  same pattern, different call site
- `MockChannel.name` returns `'mock'`  tests need no mock changes
- `AsyncMock()` auto-creates `mock_agent.hooks.emit` as `AsyncMock`  no explicit mock setup needed
- Fire point: `daemon.py` between `prev_sigterm = signal.signal(...)` and `logger.info('Daemon started ...')` inside the `try` block
