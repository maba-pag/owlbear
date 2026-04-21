---
id: 1054
title: 'C-09: RED — engine activity/session tests'
status: in-progress
priority: needed
created: 2026-04-21T10:42:50.316514+00:00
updated: 2026-04-21T17:33:53.311574+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §8.9
Module: `serve/kanban/tests/test_engine_activity.py`

## Acceptance Criteria

- [ ] AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions
- [ ] AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with `active`/`all`/`blocked-or-rejected`/`released` semantics matching §7.2
- [ ] Fresh canonical stream — no legacy migration of old activity history
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes

**Third attempt** — added 2 genuinely failing tests to resolve RED phase.

**File:** `serve/kanban/tests/test_engine_activity.py`

**Context:** The 22 tests from the previous retry were all PASSING because the builder had already implemented AC-C42 and AC-C43. Identified two behavioral gaps between the normative spec (paper-c.md §7.2) and the implementation:

1. **Sweep-released session visibility** — §7.2 specifies that `sweep-release` closes a session that must be visible in `list_sessions(filter="all")`. Current implementation silently drops sweep-closed sessions (no `WorkSession` appended in `_collect_task_sessions` for `sweep-release`).
2. **Unknown filter validation** — AC-C43 defines a closed set of filters (`active`/`all`/`failed-or-rejected`/`released`). Unknown filter names should raise `ValueError`; current implementation silently returns all sessions.

**New tests (both FAIL):**
- `test_ac_c43_sweep_released_session_visible_in_all_filter` — FAIL: no session produced for sweep-released task
- `test_ac_c43_unknown_filter_raises_value_error` — FAIL: no ValueError raised for unknown filter

**Results:** 24 tests total — 22 PASS, 2 FAIL (RED ✓). Ruff clean.

**AC coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: emit ActivityEvent for claim/edit/move/end_work/sweep | 8 tests | PASS (implementation done) |
| AC-C43: list_sessions WorkSession contract | 12 tests | PASS (implementation done) |
| AC-C43: sweep-released sessions visible | 1 test | **FAIL (RED)** |
| AC-C43: unknown filter raises ValueError | 1 test | **FAIL (RED)** |
| Fresh canonical stream | 1 test | PASS (implementation done) |