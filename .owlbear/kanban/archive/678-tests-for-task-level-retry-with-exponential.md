---
id: 678
title: Tests for task-level retry with exponential backoff (#625)
status: archived
priority: important
created: 2026-03-08T13:50:08.4197983+01:00
updated: 2026-03-09T16:15:34.5874852+01:00
started: 2026-03-08T16:42:55.9976882+01:00
completed: 2026-03-09T16:15:34.5874852+01:00
tags:
    - test
    - scope:core
    - agent
depends_on:
    - 512
    - 614
class: standard
---

TDD test task for #625. Write tests before implementation.

AC:
- [ ] TestRetryEntry: dataclass fields (task_id, attempt, next_due, last_error), default values
- [ ] TestRetryConfig: task_retry_max_attempts (default 5, rejects <=0), task_retry_backoff_base (default 10.0, rejects <=0), task_retry_backoff_max (default 320.0, rejects <=0)
- [ ] TestReconcileSchedulesRetry: failed task creates RetryEntry in state.retries with correct next_due and attempt=1; task stays in claimed
- [ ] TestReconcileIncrementsRetry: second failure increments attempt and recalculates next_due with higher delay
- [ ] TestBackoffFormula: delay = min(base * 2**(attempt-1), max) for attempts 1..6
- [ ] TestRetryExhaustion: attempt > max_attempts triggers kanban_edit(block=...) and removes from retries+claimed
- [ ] TestRetryDispatch: poll_tick re-dispatches retry entries where next_due <= now; removes from retries; adds to running
- [ ] TestRetryNotDueYet: poll_tick skips retry entries where next_due > now
- [ ] TestRetryDispatchUsesWip: re-dispatch loads WIP context into prompt
- [ ] TestExistingTestsUnbroken: all pre-existing test_poll_dispatch tests pass
- [ ] ruff clean
