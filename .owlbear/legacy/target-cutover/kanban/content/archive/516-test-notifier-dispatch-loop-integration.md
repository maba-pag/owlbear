---
id: 516
title: 'Test: Notifier dispatch loop integration'
status: archived
priority: medium
created: 2026-04-01 07:07:25.153140+02:00
updated: 2026-04-04 07:10:33.609818+02:00
started: 2026-04-04 07:09:44.684714+02:00
completed: 2026-04-04 07:09:44.684714+02:00
tags:
- phase-3
- scope:orchestrator
- type:test
- test
depends_on:
- 515
class: standard
archival_reason: completed
archival_refs: []
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
