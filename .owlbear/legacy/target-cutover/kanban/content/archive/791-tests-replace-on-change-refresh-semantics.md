---
id: 791
title: Tests — Replace-on-change refresh semantics
status: archived
priority: medium
created: '2026-04-10T12:31:33.717159+00:00'
updated: '2026-04-13T05:22:06.078388+00:00'
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
[[2026-04-12]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Tests verify delete_document_data(existing_id) before new insertion | PASS — 3 tests cover exact ID, ordering, and no-prior-id skip | None |
| AC2: No ghost documents after content-change re-ingest (F1 regression) | PASS — F1 regression test, back-to-back changes, ok-status check | None |
| AC3: Unchanged content skips (no delete, no re-ingest) | PASS — 4 tests: skipped status, no delete, no insert, preserved ID | None |
| AC4: File: tests/test_replace_on_change_775.py | PASS — file exists with 218 lines, 11 tests | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for replace-on-change semantics only |
| Interface clarity | PASS | AC specifies exact function calls and behaviors to verify |
| Dependency correctness | FAIL | depends_on [785] spurious — tests use MagicMock exclusively, no schema v9 dependency |
| Module layering | PASS | Test file in tests/ directory |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Focused mock-based tests, no over-engineering |
| Premise challenge | PASS | Tests validate a documented bug fix (F1 ghost document) |
| Pattern consistency | PASS | TestFromAC_ naming, pytest.mark.asyncio, helper factories |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Dependency Analysis

DEPENDS_ON-CORRECTION: task #791 should have depends_on [] (empty). Current depends_on [785] is spurious — tests use MagicMock for doc_store and never touch schema, init_db, or any schema v9 features.

### Notes

- Test file already exists with 11 tests across 1 class covering all 3 behavioral AC lines
- Overlap exists with TestFromAC_ReplaceOnChangeRefresh in test_authenticated_content_pipeline_775.py (RED-phase scaffolding from parent #775) — consolidation is a cleanup concern, not an architecture block
- Tagged type:test — pass-through tag present

### Challenge Results
- Challenger: reconsider (confidence 0.65) — flagged test duplication and spurious dependency
- Architect response: partially accepted — dependency correction applied, duplication concern acknowledged but not blocking (AC scopes to specific file, cleanup is separate)

### Verdict: APPROVE
### Action Taken: Advanced to todo. Flagged DEPENDS_ON-CORRECTION for orchestrator: remove depends_on [785].
[[2026-04-12]]
## Test-Writer Notes

- **Task type**: `type:test` (NON_IMPL_TAGS → pass-through per w-tdd-red Step 1a)
- **Test file**: `tests/test_replace_on_change_775.py`
- **Test class**: `TestFromAC_ReplaceOnChangeSemantics`
- **Test count**: 10 tests across 3 AC categories
- **RED phase status**: N/A — all 10 tests PASS (implementation already complete)

### Why all tests pass

The `IngestPipeline.ingest()` fix for F1 (ghost document bug) was implemented as part of parent task #775 before this isolated test task was processed through the formal TDD pipeline. The implementation in `serve/knowledge/src/owlbear_knowledge/ingest.py` already contains:

```python
if existing_id is not None:
    self._docs.delete_document_data(existing_id)
self._docs.insert_document(doc_id, intake, scope=scope)
```

### AC coverage (verified passing)

| AC Line | Tests | Status |
|---------|-------|--------|
| AC1: delete_document_data(existing_id) before insert | `test_delete_called_with_exact_existing_id`, `test_delete_precedes_insert_when_content_changes`, `test_new_document_no_prior_id_skips_delete` | ALL PASS |
| AC2: No ghost documents after re-ingest (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change`, `test_back_to_back_changes_each_delete_own_prior`, `test_change_path_returns_ok_status` | ALL PASS |
| AC3: Unchanged content skips | `test_unchanged_content_returns_skipped`, `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert`, `test_unchanged_content_preserves_existing_document_id_in_result` | ALL PASS |
| AC4: File path | `tests/test_replace_on_change_775.py` exists | PASS |

### Builder action

No new implementation needed. Builder should verify AC conformance via `uv run pytest tests/test_replace_on_change_775.py` — all 10 tests should pass against existing `ingest.py`.
[[2026-04-13]]
## Builder Notes
- Task type: `type:test` — non-impl pass-through
- No code changes needed; implementation already exists in `serve/knowledge/src/owlbear_knowledge/ingest.py` (landed in parent #775)
- Test file: `tests/test_replace_on_change_775.py`

### Test Results
- **10/10 passed** (5.91s), no failures
- All tests in `TestFromAC_ReplaceOnChangeSemantics`

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1: delete_document_data(existing_id) before insert | test_delete_called_with_exact_existing_id, test_delete_precedes_insert_when_content_changes, test_new_document_no_prior_id_skips_delete | PASS |
| AC2: No ghost docs after re-ingest (F1 regression) | test_f1_regression_ghost_doc_not_left_after_change, test_back_to_back_changes_each_delete_own_prior, test_change_path_returns_ok_status | PASS |
| AC3: Unchanged content skips | test_unchanged_content_returns_skipped, test_unchanged_content_skips_delete, test_unchanged_content_skips_insert, test_unchanged_content_preserves_existing_document_id_in_result | PASS |
| AC4: File path | tests/test_replace_on_change_775.py exists | PASS |

### Lint
- No new files changed — lint not required for pass-through

[[2026-04-13]]
## Review Evidence

### Test Results
pytest: **10 passed, 0 failed** (quality-runner independent run)
ruff: **clean** — 0 violations
Coverage `owlbear_knowledge.ingest`: **64%** (expected — tests target replace-on-change path only, not full pipeline)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delete_document_data(existing_id) before insert | `test_delete_called_with_exact_existing_id` (assert_called_once_with exact ID), `test_delete_precedes_insert_when_content_changes` (call-order capture), `test_new_document_no_prior_id_skips_delete` (assert_not_called) — all pass | PASS |
| AC2: No ghost documents after re-ingest (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change` (delete + insert assertions), `test_back_to_back_changes_each_delete_own_prior` (call_count==2, exact IDs in order), `test_change_path_returns_ok_status` (status=='ok') — all pass | PASS |
| AC3: Unchanged content skips | `test_unchanged_content_returns_skipped`, `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert`, `test_unchanged_content_preserves_existing_document_id_in_result` — all pass | PASS |
| AC4: File tests/test_replace_on_change_775.py | File exists, 10 tests in TestFromAC_ReplaceOnChangeSemantics | PASS |

### Implementation Verification
Read `ingest.py` lines 203–210 — confirmed:
```python
if existing_id is not None:
    self._docs.delete_document_data(existing_id)
self._docs.insert_document(doc_id, intake, scope=scope)
```
Implementation matches what tests assert.

### Assertion Strength
All assertions are discriminating: `assert_called_once_with(exact_id)`, call-order index comparison with failure messages, `assert_not_called()`, `result.document_id == existing_id`. None would pass with a broken implementation.

### TestFromAC_ Modifications
None — class created fresh for this task; builder made zero code changes (correct pass-through handling for type:test task).

### Deductions
- Tests: 0 (10/10 pass)
- Lint: 0 (clean)
- AC compliance: 0 (all 4 lines covered)
- Assertion strength: 0 (all discriminating)
- TestFromAC_ integrity: 0 (no modifications)
- Security: 0 (no system boundary, pure mock-based)

### Verdict
Confidence: **0.97** → **PASS #791 → docs**
[[2026-04-13]]
## Docs Gate

| Item | Applies? | Status | Evidence |
|------|----------|--------|---------|
| 1. Behavior/API Change | No | N/A | type:test pass-through — no behavior/API changed by #791 |
| 2. Module Docstrings | No | N/A | No .py modules created/modified; only tests/test_replace_on_change_775.py added; module docstring (lines 1–11) is accurate (AC coverage, F1 regression description) |
| 3. External Attribution | No | N/A | Tests use MagicMock only — no external patterns |
| 4. CLI Changes | No | N/A | No CLI touchpoints |
| 5. Research Doc | No | N/A | No .owlbear/research/ doc produced for this task |
| 6. No Impact | Yes | CONFIRMED | Pure test file addition; all checklist items N/A |

Files updated: none
Scratch files: none found
No commit required.
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delete_document_data(existing_id) before insert | test_delete_called_with_exact_existing_id (assert_called_once_with), test_delete_precedes_insert (call-order capture), test_new_document_no_prior_id_skips_delete (assert_not_called) | PASS |
| AC2: No ghost docs after re-ingest (F1 regression) | test_f1_regression_ghost_doc_not_left_after_change (delete+insert asserts), test_back_to_back_changes_each_delete_own_prior (call_count==2, exact IDs), test_change_path_returns_ok_status | PASS |
| AC3: Unchanged content skips | test_unchanged_content_returns_skipped, _skips_delete, _skips_insert, _preserves_existing_document_id_in_result (assert_not_called + value checks) | PASS |
| AC4: File path | tests/test_replace_on_change_775.py exists, 220 lines, 10 tests | PASS |

### Test Results
- pytest: 10 passed, 0 failed (task-scoped); full suite clean
- ruff: All checks passed

### Architect Quality: 4/5
Specific, verifiable AC. Minor gap: spurious depends_on [785] flagged by arch review but not corrected upstream (cosmetic).

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality <=3: N/A (-.00)
- Missing reviewer evidence: 0 (-.00)
- Full-suite failures in scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 12e0e423 | test | tests/test_replace_on_change_775.py | #791 |