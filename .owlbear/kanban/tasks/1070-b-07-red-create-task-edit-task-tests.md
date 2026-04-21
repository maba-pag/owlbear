---
id: 1070
title: 'B-07: RED — create_task + edit_task tests'
status: todo
priority: needed
created: 2026-04-21T10:48:33.317250+00:00
updated: 2026-04-21T10:48:33.317250+00:00
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
Brief B (#1044) — paper-integration.md §1.4, §1.5, §3.2, §3.4, §3.5, §4
Module: `serve/kanban/tests/test_engine_create_edit.py`

Test AgentView.create_task and AgentView.edit_task. Covers validation matrix, body size limits, predicate-on-create, body-exclusive, block_reason semantics, no-op detection, parent/dep existence checks, archival-field gates, timestamp wire format.

## Acceptance Criteria

- [ ] AC6: `edit_task(<archived>, archival_reason="completed")` → ValidationError(ERR_COMPLETED_REQUIRES_DONE)
- [ ] AC14: `edit_task(id, body=..., append_body=...)` both set → ValidationError(ERR_BODY_EXCLUSIVE)
- [ ] AC24: `create_task(..., depends_on=[99999])` → ValidationError(ERR_DEP_NOT_FOUND)
- [ ] AC25: `edit_task(id, add_dep=[99999])` → ValidationError(ERR_DEP_NOT_FOUND)
- [ ] AC29: `created`, `updated` carry explicit `±HH:MM` or `Z`
- [ ] AC30: `edit_task(append_body=..., timestamp=true)` prepends ISO timestamp
- [ ] AC-NEW-15: `edit_task(id, parent=99999)` → ValidationError(ERR_PARENT_NOT_FOUND)
- [ ] No `status` param on create_task — tasks created at BoardConfig.entry_status (D50)
- [ ] Body >500KB → ValidationError(ERR_BODY_TOO_LARGE); >100KB → guidance warning (D35+D47)
- [ ] Post-append total body checked against size caps (D47)
- [ ] `block_reason` non-empty sets blocked; empty/null clears both (D53)
- [ ] No-op call (no field changes) → ValidationError(ERR_NO_OP)
- [ ] Archival fields on non-archived task → ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)
- [ ] Archival refs matrix per §3.2 (required/forbidden/missing/self/cycle)
- [ ] Predicate on entry_status fires on create (D15+D50)
- [ ] All tests fail (RED phase)