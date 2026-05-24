---
id: 1817
title: Repair engine validation push tests
status: done
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:43:25+02:00
tags:
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The three `tests/test_engine_validation_push.py` failures are traced to current predicate-validation behavior.
  - The intended owner of status predicate enforcement is confirmed before code changes.
  - Focused validation-push tests pass or have documented follow-up tasks.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has three failures in `tests/test_engine_validation_push.py`, covering unsatisfied status predicates, move validation, and preserved error codes/messages.

## Evidence
- Failing classes: `TestFromAC_ValidateStatusPredicate`, `TestFromAC_EngineMoveValidation`, and `TestFromAC_ErrorCodesPreserved`.

## Boundary
Do not move validation responsibilities between `AgentView` and `KanbanEngine` without explicit approval.

## Decision
User approved implementing #1817. The failures were stale predicate-topology expectations:
- `KanbanEngine.validate_status_predicate()` still owns direct predicate validation when passed a config object containing `policy.status_predicates`.
- Runtime board operations such as `move_task()` load product topology, so predicates embedded in `config.yml` are intentionally ignored.

The tests now mutate the copied `BoardConfig` for direct validator coverage and assert that config-file predicates do not block `move_task()`.

## Verification
- `uv run ruff check tests/test_engine_validation_push.py` — passed.
- `uv run pytest tests/test_engine_validation_push.py -q --tb=short` — 51 passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 11 failed, 529 passed.

## Remaining
The root glob remains red due to #1818, #1819, #1820, and #1821.