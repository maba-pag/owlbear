---
id: 516
title: 'Test: Notifier dispatch loop integration'
status: backlog
priority: someday
created: 2026-04-01T07:07:25.1531395+02:00
updated: 2026-04-01T22:27:31.0635663+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:test
    - test
depends_on:
    - 515
blocked: true
block_reason: 'Feature deferred per user decision (DR 514): no Slack available'
class: standard
---

## Objective
TDD RED phase: write failing tests for Notifier integration into the orchestrator dispatch loop.
See docs/research/slack-notification-v2.md §3.2 for integration points.

## Acceptance Criteria
- [ ] Test file: `tests/test_notifier_loop_integration.py`
- [ ] Test `run_loop()` calls `notifier.on_dispatch(task_id, agent)` after each successful `dispatch_entry()` call
- [ ] Test `_apply_wave_result()` calls `notifier.on_completion(task_id, agent, success=True)` on success
- [ ] Test `_apply_wave_result()` calls `notifier.on_completion(task_id, agent, success=False)` on failure
- [ ] Test `run_loop(notifier=None)` (default): no notification calls, no AttributeError
- [ ] Test notifier raising an exception does not abort the dispatch loop (error is suppressed)
- [ ] Test `orchestrate()` accepts and passes `notifier` parameter to `run_loop()`
- [ ] All tests use a mock `Notifier` — no real Slack calls
- [ ] All tests fail before implementation (TDD RED)
