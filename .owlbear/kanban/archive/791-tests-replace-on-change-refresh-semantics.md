---
id: 791
title: Tests — Replace-on-change refresh semantics
status: done
priority: needed
created: '2026-04-10T12:31:33.717159+00:00'
updated: '2026-04-11T17:23:42.480664+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on:
- 785
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify: when content changes for an existing document, the old document is deleted via `delete_document_data(existing_id)` before new insertion
- Tests verify: no ghost documents remain after content-change re-ingest (F1 regression test)
- Tests verify: unchanged content still skips (no delete, no re-ingest)
- File: `tests/test_replace_on_change_775.py`

## Context
- WS-D: Pipeline Integration
- Scope item 10 from #775
- See research F1: ghost document bug — existing_id unused in changed branch
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test suite for one behavioral concern: replace-on-change semantics |
| Interface clarity | PASS | AC specifies exact method calls (`delete_document_data(existing_id)`), ordering (delete before insert), and skip behavior |
| Dependency correctness | WARN | Declared dep on #785 (Schema v9, `todo`) is spurious — all 10 tests use MagicMock, zero real DB. No `edit_task` tool available to remove. Impact: scheduling delay only |
| Module layering | PASS | Test file in `tests/` — no layering concern |
| TDD compliance | PASS | This IS the test task — no preceding test needed |
| KISS/YAGNI | PASS | 10 tests covering 3 AC lines with shared helpers. No over-engineering |
| Premise challenge | PASS | Tests verify real bug fix: F1 ghost document bug where `existing_id` was captured but never passed to `delete_document_data()` in the changed-content branch |
| Pattern consistency | PASS | Uses `pytest.mark.asyncio`, `MagicMock`/`AsyncMock`, helper factories — matches existing test patterns (e.g., `test_authenticated_content_pipeline_775.py`) |
| Security surface | PASS | Test file — no new system boundary |
| Single domain | PASS | Knowledge domain only |

### Codebase Evidence

- Implementation: `serve/knowledge/src/owlbear_knowledge/ingest.py` lines 169-172 — `if existing_id is not None: self._docs.delete_document_data(existing_id)` before `insert_document`
- Delete cascade: `serve/knowledge/src/owlbear_knowledge/document_store.py` lines 245-267 — removes entities, edges, chunks, document_status, documents
- Delta detection: `serve/knowledge/src/owlbear_knowledge/status_store.py` `check_content_changed()` returns `(changed, existing_document_id)`
- Test file: `tests/test_replace_on_change_775.py` — 10 tests already exist covering all 3 AC lines
- Overlapping coverage: `tests/test_authenticated_content_pipeline_775.py` `TestFromAC_ReplaceOnChangeRefresh` — 4 additional tests for same behavior (SC10)

### Challenge Results
- Challenger: proceed (confidence 0.72)
- Concerns: spurious #785 dependency (tests use mocks, no real DB needed); test file already exists (task may be pre-complete)
- Architect response: accepted both observations. Dependency cannot be removed (no `edit_task` tool); test-writer will process as pass-through if tests already pass. Neither concern affects AC precision or architectural soundness. Override justified: 0.72 reflects operational scheduling concern, not structural defect.

### Notes for Test-Writer
- Test file `tests/test_replace_on_change_775.py` appears to already exist with full AC coverage. Verify tests pass; if green, issue pass-through note.
- Dependency on #785 uses mocks — tests are runnable independent of schema v9 migration status.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. Test file pre-exists with full coverage.
[[2026-04-11]]
## Test-Writer Notes

- **Test file:** `tests/test_replace_on_change_775.py`
- **Disposition:** Pre-existing file — pass-through (all tests already GREEN)

### Test Run Result

```
10 passed in 5.06s
```

All 10 tests pass against the current implementation. The RED phase was completed in a prior cycle; the implementation fix is already in place.

### AC Coverage Table

| AC Line | Tests | Status |
|---------|-------|--------|
| AC1 — `delete_document_data(existing_id)` called before insert | `test_delete_called_with_exact_existing_id`, `test_delete_precedes_insert_when_content_changes`, `test_new_document_no_prior_id_skips_delete` | PASS (3) |
| AC2 — No ghost documents after content-change re-ingest (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change`, `test_back_to_back_changes_each_delete_own_prior`, `test_change_path_returns_ok_status` | PASS (3) |
| AC3 — Unchanged content skips (no delete, no re-ingest) | `test_unchanged_content_returns_skipped`, `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert`, `test_unchanged_content_preserves_existing_document_id_in_result` | PASS (4) |

**Total: 10 tests, all PASS — implementation pre-complete. Builder proceed to verification/done.**
[[2026-04-11]]
## Builder Notes

- **Disposition:** Pass-through — test file `tests/test_replace_on_change_775.py` pre-exists with full AC coverage; implementation already complete from prior cycle.
- **Files changed:** None — no code implementation required (test-only task, tests pre-existing)

### Test Results

```
10 passed
```

| AC Line | Tests | Status |
|---------|-------|--------|
| AC1 — `delete_document_data(existing_id)` called before insert | 3 tests | PASS |
| AC2 — No ghost documents after re-ingest (F1 regression) | 3 tests | PASS |
| AC3 — Unchanged content skips (no delete, no re-ingest) | 4 tests | PASS |

### Lint

```
ruff check tests/test_replace_on_change_775.py — All checks passed!
```

### Evidence Summary

- 10/10 tests pass against current implementation
- ruff: clean
- No code changes required — implementation fix was already in place from prior cycle
- Builder-discovered tests: none (full AC coverage already present)
[[2026-04-11]]
## Review Evidence

### Test Results
pytest: **10 passed, 0 failed** (independently run — builder self-report confirmed)

### Lint
ruff: **clean** — 0 violations

### Coverage
`owlbear_knowledge.ingest`: 67% — no deduction. Builder made **no code changes** (pass-through task); 90% threshold applies to touched modules only. Zero modules modified. Other test files cover remaining ingest paths.

### TestFromAC_* Integrity
- `TestFromAC_ReplaceOnChangeSemantics` present and unmodified — builder added no code, so no modifications possible. No weakened or removed assertions. ✓

### AC Compliance

| AC Line | Tests | Evidence | Status |
|---------|-------|----------|--------|
| AC1 — `delete_document_data(existing_id)` called before insert | `test_delete_called_with_exact_existing_id`, `test_delete_precedes_insert_when_content_changes`, `test_new_document_no_prior_id_skips_delete` | `assert_called_once_with(prior_id)` fails if delete omitted; `call_order.index("delete") < call_order.index("insert")` fails if order reversed | COVERED |
| AC2 — No ghost documents after content-change re-ingest (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change`, `test_back_to_back_changes_each_delete_own_prior`, `test_change_path_returns_ok_status` | Exact ID assertion + call_count=2 across successive changes; both delete AND insert asserted to fire | COVERED |
| AC3 — Unchanged content skips (no delete, no re-ingest) | `test_unchanged_content_returns_skipped`, `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert`, `test_unchanged_content_preserves_existing_document_id_in_result` | `assert_not_called()` on both delete and insert; also verifies existing_id preserved in result | COVERED |

### Assertion Quality
STRONG — uses `assert_called_once_with` (not just `assert_called`), call-order side-effect tracking, `assert_not_called()` for all negative paths, `call_count` for multi-ingest scenario. No lazy `assert result` patterns found.

### Mutation Robustness
- Remove `delete_document_data(existing_id)` line → AC1 and AC2 tests fail
- Reverse delete/insert order → `test_delete_precedes_insert_when_content_changes` fails on call_order index assertion
- Remove `if existing_id is not None:` guard → `test_new_document_no_prior_id_skips_delete` fails
- Remove early return when `not changed` → both `test_unchanged_content_skips_delete` and `test_unchanged_content_skips_insert` fail

### Security
Test file only — no system boundary, no new dependencies, no security surface.

### Builder Process Quality
CLEAN — 1 builder cycle, pass-through disposition (pre-existing tests). No loop pattern.

### Deductions
None.

### Verdict
Confidence: **.96** → **PASS #791 → docs**
[[2026-04-11]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` pass-through — no application logic created or modified; tests pre-existed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified; zero files changed by builder |
| 3 | External attribution | No | N/A | No external patterns referenced in AC, research, or review |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | Task references F1 finding from parent #775 research doc (`.owlbear/research/775-phase1-browser-pipeline-schema.md`) — no dedicated #791 research doc produced |

### Scratch Files
None found matching `.owlbear/scratch/791-*`.

### Files Updated
None — no docs impact.

### Verdict
No documentation changes required. All checklist items N/A. Advancing to done.
[[2026-04-11]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — `delete_document_data(existing_id)` called before insert | `test_delete_called_with_exact_existing_id` (assert_called_once_with), `test_delete_precedes_insert_when_content_changes` (call_order index assertion), `test_new_document_no_prior_id_skips_delete` (assert_not_called) | PASS |
| AC2 — No ghost documents after re-ingest (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change` (delete + insert both asserted), `test_back_to_back_changes_each_delete_own_prior` (call_count=2 + per-ID tracking), `test_change_path_returns_ok_status` | PASS |
| AC3 — Unchanged content skips (no delete, no re-ingest) | `test_unchanged_content_returns_skipped`, `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert` (all assert_not_called), `test_unchanged_content_preserves_existing_document_id_in_result` | PASS |
| File: `tests/test_replace_on_change_775.py` | File exists, committed at `12e0e423`, clean working tree | PASS |

### Test Results
- pytest (task-scoped): 10 passed, 0 failed
- pytest (full suite): 291 failed, 3462 passed — all failures pre-existing/unrelated (orchestrator_loop, planner_gates, knowledge_foundation, analysis, etc.). Zero failures in task scope.
- ruff: All checks passed

### Reviewer Evidence
Detailed section present with .96 PASS verdict. Includes mutation robustness analysis, assertion quality assessment (STRONG), and per-AC coverage mapping. Trusted code-level findings.

### Architect Quality: 4/5
AC lines are specific — exact method names (`delete_document_data(existing_id)`), ordering constraints (delete before insert), and skip behavior (no delete, no re-ingest). Minor gap: spurious dependency on #785 (tests use mocks, no real DB needed) caused unnecessary scheduling constraint. Otherwise clean.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 3 + file check covered) → −0.00
- Lint violations: 0 → −0.00
- AC quality ≤ 3: no (4/5) → −0.00
- Missing reviewer evidence: no (detailed) → −0.00
- Full-suite failures in task scope: 0 → −0.00

### Confidence: .98
### Action: archive