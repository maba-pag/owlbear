# Search Result Provenance Contract — Implementation Design

> **Owning task:** #1332 — P3-16: Search result provenance contract
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1332 requires `search_knowledge` results to include provenance fields populated from actual graph/source store data — not just the MCP serialization scaffolding (done in prior tasks). The MCP layer (`SearchResult` TypedDict, serializers) is already wired. The gap is in `KnowledgeQueryService.query()` and `StructuredSearchResult`, which do not produce provenance fields from real data.

**Question:** What changes to `query_service.py` and `server.py` populate `retrieval_path`, `entities`, `related_sources`, and `source` from existing graph/source store APIs?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Brief §4.8 | `.owlbear/briefs/draft-knowledge-activation/brief.md` L124-152 | 1.0 |
| `query_service.py` (current) | `serve/knowledge/src/owlbear_knowledge/query_service.py` | 1.0 |
| `server.py` MCP layer | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L73-220, 637-668 | 0.9 |
| `graph_store.py` APIs | `serve/knowledge/src/owlbear_knowledge/graph_store.py` | 0.9 |
| `source_store.py` APIs | `serve/knowledge/src/owlbear_knowledge/source_store.py` | 0.8 |
| `retrieval.py` RetrievalResult | `serve/knowledge/src/owlbear_knowledge/retrieval.py` | 0.8 |
| `models.py` Domain models | `serve/knowledge/src/owlbear_knowledge/models.py` | 0.7 |
| #1331 research doc | `.owlbear/research/1331-search-provenance-contract.md` | 0.7 |
| #1331 tests (21, all green) | `tests/test_search_provenance_1331.py` | 0.9 |

## 3. Analysis

### Current vs Required Data Flow

| Field | MCP Serializer | StructuredSearchResult | Data Source | Status |
|-------|---------------|----------------------|-------------|--------|
| `score` | ✅ | ✅ `score` | Vector similarity | Done |
| `source.name` | ✅ `_serialize_source` | ❌ missing | `source_store.get(doc.source_id).name` | Gap |
| `source.url` | ✅ `_serialize_source` | ❌ missing | `source_store.get(doc.source_id).config["url"]` | Gap |
| `retrieval_path` | ✅ `getattr(r, ..., "vector")` | ❌ missing | Retriever presence + `entities_found > 0` | Gap |
| `entities` | ✅ `_serialize_search_entities` | ❌ missing | `graph_store.list_entities_for_document(doc_id)` | Gap |
| `related_sources` | ✅ `_serialize_related_sources` | ❌ missing | Entity edges to other-source documents | Gap |

### Retrieval Path Logic

| Condition | retrieval_path | Rationale |
|-----------|---------------|-----------|
| No retriever (`self._retriever is None`) | `"vector"` | Pure vector similarity |
| Retriever used, `entities_found == 0` | `"vector"` | Graph expanded but found nothing |
| Retriever used, `entities_found > 0` | `"vector+graph"` | Both paths contributed |
| Graph-only query | `"graph"` | Not yet supported — no codepath exists |

Current architecture always starts with vector search. Pure `"graph"` requires a graph-only query path that doesn't exist. For now, valid values are `"vector"` and `"vector+graph"`.

### Related Sources Resolution

To populate `related_sources`, for each document's entities:
1. `graph_store.list_entities_for_document(doc_id)` → entity list
2. For each entity, `graph_store.list_edges(source_id=entity.id)` → outgoing edges
3. For each edge, resolve target entity → target `document_id` → target source
4. If target source ≠ current source → add to `related_sources`

**Performance:** O(entities × edges) per result. With small graph sizes (< 10K entities), this is acceptable. For scale, a denormalized `related_sources` table would be needed — out of scope per AC.

### Implementation Approach

**Option A: Extend StructuredSearchResult (recommended)**

Add provenance fields to `StructuredSearchResult` with defaults. Populate them in `KnowledgeQueryService.query()`. The MCP layer's `getattr()` calls naturally pick up real values.

| Criteria | Score |
|----------|-------|
| Minimal diff | ✅ ~40 LOC changes |
| KISS | ✅ extends existing model |
| No new abstractions | ✅ uses existing store APIs |
| Backward compat | ✅ defaults preserve existing behavior |
| Test coverage | ✅ #1331 tests (MCP layer) + need query-service-level tests |

**Option B: Separate provenance DTO**

Create a `SearchProvenance` model passed alongside `StructuredSearchResult`. Rejected — adds abstraction for a single consumer.

### Required Changes

1. **`StructuredSearchResult`** — add fields:
   - `retrieval_path: str = "vector"`
   - `entities: list[dict[str, str]] = []` (each `{name, type}`)
   - `related_sources: list[dict[str, str]] = []` (each `{name, relationship, entity}`)
   - `source: KnowledgeSource | None = None`

2. **`KnowledgeQueryService.__init__`** — accept optional `source_store` parameter

3. **`KnowledgeQueryService.query()`** — after resolving doc:
   - Populate `entities` from `list_entities_for_document(doc_id)`
   - Look up `source` from `source_store.get(doc.source_id)` if source_store available
   - Determine `retrieval_path` from retriever presence + entities found
   - Resolve `related_sources` via entity edge traversal to cross-source documents

4. **`_search_chunks`** — return `RetrievalResult` (not just chunks) when retriever is used, so `query()` can inspect `entities_found`

5. **`_serialize_source` in server.py** — already handles `KnowledgeSource` via `getattr` patterns; may need `config["url"]` fallback (already implemented)

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Performance: edge traversal per result | Low | Bounded by enrichment graph size; lazy evaluation |
| Breaking `query()` callers | Low | New fields have defaults; existing consumers unaffected |
| `source_store` not available at init | Low | Optional param; `source` stays None when unavailable |
| `_search_chunks` signature change | Medium | Internal method, only called by `query()` |

## 4. Recommendation

**Option A: Extend StructuredSearchResult** — confidence: **0.88**

Minimal, KISS-aligned approach. Extends the existing model with defaulted fields, populates from existing graph/source store APIs. No new abstractions. The MCP serializers already handle the output format correctly via `getattr()` patterns.

Challenge: SKIPPED — single viable option, straightforward extension of existing patterns, no design trade-off.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1332 (implementation) already exists. The #1331 tests (21, all green) validate the MCP serialization layer. Implementation needs query-service-level tests to verify provenance population from real stores — these should be added as part of the #1332 implementation scope (AC: "All #1331 tests pass green" already covered; query-service tests are implementation detail).
