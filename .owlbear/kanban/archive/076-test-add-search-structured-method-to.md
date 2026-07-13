---
id: 76
title: 'Test: Add search_structured method to KnowledgeQueryService'
status: archived
priority: medium
created: 2026-03-26 20:40:19.702702+01:00
updated: 2026-03-28 00:53:29.365567+01:00
started: 2026-03-28 00:52:52.310062+01:00
completed: 2026-03-28 00:52:52.310062+01:00
tags:
- phase-2
- scope:knowledge
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests (TDD RED) for search_structured() before the builder implements #70.

## Acceptance Criteria
- [ ] New file v1/tests/test_knowledge_query_service_structured.py (follows *_expansion.py, *_consolidation.py precedent)
- [ ] Test: search_structured returns list[StructuredSearchResult] with doc_id, title, score, snippet, entity_type, scope
- [ ] Test: search_structured returns empty list when no results
- [ ] Test: search_structured returns empty list when all below threshold
- [ ] Test: search_structured resolves entity_type from linked entities (None when no entity linked)
- [ ] Test: search_structured catches exceptions and returns empty list with WARNING log
- [ ] Test: search_structured respects top_k parameter
- [ ] Test: search_structured does not break existing query_for_context() tests (run full test_knowledge_query_service*.py suite)
- [ ] All tests FAIL at this point (RED phase â€” ImportError on StructuredSearchResult import is expected)

## Context
Preceding test task for #70. See docs/research/search-structured-method.md and docs/research/search-structured-tests.md.

## Architecture Notes
- File: v1/tests/test_knowledge_query_service_structured.py (new, separate from existing 420-line test file)
- Reuse existing fixtures: mock_vector_store, mock_graph_store, mock_embedding_provider, _make_doc
- Add list_entities_for_document mock on mock_graph_store (method exists at graph.py L157)
- Import StructuredSearchResult from owlbear.memory.knowledge.query_service (will fail in RED â€” that's correct)
- 5 test classes: TestSearchStructuredResults, TestSearchStructuredEmpty, TestSearchStructuredEntityResolution, TestSearchStructuredErrorHandling, TestSearchStructuredTopK

[[2026-03-27]] Fri 03:36
## Test-Writer Notes
- Test file: v1/tests/test_knowledge_query_service_structured.py
- Classes: TestFromAC_StructuredResults, TestFromAC_StructuredEmpty, TestFromAC_EntityResolution, TestFromAC_ErrorHandling, TestFromAC_TopK
- Tests per category: happy 8, edge 5, error 5, boundary 4
- Total: 27 tests, all FAIL (ImportError on StructuredSearchResult import)
- ruff: clean
- AC coverage:
  - Returns list[StructuredSearchResult] with all fields: TestFromAC_StructuredResults (8 tests)
  - Empty list on no results: TestFromAC_StructuredEmpty.test_returns_empty_list_when_no_vector_results
  - Empty list when all below threshold: TestFromAC_StructuredEmpty.test_returns_empty_list_when_all_below_threshold
  - entity_type from linked entities: TestFromAC_EntityResolution (5 tests, incl. None when no entity)
  - Catches exceptions, returns [], WARNING log: TestFromAC_ErrorHandling (5 tests)
  - Respects top_k: TestFromAC_TopK (5 tests incl. top_k=0, top_k > available)

[[2026-03-27]] Fri 05:09
## Builder Notes
- Files changed: v1/src/owlbear/memory/knowledge/query_service.py, v1/src/owlbear/memory/knowledge/__init__.py
- Tests: 27 passed in tests/test_knowledge_query_service_structured.py.
- Additional regression slice: full test_knowledge_query_service*.py run reported 80 passed and 2 pre-existing failures in TestBootstrapRetrieverWiring (unrelated to touched files).
- Coverage: 94% on src/owlbear/memory/knowledge/query_service.py (79 passed, 3 deselected in scoped run excluding unrelated bootstrap failures).
- Lint: ruff passed on touched files.
- Evidence: Implemented StructuredSearchResult model, added search_structured API with threshold filtering, entity type resolution, top_k handling, exception logging and empty-list fallback, and exported symbol via knowledge lazy import map.
- Fixes applied: None beyond required implementation and lint cleanup.

[[2026-03-27]] Fri 07:48
## Review Evidence

### Test Results
- Structured search slice: 27 passed, 0 failed, 5 warnings.
- KnowledgeQueryService regression slice: 80 passed, 2 failed, 5 warnings. The two failures are the same pre-existing bootstrap wiring failures in v1/tests/test_knowledge_query_service_expansion.py lines 566 and 597 with ValueError: too many values to unpack (expected 3). No new structured-search regression appeared in this slice.

### Lint Results
- Task-scoped ruff on the touched files passed.

### Coverage
- Scoped coverage passed after isolated plugin suppression. v1/src/owlbear/memory/knowledge/query_service.py reported 41 percent because bare coverage reports the whole file, not just the new method, so that percentage is not the verdict basis for this scoped review.

### Pass 1 - Critical
- Test-writer AC coverage:
  - The snippet check in v1/tests/test_knowledge_query_service_structured.py lines 177-178 asserts only that snippet is a string and non-empty. A broken implementation returning any unrelated non-empty string would still pass, so the result-shape AC mapping is LAX.
  - The top_k checks at lines 511 and 547 assert only len(result) <= 2 and descending scores. They do not prove that the highest-scoring two hits are returned. An implementation that drops the best hit and returns any two descending results would still pass. No compensating TestBuilderDiscovered test was added.
- Security review: no issues found in the touched implementation.
- Test integrity: the final file still contains the five TestFromAC classes listed in the task body notes at lines 89, 222, 304, 409, and 491. Git shows the file as a new untracked file with no prior history, so comparison was against the recorded Test-Writer Notes rather than a prior commit. No removed or weakened TestFromAC coverage was found from that comparison.
- Test quality:
  - Assertion specificity: WEAK.
  - Negative and error-path coverage: ADEQUATE.
  - Manual mutation reasoning: WEAK. The loose top_k assertions would not catch a mutation that returns the wrong two results.
  - Test independence: STRONG.
  - Descriptive names: STRONG.
- Data safety: no issues found.
- Implementation-aware gap analysis: builder logic in v1/src/owlbear/memory/knowledge/query_service.py lines 142-146 performs threshold filtering and top_k slicing. The current tests do not pin exact top_k membership against doc IDs or exact score set, so the highest-hit selection behavior remains under-tested.

### AC Compliance
- New file exists: PASS. v1/tests/test_knowledge_query_service_structured.py is present.
- search_structured returns list[StructuredSearchResult] with doc_id, title, score, snippet, entity_type, scope: FAIL. doc_id, title, score, scope, and entity_type are covered, but snippet provenance is not specifically asserted.
- search_structured returns empty list when no results: PASS.
- search_structured returns empty list when all below threshold: PASS.
- search_structured resolves entity_type from linked entities and None when no entity linked: PASS.
- search_structured catches exceptions and returns empty list with WARNING log: PASS.
- search_structured respects top_k parameter: FAIL. The suite does not prove exact top_k membership or highest-hit retention.
- search_structured does not break existing query_for_context() tests: PASS, with the note above about the two unchanged pre-existing bootstrap failures.
- All tests FAIL at RED phase: not applicable in review; builder state is expected to pass.

### Verdict
- FAIL. Confidence .94. The implementation passes and the regression slice matches the builder report, but this task is the test-quality gate and two AC-critical assertions remain too permissive to prevent subtle regressions.

### Action Taken
- Returning task to todo. Required fix: strengthen the snippet assertion to verify content provenance, and strengthen top_k coverage to assert the exact returned doc IDs or score set for the requested top_k.

[[2026-03-27]] Fri 08:34
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited two weak assertion areas: snippet provenance and top_k exact membership
- Added 5 new tests (27 existing preserved, all 32 pass against correct builder implementation):
  - TestFromAC_StructuredResults: test_snippet_equals_document_content_when_short, test_snippet_is_first_500_chars_of_content
  - TestFromAC_TopK: test_top_k_returns_exact_count_not_at_most, test_top_k_returns_exact_highest_scoring_doc_ids, test_top_k_excludes_lower_scoring_docs
- All 32 tests PASS (implementation already handles these correctly)
- New tests will catch future regressions: snippet sourcing from wrong document or wrong truncation; top_k returning wrong or fewer docs
- ruff: clean

## Builder Notes
- Files changed: None in this retry cycle. Existing implementation in v1/src/owlbear/memory/knowledge/query_service.py already satisfies the strengthened assertions.
- Tests: v1/tests/test_knowledge_query_service_structured.py reports 32 passed and 0 failed.
- Regression slice: knowledge query service test files report 85 passed, 2 failed, 5 warnings. The 2 failures are pre-existing in v1/tests/test_knowledge_query_service_expansion.py with unpack mismatch in bootstrap wiring tests.
- Coverage: structured suite coverage run completed successfully.
- Lint: ruff check passed for v1/src/owlbear/memory/knowledge/query_service.py, v1/src/owlbear/memory/knowledge/__init__.py, and v1/tests/test_knowledge_query_service_structured.py.
- Evidence: retry tests for snippet provenance and exact top_k membership pass without additional implementation changes.
- Fixes applied: None.

[[2026-03-28]] Sat 00:53
## Commits

- 05b0915 test: add search_structured TDD tests (#76, auditor) -- v1/tests/test_knowledge_query_service_structured.py, v1/src/owlbear/memory/knowledge/query_service.py
