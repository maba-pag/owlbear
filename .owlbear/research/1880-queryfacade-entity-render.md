# QueryFacade — Entity Lookup & Render

> **Owning task:** #1880 — Knowledge: QueryFacade — entity lookup & render
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1880 adds `lookup_entity(EntityLookupRequest)` and `render_context(ContextRenderRequest)` to the existing `QueryFacade` class (which already implements `search` from #1879). The question: what's the implementation approach, and what protocol gaps need filling?

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| OwlBear QueryFacade protocol | `serve/knowledge/src/owlbear_knowledge/protocols/query.py` | 1.0 — defines contracts |
| OwlBear GraphStore protocol | `serve/knowledge/src/owlbear_knowledge/protocols/graph.py` | 1.0 — entity/evidence ops |
| OwlBear GraphStore SQLite impl | `serve/knowledge/src/owlbear_knowledge/stores/graph.py` | 0.9 — confirms indexed `entity_id` col |
| OwlBear retrieval.py expansion | `serve/knowledge/src/owlbear_knowledge/retrieval.py` | 0.8 — existing context format |
| OwlBear query_service.py | `serve/knowledge/src/owlbear_knowledge/query_service.py` | 0.7 — legacy rendering |
| Microsoft GraphRAG local_context | `graphrag/query/context_builder/local_context.py` | 0.7 — entity table rendering |
| ARCHITECTURE.md max_chars policy | `protocols/ARCHITECTURE.md` R49 | 0.9 — budget semantics |

## 3. Analysis

### 3.1 lookup_entity Implementation

| Step | Method | Notes |
|------|--------|-------|
| Resolve entity | `get_entity(id)` or `find_entities(EntityQuery(name, type))` | XOR validated by model_validator on request |
| Disambiguate name | First result from `find_entities` | Protocol says strategy is implementation-defined |
| Expand neighbourhood | `traverse(TraversalQuery(entity_id, max_hops=expand_hops, relation_types))` | Skipped when expand_hops=0 |
| Related chunks | **GAP** — needs reverse evidence lookup (entity→chunk_ids) | See §3.2 |

### 3.2 Protocol Gap: chunk_ids_for_entity

**Problem:** `claims_for_chunk(chunk_id)` goes chunk→entity. `EntityLookupResult.related_chunks` requires entity→chunk direction. The `graph_evidence` table has `entity_id` indexed (`idx_graph_evidence_entity_id`), but no protocol method queries it in this direction.

| Option | Description | Pro | Con | Confidence |
|--------|-------------|-----|-----|------------|
| A: Add `chunk_ids_for_entity(entity_id)` to GraphStore | New protocol method returning `tuple[str, ...]` | Clean, single-query, uses existing index | Protocol change (minor) | 0.85 |
| B: Scan all chunks via Content | `list_chunks` per doc, `claims_for_chunk` each | No protocol change | O(n) — impractical at scale | 0.10 |
| C: Empty related_chunks | Return `()` always | Zero work | Violates protocol guarantee | 0.00 |

**Recommendation:** Option A. One SQL query (`SELECT DISTINCT chunk_id FROM graph_evidence WHERE entity_id = ?`), 5 LOC in store, 3-line protocol addition. Risk: minimal — the column/index already exists.

### 3.3 render_context Implementation

| Approach | Format | Budget Strategy | Confidence |
|----------|--------|-----------------|------------|
| Structured sections | Markdown-like: `## Entity`, `## Relationships`, `## Sources` | Append items until max_chars; set truncated=True on overflow | 0.85 |
| Pipe-delimited tables (GraphRAG style) | `id|entity|description|rank` | Token counting per row | 0.60 |
| One-line per item (retrieval.py style) | `{name} --[rel]--> {target}: {desc}` | Word budget | 0.70 |

**Recommendation:** Structured sections — more readable for LLMs, matches our use case (personal KB with rich entity descriptions). Truncation strategy: prioritize entity description > neighbours > source chunks (lowest-scored first).

### 3.4 Error Handling

| Input | Result |
|-------|--------|
| `entity_id` not found → `get_entity` returns None | Raise `LookupError` (per protocol) |
| `entity_name` matches nothing | Raise `LookupError` (per protocol) |
| `render_context` with neither result | Raise `ValueError` (per protocol) |
| expand_hops=0 | neighbourhood=None, skip traversal |

### 3.5 Trade-off: sync vs async

Protocol declares `lookup_entity` as sync, `render_context` as sync. Both call sync GraphStore methods + sync `Content.get_chunk`. No async needed. Matches #1879 pattern where the facade's `search` is async only because ContentStore.search is async.

## 4. Recommendation

**Approach:** Implement both methods in `serve/knowledge/src/owlbear_knowledge/query_facade.py` as synchronous composition over injected stores. Add `chunk_ids_for_entity` to GraphStore protocol as prerequisite.

**Confidence:** 0.85

**Challenge:** FALLBACK — trivial composition task, no ambiguous architecture decisions; challenger reserved for T2/T3 outcomes.

**Tier:** T1 (autonomous) — extends existing facade with protocol-defined methods. The protocol addition (`chunk_ids_for_entity`) is implied by the existing indexed column and directly serves the protocol guarantee.

## 5. Follow-up Tasks

1. **GraphStore protocol: add `chunk_ids_for_entity`** — add method to protocol + implement in SQLite store (prerequisite for #1880 builder)
2. **QueryFacade: implement lookup_entity + render_context** — the main #1880 implementation (depends on follow-up 1)
