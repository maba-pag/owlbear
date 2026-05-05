# Search Result Provenance Contract — Test Design

> **Owning task:** #1331 — P3-15: Tests — Search result provenance contract
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1331 requires tests verifying that `search_knowledge` responses include machine-readable provenance fields per Brief §4.8. The implementation task (#1332) will modify `StructuredSearchResult`, `KnowledgeQueryService.query()`, and the `search_knowledge` MCP tool.

**Question:** What fields must the tests assert, and what test architecture ensures deterministic verification regardless of enrichment state?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| Brief §4.8 (`.owlbear/briefs/draft-knowledge-activation/brief.md` L124-152) | 1.0 — canonical contract spec |
| `serve/knowledge/src/owlbear_knowledge/query_service.py` (current impl) | 0.9 — baseline to extend |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (search_knowledge) | 0.9 — MCP layer shape |
| `serve/mcp-knowledge/tests/test_search_v2.py` (existing tests) | 0.8 — test patterns to follow |
| `serve/knowledge/src/owlbear_knowledge/models.py` (KnowledgeSource, Entity) | 0.8 — source/entity models |
| `serve/knowledge/src/owlbear_knowledge/graph_store.py` (list_entities_for_document) | 0.7 — retrieval infrastructure |

## 3. Analysis

### Current vs Required Response Shape

| Field | Current | Required (§4.8) | Source |
|-------|---------|-----------------|--------|
| `title` | ✅ | ✅ | StructuredSearchResult |
| `score` | ✅ | ✅ | vector similarity |
| `snippet` | ✅ | ✅ (as `chunk_text`) | Document.content[:500] |
| `entity_type` | ✅ | — (subsumed by `entities`) | first entity |
| `source.name` | ❌ | ✅ | KnowledgeSource.name |
| `source.url` | ❌ | ✅ | KnowledgeSource.config["url"] |
| `retrieval_path` | ❌ | ✅ | "vector" / "graph" / "vector+graph" |
| `entities` | ❌ | ✅ | [{name, type}] from graph |
| `related_sources` | ❌ | ✅ | [{name, relationship, entity}] from edges |

### Test Layers

| Layer | What it tests | Mock strategy |
|-------|--------------|---------------|
| MCP tool (`search_knowledge`) | Response dict shape includes provenance keys | Mock `query_service.query()` returning StructuredSearchResult with provenance fields |
| Query service (`KnowledgeQueryService.query()`) | Populates provenance from graph/source stores | Mock graph_store + source_store; verify entity/source/path assembly |
| Determinism | Shape is identical when enrichment absent | Return entities=[], related_sources=[] |

### Retrieval Path Logic

- `"vector"` — result came only from vector similarity (no graph expansion contributed)
- `"graph"` — result surfaced only via graph traversal (entity-linked documents)
- `"vector+graph"` — both paths contributed to the result

Current `RetrievalResult` does not track per-chunk retrieval path. The implementation will need to mark this — tests should assert the field exists with valid enum values.

### Empty-State Determinism

When enrichment has NOT been run on a source:
- `entities` → `[]` (no entity extraction happened)
- `related_sources` → `[]` (no cross-source edges exist)
- `retrieval_path` → `"vector"` (only vector search possible)
- `source` → still populated (source identity is set at ingest time, not enrichment time)

## 4. Recommendation

**Approach:** Two test classes following the existing `test_search_v2.py` pattern:

1. **`TestFromAC_SearchProvenanceContract`** — MCP tool level: mock `query_service.query()` to return objects with all provenance fields, verify `search_knowledge` exposes them in response dicts.
2. **`TestFromAC_SearchProvenanceDeterminism`** — Verify empty arrays for unenriched results; verify shape consistency; verify `source` is always present.

Test file: `tests/test_search_provenance_1331.py`

Confidence: **0.90** — well-specified by the brief, existing test patterns are clear, infrastructure is sufficient.

Challenge: SKIPPED — trivial test-shape research, no design trade-off requiring adversarial review.

## 5. Follow-up Tasks

No additional tasks needed — #1331 (tests) and #1332 (implementation) already exist as a TDD pair.
