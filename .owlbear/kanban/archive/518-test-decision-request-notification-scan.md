---
id: 518
title: 'Test: Decision-request notification scan'
status: archived
priority: medium
created: 2026-04-01 07:07:44.706718+02:00
updated: 2026-04-04 07:10:37.322693+02:00
started: 2026-04-04 07:09:47.054252+02:00
completed: 2026-04-04 07:09:47.054252+02:00
tags:
- phase-3
- scope:orchestrator
- scope:notifications
- type:test
- test
depends_on:
- 515
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for per-cycle blocked-task detection that triggers decision-request notifications.
See docs/research/slack-notification-v2.md §3.2 for the blocked-task scan pattern.

## Acceptance Criteria
- [ ] Test file: `tests/test_decision_notification_scan.py`
- [ ] Test that `run_loop()` calls `notifier.on_decision_request(task_id, reason)` for blocked tasks returned by `read_board()`
- [ ] Test duplicate suppression: a task notified as blocked in cycle N is NOT re-notified in cycle N+1 if still blocked
- [ ] Test unblocked removal: if a previously-blocked task is no longer in the blocked set, it is removed from the notified set (can be re-notified if blocked again)
- [ ] Test `notifier=None`: blocked-task scan is skipped entirely (no `read_board` call for blocked tasks)
- [ ] Test notifier error during scan: exception is suppressed, loop continues
- [ ] All tests use mock `Notifier` and mock `read_board` — no real board or Slack calls
- [ ] All tests fail before implementation (TDD RED)
