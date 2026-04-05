# Knowledge Scoping — Per-Agent, Per-Project, and Global Namespaces

> **Owning task:** #135 — Knowledge scoping — per-agent, per-project, and global namespaces
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge graph (sqlite + sqlite-vec) stores entities, edges, documents, chunks, and embeddings in a single flat namespace. All agents and projects share the same data. This research investigates how to partition knowledge into scopes — global (shared), per-project, and per-agent — without duplicating the storage layer.

**Key constraint:** single SQLite file, KISS, no enterprise multi-tenancy.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Mem0 (mem0ai) | github.com/mem0ai/mem0 | .95 | Multi-level memory scoping via `user_id`, `agent_id`, `run_id` metadata fields on every vector store entry. `_build_filters_and_metadata()` constructs scope filters at query time. At least one scope ID required per operation. 48k stars, Apache-2.0. |
| LightRAG (HKUDS) | github.com/HKUDS/LightRAG | .85 | `workspace` parameter for data isolation. PostgreSQL: adds `workspace` field to tables. File-based: subdirectories. Qdrant: payload-based partitioning. 28.7k stars. |
| ChromaDB | docs.trychroma.com | .60 | Collections as primary namespace. Higher-level tenant/database scoping. Separate collections per logical group. |

## 3. Analysis

### 3.1 Scoping Strategy — Comparison

| Criterion | Column-based filter (.90) | Metadata JSON filter (.55) | Separate DBs (.40) |
|-----------|--------------------------|----------------------------|---------------------|
| Schema change | `ALTER TABLE ADD scope` (5 tables) | None | None (new files) |
| Query complexity | `WHERE scope IN (...)` | App-layer JSON parse + filter | Multiple connections |
| Vec0 compatibility | Post-filter via bridge table | Same post-filter | Separate vec0 per DB |
| Cross-scope search | Single query with IN clause | Single query + app filter | Union across DBs |
| Migration effort | Low (~20 LOC migration fn) | None | Medium (connection mgr) |
| KISS score | **High** | Medium (hidden complexity) | Low (connection juggling) |
| Performance | Good (indexed column) | Poor (JSON parse per row) | Good (smaller DBs) |
| Prior art | LightRAG (PG workspace field), Mem0 (promoted payload keys) | Mem0 (fallback pattern) | LightRAG (file-based) |
| Data isolation | Logical (same DB) | Logical (same DB) | Physical (diff files) |

### 3.2 Scope Identifier Format

| Format | Example | Pros | Cons |
|--------|---------|------|------|
| Flat string | `"global"`, `"project:owlbear"`, `"agent:builder"` | Simple, human-readable, grep-able | Need convention for parsing |
| Hierarchical | `"global"`, `"project/owlbear"`, `"project/owlbear/agent/builder"` | Shows nesting | Over-engineered for 3 levels |
| Separate columns | `scope_level TEXT, scope_name TEXT` | Typed queries | Doubles the schema surface |

**Verdict:** Flat string with `":"` separator. Three canonical prefixes: `global`, `project:{name}`, `agent:{name}`. Simple, extensible if ever needed, zero parsing overhead.

### 3.3 Vector Search Scoping

sqlite-vec's `vec0` virtual tables only support `WHERE embedding MATCH ? AND k = ?`. No arbitrary WHERE clauses. Two options:

| Approach | Description | Verdict |
|----------|-------------|---------|
| **Post-filter via bridge table** (.85) | Over-fetch from vec0 (k×3), filter results through `embedding_rowid_map.scope IN (...)` | Already matches our reranker pattern |
| Partition key in vec0 (.60) | `+scope text partition key` in vec0 DDL | Requires re-creating virtual tables; partition keys only support exact match, not IN; need one query per scope then merge |

**Winner:** Post-filter via bridge table. It reuses the existing over-fetch pattern from `_search_with_reranker`, avoids vec0 DDL changes, and keeps the migration simple.

## 4. Recommendation (.90 confidence)

**Column-based scope filtering** — add a `scope TEXT DEFAULT 'global'` column to 5 tables, filter at query time.

### Design decisions

1. **Scope column, not metadata.** Dedicated column is indexable, queryable with `IN`, and explicit. Mem0 stores scopes in vector payload metadata; we use a proper column because SQLite makes it trivial and our bridge-table pattern already does rowid lookups.

2. **Flat string format.** Values: `"global"`, `"project:{name}"`, `"agent:{name}"`. No hierarchy needed — OwlBear has exactly 3 scope levels.

3. **Post-filter for vector search.** Over-fetch from vec0 (k × 3), join through `embedding_rowid_map WHERE scope IN (?)`, return top k. Same pattern as existing reranker.

4. **Scope resolution at the caller.** The agent/pipeline decides which scopes to query: typically `["global", "project:{current}", "agent:{self}"]`. GraphStore/VectorStore just accept a `scopes: list[str]` parameter — they don't know about scope semantics.

5. **Default is `"global"`.** All existing data stays accessible. Zero-migration for existing entries — they default to global scope.

6. **Schema v3 migration.** Follows existing `_migrate_v1_to_v2` pattern. Five `ALTER TABLE ADD COLUMN` statements wrapped in `contextlib.suppress(OperationalError)` for idempotency.

### Schema impact

```sql
-- v2 → v3 migration (5 ALTER TABLE statements)
ALTER TABLE entities ADD COLUMN scope TEXT DEFAULT 'global';
ALTER TABLE documents ADD COLUMN scope TEXT DEFAULT 'global';
ALTER TABLE edges ADD COLUMN scope TEXT DEFAULT 'global';
ALTER TABLE chunks ADD COLUMN scope TEXT DEFAULT 'global';
ALTER TABLE embedding_rowid_map ADD COLUMN scope TEXT DEFAULT 'global';

-- Optional: index for performance on larger datasets
CREATE INDEX IF NOT EXISTS idx_entities_scope ON entities(scope);
CREATE INDEX IF NOT EXISTS idx_documents_scope ON documents(scope);
CREATE INDEX IF NOT EXISTS idx_embedding_rowid_map_scope ON embedding_rowid_map(scope);
```

### Model impact

```python
# Entity, Edge, Document models gain:
scope: str = "global"
```

### API impact

```python
# GraphStore methods gain optional scopes parameter:
def list_entities(self, entity_type=None, scopes=None) -> list[Entity]: ...
def insert_entity(self, entity: Entity) -> None: ...  # scope from entity.scope

# VectorStore.search_similar gains scopes:
def search_similar(self, query_embedding, top_k=5, ..., scopes=None): ...

# IngestPipeline gains scope:
async def ingest(self, source, scope="global") -> IngestResult: ...
```

## 5. Follow-up Tasks

1. **Schema v3 migration** — Add scope column to 5 tables, bump `_SCHEMA_VERSION` to 3, write `_migrate_v2_to_v3`.
2. **Model scope field** — Add `scope: str = "global"` to Entity, Edge, Document Pydantic models.
3. **GraphStore scoped queries** — Update all CRUD methods to accept/filter by scope(s).
4. **VectorStore scoped search** — Update `search_similar` and `store_embedding` to use scope on bridge table.
5. **IngestPipeline scope passthrough** — Accept scope param and propagate to graph/vector stores.
