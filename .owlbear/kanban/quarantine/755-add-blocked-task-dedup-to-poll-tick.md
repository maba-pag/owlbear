---
id: 755
title: Add blocked-task dedup to poll_tick
status: archived
priority: important
created: 2026-03-12T10:50:56.8425584+01:00
updated: 2026-03-12T11:10:51.1595165+01:00
started: 2026-03-12T11:10:51.1595165+01:00
completed: 2026-03-12T11:10:51.1595165+01:00
tags:
    - phase-4
    - agent
    - scope:core
depends_on:
    - 757
class: standard
---

## Acceptance Criteria

- [ ] Add `last_attempted_at: dict[str, datetime]` field to OrchestratorState (task_id -> timezone-aware UTC datetime)
- [ ] poll_tick records `last_attempted_at[task_id] = now(UTC)` when dispatching a task (both new and retry paths)
- [ ] poll_tick skips todo tasks where `last_attempted_at[task_id]` exists AND `task[updated] < last_attempted_at[task_id]` (no new kanban activity since last attempt)
- [ ] Skipped tasks logged at DEBUG level with reason string including task_id and both timestamps
- [ ] In-memory only (lost on daemon restart -- acceptable for v1, KISS)
- [ ] Parse `updated` from kanban_list JSON output (ISO 8601 with timezone) using `datetime.fromisoformat()`

## Architecture Notes

- Extends OrchestratorState dataclass (same module as RunningTask, RetryEntry)
- kanban_list --json and kanban_show --json both return `updated` timestamp per task
- The `updated` field is ISO 8601 with timezone info (e.g. `2026-03-12T10:50:56.8425584+01:00`)
- Use timezone-aware datetimes throughout for correct comparison
- This is in-memory dedup only; daemon restart resets state (fresh attempt for all tasks)
- No new config field needed -- feature is always-on in poll_tick
- NOTE: existing `kanban_list(format=json)` call has a format kwarg not in KanbanToolset.kanban_list signature (pre-existing mock-masked issue). Builder may encounter this if testing against real toolset.

## References

- Paperclip skip-blocked pattern: skills/paperclip/SKILL.md step 4
- Research: docs/research/paperclip.md
- Existing: src/owlbear/daemon.py poll_tick(), OrchestratorState
- Test patterns: tests/test_poll_dispatch.py, tests/test_daemon_coverage_gaps.py

[[2026-03-12]] Thu 11:10

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add last_attempted_at field to OrchestratorState | Clear, verifiable, correct type | Refined: specified timezone-aware UTC |
| poll_tick records timestamp on dispatch | Clear | Refined: clarified both new and retry paths |
| poll_tick skips tasks with no new activity | Clear comparison logic | Refined: explicit task[updated] reference |
| Log skipped tasks at DEBUG | Clear, verifiable | Refined: specified log content (task_id + timestamps) |
| In-memory only | Clear constraint, KISS | Kept |
| Unit tests bundled in AC | TDD violation | Removed: created separate test task #757 |
| Parse updated from kanban_list JSON | NEW -- builder needs to know data format | Added for clarity |

### Architecture Notes

- OrchestratorState dataclass extension follows existing pattern (RunningTask, RetryEntry in same module)
- kanban_list --json and kanban_show --json both return ISO 8601 `updated` field (verified)
- Pre-existing issue: poll_tick calls kanban_list(format=json) but KanbanToolset.kanban_list doesn't accept format kwarg. Tests mask this via MagicMock. Noted in AC but not blocking.
- Dedup logic is simple filter in existing step 5 (filter already-claimed). Minimal diff.
- No new system boundaries or security surface

### Changes Made

- Deleted #754 (exact duplicate of #755 -- same title, AC, body, tags, created timestamp)
- Refined AC: removed bundled tests, added timezone/format specifics, clarified both dispatch paths
- Created #757 (TDD RED test task) at todo status
- Added depends_on: #757 to #755
- Moved #755 to todo

### Dependencies

- Added: #757 (tests) -- must complete RED phase before #755 GREEN phase
- Verified: no other blocking dependencies
