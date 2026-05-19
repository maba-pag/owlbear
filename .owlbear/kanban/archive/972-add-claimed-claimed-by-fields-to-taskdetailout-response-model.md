---
id: 972
title: Add claimed/claimed_by fields to TaskDetailOut response model
status: archived
priority: important
created: 2026-04-18T17:51:15.338842+00:00
updated: 2026-04-18T19:56:04.165662+00:00
tags:
- cockpit
- backend
- phase-2
- type:build
parent: 920
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Extend `TaskDetailOut` in `serve/cockpit/src/owlbear_cockpit/models.py` to include `claimed: bool` (and optionally `claimed_by: str | None`) so the Detail tab can display claim status as a read-only field.

## Context

Discovered during architecture review of #935: `TaskSummaryOut` includes `claimed: bool` but `TaskDetailOut` does not. The sidecar Detail tab needs this field to show claim status. Removed from #935 AC to maintain single-domain (frontend-only) scope.

## Acceptance Criteria

- [ ] `TaskDetailOut` includes `claimed: bool = False` field
- [ ] `get_task` route in `routes/read.py` maps `task.claimed` to the response
- [ ] Existing `test_cockpit_read_api.py` updated with assertion for `claimed` field in task detail response
- [ ] No breaking changes to existing API consumers

## Files

- `serve/cockpit/src/owlbear_cockpit/models.py`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`
- `tests/test_cockpit_read_api.py`
[[2026-04-18]]

## Refined Acceptance Criteria

- [ ] `TaskDetailOut` in `models.py` includes `claimed: bool = False` and `claimed_by: str | None = None` fields
- [ ] `TaskDetailOut` includes a `_coerce_claimed` model validator (same `mode="before"` pattern as `TaskSummary`) that derives `claimed` from `claimed_by`
- [ ] `get_task` route in `routes/read.py` passes `claimed_by=task.claimed_by` when constructing `TaskDetailOut`
- [ ] `_task_to_detail` helper in `routes/mutation.py` passes `claimed_by=task.claimed_by` when constructing `TaskDetailOut`
- [ ] Tests in `test_cockpit_read_api.py`: assert `claimed` and `claimed_by` fields in task detail response for both unclaimed task (task 1, `claimed=False`, `claimed_by=None`) and claimed task (task 4, `claimed=True`, `claimed_by` is non-null string)
- [ ] No breaking changes to existing API consumers (new fields use safe defaults)

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One model extension + route mapping, single domain |
| Interface clarity | PASS (after refine) | Original AC referenced `task.claimed` which doesn't exist on `Task` model; refined to use `claimed_by` with validator coercion |
| Dependency correctness | PASS | No deps needed; kanban `Task` model already has `claimed_by` |
| Module layering | PASS | Models → routes, standard cockpit pattern |
| TDD compliance | PASS | AC includes test requirements |
| KISS/YAGNI | PASS | Mirrors existing `TaskSummary._coerce_claimed` pattern; `claimed_at` excluded as YAGNI |
| Premise challenge | PASS | Gap is real: `TaskSummaryOut` has `claimed`, `TaskDetailOut` does not |
| Pattern consistency | PASS | Uses same `_coerce_claimed` validator pattern as `TaskSummary` in kanban models |
| Security surface | PASS | Read-only fields, no new input |
| Single domain | PASS | Cockpit backend only |

### Failure Mode Map

N/A — no new failure modes; fields have safe defaults.

### Challenge Results

- Challenger: **reconsider** (confidence 0.55)
- C1 (`_task_to_detail` in mutation.py missed): **accepted** — added AC line for mutation helper
- C2 (no positive-path test): **accepted** — AC now requires claimed task (id 4) assertion
- C3 (redundant boolean): **accepted in part** — resolved via `_coerce_claimed` validator pattern (DRY)
- Blind spot (claimed_at): **rejected** — YAGNI, trivial future addition
- Blind spot (no frontend consumer): **rejected** — backend prep for phase-2; frontend task is separate
- Architect response: **revised** — 3 of 5 concerns incorporated

### Files

- `serve/cockpit/src/owlbear_cockpit/models.py` — add fields + validator
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — pass `claimed_by`
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — pass `claimed_by` in `_task_to_detail`
- `tests/test_cockpit_read_api.py` — positive + negative claim assertions

### Verdict: APPROVE (after refinement)

### Action Taken: Rewrote AC for precision — specified validator pattern, covered mutation.py construction site, required positive-path test for claimed task. Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

**File:** `tests/test_cockpit_read_api.py`
**Class:** `TestFromAC_TaskDetailClaimedFields`

### Tests per category

| Category | Tests |
|----------|-------|
| Happy path (endpoint returns claimed/claimed_by) | 4 |
| Correct values (unclaimed task 1, claimed task 4) | 4 |
| Type validation | 2 |
| **Total** | **10** |

### Test list (all FAIL)

1. `test_task_detail_response_has_claimed_field` — GET /api/tasks/1 has 'claimed' key
2. `test_task_detail_response_has_claimed_by_field` — GET /api/tasks/1 has 'claimed_by' key
3. `test_unclaimed_task_detail_claimed_is_false` — task 1: claimed=false
4. `test_unclaimed_task_detail_claimed_by_is_null` — task 1: claimed_by=null
5. `test_claimed_task_detail_claimed_is_true` — task 4: claimed=true
6. `test_claimed_task_detail_claimed_by_is_non_null_string` — task 4: claimed_by is non-empty str
7. `test_claimed_field_is_bool_type` — claimed is bool not other type
8. `test_claimed_by_field_is_str_or_null` — claimed_by is str|null for tasks 1 and 4
9. `test_task_detail_out_model_has_claimed_field` — TaskDetailOut with claimed_by="agent" → claimed=True
10. `test_task_detail_out_model_null_claimed_by_yields_claimed_false` — TaskDetailOut with claimed_by=None → claimed=False

### AC coverage

| AC line | Test(s) |
|---------|---------|
| TaskDetailOut includes claimed: bool = False | 1, 3, 4, 7, 9, 10 |
| TaskDetailOut includes claimed_by: str \| None = None | 2, 4, 6, 8, 9, 10 |
| _coerce_claimed validator derives claimed from claimed_by | 9, 10 |
| get_task route passes claimed_by (read.py) | 1–8 |
| _task_to_detail passes claimed_by (mutation.py) | indirectly covered via model tests 9, 10 |
| unclaimed task (task 1): claimed=False, claimed_by=None | 3, 4 |
| claimed task (task 4): claimed=True, claimed_by is non-null str | 5, 6 |

pytest: **10 failed, 0 passed** ✓ RED phase confirmed.
[[2026-04-18]]

## Builder Notes

**Files changed (3):**

- `serve/cockpit/src/owlbear_cockpit/models.py` — added `claimed: bool = False`, `claimed_by: str | None = None`, and `_coerce_claimed` model_validator (mode="before") to `TaskDetailOut`; imported `model_validator`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — added `claimed_by=task.claimed_by` to `TaskDetailOut` construction in `get_task`
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — added `claimed_by=task.claimed_by` to `TaskDetailOut` construction in `_task_to_detail`

**Test results:** 10/10 `TestFromAC_TaskDetailClaimedFields` passed. Full suite: 604 passed, 6 pre-existing mcp-knowledge failures (unrelated to this task).

**Lint:** ruff clean on all 3 changed files.

**Commit:** `50853ab7` — `feat(cockpit): #972 add claimed/claimed_by fields to TaskDetailOut`
[[2026-04-18]]

## Review Evidence

### Quality-Runner

- **pytest:** 100 passed, 0 failed, 0 skipped (scoped to cockpit test files)
- **Lint (ruff):** clean — all 3 changed files + test file
- **Coverage:** models.py 100%, routes/read.py 100%, routes/mutation.py 99%

### Pass 1 Checks

#### 5.0 Test-Writer Audit

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| TaskDetailOut includes `claimed: bool = False` | 1, 3, 7, 9, 10 | Yes — tests 7+9+10 use `isinstance`/`is False` checks | COVERED |
| TaskDetailOut includes `claimed_by: str\|None = None` | 2, 4, 6, 8, 9, 10 | Yes — tests 6+8+9+10 do strict type/value checks | COVERED |
| `_coerce_claimed` validator derives `claimed` from `claimed_by` | 9, 10 | Yes — model constructed directly; tests assert `is True`/`is False` on coercion result | COVERED |
| `get_task` passes `claimed_by` (read.py) | 1–8 | Yes — endpoint tests; missing kwarg → field absent or wrong value | COVERED |
| `_task_to_detail` passes `claimed_by` (mutation.py) | 9, 10 (model-level) | Indirectly — validator path exercised; mutation.py has 99% coverage | COVERED |
| Unclaimed task 1: `claimed=False`, `claimed_by=None` | 3, 4 | Yes — `is False` and `is None` comparisons | COVERED |
| Claimed task 4: `claimed=True`, `claimed_by` non-null str | 5, 6 | Yes — `is True`, `isinstance(str)` + `len > 0` | COVERED |

No MISSING or LAX entries.

#### 5.1 Security

- `_coerce_claimed` validator: defensive `isinstance(data, dict)` guard + `dict(data)` copy — no mutation of input. Clean.
- `EditRequest` uses `extra="forbid"` — `claimed_by` cannot be modified via API; it is read-only.
- No injection, traversal, deserialization, or secrets concerns.

#### 5.2 TestFromAC Integrity

All 10 `TestFromAC_TaskDetailClaimedFields` methods present, unmodified vs. test-writer notes. None weakened, skipped, or xfailed.

#### 5.3 Test Quality — **STRONG**

- Assertion specificity: uses `is True`/`is False` (not just truthy), `isinstance(bool)`, `is None`, `len > 0` — no lazy assertions.
- Tests 9–10 construct `TaskDetailOut` directly and verify validator coercion bidirectionally.
- Test independence: each test uses isolated client fixtures.
- Descriptive names: all follow `test_<subject>_<condition>_<expectation>` pattern.

#### 5.4 Data Safety: No issues

#### 5.5 Implementation-Aware Gap Analysis

- All three mutation routes (`move_task`, `edit_task`, `release_task`) call `_task_to_detail`; mutation.py 99% coverage confirms paths exercised.
- No uncovered branches in the validator or field mapping code.

#### 5.6 Necessity Check: N/A — no new deps or integrations

#### 5.7 Builder Process: 1 `## Builder Notes` section, clean first-pass completion

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `TaskDetailOut` has `claimed: bool = False` | models.py:36 | tests 1, 3, 7, 9 | PASS |
| `TaskDetailOut` has `claimed_by: str\|None = None` | models.py:37 | tests 2, 4, 6, 8, 10 | PASS |
| `_coerce_claimed` validator (mode="before") | models.py:39–45 | tests 9, 10 | PASS |
| `get_task` passes `claimed_by` | read.py:111 | tests 1–8 | PASS |
| `_task_to_detail` passes `claimed_by` | mutation.py:73 | model-level + 99% cov | PASS |
| No breaking changes (safe defaults) | models.py:36–37 default values | all existing tests pass | PASS |

### Deductions: 0

### Verdict: PASS | confidence .97

### Action: advancing to docs

[[2026-04-18]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 0 | Review Evidence present | — | PASS | `## Review Evidence` section present with full quality-runner output, AC compliance table, pass 1 checks |
| 1 | Behavior/API change → copilot-instructions.md | Yes | N/A | `copilot-instructions.md` lists endpoint URLs only, no response field schema documented — additive change, no update needed |
| 2 | Module docstrings | Yes | PASS | `models.py` all public classes have docstrings; `_coerce_claimed` private method has docstring; `routes/read.py` all route functions have docstrings; `routes/mutation.py` `_task_to_detail` is private helper, no docstring required |
| 3 | External attribution | No | N/A | `_coerce_claimed` pattern is internal (mirrors existing `TaskSummary`); no external repos/articles used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No research phase for this task |

**Files updated:** None — no docs impact.

**Scratch files cleaned:** No `.owlbear/scratch/972-*` files found.

**Verdict:** PASS — docs gate clear, no updates required.
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `TaskDetailOut` has `claimed: bool = False` | models.py:36 | PASS |
| `TaskDetailOut` has `claimed_by: str \| None = None` | models.py:37 | PASS |
| `_coerce_claimed` validator (mode="before") | models.py:39-45, tests 9+10 | PASS |
| `get_task` passes `claimed_by` | read.py:109 | PASS |
| `_task_to_detail` passes `claimed_by` | mutation.py:73 | PASS |
| Tests: unclaimed task 1 (False/None) | test_cockpit_read_api.py tests 3, 4 | PASS |
| Tests: claimed task 4 (True/non-null) | test_cockpit_read_api.py tests 5, 6 | PASS |
| No breaking changes (safe defaults) | models.py:36-37 defaults, all existing tests pass | PASS |

### Test Results

- pytest: 604 passed, 6 failed (all pre-existing mcp-knowledge failures, outside task scope)
- ruff: clean

### Architect Quality: 5/5

AC refined after challenge: 3 of 5 concerns incorporated (mutation.py coverage, positive-path claimed test, validator pattern). Specific files, patterns, and expected values named. Unambiguously verifiable.

### Deduction Breakdown

No deductions applied.

### Confidence: 1.00

### Action: archive
