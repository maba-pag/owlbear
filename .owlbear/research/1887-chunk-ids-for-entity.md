# GraphStore — chunk_ids_for_entity Protocol Method

> **Owning task:** #1887 — Knowledge: GraphStore — chunk_ids_for_entity protocol method
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1880 research identified a protocol gap: `claims_for_chunk(chunk_id)` provides chunk→entity direction, but `EntityLookupResult.related_chunks` needs the reverse (entity→chunk). Should we add `chunk_ids_for_entity` to GraphStore, and what's the implementation?

## 2. Sources Studied

| Source | Path | Relevance |
|--------|------|-----------|
| GraphStore protocol | `serve/knowledge/src/owlbear_knowledge/protocols/graph.py` | 1.0 |
| SqliteGraphStore impl | `serve/knowledge/src/owlbear_knowledge/stores/graph.py` | 1.0 |
| #1880 research doc | `.owlbear/research/1880-queryfacade-entity-render.md` §3.2 | 0.9 |
| Existing test patterns | `tests/test_graph_store_1874.py` | 0.8 |

## 3. Analysis

### 3.1 Feasibility

| Criterion | Assessment |
|-----------|------------|
| Theoretical validity | Sound — symmetric to `claims_for_chunk`; standard reverse-index lookup |
| Environment audit | Not provided by existing methods — confirmed no equivalent exists |
| Architecture fit | Follows exact GraphStore protocol conventions (tuple return, never-raises) |
| Technical feasibility | `graph_evidence.entity_id` indexed (`idx_graph_evidence_entity_id`); single query |

### 3.2 Implementation Approach

| Aspect | Detail |
|--------|--------|
| Protocol addition | `chunk_ids_for_entity(entity_id: str) -> tuple[str, ...]` — returns distinct chunk_ids; empty tuple for unknown entity; never raises |
| SQL | `SELECT DISTINCT chunk_id FROM graph_evidence WHERE entity_id = ?` |
| Scope | ~5 LOC protocol, ~8 LOC implementation |
| Pattern precedent | Mirrors `claims_for_chunk` — same table, inverse direction, same never-raises guarantee |

### 3.3 Testing Strategy

- Unit test: insert entity + evidence linking 2 chunks → verify returned tuple contains both chunk_ids
- Empty case: query unknown entity_id → returns `()`
- Deduplication: multiple evidence rows for same chunk_id → still returns one entry
- Fixture reuse: same `SqliteGraphStore` fixture pattern as `test_graph_store_1874.py`

## 4. Recommendation

Proceed with implementation as specified in task body. Confidence: **0.90**.

Challenge: SKIP — trivial protocol addition with validated prior research (#1880 §3.2).

## 5. Follow-up Tasks

None needed — this task IS the follow-up from #1880 research. Builder can proceed directly after this advances to backlog.
