---
id: 517
title: Integrate Notifier into dispatch loop (run_loop)
status: backlog
priority: someday
created: 2026-04-01T07:07:35.0254784+02:00
updated: 2026-04-01T22:27:31.7035356+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:build
depends_on:
    - 516
blocked: true
block_reason: 'Feature deferred per user decision (DR 514): no Slack available'
class: standard
---

## Objective
Wire the Notifier protocol into the orchestrator dispatch loop so notifications fire at dispatch, completion, and failure points.
See docs/research/slack-notification-v2.md §3.2 for integration points.

## Acceptance Criteria
- [ ] `run_loop()` signature: add `notifier: Notifier | None = None` parameter
- [ ] `dispatch_entry()` signature: add `notifier: Notifier | None = None` parameter
- [ ] After successful ACP prompt in `dispatch_entry()`: call `await notifier.on_dispatch(entry.task_id, entry.agent)` (guarded by `if notifier is not None`)
- [ ] In `_apply_wave_result()`: call `notifier.on_completion(task_id, agent, success=...)` for success and failure outcomes (guarded)
- [ ] `orchestrate()` accepts `notifier: Notifier | None = None` and passes it to `run_loop()`
- [ ] All notifier calls wrapped in `contextlib.suppress(Exception)` — notification failures never abort dispatch
- [ ] When `notifier is None` (default), zero overhead — no calls, no attribute access
- [ ] Existing tests continue to pass (backward-compatible signature change via default=None)
- [ ] All tests from #516 pass
