---
id: 1065
title: 'B-01: RED — models + errors tests'
status: todo
priority: needed
created: 2026-04-21T10:47:39.046535+00:00
updated: 2026-04-21T10:47:39.046535+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1059
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §2, §3.6
Module: `serve/kanban/tests/test_engine_models.py`

Test Pydantic models (TaskSummary, TaskFull, DispatchEntry, Wave, response envelopes) and KanbanError hierarchy (ValidationError, NotFoundError, ConcurrencyError, ConfigError, MigrationRequiredError). Validates field presence, computed fields, error code catalogue, and projection contracts.

Cross-brief: depends on #1059 (storage.py public surface GREEN) because engine models must align with storage `Task` type.

## Acceptance Criteria

- [ ] TaskSummary has all §2.1 fields including computed `claimed` and `dep_status`
- [ ] TaskFull extends TaskSummary with `created`, `updated`, `body` per §2.2
- [ ] DispatchEntry has `agent` field per §2.3 + D24
- [ ] Wave has `index: int` + `tasks: list[DispatchEntry]` per §2.4
- [ ] Response envelopes: ListTasksResponse, ShowTaskResponse, PickTasksResponse, SingleTaskResponse per §2.5
- [ ] AC16: No projection includes `file` field
- [ ] AC17: No `claimed_by` field; `claimed_at` + `claimed` present
- [ ] KanbanError subclasses carry `code: str` and `user_message: str` per §3.6 + D57
- [ ] Error code catalogue covers all ERR_* codes from §1 and §4
- [ ] All tests fail (RED phase)