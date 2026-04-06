# Three-Way Comparison: Project-Local Knowledge Architecture

> **Owning task:** #616 — Add project-local knowledge source (.owlbear/knowledge/) to mcp-knowledge
> **Date:** 2026-04-06 **Status:** Complete (clarification response)

## 1. Context

User requested a head-to-head comparison of three approaches for supporting project-local knowledge in mcp-knowledge. Prior research collapsed two options into a single dismissal; this doc gives each option equal treatment.

**Goal:** When working in a target project, the knowledge server reads from both global (`store/knowledge/`) and project-local (`.owlbear/knowledge/`) sources.

## 2. Sources

| Source | URL | Relevance |
|--------|-----|-----------|
| mcp-knowledge server.py | serve/mcp-knowledge/ (internal) | .95 |
| scope_transfer.py | serve/knowledge/ (internal) | .95 |
| Schema v8 (#135 scope infra) | serve/knowledge/schema.py (internal) | .90 |
| SQLite ATTACH DATABASE | sqlite.org/lang_attach.html | .85 |
| LightRAG workspace scoping | github.com/HKUDS/LightRAG | .80 |

## 3. What Each Option Does

### Option A — Dual-Stack Facade

Opens **two separate SQLite connections** on startup. `AppContext` gains `local_conn` and `local_graph_store` fields. Server detects `.owlbear/knowledge/knowledge.db` (if present) and opens it alongside the global DB. Each MCP tool handler queries both connections and merges results (union by score for search, concatenation for lists). Ingest routes to the correct DB via a `target` parameter.

**Data location:**
- Global: `store/knowledge/knowledge.db` — always open
- Project: `.owlbear/knowledge/knowledge.db` — opened if present, skipped if absent
- Qdrant: single `:memory:` instance, must load embeddings from **both** DBs on every restart

### Option B — ATTACH DATABASE

Uses SQLite's `ATTACH DATABASE` statement to attach the project DB as schema `local` within the **single existing connection**. Creates UNION views (e.g., `CREATE TEMP VIEW all_documents AS SELECT *, 'global' AS _source FROM main.documents UNION ALL SELECT *, 'local' AS _source FROM local.documents`). GraphStore queries either use these views or qualified table names (`main.documents`, `local.documents`).

**Data location:**
- Global: `store/knowledge/knowledge.db` (the `main` schema)
- Project: `.owlbear/knowledge/knowledge.db` (the `local` schema, attached at startup)
- Qdrant: same as Option A — must re-index both DBs' embeddings on restart

### Option C — Scope Params + Import/Export

Uses a **single SQLite DB** file. All tables already have a `scope` column (schema v8, #135). Exposes the existing `scope`/`scopes` parameter on MCP tool handlers. Adds `import_scope` (reads `.owlbear/knowledge/knowledge.db`, copies rows into main DB under scope `"project:{name}"`) and `export_scope` (dumps scoped rows to a portable file). Both tools already exist in `scope_transfer.py`.

**Data location:**
- ALL runtime data: `store/knowledge/knowledge.db` (single file)
- Project knowledge: distinguished by `scope = "project:{name}"` column value
- `.owlbear/knowledge/knowledge.db`: portable snapshot (import source / export target), not live
- Qdrant: single instance, scope filtering via payload — embeddings loaded once at import

## 4. Comparison

| Criterion | A: Dual-Stack | B: ATTACH DATABASE | C: Scope Params |
|-----------|---------------|--------------------|--------------------|
| **Physical file isolation** | Yes — two live files | Yes — two live files | No — one file, logical isolation |
| **Live project access** | Yes — changes visible immediately | Yes — changes visible immediately | No — must import; snapshot-based |
| **Portability** | High — copy the file | High — copy the file | High — export produces a file |
| **Number of SQLite connections** | 2 | 1 (ATTACH adds second DB to same conn) | 1 |
| **GraphStore code changes** | All methods need if/merge logic for two stores | All SQL rewritten with qualified names or UNION views | Zero — already supports `scopes` param |
| **Tool handler changes** | All 5+ handlers: query both, merge, dedup | Transparent if using views; else same as A | Expose existing `scope`/`scopes` param only |
| **Qdrant cold-start on restart** | Must re-embed both DBs (~20-55s for 50-200 chunks) | Same as A | No — embeddings loaded once at import time |
| **Schema migration** | Two independent `init_db()` calls; silently migrates project files | Same as A | Single `init_db()` — no project file modification |
| **Transaction atomicity** | Independent per connection | Atomic across attached DBs **except** with WAL mode or `:memory:` main | Single DB — fully atomic |
| **Existing infra reuse** | Low | Low | High — #135 scope columns, scope_transfer.py |
| **LOC delta estimate** | ~500-800 | ~400-600 | ~300 (mostly already written) |
| **Test surface expansion** | ~2x (each tool: global-only, local-only, both) | ~2x (same) | ~1.3x (scope param pass-through) |

## 5. Detailed Pros and Cons

### A: Dual-Stack Facade

**Pro:**
- Cleanest physical isolation — project KB is a self-contained file in `.owlbear/knowledge/`
- Live access — no import step; project DB changes are visible instantly
- Conceptually intuitive: "two knowledge bases, one interface"
- Project file can be git-committed and shared without any export step

**Con:**
- Qdrant cold-start: in-memory Qdrant loses all embeddings on restart. Must re-embed chunks from both DBs. With BGE-M3 (CPU, lazy-load), model load alone is ~15-30s. 50-200 chunks adds 2-25s embedding time. This delay hits every server restart.
- Double tool handler complexity: every handler (search, ingest, list_entities, list_sources, get_stats, bookmarks) needs branching logic to query both DBs and merge results
- Schema drift: `init_db()` runs on both files. If OwlBear updates schema (e.g., v8 → v9), opening a project DB auto-migrates it — silently modifying files in the target project
- Doubles AppContext fields: second conn, second graph_store, second source_store
- Error handling doubles: each tool must handle "local DB absent" gracefully
- Testing surface roughly doubles

### B: ATTACH DATABASE

**Pro:**
- Single connection — no duplicate AppContext fields
- Physical isolation — same as Option A
- SQLite-native feature — well-documented, stable
- Can create UNION views for transparent access (read queries "just work" through views)
- Live access — same as Option A

**Con:**
- Every raw SQL statement in GraphStore needs qualified table names or UNION views. Current GraphStore has ~20 SQL statements; all need `main.` / `local.` prefixes or view rewrites
- UNION views: read queries scan both DBs even when you only want one scope (unless WHERE filters are added, which partially defeats the transparency benefit)
- Transaction atomicity caveat: "If the main database is ':memory:' or if journal_mode is WAL, then transactions continue to be atomic within each individual database file" — not across files. WAL is common for performance
- Same Qdrant cold-start problem as Option A
- Same schema drift problem as Option A
- Dynamic ATTACH/DETACH lifecycle: must attach on startup if project DB exists, skip if not, detach on shutdown, handle mid-session changes
- Views must be recreated if the attached DB changes or is absent
- ATTACH limit: 10 databases per connection (not a practical concern, but an architectural constraint)

### C: Scope Params + Import/Export

**Pro:**
- Minimal code — most infrastructure already exists (#135 scope columns, `scope_transfer.py`)
- No Qdrant cold-start complication — single DB, embeddings loaded once during import
- No schema drift — single DB file, single `init_db()` path
- Content-hash dedup built into `import_scope` (skips already-imported documents)
- Consistent query model: `scopes=["global", "project:myapp"]` returns merged results natively
- Test surface stays small (scope param pass-through tests only)
- KISS/YAGNI aligned — fewest moving parts

**Con:**
- NOT live access — project knowledge must be explicitly imported. Changes to `.owlbear/knowledge/knowledge.db` after import require re-import
- All data in one file — no physical isolation during runtime (logical isolation via scope column)
- Import is a copy operation — creates duplicate data (increases DB size)
- If you forget to import, project knowledge is invisible
- Export required to update the portable `.owlbear/knowledge/knowledge.db` snapshot

## 6. Risk Summary

| Risk | A: Dual-Stack | B: ATTACH | C: Scope Params |
|------|---------------|-----------|-----------------|
| Qdrant restart delay | **High** — 20-55s on every restart | **High** — same | **None** — one-time at import |
| Schema drift | **Medium** — silent migration of project files | **Medium** — same | **None** — single DB |
| Code complexity | **High** — double handlers | **High** — SQL rewrite | **Low** — param exposure |
| Data staleness | None — live | None — live | **Low** — must re-import |

## 7. Recommendation (.82 confidence)

**Option C** — Scope Params + Import/Export. For this single-developer, laptop-resident system, the live-access benefit of A/B doesn't justify the Qdrant cold-start cost, SQL rewrite burden, and schema drift risk. The import step is a one-time `import_scope` tool call per project. The existing scope infrastructure makes this the cheapest and safest path.

If live access becomes important later, Option B (ATTACH) is the better upgrade path over Option A — it preserves the single-connection model and doesn't require duplicate AppContext fields.

Challenge: SKIPPED — clarification response to user, not a new recommendation.
