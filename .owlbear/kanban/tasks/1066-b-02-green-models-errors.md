---
id: 1066
title: 'B-02: GREEN — models + errors'
status: todo
priority: critical
created: 2026-04-21T10:47:48.612099+00:00
updated: 2026-04-21T10:47:48.612099+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1065
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §2, §3.6
Module: `serve/kanban/src/owlbear_kanban/models.py`, `serve/kanban/src/owlbear_kanban/errors.py`

Implement Pydantic models and error hierarchy. Models: TaskSummary (§2.1), TaskFull (§2.2), DispatchEntry (§2.3), Wave (§2.4), response envelopes (§2.5). Errors: KanbanError base, ValidationError, NotFoundError, ConcurrencyError, ConfigError, MigrationRequiredError — all with `code` + `user_message` per D27+D57.

## Acceptance Criteria

- [ ] All RED tests from B-01 (#1065) pass
- [ ] `dep_status` is computed property (pure function, not stored) per D38
- [ ] `claimed` is computed from `claimed_at is not None`
- [ ] No `file` field on any projection model (AC16)
- [ ] No `claimed_by` field (AC17, D11)
- [ ] Error hierarchy uses frozen `code` strings matching ERR_* catalogue
- [ ] `archival_reason` field typed as `str | None` (enum validated at write sites, not model)
- [ ] `archival_refs` typed as `list[int]` with default empty list