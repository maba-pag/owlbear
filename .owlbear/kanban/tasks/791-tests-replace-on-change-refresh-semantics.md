---
id: 791
title: Tests — Replace-on-change refresh semantics
status: in-progress
priority: needed
created: '2026-04-10T12:31:33.717159+00:00'
updated: '2026-04-12T22:12:39.114818+00:00'
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