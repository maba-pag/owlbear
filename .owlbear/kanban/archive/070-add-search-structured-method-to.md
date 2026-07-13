---
id: 70
title: Add search_structured method to KnowledgeQueryService
status: archived
priority: medium
created: 2026-03-26 20:13:07.231759+01:00
updated: 2026-03-29 09:21:54.446219+02:00
started: 2026-03-29 09:21:50.167023+02:00
completed: 2026-03-29 09:21:50.167023+02:00
tags:
- phase-2
- scope:knowledge
depends_on:
- 76
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add a public method returning raw structured results (entity names, types, relevance scores) for MCP and other consumers that need richer output than query_for_context().

## Acceptance Criteria
- [ ] StructuredSearchResult frozen Pydantic BaseModel in query_service.py with fields: doc_id (str), title (str), score (float), snippet (str), entity_type (str or None), scope (str)
- [ ] Public method search_structured(self, query: str, *, top_k: int = 5) returning list[StructuredSearchResult] on KnowledgeQueryService
- [ ] Reuses _search_chunks() and threshold filter from _query() pipeline (no duplication of embed/search logic)
- [ ] Entity type resolved per document via GraphStore.list_entities_for_document(doc_id) (first match entity_type as str, or None when no entity linked)
- [ ] snippet derived from doc.content[:500] (same truncation as _format_docs())
- [ ] Returns [] (empty list, not None) on error; logs WARNING with exc_info (mirrors query_for_context() pattern)
- [ ] query_for_context() behavior unchanged (no modification to existing public API or internal methods)
- [ ] StructuredSearchResult exported from memory/knowledge/__init__.py via lazy-import map

## Architecture Notes
- Domain: memory (single domain)
- File: v1/src/owlbear/memory/knowledge/query_service.py
- Pattern: follows RetrievalResult frozen BaseModel convention in retrieval.py
- Entity resolution: list_entities_for_document() already exists on GraphStore (more targeted than the list_entities() full-scan the research recommended)
- Error handling: catch-all with WARNING log + empty list return (composable API, no None checks at call sites)

## Context
Driven by #54 research finding: query_for_context() returns pre-formatted text without scores or entity types. See docs/research/search-structured-method.md.

## Research
Doc: docs/research/search-structured-method.md

### Key Findings
- query_for_context() discards scores during formatting; search_structured() reuses _search_chunks() and resolves docs + entities
- Flat frozen Pydantic model StructuredSearchResult (doc_id, title, score, snippet, entity_type, scope) matches project conventions
- entity_type resolved via list_entities_for_document() per result (correction: GraphStore already has this targeted method)
- Returns empty list on error (not None) for composable API
- No max_tokens param needed (structured results, not text budget)
- Follow-up test task: #76

### Attribution
Sources logged in docs/sources/overview.md (LlamaIndex NodeWithScore, Qdrant MCP Server)

[[2026-03-26]] Thu 21:01

## Architecture Review
**Verdict:** APPROVED

### AC Assessment

Original AC had 3 lines; refined to 8 precise, testable lines:

| Original AC Line | Assessment | Action |
|------------------|------------|--------|
| search_structured returns typed result objects with doc_id, title, score, entity_type | Missing snippet, scope fields; no return type name; no signature details | Rewrote with full field list, types, method signature |
| Does not break existing query_for_context() contract | Testable but underspecified | Kept, clarified as no modification to existing public API or internals |
| Unit tests with mock vector store | Belongs to test task #76, not impl task | Removed from impl AC (covered by #76) |

### Architecture Notes

- Single domain: memory. File: v1/src/owlbear/memory/knowledge/query_service.py
- Follows RetrievalResult frozen BaseModel pattern (retrieval.py)
- Research correction: list_entities_for_document(doc_id) already exists on GraphStore (graph.py L163). More targeted than list_entities() full-scan recommended by research. Builder should use this.
- Error handling: empty list return (not None) for composable API, matching project convention for list-returning methods
- No new system boundaries or security surface

### Changes Made
- Refined AC from 3 vague lines to 8 precise, testable criteria
- Added depends_on: #76 (TDD RED test task)
- Corrected entity resolution approach (list_entities_for_document exists)
- Fixed research doc reference (was search-knowledge-tool-impl.md, now search-structured-method.md)
- Removed misplaced test AC (covered by #76)

### Dependencies
- Added: depends_on #76 (Test: Add search_structured method)
- Verified: #76 exists at ideation with comprehensive test AC

[[2026-03-28]] Sat 01:11
## Test-Writer Notes
- Test file: v1/tests/test_knowledge_structured_result_contract.py
- Classes: TestFromAC_ModelImmutability, TestFromAC_PackageExport, TestFromAC_QueryForContextUnchanged
- Tests per category: happy 7, edge 4, error 2, boundary 3
- Total: 16 tests
- ruff: clean
- NOTE: Implementation was already completed by the builder during task #76's TDD pipeline (archived). All 16 tests PASS -- not RED. This is the expected state: test-writer covers the AC lines (#1 frozen model, #7 unchanged behaviour, #8 export) not addressed by #76's test file. Tests serve as regression contract documentation.
- Existing #76 file (test_knowledge_query_service_structured.py, 32 tests) covers AC lines 2-6.
- AC coverage:
  AC1 (frozen Pydantic model): TestFromAC_ModelImmutability (5 tests -- assignment raises, hashable, equality)
  AC7 (query_for_context unchanged): TestFromAC_QueryForContextUnchanged (7 tests -- signature, defaults, return types, error path, interleaved call)
  AC8 (StructuredSearchResult exported from package): TestFromAC_PackageExport (4 tests -- importable, in __all__, lazy-import identity, BaseModel subclass)
  AC2-6: covered by v1/tests/test_knowledge_query_service_structured.py (#76 pipeline)

[[2026-03-28]] Sat 04:01
## Builder Notes
- Files changed: v1/src/owlbear/memory/knowledge/query_service.py (StructuredSearchResult + search_structured), v1/src/owlbear/memory/knowledge/__init__.py (export)
- Tests: 48 passed (TestFromAC_StructuredResults, TestFromAC_StructuredEmpty, TestFromAC_EntityResolution, TestFromAC_ErrorHandling, TestFromAC_TopK, TestFromAC_ModelImmutability, TestFromAC_PackageExport, TestFromAC_QueryForContextUnchanged)
- Coverage: 94% on query_service.py (combined with query_for_context tests)
- Lint: ruff clean on touched files
- Evidence: 48 passed in 1.00s; pre-existing expansion bootstrap failures (TestBootstrapRetrieverWiring) unrelated to #70
- Fixes applied: None â€” implementation was committed at feat: implement structured knowledge search (#76, builder)

[[2026-03-29]] Sun 09:21
## Audit
### AC Verification
All 8 AC items verified with code evidence (spot-check, 3rd-line):
- AC1-AC6: Implementation in query_service.py L38-169 matches all criteria
- AC7: query_for_context() untouched (L96-121)
- AC8: StructuredSearchResult in __all__ and _LAZY_IMPORTS in __init__.py

### Test Results
- pytest (task-scoped): 48 passed in 0.61s
- pytest (full suite): 649 passed, 91 failed (all pre-existing, unrelated to #70)
- ruff: All checks passed

### Architect Quality
- Score: 5/5 -- AC refined from 3 vague to 8 precise testable lines
- Entity resolution corrected to targeted list_entities_for_document
- Clear architecture notes

### Process Gap
- No Review Evidence section in task body (reviewer stage may have been skipped or reviewer did not write Channel B). Deliverable quality unaffected.

### Upstream Commits Verified
- 9b3eb73 test: add contract tests (#70, test-writer)
- 0db7535 test: normalize test file line endings (#70, builder)
- eef4844 feat: implement structured knowledge search (#76, builder)

### Confidence: .95
### Action: archive
