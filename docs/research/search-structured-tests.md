# Test Patterns for search_structured() — TDD RED

> **Owning task:** #76 — Test: Add search_structured method to KnowledgeQueryService
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #76 writes failing TDD RED tests for `search_structured()` before the builder implements #70. This research validates feasibility and documents the mock/fixture patterns the test writer should follow.

## 2. Sources

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Existing tests for KnowledgeQueryService | `v1/tests/test_knowledge_query_service.py` | .95 |
| 2 | Expansion feature tests (separate file pattern) | `v1/tests/test_knowledge_query_service_expansion.py` | .90 |
| 3 | Consolidation feature tests (separate file pattern) | `v1/tests/test_knowledge_query_service_consolidation.py` | .90 |
| 4 | GraphStore.list_entities_for_document | `v1/src/owlbear/memory/knowledge/graph.py` L157 | .85 |
| 5 | Entity model with entity_type field | `v1/src/owlbear/memory/knowledge/models.py` L85 | .85 |
| 6 | Parent research doc for #70 | `docs/research/search-structured-method.md` | .95 |

## 3. Analysis

### 3.1 Test File Placement

| Option | Precedent | KISS |
|--------|-----------|------|
| A: Extend `test_knowledge_query_service.py` (420 lines) | No — expansion and consolidation each got separate files | Low — file grows large |
| B: New `test_knowledge_query_service_structured.py` | Yes — matches `*_expansion.py`, `*_consolidation.py` pattern (Src 2, 3) | High |

**Recommendation (.90):** Option B — separate file.

### 3.2 Fixture and Mock Strategy

Existing tests (Src 1) use identical fixtures across all three test files:

| Fixture | Mock target | Return default | Reusable? |
|---------|-------------|----------------|-----------|
| `mock_vector_store` | `VectorStoreProtocol` | `search_similar → []` | Yes |
| `mock_graph_store` | `GraphStore` | `get_document → None` | Yes — need to add `list_entities_for_document` |
| `mock_embedding_provider` | `EmbeddingProvider` | `embed_hybrid → [HybridEmbedding(...)]` | Yes |
| `service` | `KnowledgeQueryService` | default construction | Yes |
| `_make_doc()` | helper | creates `Document` | Yes |

**New mock needed:** `mock_graph_store.list_entities_for_document` returning `list[Entity]`. GraphStore already has this method (Src 4, line 157) — more targeted than the `list_entities()` + dict lookup in the #70 research doc.

### 3.3 Entity Resolution API

The #70 research recommended `list_entities()` + dict lookup (approach B). However, `list_entities_for_document(document_id)` already exists (Src 4):

| API | Scope | KISS | Perf |
|-----|-------|------|------|
| `list_entities()` + dict | All entities, filter client-side | Medium | O(n) all entities |
| `list_entities_for_document(doc_id)` | Single document | High | O(1) SQL WHERE |

**Recommendation (.85):** Tests should mock `list_entities_for_document` — the builder will likely prefer the targeted API. If the builder chooses a different approach, tests remain valid (mock the actual call used).

### 3.4 RED Phase Failure Modes

Tests will fail in two ways:

| Failure | Cause | When |
|---------|-------|------|
| `ImportError` | `StructuredSearchResult` not yet defined in `query_service.py` | Module load |
| `AttributeError` | `search_structured()` not yet defined on `KnowledgeQueryService` | Test execution |

The `ImportError` is the primary RED signal — all tests fail at import time. This matches how `*_expansion.py` tests initially failed (importing `RetrievalResult` before it existed).

### 3.5 Test Class Organization

Following Src 1's pattern, organize by concern:

| Class | AC line tested |
|-------|----------------|
| `TestSearchStructuredResults` | Returns `list[StructuredSearchResult]` with all fields |
| `TestSearchStructuredEmpty` | Empty list on no results and below-threshold |
| `TestSearchStructuredEntityResolution` | entity_type from linked entities, None when unlinked |
| `TestSearchStructuredErrorHandling` | Catches exceptions, returns `[]`, WARNING log |
| `TestSearchStructuredTopK` | Respects top_k parameter |

## 4. Recommendation (.90 confidence)

Task #76 is fully feasible. The test writer should:

1. Create `v1/tests/test_knowledge_query_service_structured.py`
2. Copy fixture pattern from existing test files (Src 1–3)
3. Add `list_entities_for_document` mock on `mock_graph_store`
4. Import `StructuredSearchResult` from `query_service` (will fail → RED)
5. Organize into 5 test classes matching AC lines

No blockers. No external dependencies. Infrastructure is mature.

## 5. Follow-up Tasks

No additional tasks needed — #76 already captures the full test scope. #70 captures the implementation scope. The architect gates both.
