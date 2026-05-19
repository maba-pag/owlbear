---
id: 954
title: Extend TaskSummaryOut with block_reason and claimed fields
status: archived
priority: needed
created: 2026-04-18T13:41:19.335936+00:00
updated: 2026-04-18T14:18:52.778555+00:00
tags:
- cockpit
- backend
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
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
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 40 passed, 0 failed

### Lint: clean

### Coverage

- owlbear_cockpit.models: 100%
- owlbear_cockpit.routes.read: 100%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC#1 — `block_reason: str\|None = None` in `TaskSummaryOut` | `test_task_summary_has_block_reason_field` | Yes — `"block_reason" in task` fails if field absent | COVERED |
| AC#1 — `claimed: bool = False` in `TaskSummaryOut` | `test_task_summary_has_claimed_field` | Yes — `"claimed" in task` fails if field absent | COVERED |
| AC#2 — adapter maps from engine `TaskSummary` | `test_blocked_task_block_reason_is_correct_value`, `test_claimed_task_claimed_is_true` | Yes — value assertions catch wrong or missing mapping | COVERED |
| AC#3 — tests updated with new field coverage | All 7 `TestFromAC_TaskSummaryFields` tests; arch-review refinements met | Yes — class verifies presence, values, and defaults | COVERED |
| AC#4 — `GET /api/tasks` includes both fields per task | `test_all_tasks_have_block_reason_and_claimed_with_correct_types` | Yes — type+presence check over all returned tasks | COVERED |
| Arch-review — default null/false | `test_unblocked_task_block_reason_is_null`, `test_unclaimed_task_claimed_is_false` | Yes — asserts `is None` and `is False` explicitly | COVERED |

#### Security Review

No issues. Read-only API, additive field pass-through, no new input boundaries, no new dependencies, no deserialization risk.

#### Test Integrity

No `TestFromAC_*` methods were modified by the builder. Builder changed only `models.py` and `routes/read.py` — test file untouched.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 7 TestFromAC_TaskSummaryFields tests | Unchanged | PRESERVED |

#### Test Quality

STRONG on all dimensions:

- Assertion specificity: specific value assertions (`== "waiting on dependency"`, `is True`, `is None`, `is False`, `isinstance(..., bool)`)
- Fixture: board_dir extended with claimed Task 4 (via `seed_engine.claim_task("4")`) and blocked Task 3 (via `edit_task("3", blocked=True, block_reason="waiting on dependency")`)
- Test independence: each test makes independent HTTP requests with specific filter params
- Descriptive names: all tests named per intent

#### Data Safety

No issues. No concurrency, no LLM output persistence, no unbounded input.

#### Implementation-Aware Test Gap Analysis

2 files changed: `models.py` (2 field additions with defaults) and `routes/read.py` (2 kwargs added to `TaskSummaryOut` constructor). Both paths fully exercised. No untested branches.

#### Builder Process Quality

CLEAN — single `## Builder Notes` section, no retries.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1 — `block_reason: str\|None = None` | models.py:16 | `test_task_summary_has_block_reason_field` | PASS |
| AC#1 — `claimed: bool = False` | models.py:17 | `test_task_summary_has_claimed_field` | PASS |
| AC#2 — adapter mapping | read.py: `block_reason=s.block_reason, claimed=s.claimed` in `TaskSummaryOut` constructor | `test_blocked_task_block_reason_is_correct_value`, `test_claimed_task_claimed_is_true` | PASS |
| AC#3 — tests updated | 7 TestFromAC tests, board_dir with claimed + blocked tasks | Full TestFromAC_TaskSummaryFields class | PASS |
| AC#4 — `GET /api/tasks` exposes both fields | 40/40 pass; all summaries carry both fields | `test_all_tasks_have_block_reason_and_claimed_with_correct_types` | PASS |
| Arch-review — defaults | models.py defaults; assertions in two boundary tests | `test_unblocked_task_block_reason_is_null`, `test_unclaimed_task_claimed_is_false` | PASS |

### Verdict

Confidence: .98 → PASS #954 → docs
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A — no update needed | `.github/copilot-instructions.md` §4 documents endpoint URLs/purpose, not response field shapes; additive field addition doesn't require docs update at that abstraction level |
| 2 | Module docstrings | Yes | Verified accurate | `TaskSummaryOut` docstring ("Summary projection of a task for list endpoints.") accurate; `list_tasks()` docstring describes caching behaviour, not field list — both correct post-change |
| 3 | External attribution | No | N/A | Task research notes "all codebase" sources only; no external patterns |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/954-tasksummaryout-fields.md` exists; linked in task body Research section |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/954-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1 — `block_reason: str\|None = None` in `TaskSummaryOut` | models.py:17 | PASS |
| AC#1 — `claimed: bool = False` in `TaskSummaryOut` | models.py:18 | PASS |
| AC#2 — adapter maps from engine `TaskSummary` | read.py:80-81 `block_reason=s.block_reason, claimed=s.claimed` | PASS |
| AC#3 — tests updated with new field coverage | 7 TestFromAC_TaskSummaryFields tests (commit 46891f21); arch-review refinements met | PASS |
| AC#4 — `GET /api/tasks` includes both fields per task | read.py constructor + test_all_tasks_have_block_reason_and_claimed_with_correct_types | PASS |
| Arch-review — default null/false | models.py defaults + test_unblocked_task_block_reason_is_null, test_unclaimed_task_claimed_is_false | PASS |

### Test Results

- pytest: 589 passed, 6 failed (all pre-existing mcp-knowledge failures, zero cockpit regressions)
- ruff: clean

### Architect Quality: 4/5

AC#1,2,4 were specific (types, defaults, files). AC#3 under-specified but architect caught it during review and added 3 binding refinements (claimed fixture, value assertions, default verification). Solid upstream work.

### Deduction Breakdown

- No AC lines without evidence: 0
- Lint clean: 0
- AC quality 4/5 (above 3): 0
- Reviewer evidence present and detailed: 0
- No full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
