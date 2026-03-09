---
id: 679
title: Tests for task-level retry (#625)
status: archived
priority: important
created: 2026-03-08T13:50:14.3826437+01:00
updated: 2026-03-09T19:31:17.857581+01:00
started: 2026-03-08T16:08:41.9406308+01:00
completed: 2026-03-09T19:31:17.857581+01:00
tags:
    - test
    - scope:core
    - agent
depends_on:
    - 512
    - 614
class: standard
---

TDD test task for #625 (task-level retry with exponential backoff). Write tests in `tests/test_poll_dispatch.py` before implementation.

AC:

- [ ] `TestRetryEntry`: dataclass has fields `task_id: str`, `attempt: int`, `next_due: datetime`, `last_error: str`; verify defaults and construction
- [ ] `TestRetryConfig`: `task_retry_max_attempts` default 5, rejects <=0; `task_retry_backoff_base` default 10.0, rejects <=0; `task_retry_backoff_max` default 320.0, rejects <=0
- [ ] `TestReconcileSchedulesRetry`: failed task creates `RetryEntry` in `state.retries` with `attempt=1` and correct `next_due`; task stays in `claimed`
- [ ] `TestReconcileIncrementsRetry`: second failure on same task increments `attempt` to 2 and recalculates `next_due` with doubled delay
- [ ] `TestBackoffFormula`: `delay = min(base * 2**(attempt-1), max)` verified for attempts 1 through 6 (values: 10, 20, 40, 80, 160, 320)
- [ ] `TestRetryExhaustion`: when `attempt > max_attempts`, calls `kanban.kanban_edit(task_id, block=...)` and removes from `retries` + `claimed`
- [ ] `TestRetryDispatch`: `poll_tick` re-dispatches retry entries where `next_due <= now`; entry removed from `retries`, new task added to `running`
- [ ] `TestRetryNotDueYet`: `poll_tick` skips retry entries where `next_due > now`
- [ ] `TestRetryDispatchUsesWip`: re-dispatched retry loads WIP context into prompt via `wip_store.load()`
- [ ] All pre-existing `test_poll_dispatch.py` tests pass
- [ ] ruff clean

[[2026-03-09]] Mon 19:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestRetryEntry: dataclass fields + defaults | daemon.py L106-113: all 4 fields, correct defaults. 2 tests pass. | PASS |
| TestRetryConfig: 3 config fields, defaults, validation | config.py L249-261 + validators L358-383. 9 tests pass. | PASS |
| TestReconcileSchedulesRetry: retry on failure | daemon.py L525-550: creates RetryEntry, keeps claimed. 3 tests pass. | PASS |
| TestReconcileIncrementsRetry: attempt increment | daemon.py L525-526: increments attempt. 1 test verifies attempt=2 + 20s delay. | PASS |
| TestBackoffFormula: min(base*2^(a-1), max) | daemon.py L479-483: exact formula. 3 tests verify sequence + cap + custom. | PASS |
| TestRetryExhaustion: block + remove | daemon.py L528-540: blocks, pops, discards. 1 test verifies all three. | PASS |
| TestRetryDispatch: re-dispatch due retries | daemon.py L645-671: iterates due, dispatches. 1 test confirms. | PASS |
| TestRetryNotDueYet: skip future retries | daemon.py L644: next_due <= now check. 1 test confirms skip. | PASS |
| TestRetryDispatchUsesWip: WIP in retry prompt | daemon.py L660-664: loads WIP + CONTINUE_FORWARD. 1 test confirms. | PASS |
| All pre-existing tests pass | Full suite: 1315 passed, 20 skipped, 2 env failures (slack_sdk missing + temp dir perm). | PASS |
| ruff clean | ruff check on task files: All checks passed | PASS |

### Test Results
- pytest (full suite): 1315 passed, 20 skipped, 2 pre-existing env failures (unrelated)
- ruff (task files): All checks passed

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 19:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestRetryEntry: dataclass fields + defaults | daemon.py L106-113: all 4 fields, correct defaults. 2 tests pass. | PASS |
| TestRetryConfig: 3 config fields, defaults, validation | config.py L249-261 + validators L358-383. 9 tests pass. | PASS |
| TestReconcileSchedulesRetry: retry on failure | daemon.py L525-550: creates RetryEntry, keeps claimed. 3 tests pass. | PASS |
| TestReconcileIncrementsRetry: attempt increment | daemon.py L525-526: increments attempt. 1 test verifies attempt=2 + 20s delay. | PASS |
| TestBackoffFormula: min(base*2^(a-1), max) | daemon.py L479-483: exact formula. 3 tests verify sequence + cap + custom. | PASS |
| TestRetryExhaustion: block + remove | daemon.py L528-540: blocks, pops, discards. 1 test verifies all three. | PASS |
| TestRetryDispatch: re-dispatch due retries | daemon.py L645-671: iterates due, dispatches. 1 test confirms. | PASS |
| TestRetryNotDueYet: skip future retries | daemon.py L644: next_due <= now check. 1 test confirms skip. | PASS |
| TestRetryDispatchUsesWip: WIP in retry prompt | daemon.py L660-664: loads WIP + CONTINUE_FORWARD. 1 test confirms. | PASS |
| All pre-existing tests pass | Full suite: 1315 passed, 20 skipped, 2 env failures (slack_sdk missing + temp dir perm). | PASS |
| ruff clean | ruff check on task files: All checks passed | PASS |

### Test Results
- pytest (full suite): 1315 passed, 20 skipped, 2 pre-existing env failures (unrelated)
- ruff (task files): All checks passed

### Confidence: .97
### Action: archive
