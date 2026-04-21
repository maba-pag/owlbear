---
id: 1069
title: 'B-05: RED — list_tasks + show_task tests'
status: todo
priority: needed
created: 2026-04-21T10:48:33.304571+00:00
updated: 2026-04-21T10:48:33.304571+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1068
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.1, §1.2, §3.3, §4
Module: `serve/kanban/tests/test_engine_reads.py`

Test AgentView.list_tasks and AgentView.show_task. Covers query filtering, ids-exclusive validation, section extraction, dep_status computation, archived-task reads, missing_ids population, guidance emission.

## Acceptance Criteria

- [ ] AC1: `show_task(<archived_id>)` returns TaskFull with archived fields populated
- [ ] AC2: `list_tasks(status="archived")` returns archived only
- [ ] AC3: `list_tasks(ids=[active, archived, missing])` returns 2 + `missing_ids=[missing]`
- [ ] AC10: `show_task(id, section="audit")` returns matching heading content (case-insensitive)
- [ ] AC11: `show_task(id, section="missing")` → `body=None`, `missing_sections=["missing"]`
- [ ] AC12: Multiple section matches → guidance includes occurrence count
- [ ] AC15: `list_tasks(ids=[1], status="todo")` → ValidationError(ERR_IDS_EXCLUSIVE)
- [ ] Invalid `status` enum → ValidationError(ERR_INVALID_STATUS)
- [ ] Invalid `priority` enum → ValidationError(ERR_INVALID_PRIORITY)
- [ ] Invalid `archival_reason` enum → ValidationError(ERR_ARCHIVAL_REASON_INVALID)
- [ ] `show_task` with empty `section=""` → ValidationError(ERR_SECTION_EMPTY)
- [ ] `show_task` with non-existent id → NotFoundError(ERR_NOT_FOUND)
- [ ] Default: excludes archived unless `status="archived"` or `ids` used
- [ ] `dep_status` computed per §3.3 (blocked > redirect > ok > None)
- [ ] All tests fail (RED phase)