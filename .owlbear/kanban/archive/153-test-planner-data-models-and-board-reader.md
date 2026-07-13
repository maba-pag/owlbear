---
id: 153
title: 'Test: planner data models and board reader'
status: archived
priority: medium
created: 2026-03-29 19:26:49.053208+02:00
updated: 2026-03-30 17:02:25.153314+02:00
started: 2026-03-29 19:26:53.836495+02:00
completed: 2026-03-30 17:02:03.764479+02:00
tags:
- phase-2
- ' scope:orchestrator'
- ' type:test'
- ' test'
depends_on:
- 14
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

### tests/test_planner_models.py

- [ ] Task model: roundtrip validation from kanban-md JSON (all 15 fields)
- [ ] Task model: `class` field alias — JSON key "class" maps to `task_class` attribute
- [ ] Task model: frozen — assignment raises TypeError or ValidationError
- [ ] Task model: optional fields (`started`, `completed`, `claimed_by`, `claimed_at`) default to None
- [ ] DispatchEntry model: validates task_id/agent/target_status, frozen
- [ ] DispatchPlan model: validates entries list, frozen
- [ ] task_list_adapter: valid JSON array parses to list[Task]
- [ ] task_list_adapter: empty JSON array parses to empty list

### tests/test_planner_board.py

- [ ] read_board() success: mocked subprocess returns valid JSON, returns list[Task]
- [ ] read_board() empty board: mocked subprocess returns `[]`, returns empty list
- [ ] read_board() non-zero exit: mocked subprocess rc=1, raises BoardReadError with stderr in message
- [ ] read_board() missing binary: subprocess raises FileNotFoundError, propagates
- [ ] read_board() scope filter: scope="phase-2" adds --tag phase-2 to subprocess args
- [ ] read_board() default args: verifies --json --unblocked --not-blocked --unclaimed --no-color --dir flags
- [ ] All tests FAIL (RED phase) against stub modules
- [ ] ruff clean

### Patterns
- Mock asyncio.create_subprocess_exec for board reader tests
- Use canned kanban-md JSON from research doc S3.1 schema
- Follow packages/mcp-kanban/tests/test_server.py subprocess mocking pattern

[[2026-03-30]] Mon 14:21
## Test-Writer Notes
- This task IS a test-writing task (tagged test). No separate TW pass needed — the task itself is TW output.
- Architect approved atomicity: "single test task appropriate for same-domain models and reader."
- Retroactively added by manual triage (2026-03-30) to unblock Gate 4.

[[2026-03-30]] Mon 15:11
## Review Evidence
pytest: 27 passed, 0 failed | ruff: All checks passed! | Coverage: board.py 100%, models.py 100%
AC Compliance: All 14 AC lines PASS
Verdict: PASS confidence 0.97

[[2026-03-30]] Mon 17:02
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0735335 | chore | kanban/tasks/153-*.md | #153 |
