# GraphStore — Evidence, Aliases & Traversal

> **Owning task:** #1874 — Knowledge: GraphStore — evidence, aliases & traversal
> **Date:** 2026-05-26  **Status:** Complete

## 1. Context and Question

Complete the `SqliteGraphStore` protocol implementation: evidence provenance (chunk→entity/edge linking), alias management, BFS traversal, and stats. Task #1873 delivered entity/edge CRUD; this task adds the remaining 6 methods + 2 tables.

Key questions: (1) evidence storage pattern (soft-delete vs hard-delete), (2) orphan cascade strategy, (3) BFS traversal approach (reuse `get_adjacent` vs raw SQL), (4) alias conflict detection.

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| Protocol definition | `serve/knowledge/src/owlbear_knowledge/protocols/graph.py` | 1.0 |
| Existing impl (task #1873) | `serve/knowledge/src/owlbear_knowledge/stores/graph.py` | 1.0 |
| Legacy `get_neighbors` BFS | `serve/knowledge/src/owlbear_knowledge/graph_store.py:401` | .90 |
| LightRAG chunk tracking | github.com/HKUDS/LightRAG (`operate.py`, `utils_graph.py`) | .80 |
| Task #1873 research | `.owlbear/research/1873-graphstore-entities-edges.md` | .85 |
| example-graphrag-with-sqlite | github.com/stephenc222/example-graphrag-with-sqlite | .60 |
| Grounded KG Extraction (MDPI 2026) | mdpi.com/2073-431X/15/3/178 | .70 |

## 3. Analysis

### 3.1 Evidence: Hard-Delete (Protocol Authoritative)

| Approach | History preserved? | Orphan query complexity | Protocol alignment | KISS |
|----------|-------------------|------------------------|-------------------|------|
| Soft-delete (`invalidated` flag) | Yes | `WHERE invalidated=0` needed on orphan check | Task body says "marked invalidated" | Moderate |
| Hard-delete (DELETE rows) | No | Simple COUNT = 0 check | Protocol guarantee: "records are deleted" | High |

**Decision (.90):** Hard-delete. Rationale: Protocol is authoritative (established in #1873 research). The guarantee states "All evidence records … are deleted." The field `invalidated_evidence_ids` names the IDs invalidated by the operation (past tense), not a storage state column. Task body "marked invalidated" is aspirational but overridden by protocol. No `invalidated` column needed — simpler schema, simpler orphan detection (`COUNT(*)=0`).

### 3.2 Evidence ID Strategy

| Approach | Deterministic? | Allows duplicates? | Idempotent? |
|----------|---------------|-------------------|-------------|
| UUID4 | No | Yes (same chunk→entity can be recorded multiple times) | No |
| UUID5 from `(chunk_id, claim_type, entity_id\|edge_id)` | Yes | No (same evidence = same ID) | Yes |

**Decision (.85):** UUID5 deterministic IDs (consistent with entity/edge pattern). `uuid5(NAMESPACE_URL, f"evidence:{chunk_id}:{entity_id or edge_id}")`. Same identity → same ID. Upsert semantic: if evidence already exists, update confidence/metadata (allows re-extraction with refined confidence). Matches entity/edge upsert pattern.

### 3.3 Orphan Detection & Cascade

Protocol guarantee: "Entities and edges that lose ALL evidence are reported as orphaned (and deleted from graph_* tables)."

| Approach | Correctness | Complexity | Performance |
|----------|------------|------------|-------------|
| Per-entity/edge COUNT after invalidation | Correct | Low | O(affected entities + edges) |
| Batch SQL subquery | Correct | Low | Single roundtrip |

**Decision (.90):** Two-step within transaction:
1. Collect affected entity_ids/edge_ids from evidence WHERE chunk_id IN (?...)
2. DELETE FROM graph_evidence WHERE chunk_id IN (?...)
3. For each affected entity_id: COUNT remaining evidence → if 0, DELETE from graph_entities
4. For each affected edge_id: COUNT remaining evidence → if 0, DELETE from graph_edges
5. Return IDs of deleted evidence + orphaned entities + orphaned edges

Note: entities/edges created via `upsert_entity`/`upsert_edge` without evidence are never orphaned (they have no evidence to lose). Only entities/edges that had evidence AND lost all of it become orphans.

### 3.4 BFS Traversal

| Approach | Reuse | Performance | Complexity |
|----------|-------|-------------|------------|
| Call `get_adjacent()` per hop | High | Multiple queries, N per level | Low |
| Raw SQL per hop | None | Single query per hop, can batch | Moderate |
| Recursive CTE | None | Single query, all hops | High (SQLite CTE depth limits) |

**Decision (.85):** Call `get_adjacent()` per hop (reuse existing method). Standard `deque` BFS matching legacy pattern. Advantages: (a) tested adjacency logic reused, (b) relation_types filter already implemented in `get_adjacent`, (c) direction is BOTH (TraversalQuery has no direction field). Performance adequate for max_hops≤5 and limit≤1000.

Critical: validate seed entity exists BEFORE BFS loop (raise `LookupError` if not). `get_adjacent()` returns empty for unknown entities — the stronger error contract on `traverse()` requires explicit pre-validation via `_entity_exists()` or `get_entity()`.

BFS produces `TraversalResult(entities, edges)` — collect unique entities and edges during traversal. Protocol makes BFS vs DFS an implementation detail; BFS chosen for consistency with legacy and breadth-first discovery semantics.

### 3.5 Alias Implementation

Protocol constraints:
- Canonicalize alias_name identically to entity names
- `find_entities` resolves aliases (already implemented with graceful degradation)
- Idempotent: same canonical alias + entity = return existing
- Error: entity_id doesn't exist → `LookupError`
- Error: alias_name conflicts with different entity's canonical_name → `ValueError`

Alias ID: UUID5 from `f"alias:{entity_id}:{canonical_alias}"` — deterministic, prevents duplicates.

### 3.6 Table DDL

```sql
CREATE TABLE IF NOT EXISTS graph_evidence (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    entity_id TEXT,
    edge_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES graph_entities(id),
    FOREIGN KEY (edge_id) REFERENCES graph_edges(id)
);
CREATE INDEX IF NOT EXISTS idx_graph_evidence_chunk ON graph_evidence(chunk_id);
CREATE INDEX IF NOT EXISTS idx_graph_evidence_entity ON graph_evidence(entity_id);
CREATE INDEX IF NOT EXISTS idx_graph_evidence_edge ON graph_evidence(edge_id);

CREATE TABLE IF NOT EXISTS graph_aliases (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    alias_name TEXT NOT NULL,
    canonical_alias TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES graph_entities(id),
    UNIQUE(entity_id, canonical_alias)
);
CREATE INDEX IF NOT EXISTS idx_graph_aliases_canonical ON graph_aliases(canonical_alias);
```

### 3.7 Stats

Four COUNT queries (evidence counts all rows — no soft-delete state):
```python
GraphStats(entities=..., edges=..., evidence_claims=..., aliases=...)
```

### 3.8 AC ↔ Protocol Reconciliation

The AC uses approximate wording; protocol types are authoritative:
- AC "direction" → TraversalQuery has no direction field; traversal explores BOTH.
- AC "path information" → TraversalResult has `entities` + `edges`; edges encode the path.
- AC "entity_count, edge_count, evidence_count, alias_count" → Protocol fields: `entities, edges, evidence_claims, aliases`.
- AC "returns … with counts" → EvidenceInvalidationResult has ID tuples; `len()` gives counts.
- AC "start_entity_id" → Protocol field: `entity_id`.

## 4. Recommendation

Proceed with revised decisions (hard-delete, upsert evidence, explicit seed validation). Total implementation: ~200 LOC in existing `graph.py`. Confidence: **.85**

Challenge: reconsider — confidence in original after revision: **.85**

Challenger identified 3 critical issues (contract drift resolved by protocol authority, AC mismatch resolved by reconciliation, traversal error contract resolved by pre-validation) and 2 moderate issues (evidence upsert semantics resolved, alias cross-conflict accepted as non-blocking). Risk reduced from high to low after revisions.

LightRAG embeds `source_id` directly in nodes/edges (denormalized). Our normalized `graph_evidence` table is cleaner for: targeted invalidation, multi-chunk evidence per entity, orphan detection. Trade-off: one extra JOIN for evidence queries, but evidence queries are not on the hot path.

## 5. Follow-up Tasks

- Task proceeds to backlog for architecture review. No additional follow-up tasks needed — implementation scope is clear and self-contained.
