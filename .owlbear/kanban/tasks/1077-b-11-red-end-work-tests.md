---
id: 1077
title: 'B-11: RED — end_work tests'
status: todo
priority: needed
created: 2026-04-21T10:50:12.206656+00:00
updated: 2026-04-21T10:50:12.206656+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1075
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.8, §4
Module: `serve/kanban/tests/test_engine_end_work.py`

Test AgentView.end_work — the 4-outcome lifecycle endpoint. Covers outcome dispatch, forbidden-parameter matrix (deterministic per §1.8), atomic semantics (D41), claim validation, idempotent release (D55), auto-advance/auto-archive (D52+D51), predicate on destination.

## Acceptance Criteria

- [ ] AC18: `end_work(id, "success")` auto-advances one step; from terminal archives completed/[]; clears claim
- [ ] AC19: `end_work(id, "reject", move_to="archived", reason, note)` archives + appends + clears
- [ ] AC20: `end_work(id, "release")` clears claim, no status change
- [ ] AC-NEW-1: `end_work(id, "block")` without block_reason → ERR_BLOCK_REASON_REQUIRED
- [ ] AC-NEW-2: `end_work(id, "block", block_reason=r)` sets blocked+block_reason, clears claim
- [ ] AC-NEW-3: `end_work(id, "block", block_reason=r, move_to=s)` additionally moves (predicate fires)
- [ ] AC-NEW-4: `end_work(outcome="block")` response guidance suggests AR/DR creation
- [ ] AC-NEW-5: end_work(reject, move_to=...) skipping >1 emits skip-warning
- [ ] AC-NEW-6: `end_work(id, "<invalid>")` → ERR_INVALID_OUTCOME
- [ ] AC-NEW-7: `end_work(id, "release")` on unclaimed → pure no-op (updated NOT advanced, note NOT appended)
- [ ] AC-NEW-8: `end_work(id, "success"/"reject"/"block")` on unclaimed → ERR_NOT_CLAIMED
- [ ] AC-NEW-9: Forbidden-parameter matrix fully tested (success+move_to, success+archival_reason, etc.)
- [ ] AC-NEW-10: `end_work(id, "reject")` without move_to → ERR_REJECT_REQUIRES_MOVE_TO
- [ ] AC-NEW-11: Non-block outcome with block_reason → ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK
- [ ] AC-NEW-12: success from non-terminal with predicate fail → ERR_PREDICATE_FAILED; claim NOT cleared (D41)
- [ ] AC-NEW-13: block+move_to with predicate fail → claim NOT cleared, blocked NOT set (D41)
- [ ] AC-NEW-17: reject to archived without archival_reason → ERR_ARCHIVAL_REASON_REQUIRED
- [ ] AC-NEW-18: release with move_to → ERR_MOVE_TO_FORBIDDEN_ON_RELEASE
- [ ] AC-NEW-19: release with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] AC-NEW-20: block with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] Note prepended with ISO 8601 timestamp on append (D20/AC30)
- [ ] Multiple parameter errors → leftmost-row, leftmost-column violation raised (deterministic)
- [ ] All tests fail (RED phase)