# Import/Export Tools for Project-Local Knowledge Snapshots

> **Owning task:** #618 — Build import/export tools for project-local knowledge snapshots
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #618 asks how to implement `import_scope` and `export_scope` MCP tools for mcp-knowledge. Research #616 recommended scope-based import/export over dual-stack databases. This research validates the implementation approach: data flow, FK remapping, dedup, embedding materialization, and security.

**Key constraint:** Single-developer laptop system, KISS/YAGNI, SQLite + Qdrant (`:memory:`).

## 2. Sources Studied

| Source | URL / Path | Relevance | What |
|--------|-----------|-----------|------|
| OwlBear #616 research | .owlbear/research/project-local-knowledge-source.md | .95 | Recommends option C (scope params + import/export) at .80 confidence |
| OwlBear #135 research | .owlbear/research/knowledge-scoping.md | .90 | Column-based scope filtering, scope format `project:{name}`, scope on all tables |
| schema.py v8 | serve/knowledge/src/owlbear_knowledge/schema.py | .95 | 9 tables, `scope TEXT DEFAULT 'global'` on core tables, PRAGMA foreign_keys = ON |
| qdrant.py | serve/knowledge/src/owlbear_knowledge/qdrant.py | .90 | `:memory:` default, scope payload filtering via MatchAny, store_embedding accepts scope |
| Python sqlite3 docs | docs.python.org/3/library/sqlite3.html | .85 | `?mode=ro` URI for read-only, `Connection.backup()` API, transaction context manager |
| SQLite ATTACH DATABASE | sqlite.org/lang_attach.html | .60 | Cross-DB queries via qualified names — considered but rejected (less control over dedup/remapping) |
| document_store.py | serve/knowledge/src/owlbear_knowledge/document_store.py | .90 | Legacy+new embedding APIs, store_extractions with scope, check_content_changed for dedup |
| _paths.py | serve/knowledge/src/owlbear_knowledge/_paths.py | .85 | sandbox_path: null byte check + resolve + is_relative_to |

## 3. Analysis

### 3.1 Implementation Approach Options

| Criterion | A: Row-level SELECT+INSERT (.82) | B: ATTACH + INSERT...SELECT (.55) | C: Via IngestPipeline (.40) |
|-----------|----------------------------------|-----------------------------------|----------------------------|
| FK remapping | Python dicts, explicit order | SQL-level aliasing in INSERT | N/A (re-extracts everything) |
| Dedup control | Per-document content hash check | Requires subquery or pre-check | Built-in via check_content_changed |
| Scope rewrite | Simple dict update per row | SQL expression in INSERT | Scope param on ingest_text |
| Entity preservation | Yes — imports original graph | Yes | **No** — re-extracts, different results |
| Embedding handling | Re-embed chunk texts (required) | Re-embed chunk texts (required) | Included in pipeline |
| KISS score | **High** | Medium (SQL complexity) | Low (wasteful re-extraction) |
| Error atomicity | Python `with conn:` transaction | Same | Pipeline per-doc (partial state) |
| LOC estimate | ~200-250 | ~120-150 | ~80 (but wrong results) |

### 3.2 FK Dependency Graph (6 relationships)

```
documents ← chunks.document_id (FK)
documents ← entities.document_id (semantic, nullable)
documents ← document_status.document_id (PK ref)
chunks ← entities.chunk_id (semantic, nullable)
entities ← edges.source_id (FK)
entities ← edges.target_id (FK)
```

**Required insert order:** documents → document_status → chunks → entities → edges

### 3.3 Tables In/Out of Scope

| Table | Import/Export? | Reason |
|-------|---------------|--------|
| documents | **Yes** | Core knowledge |
| chunks | **Yes** | Core knowledge |
| entities | **Yes** | Core graph |
| edges | **Yes** | Core graph |
| document_status | **Yes** | Content hash dedup depends on it |
| knowledge_sources | No | Configuration, not knowledge; UNIQUE(name, scope) conflicts |
| bookmarks | No | URL references, UNIQUE(url, scope) conflicts |
| consolidations | No | Contains entity ID JSON arrays that would need remapping |
| schema_version | No | Managed by init_db |

### 3.4 Qdrant Embedding Materialization

Qdrant runs in `:memory:` — all embeddings are ephemeral. On import, chunk texts must be embedded and stored in Qdrant for search to work. This uses existing `embedder.embed()` + `vector_store.store_embedding()`. Cost: proportional to chunk count. Acceptable for laptop-scale KBs.

On export, Qdrant data is NOT included (ephemeral by design). Embeddings are recomputed on import.

## 4. Recommendation (.78 confidence)

**Row-level SELECT+INSERT** (Option A) with these design decisions:

1. **Read-only source**: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` after `sandbox_path()` validation
2. **New UUIDs on import**: Generate fresh IDs for all rows, maintain 4 mapping dicts (doc, chunk, entity, edge)
3. **Ordered inserts**: documents → document_status → chunks → entities → edges (respects FK constraints)
4. **Atomic transaction**: Wrap entire import in `with conn:` — all-or-nothing, no partial state
5. **Content hash dedup**: Per document via `compute_content_hash()` — skip duplicates (AC2)
6. **Scope rewrite on import**: All rows get `scope="project:{name}"` (AC1)
7. **Preserve scope on export**: Export copies rows as-is; scope rewrite only on import side
8. **Re-embed, don't re-extract**: Import chunk texts into Qdrant; preserve original entity/edge graph
9. **Exclude operational tables**: knowledge_sources, bookmarks, consolidations out of v1
10. **Auto-detect**: Check `.owlbear/knowledge/knowledge.db` existence, use if no explicit path (AC5)

Challenge: proceed with amendments — confidence in original: .82 → .78 after FK complexity adjustment
Challenger raised valid concerns about FK mapping surface (6 not 3 relationships), LOC underestimate (~200-250 not ~120), and export scope preservation. All accepted.

### Dependency note

#617 (expose scope params in MCP tools) is needed for *querying* imported data but not for the import/export tools themselves. The two tasks can be built independently.

## 5. Follow-up Tasks

See kanban tasks created at ideation status below. Task #618 itself needs decomposition by the planner into atomic subtasks.
