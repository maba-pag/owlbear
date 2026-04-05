# Project-Local Knowledge Source for mcp-knowledge

> **Owning task:** #616 — Add project-local knowledge source (.owlbear/knowledge/) to mcp-knowledge
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

The five-tier restructure (#598) envisions `.owlbear/knowledge/` as a project-local knowledge directory. Task #616 asks: how should the mcp-knowledge server support reading from both `store/knowledge/` (global) and `.owlbear/knowledge/` (local)?

Five open questions from the task: (1) dual DB management, (2) result merging, (3) ingest targeting, (4) env var configuration, (5) Qdrant dual-source handling.

**Key constraint:** single-developer laptop-resident system, KISS/YAGNI, Python 3.12 + FastMCP + SQLite + Qdrant.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| OwlBear #135 research | docs/research/knowledge-scoping.md | .95 | Column-based scope filtering already implemented (schema v8). Scope column on all tables, QdrantVectorStore scope payload filtering, KnowledgeQueryService scopes param. |
| LightRAG workspace | github.com/HKUDS/LightRAG | .85 | File-based: separate subdirectories per workspace. PG: `workspace` column isolation. Pattern: column-level filtering for shared backends, directory-level for file backends. |
| Mem0 scoping | github.com/mem0ai/mem0 | .75 | Multi-level memory: user_id, session_id as metadata/payload keys. Query-time filtering. Shared backend with logical separation. |
| SQLite ATTACH DATABASE | sqlite.org/lang_attach.html | .70 | Cross-database queries via qualified table names. Atomic transactions for file-backed DBs. Max 10 attached DBs. Requires qualified names or UNION views. |
| mcp-knowledge server.py | serve/mcp-knowledge/ (internal) | .95 | Current architecture: single `sqlite3.Connection`, single `AppContext`, `QdrantVectorStore()` defaults to `:memory:`, 5 MCP tool handlers. |

## 3. Analysis

### 3.1 Architecture Options

| Criterion | A: Dual-stack facade (.55) | B: ATTACH DATABASE (.40) | C: Scope params + import/export (.80) | D: Single DB, no file (.60) |
|-----------|---------------------------|--------------------------|----------------------------------------|---------------------------|
| Physical isolation | Two live DB files | Two live DB files | Export snapshot + scoped import | None |
| KISS score | Medium | Low | **High** | **Highest** |
| Code impact | 4 new AppContext fields, 5 tool handlers rewritten | Every SQL in GraphStore modified | Expose existing scope params + ~50 LOC import/export | Zero |
| Qdrant handling | Cold-start re-index for local DB on every restart | Same cold-start problem | Single instance, scope filtering (already works) | Already works |
| Schema lifecycle | Two live DBs need independent migration; risk of silent migration in target repos | Same risk | Exports are snapshots, no drift | N/A |
| Portability | Yes (live file) | Yes (live file) | Yes (export file) | No |
| Existing infra reuse | Low — new dual wiring | Low — SQL rewrite | **High** — scope system from #135 | **Highest** |
| Prior art | LightRAG file-mode | SQLite docs | Mem0 query-time filtering; LightRAG PG workspace column | OwlBear #135 |

### 3.2 Qdrant Cold-Start Problem (key differentiator)

`QdrantVectorStore()` defaults to `:memory:`. Vector embeddings are lost on every server restart. Options A and B must solve: how to re-index local DB embeddings into Qdrant on startup. This adds startup latency proportional to local KB size and complicates the lifespan manager. Option C avoids this entirely — import materializes embeddings into the shared Qdrant once at import time.

### 3.3 Answers to Open Questions

| Question | Answer (Option C) |
|----------|-------------------|
| Q1: Two SQLite DBs? | No. Single DB. Project knowledge imported under scope. |
| Q2: Merge search results? | Use `scopes` param on `search_knowledge` (already supported downstream). |
| Q3: Ingest target? | Expose `scope` param on `ingest_document` tool. Default: `"global"`. |
| Q4: Env var for local path? | `OWLBEAR_LOCAL_KB_PATH` for import source. Auto-detect `.owlbear/knowledge/knowledge.db`. |
| Q5: Qdrant dual sources? | Single Qdrant instance. Scope payload filtering already implemented. |

## 4. Recommendation (.80 confidence)

**Scope-based tool parameters + import/export** (Option C).

Expose the existing `scopes` parameter in `search_knowledge` and `scope` in `ingest_document` tool signatures — both are already fully supported by downstream services (KnowledgeQueryService, IngestPipeline). Add `import_scope`/`export_scope` tools (~50 LOC each) for portable `.owlbear/knowledge/knowledge.db` snapshots.

**Why not dual-stack:** The challenger identified three costs not in the initial .82 estimate: (1) Qdrant cold-start re-indexing on every restart, (2) all 5 tool handlers need branching logic (not just search), (3) silent schema migration of files in target project repos. These push dual-stack to .55 confidence.

**Why not single-DB-no-file:** Portability is a real requirement per the five-tier design intent. Export/import gives physical separation without runtime complexity.

Challenge: reconsider — confidence in original: .55 (revised down from .82)
Challenger raised valid concern about Qdrant cold-start, 5-handler rewrite cost, and schema drift. Adopted counter-proposal (scope params + import/export) at .80 confidence.

## 5. Follow-up Tasks

1. **Expose scope params in MCP tools** — Add `scopes` to `search_knowledge`, `scope` to `ingest_document`, `scope` to `list_entities` tool signatures. Downstream already supports them.
2. **Build import/export tools** — `import_scope` reads `.owlbear/knowledge/knowledge.db` and ingests into global DB under a project scope. `export_scope` dumps scoped data to a portable SQLite file.
3. **Decision request** — T3 finding: this changes user-facing tool behavior and adds new MCP tools. Needs user approval before implementation.
