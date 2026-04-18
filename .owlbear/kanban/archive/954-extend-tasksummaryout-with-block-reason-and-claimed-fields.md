---
id: 954
title: Extend TaskSummaryOut with block_reason and claimed fields
status: review
priority: needed
created: 2026-04-18T13:41:19.335936+00:00
updated: 2026-04-18T14:09:00.097109+00:00
tags:
- cockpit
- backend
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: odd-mist
claimed_at: 2026-04-18T14:09:00.097109+00:00
---
## Objective

Add `block_reason: str | None` and `claimed: bool` to `TaskSummaryOut` in the cockpit API. The kanban engine's `TaskSummary` already has both fields — they just need to be passed through the adapter and exposed in the API response.

## Context

Discovered during #931 research: the cockpit `TaskSummaryOut` is missing fields needed for the kanban board UI (block badge tooltip, running indicator). See `.owlbear/research/931-kanban-board-tests.md` §3.1.

## Acceptance Criteria

- [ ] `TaskSummaryOut` in `serve/cockpit/src/owlbear_cockpit/models.py` includes `block_reason: str | None = None` and `claimed: bool = False`
- [ ] Adapter maps these from the engine's `TaskSummary`
- [ ] Existing cockpit API tests updated to cover the new fields
- [ ] `GET /api/tasks` response includes `block_reason` and `claimed` per task

## Files

- `serve/cockpit/src/owlbear_cockpit/models.py`
- `serve/cockpit/src/owlbear_cockpit/adapter.py`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`
- `tests/test_cockpit_read_api.py`
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/954-tasksummaryout-fields.md
- Sources: 5 studied, 4 high-relevance (all codebase)
- Recommendation: Direct implementation — mechanical 3-file change (confidence: 0.95)
- Tier: T1 Autonomous — additive field pass-through, no architecture/security impact
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none

Key findings: Engine `TaskSummary` already has both fields. Adapter passes them through. Only the Pydantic model (`TaskSummaryOut`) and route constructor need updating. Pattern is already established by `TaskDetailOut.block_reason`. No risks — additive change with defaults.
[[2026-04-18]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: add two related fields to one API model |
| Interface clarity | PASS | Field names, types, and defaults specified in AC |
| Dependency correctness | PASS | No dependencies needed; engine already exposes both fields |
| Module layering | PASS | cockpit depends on kanban engine (correct direction) |
| TDD compliance | PASS | Test-writer will handle RED phase |
| KISS/YAGNI | PASS | Both fields needed for frontend kanban board UI (block badge tooltip, running indicator) |
| Premise challenge | PASS | Fields genuinely missing from summary projection; detail model already has block_reason |
| Pattern consistency | PASS | Follows established TaskDetailOut.block_reason pattern; explicit-kwargs construction in read.py |
| Security surface | PASS | Read-only API, no new input boundaries |
| Single domain | PASS | Cockpit API domain only |

### AC Refinements (binding for test-writer and builder)

AC#3 ("Existing cockpit API tests updated to cover the new fields") is under-specified. The following refinements apply:

1. **Test fixture must include at least one claimed task** — the existing board_dir fixture has no claimed tasks, so `claimed: true` would never be verified. Add a `claimed_by` field to one fixture task (the engine's `_coerce_claimed` validator converts it to `claimed: bool`).
2. **Tests must assert correct values** for both `block_reason` and `claimed` — not just field presence. Verify `block_reason == "waiting on dependency"` for the blocked task, `claimed == true` for the claimed task.
3. **Tests must verify defaults** — `block_reason: null` for unblocked tasks, `claimed: false` for unclaimed tasks.

### Scope Notes

- The adapter (`adapter.py`) is a thin pass-through returning engine objects directly. No adapter changes needed — the mapping happens in the route constructor in `read.py` (add `block_reason=s.block_reason, claimed=s.claimed` kwargs).
- `parent` and `depends_on` are also missing from `TaskSummaryOut` but are out of scope for this task. The summary projection intentionally excludes graph fields. If the frontend needs them later, that's a separate task.
- No `claimed` query filter is included — this task is field passthrough only. Filter can follow if the frontend needs it.

### Challenge Results
- Challenger: proceed (confidence 0.65, below 0.80 threshold)
- Key concerns: AC#3 under-specified, no claimed fixture, test value-correctness gaps
- Architect response: accepted — refined AC#3 with binding test requirements above

### Verdict: APPROVE (with AC refinements)
### Action Taken: Advanced to todo with binding AC refinements for test-writer
[[2026-04-18]]
## Test-Writer Notes
- Test file: tests/test_cockpit_read_api.py
- Classes: `TestFromAC_TaskSummaryFields` (new), existing classes unchanged
- Tests per category: happy 2, edge 0, error 0, boundary 5
- Total: 7 tests, all FAIL
- ruff: clean

**AC Coverage:**
| AC | Tests |
|----|-------|
| AC#1 — `TaskSummaryOut` includes `block_reason` and `claimed` | `test_task_summary_has_block_reason_field`, `test_task_summary_has_claimed_field` |
| AC#2 — adapter maps fields from engine `TaskSummary` | `test_blocked_task_block_reason_is_correct_value`, `test_claimed_task_claimed_is_true` |
| AC#4 — `GET /api/tasks` includes both fields per task | `test_all_tasks_have_block_reason_and_claimed_with_correct_types` |
| Arch-review — default null/false for unblocked/unclaimed | `test_unblocked_task_block_reason_is_null`, `test_unclaimed_task_claimed_is_false` |

**Fixture change:** `board_dir` extended from 3 → 4 tasks. Task 4 (tag=delta, in-progress, important) is claimed via `seed_engine.claim_task("4")`. All existing 33 tests continue to pass (filter count assertions unaffected).

**Failure mode:** All 7 fail with `AssertionError: Task summary missing 'block_reason'/'claimed'` or `KeyError` — fields absent from `TaskSummaryOut` serialisation. Correct root cause confirmed.

**Commit:** `46891f21`
[[2026-04-18]]
## Builder Notes

**Files changed (2):**
- `serve/cockpit/src/owlbear_cockpit/models.py` — added `block_reason: str | None = None` and `claimed: bool = False` to `TaskSummaryOut`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — added `block_reason=s.block_reason, claimed=s.claimed` to `TaskSummaryOut` constructor in `list_tasks()`

**Test results:** 40 passed (33 existing + 7 new TestFromAC_TaskSummaryFields), 0 failed

**Lint:** ruff clean

**Coverage:** existing cockpit coverage unchanged (additive pass-through fields)

**Commit:** `1150876e` — `feat(cockpit): add block_reason and claimed to TaskSummaryOut (#954)`

**Evidence:** Engine `TaskSummary` already exposed both fields. Mechanical 2-file change as specified in AC. No TestBuilderDiscovered tests needed — no edge cases beyond what the test-writer covered.