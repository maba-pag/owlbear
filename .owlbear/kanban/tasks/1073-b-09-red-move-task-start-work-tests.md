---
id: 1073
title: 'B-09: RED — move_task + start_work tests'
status: todo
priority: needed
created: 2026-04-21T10:49:15.724135+00:00
updated: 2026-04-21T10:49:15.724135+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1072
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.6, §1.7, §3.1, §3.2, §3.4, §4
Module: `serve/kanban/tests/test_engine_move_claim.py`

Test AgentView.move_task and AgentView.start_work. Covers status transitions, archival validation matrix, predicate on destination, claim semantics (lazy-release on expired, blocked/archived not claimable), skip-transition guidance.

## Acceptance Criteria

- [ ] AC4: `move_task(id, "archived")` without `archival_reason` → ValidationError(ERR_ARCHIVAL_REASON_REQUIRED)
- [ ] AC5: `move_task(id, "archived", "completed")` from non-terminal → ValidationError(ERR_COMPLETED_REQUIRES_DONE)
- [ ] AC7: `move_task(id, "archived", "deprecated")` empty refs → ValidationError(ERR_ARCHIVAL_REFS_REQUIRED)
- [ ] AC8: `move_task(id, "archived", "dropped", refs=[42])` → ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN)
- [ ] AC9: Invalid `archival_reason` enum → ValidationError(ERR_ARCHIVAL_REASON_INVALID)
- [ ] AC26: `move_task(..., archival_refs=[99999])` → ValidationError(ERR_ARCHIVAL_REF_MISSING)
- [ ] AC-NEW-5: Move skipping >1 status position emits skip-warning in guidance
- [ ] AC-NEW-16: move_task/start_work on missing id → NotFoundError(ERR_NOT_FOUND)
- [ ] Invalid `status` enum → ValidationError(ERR_INVALID_STATUS) (D49 — no transition-forbidden code)
- [ ] start_work on already-claimed task → ConcurrencyError(ERR_ALREADY_CLAIMED)
- [ ] start_work on archived task → ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE)
- [ ] start_work on blocked task → ValidationError(ERR_BLOCKED_NOT_CLAIMABLE)
- [ ] start_work on expired claim → lazy-release + re-claim (D18+D36)
- [ ] D15: write-time predicate on destination status fires; failure → ERR_PREDICATE_FAILED, transition NOT applied (D41)
- [ ] Archive clears claim atomically (D17)
- [ ] `archival_reason` set when `status != "archived"` → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] All tests fail (RED phase)