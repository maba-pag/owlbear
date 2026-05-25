# GraphStore — Entities & Edges Implementation Research

> **Owning task:** #1873 — Knowledge: GraphStore — entities & edges
> **Date:** 2026-05-25  **Status:** Complete

## 1. Context and Question

Implement the new-protocol `GraphStore` concrete class for entity and edge management. Key concerns: (1) entity identity via canonical name + type, (2) deterministic ID generation, (3) metadata shallow-merge semantics (CP25), (4) alias-aware find, (5) direction-filtered adjacency queries.

Target file: `serve/knowledge/src/owlbear_knowledge/stores/graph.py`

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| SQLite UPSERT docs | sqlite.org/lang_upsert.html | .95 |
| LightRAG graph storage (multiple backends) | github.com/HKUDS/LightRAG (kg/) | .85 |
| Existing legacy `graph_store.py` | serve/knowledge/src/owlbear_knowledge/graph_store.py | .90 |
| ContentStore research #1871 (stores/ pattern) | .owlbear/research/1871-contentstore-ingest-dedup.md | .90 |
| Protocol definition | serve/knowledge/src/owlbear_knowledge/protocols/graph.py | 1.0 |
| `canonicalize_name` impl | protocols/common.py | 1.0 |
| TABLE_OWNERSHIP registry | protocols/registry.py — Graph owns `graph_*` | .85 |
| Claude Cookbook KG guide | platform.claude.com/cookbook/capabilities-knowledge-graph-guide | .75 |

## 3. Analysis

### 3.1 Entity ID Generation

| Approach | Deterministic? | Lookup-free upsert? | Collision risk | Complexity |
|----------|---------------|--------------------:|----------------|------------|
| UUID4 on first create | No | No — must SELECT first | None | Low |
| UUID5 from `(canonical_name, entity_type)` | Yes | Yes — ID known upfront | Negligible (SHA-1) | Low |
| Integer autoincrement | No | No | None | Low |

**Decision (.90):** UUID5 with a Graph-specific namespace UUID: `uuid5(GRAPH_NS, f"{canonical_name}:{entity_type}")`. Same identity always produces same ID. Matches ContentStore's document_id pattern (deterministic UUID5 from identity attributes). LightRAG uses `compute_mdhash_id(name, prefix="ent-")` — same principle (MD5 hash of name → deterministic ID).

### 3.2 Metadata Shallow-Merge (CP25)

| Approach | Correct for CP25? | Atomic? | Complexity |
|----------|-------------------|---------|------------|
| SQLite `json_patch()` in ON CONFLICT | No — deep merge, recurses into nested | Yes | Low |
| Python-side: SELECT existing → `{**old, **new}` → write | Yes — top-level only | Within transaction | Low |
| Always overwrite (no merge) | No — violates CP25 | Yes | Trivial |

**Decision (.85):** Python-side shallow merge. Flow: SELECT existing metadata → `{**existing_meta, **new_meta}` → INSERT...ON CONFLICT DO UPDATE with pre-computed merged JSON. SQLite's `json_patch` does recursive merge which violates CP25's shallow semantics.

### 3.3 Upsert SQL Pattern

SQLite UPSERT (v3.24+, Python 3.12 ships ≥3.42): `INSERT INTO ... ON CONFLICT(canonical_name, entity_type) DO UPDATE SET metadata=?, updated_at=?`. The `excluded.*` reference gives the attempted-insert values. Since we need pre-merged metadata, we bind it as a parameter rather than using `excluded.metadata`.

Two-step within explicit `BEGIN IMMEDIATE` transaction (required for thread-safety under asyncio.to_thread dispatch):
1. `SELECT metadata, created_at FROM graph_entities WHERE id = ?` (ID known from UUID5)
2. `INSERT ... ON CONFLICT(id) DO UPDATE SET ...` with merged metadata bound
3. `COMMIT`

### 3.4 Edge Identity & Upsert

Edge identity: `(source_entity_id, target_entity_id, relation_type)` — UNIQUE constraint.
Edge ID: UUID5 from `f"{source_id}:{target_id}:{relation_type}"` — deterministic.

Validation before insert: both source and target entities must exist (protocol requires `ValueError` if not). Single SELECT to verify.

### 3.5 Direction Filtering (get_adjacent)

| Direction | SQL WHERE clause |
|-----------|-----------------|
| OUTGOING | `source_entity_id = ?` |
| INCOMING | `target_entity_id = ?` |
| BOTH | `source_entity_id = ? OR target_entity_id = ?` |

Standard pattern, used identically in LightRAG's Neo4j/Postgres implementations.

### 3.6 Alias-Aware find_entities

The `graph_aliases` table is owned by task #1874. `find_entities` should attempt alias JOIN but gracefully degrade if table doesn't exist:

```sql
-- When graph_aliases exists:
SELECT DISTINCT e.* FROM graph_entities e
LEFT JOIN graph_aliases a ON a.entity_id = e.id
WHERE (e.canonical_name = ? OR a.canonical_alias = ?)
-- Fallback when table absent: query graph_entities only
```

### 3.7 Table DDL (this task scope)

```sql
CREATE TABLE IF NOT EXISTS graph_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(canonical_name, entity_type)
);
CREATE INDEX IF NOT EXISTS idx_graph_entities_type ON graph_entities(entity_type);

CREATE TABLE IF NOT EXISTS graph_edges (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL REFERENCES graph_entities(id),
    target_entity_id TEXT NOT NULL REFERENCES graph_entities(id),
    relation_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_entity_id, target_entity_id, relation_type)
);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_entity_id);
```

Note: `graph_aliases` and `graph_evidence` DDL deferred to task #1874.

### 3.8 Implementation Structure

```
serve/knowledge/src/owlbear_knowledge/stores/
├── __init__.py
└── graph.py         # SqliteGraphStore class
```

Constructor: `sqlite3.Connection` only (no external deps).
Class: `SqliteGraphStore` — synchronous, implements entity/edge CRUD subset of `GraphStore` protocol. Out-of-scope protocol methods (traverse, add_evidence, claims_for_chunk, invalidate_evidence_by_chunks, add_alias, stats) raise `NotImplementedError` until task #1874 completes them.

## 4. Recommendation

Proceed with UUID5 deterministic IDs + Python-side shallow merge + explicit SQLite transactions for upsert atomicity. Confidence: **.75**

Challenge: **reconsider** — confidence in original after revision: **.75**

Challenger identified 3 issues incorporated into revised recommendation:

1. **AC vs Protocol mismatch** (accepted): AC mentions "metadata filter" and "find_edges" but protocol has `EntityQuery` (no metadata field) and `get_adjacent`. Protocol is authoritative — implementation follows protocol surface. "get_edge(id)" is an internal convenience method (not protocol-required).

2. **Transaction safety** (accepted): MCP server dispatches to threads via `asyncio.to_thread`. Mitigation: use explicit `BEGIN IMMEDIATE` transaction for the SELECT+UPSERT sequence to ensure atomicity under concurrent access.

3. **Alias DDL boundary** (accepted): Task AC explicitly scopes DDL to graph_entities + graph_edges. Task #1874 owns graph_aliases DDL. Revised: `ensure_tables` creates only graph_entities and graph_edges. `find_entities` uses alias JOIN only if table exists (graceful degradation).

4. **Partial Protocol coverage** (rebutted): Task is greenfield, explicitly scoped. Out-of-scope methods raise `NotImplementedError`. Full Protocol conformance is verified when all layer-1 tasks complete.

5. **Legacy cutover** (rebutted): Task is tagged `greenfield`. New stores/ coexists alongside legacy code. Rewiring is a separate migration task.

## 5. Follow-up Tasks

- This task (#1873) proceeds to backlog for architecture review — no new follow-up tasks needed
- Alias + evidence + traversal operations already tracked as #1874
