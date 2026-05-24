---
id: 1817
title: Triage engine validation push tests
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
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