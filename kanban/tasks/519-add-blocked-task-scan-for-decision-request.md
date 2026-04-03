---
id: 519
title: Add blocked-task scan for decision-request notifications
status: backlog
priority: someday
created: 2026-04-01T07:07:54.3480033+02:00
updated: 2026-04-01T22:27:32.9924029+02:00
tags:
    - phase-3
    - scope:orchestrator
    - scope:notifications
    - type:build
depends_on:
    - 518
    - 517
blocked: true
block_reason: 'Feature deferred per user decision (DR 514): no Slack available'
class: standard
---

## Objective
Add per-cycle blocked-task detection to `run_loop()` so the Notifier alerts users when tasks need decisions.
See docs/research/slack-notification-v2.md §3.2 for the blocked-task scan pattern.

## Acceptance Criteria
- [ ] Each cycle in `run_loop()`, after `read_board()`: identify tasks with blocked status from the board data
- [ ] Add `notified_blocked: set[int]` field to `LoopState` for duplicate suppression
- [ ] Call `await notifier.on_decision_request(task_id, block_reason)` for each newly blocked task (not in `notified_blocked`)
- [ ] Add newly-notified task IDs to `notified_blocked`
- [ ] Remove task IDs from `notified_blocked` when they are no longer in the blocked set (allows re-notification if blocked again later)
- [ ] When `notifier is None`, skip the entire scan (no blocked-task filtering, no set operations)
- [ ] All notifier calls wrapped in `contextlib.suppress(Exception)` — scan errors never abort the loop
- [ ] All tests from #518 pass
