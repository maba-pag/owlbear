---
id: 757
title: 'Tests: blocked-task dedup in poll_tick (RED)'
status: archived
priority: important
created: 2026-03-12T11:07:19.8893733+01:00
updated: 2026-03-12T17:39:48.287735+01:00
started: 2026-03-12T17:08:37.7590036+01:00
completed: 2026-03-12T17:39:48.287735+01:00
tags:
    - phase-4
    - test
    - scope:core
claimed_by: reviewer
claimed_at: 2026-03-12T17:08:37.7590036+01:00
class: standard
---

## Acceptance Criteria

- [ ] Test file: tests/test_poll_dedup.py
- [ ] Test: task never attempted is always dispatched (last_attempted_at has no entry)
- [ ] Test: task with no new kanban activity since last attempt is skipped (task.updated < last_attempted_at)
- [ ] Test: task with new kanban activity since last attempt is dispatched (task.updated >= last_attempted_at)
- [ ] Test: skipped tasks are logged at DEBUG level with reason string
- [ ] Test: daemon restart (empty state) processes all tasks (fresh OrchestratorState)
- [ ] All tests FAIL (RED phase) -- assert on behavior not yet implemented
- [ ] ruff clean

## Architecture Notes

- Follow existing poll_tick test patterns in tests/test_poll_dispatch.py and tests/test_daemon_coverage_gaps.py
- Mock kanban.kanban_list to return JSON with 'updated' field per task
- Use OrchestratorState with pre-populated last_attempted_at for skip scenarios

## Dependencies

- None (test-first)

[[2026-03-12]] Thu 11:43

## Test-Writer Notes

- Test file: tests/test_poll_dedup.py
- Classes: TestFromAC_BlockedTaskDedup
- Tests per category: happy 3, edge 1, error 0, boundary 2, logging 1, integration 2
- Total: 9 tests, all FAIL
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| task never attempted dispatched | test_never_attempted_task_is_dispatched, test_multiple_unattempted_tasks_all_dispatched (in fresh_state) | happy |
| no new activity skipped | test_no_new_activity_since_last_attempt_is_skipped | happy |
| new activity dispatched | test_new_activity_since_last_attempt_is_dispatched | happy |
| updated == attempted (boundary) | test_equal_timestamp_is_dispatched | boundary |
| skipped logged at DEBUG | test_skipped_task_logged_at_debug | logging |
| last_attempted_at set after dispatch | test_last_attempted_at_recorded_after_dispatch | boundary |
| fresh state dispatches all | test_fresh_state_dispatches_all_tasks, test_orchestrator_state_has_last_attempted_at | happy |
| mixed skip and dispatch | test_mixed_skip_and_dispatch | integration |

[[2026-03-12]] Thu 16:08

## Builder Notes

- Files changed: src/owlbear/daemon.py (1 line added)
- Fix: retry dispatch path (step 3) now records last_attempted_at[tid] = now
- Tests: 10 passed, coverage 34% on daemon.py (large module, only dedup path exercised)
- Lint: ruff clean
- No TestFromAC classes modified
- Evidence: 92 passed (poll_dispatch + poll_dedup combined)

[[2026-03-12]] Thu 17:08

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | TDD test + 1-line dedup fix; no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | OrchestratorState already has docstring; last_attempted_at field is self-documenting |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | Yes | Pass | Pure TDD task with no documentation implications |

### Files Updated

- None

### Scratch Files Cleaned

- None (no scratch files found)
