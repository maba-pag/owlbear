---
id: 153
title: 'Test: planner data models and board reader'
status: in-progress
priority: needed
created: 2026-03-29T19:26:49.0532083+02:00
updated: 2026-03-29T19:57:53.64276+02:00
started: 2026-03-29T19:26:53.8364954+02:00
tags:
    - phase-2
    - ' scope:orchestrator'
    - ' type:test'
    - ' test'
depends_on:
    - 14
class: standard
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
