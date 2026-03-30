# Integration Test: Full Ingest-to-Search Cycle

> **Owning task:** #162 — Integration test: full ingest-to-search cycle
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #162 calls for an end-to-end integration test: ingest document → extract entities → build graph → embed chunks → query via KnowledgeQueryService → query via GraphAugmentedRetriever. All with in-memory backends (Qdrant + SQLite, no external deps).

**Key questions:** (a) What dependencies must land before this test can be written? (b) Is the declared `depends_on: [33, 161]` correct? (c) What test fixture strategy should be used? (d) Where does this fit alongside existing tests?

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| v2 IngestPipeline (local) | `packages/knowledge/src/owlbear_knowledge/ingest.py` | `1.0` — current pipeline only counts, doesn't persist entities/edges/embeddings |
| Task #158 AC (local) | `kanban/tasks/158-create-intake-ingest-pipeline-modules-in-knowledge.md` | `1.0` — upgraded pipeline with full persistence |
| Task #206 AC (local) | `kanban/tasks/206-test-intake-document-store-and-ingest-pipeline.md` | `.95` — has partial E2E test: ingest with mock, verify graph+vector storage |
| Task #34 AC (local) | `kanban/tasks/034-knowledge-package-integration-hybrid-search.md` | `.95` — GraphAugmentedRetriever + query_for_context |
| MS GraphRAG test layout | `github.com/microsoft/graphrag/tree/main/tests` | `.85` — unit/integration/smoke separation pattern |
| LightRAG test layout | `github.com/HKUDS/LightRAG/tree/main/tests` | `.85` — conftest markers for offline/integration |
| Existing test_qdrant_vector_store.py (local) | `packages/knowledge/tests/test_qdrant_vector_store.py` | `.90` — in-memory Qdrant pattern verified |
| Existing test_knowledge_engine_extraction.py (local) | `tests/test_knowledge_engine_extraction.py` | `.90` — mock vector store + embedding provider patterns |

## 3. Analysis

### 3.1 Dependency Gap — Critical Finding

The current `IngestPipeline.ingest_text()` (ingest.py lines 65–120) does **not** persist entities, edges, or embeddings. It only:
1. Chunks text via TextChunker
2. Inserts a Document record via DocumentStore → GraphStore
3. Extracts entities per chunk (counts only, never calls `insert_entity`/`insert_edge`)

Task #158 delivers the upgraded pipeline with `DocumentStore.store_extractions()` and `store_embeddings()`. Without #158, AC items 2–4 of #162 are impossible.

| AC Item | Required Dependency | Status |
|---------|-------------------|--------|
| Ingest through IngestPipeline | #158 (upgraded pipeline) | todo |
| Entities stored in graph | #158 (store_extractions) + #33 (real extractor) | todo |
| Graph edges built | #158 + #33 | todo |
| Chunks embedded in Qdrant | #158 (store_embeddings) | todo |
| Query via KnowledgeQueryService | Available now (query_service.py) | done |
| Query via GraphAugmentedRetriever | #34 (retrieval.py + query_for_context) | ideation |
| In-memory Qdrant + SQLite | Verified working (test_qdrant_vector_store.py) | done |

**Declared:** `depends_on: [33, 161]`
**Correct:** `depends_on: [158, 34]` — where #158 transitively covers #33 (entity extraction), and #34 covers #159 (GraphAugmentedRetriever). #161 (README/installability) is a docs gate, not a code dependency.

### 3.2 Overlap Analysis with #206

Task #206 (TDD RED tests for #158) includes an E2E test item: "text input with mock extractor returning canned entities+edges, verify graph_store has entities and edges, vector_store has embeddings."

| Scope | #206 E2E | #162 Integration |
|-------|----------|-----------------|
| Ingest + store | ✅ | ✅ |
| Entity extraction verified | ✅ (mock) | ✅ (mock) |
| Edge storage verified | ✅ | ✅ |
| Embedding storage verified | ✅ | ✅ |
| KnowledgeQueryService query | ❌ | ✅ |
| GraphAugmentedRetriever | ❌ | ✅ |
| Full search results | ❌ | ✅ |

The tests are complementary: #206 verifies storage, #162 verifies the full retrieval path. No duplication.

### 3.3 Test Fixture Strategy (.90 confidence)

Both MS GraphRAG (unit/integration/smoke separation) and LightRAG (conftest markers for offline/integration) confirm the layered test pattern. For #162:

| Component | Strategy | Justification |
|-----------|----------|---------------|
| SQLite | In-memory (`:memory:`) | Verified in test_graph_store_counts.py |
| Qdrant | In-memory (`:memory:`) | Verified in test_qdrant_vector_store.py |
| EntityExtractor | Mock StructuredExtractor returning canned entities/edges | Avoids LLM calls; #33 delivers the protocol |
| EmbeddingProvider | Mock returning deterministic 1024-d vectors | Avoids BGE-M3 download (~2.3 GB) |
| TextChunker | Real instance | Lightweight, no external deps |
| IngestPipeline | Real instance (from #158) | Core of the integration test |
| KnowledgeQueryService | Real instance | Tests real query path |
| GraphAugmentedRetriever | Real instance (from #34) | Tests real retrieval with graph expansion |

### 3.4 Test File Placement

Place in `tests/test_knowledge_integration.py` — root test directory, not `packages/knowledge/tests/` (which is for package-internal unit tests). This follows the existing pattern: `tests/test_knowledge_engine_extraction.py` tests the full knowledge package from outside the package boundary.

### 3.5 Test Class Structure

```
TestFromAC_IngestToSearchCycle
  test_ingest_through_pipeline           # AC1
  test_entities_extracted_and_stored     # AC2
  test_intra_doc_edges_built             # AC3
  test_chunks_embedded_and_stored        # AC4
  test_query_service_returns_results     # AC5
  test_graph_retriever_includes_expansion # AC6
  test_no_external_deps_required         # AC7 (implicit — no Docker/network)
```

All tests share a single `@pytest.fixture(scope="class")` that ingests a sample document once. Individual tests assert different aspects of the resulting state.

## 4. Recommendation (.90 confidence)

**Update #162 dependencies to `[158, 34]`** and proceed with TDD once those land. The test needs: (a) an IngestPipeline that actually persists entities/edges/embeddings (#158), and (b) a GraphAugmentedRetriever for the search-with-expansion AC (#34).

Risk: #33 and #158 have deep dependency chains (#32, #203, #206). The integration test is genuinely blocked until the full extraction → persistence chain is complete.

## 5. Follow-up Tasks

No new tasks needed — #162 already exists with correct AC. The action is dependency correction:

```
kanban\kanban-md.exe edit 162 --depends-on "158,34"
```
