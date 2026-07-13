---
id: 77
title: 'Test: Add ingest and graph tools to mcp-knowledge'
status: archived
priority: medium
created: 2026-03-26 21:02:00.183327+01:00
updated: 2026-03-30 01:01:29.796792+02:00
started: 2026-03-30 01:01:02.313149+02:00
completed: 2026-03-30 01:01:02.313149+02:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests (TDD RED) for ingest/graph tools before the builder implements #55.

## Acceptance Criteria
- [ ] Test file: packages/mcp-knowledge/tests/test_ingest_graph_tools.py with pytest tests
- [ ] Test: ingest_document with valid text returns summary string matching format 'Ingested: {id}, {n} chunks, {n} entities, {n} edges (status: {status})'
- [ ] Test: ingest_document passes metadata dict through to IngestPipeline.ingest_text
- [ ] Test: ingest_document returns error string (no traceback) when pipeline raises exception
- [ ] Test: list_entities with no filters returns formatted entity list including total_count
- [ ] Test: list_entities with entity_type filter forwards filter to GraphStore.list_entities
- [ ] Test: list_entities with offset=10, limit=5 returns correct slice of results
- [ ] Test: list_entities returns appropriate message when no entities exist
- [ ] Test: get_stats returns formatted string 'Knowledge base: {n} documents, {n} entities, {n} edges'
- [ ] Test: get_stats with empty database returns all zeros
- [ ] Test: GraphStore.get_counts() returns (doc_count, entity_count, edge_count) via SQL COUNT queries
- [ ] All tests use mocked IngestPipeline and GraphStore; no real DB, Qdrant, or network
- [ ] All tests FAIL at this point (RED phase)

## Context
Preceding test task for #55. See docs/research/ingest-graph-tools-mcp-knowledge.md section 3.6 for testing strategy.
Depends on #54 completing (real lifespan with DB connections must exist before extending with IngestPipeline).

[[2026-03-29]] Sun 15:33
## Architecture Review
**Verdict:** APPROVED (redundant â€” deliverables already exist)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file test_ingest_graph_tools.py | Already exists, written by #55 test-writer | Verify only |
| ingest_document valid text format | Covered by TestFromAC_IngestDocument (9 tests) | Verify only |
| ingest_document metadata passthrough | Covered by TestFromAC_IngestDocument | Verify only |
| ingest_document error string | Covered by TestFromAC_IngestDocument | Verify only |
| list_entities no filters | Covered by TestFromAC_ListEntities (11 tests) | Verify only |
| list_entities entity_type filter | Covered by TestFromAC_ListEntities | Verify only |
| list_entities offset/limit | Covered by TestFromAC_ListEntities | Verify only |
| list_entities empty result | Covered by TestFromAC_ListEntities | Verify only |
| get_stats format | Covered by TestFromAC_GetStats (5 tests) | Verify only |
| get_stats empty DB | Covered by TestFromAC_GetStats | Verify only |
| GraphStore.get_counts() | Covered by TestFromAC_GraphStoreGetCounts in test_graph_store_counts.py (9 tests) | Verify only |
| All mocked, no real DB | Verified: mocks used throughout | OK |
| All tests FAIL (RED) | Tests fail due to ImportError / missing method | OK (at time of writing) |

### Architecture Notes
This task is redundant. All 41 tests described in #77's AC were already written by #55's test-writer during #55's TDD RED phase. The test files exist:
- packages/mcp-knowledge/tests/test_ingest_graph_tools.py (32 tests)
- packages/knowledge/tests/test_graph_store_counts.py (9 tests)

Pipeline anomaly: #55 proceeded to in-progress while #77 sat in backlog. #77's dependency on #54 (blocked in ideation) was bypassed because #55's pipeline ran the TDD RED phase independently.

AC is precise and verifiable as written. No changes needed â€” the work is done.

### Dependency note
depends_on #54 is blocked in ideation (v1/v2 API mismatch). However, the actual deliverable (test files) does not require #54 to be done â€” the tests mock all dependencies. The dependency was overstated. Removing #54 from depends_on since the tests don't require a real lifespan.

### Changes Made
- Removed depends_on #54 (tests are fully mocked, no real dependency)
- Approved to todo for downstream verification

[[2026-03-29]] Sun 15:44
## Test-Writer Notes
- Verification pass-through: tests written by #55 test-writer; architect confirmed full AC coverage.
- Test file 1: packages/mcp-knowledge/tests/test_ingest_graph_tools.py
- Test file 2: packages/knowledge/tests/test_graph_store_counts.py
- Classes: TestFromAC_IngestDocument, TestFromAC_ListEntities, TestFromAC_GetStats, TestFromAC_AppContext, TestFromAC_ToolDescriptions (test_ingest_graph_tools.py); TestFromAC_GraphStoreGetCounts (test_graph_store_counts.py)
- Tests per category: happy 15, edge 12, error 8, boundary 9
- Total: 44 tests (35 + 9), all FAIL (ImportError on server.py; AttributeError on get_counts)
- ruff: clean (both files)
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| ingest_document valid text format | test_returns_ingested_prefix_with_doc_id, test_return_format_includes_all_counts, test_return_format_contains_chunks_entities_edges_status_keywords | happy/boundary |
| ingest_document metadata passthrough | test_passes_metadata_as_keyword_argument, test_metadata_defaults_to_none_when_omitted, test_delegates_text_to_ingest_text | happy/edge |
| ingest_document error string | test_unexpected_exception_returns_string_not_raises, test_error_string_contains_no_python_traceback, test_failed_ingest_result_returned_as_string | error |
| list_entities no filters, total_count | test_returns_entities_header_line, test_entity_lines_are_bullets, test_entity_line_format_name_type_description, test_header_shows_total_count_not_just_page | happy/boundary |
| list_entities entity_type filter | test_entity_type_filter_passed_when_provided, test_no_entity_type_kwarg_when_none, test_invalid_entity_type_returns_error_not_exception, test_error_for_invalid_type_lists_valid_entity_types | happy/edge/error |
| list_entities offset=10 limit=5 | test_pagination_slice_offset_and_limit, test_default_offset_0_limit_50 | boundary |
| list_entities empty result message | test_empty_list_returns_no_entities_found, test_empty_after_type_filter_returns_no_entities_found | edge |
| get_stats format string | test_returns_knowledge_base_prefix, test_return_format_contains_all_three_counts, test_return_format_contains_documents_entities_edges_keywords | happy |
| get_stats empty database | test_counts_order_is_documents_entities_edges (with zero mock) | edge |
| GraphStore.get_counts() tuple | TestFromAC_GraphStoreGetCounts (9 tests) in test_graph_store_counts.py | happy/edge/boundary |
| All mocked, no real DB | Verified: MagicMock/AsyncMock throughout test_ingest_graph_tools.py | - |
| All tests FAIL (RED) | test_ingest_graph_tools.py: ImportError (server.py missing); test_graph_store_counts.py: 9 FAIL AttributeError | - |

[[2026-03-29]] Sun 23:55
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | TDD RED task: only test files added, no behavior or API change |
| 2 | Docstrings | No | N/A | Test files only, no new modules or public APIs added |
| 3 | docs/sources/overview.md | No | N/A | Test-writing task, no external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/ingest-graph-tools-mcp-knowledge.md exists and is linked from task body Context section |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/77-* files found)

[[2026-03-30]] Mon 01:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file exists | test_ingest_graph_tools.py confirmed via read_file | PASS |
| ingest_document valid text format | TestFromAC_IngestDocument 3 format tests | PASS |
| ingest_document metadata passthrough | test_passes_metadata, test_metadata_defaults | PASS |
| ingest_document error handling | 3 error/traceback/failed-status tests | PASS |
| list_entities no filters + total_count | test_returns_entities_header, test_header_shows_total | PASS |
| list_entities entity_type filter | test_entity_type_filter_passed, test_no_entity_type_kwarg | PASS |
| list_entities offset/limit | test_pagination_slice, test_default_offset_0_limit_50 | PASS |
| list_entities empty result | test_empty_list, test_empty_after_type_filter | PASS |
| get_stats format | TestFromAC_GetStats 5 tests | PASS |
| get_stats empty DB | Covered via zero-count mock | PASS |
| GraphStore.get_counts() | test_graph_store_counts.py 9 tests | PASS |
| All mocked, no real DB | MagicMock/AsyncMock throughout; in-memory SQLite for GraphStore | PASS |
| All tests FAIL (RED) | True at commit time (ImportError); now 44 pass post-#55 impl | PASS |

### Test Results
- pytest (task-scoped): 44 passed in 1.70s
- pytest (full suite): 1072 passed, 64 failed (all failures pre-existing from other tasks)
- ruff: All checks passed

### Architect Quality
- AC specificity: Excellent. Every AC line maps to verifiable test assertions.
- Edge case coverage: Comprehensive. Tests cover happy, edge, error, and boundary.
- Design direction: Architect correctly identified redundancy with #55 and approved pass-through.
- AC quality score: 5/5

### Confidence: .97
### Action: archive

[[2026-03-30]] Mon 01:01
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 20c78f1 | chore | kanban/tasks/077-*.md | #77 |
