# Remove Source MCP Tool — Implementation Analysis

> **Owning task:** #1652 — P1-03: Add remove_source MCP tool with vectors-first abort
> **Date:** 2026-05-18 **Status:** Complete

## 1. Context and Question

Task #1652 requires adding a `remove_source` MCP tool to the knowledge server with vectors-first abort semantics. The brief (parent #1650, decision D8) mandates: delete Qdrant vectors first, abort on any failure, then cascade-delete SQLite data. This research validates the approach against live code and documents the implementation path.

## 2. Sources Studied

| Source | Type | Relevance | What |
|--------|------|-----------|------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Codebase | 1.0 | AppContext, lifespan, all 8 existing MCP tools, error patterns |
| `serve/knowledge/src/owlbear_knowledge/qdrant.py` | Codebase | 1.0 | `QdrantVectorStore.delete_embedding` — returns bool, raises on client errors |
| `serve/knowledge/src/owlbear_knowledge/source_store.py` | Codebase | 1.0 | `delete_cascade` — SQL cascade with commit, `get` for source lookup |
| `serve/knowledge/src/owlbear_knowledge/document_store.py` | Codebase | 0.9 | `delete_chunk_embeddings` — best-effort pattern (antipattern for this tool) |
| `serve/knowledge/src/owlbear_knowledge/schema.py` | Codebase | 0.9 | DDL for chunks, documents, entities — FK relationships |
| `modelcontextprotocol/python-sdk` (GitHub) | External | 0.8 | `ToolAnnotations.destructive_hint`, FastMCP tool registration patterns |

## 3. Analysis

### 3.1 AppContext Extension (AC-1)

`AppContext` is a `@dataclass(slots=True)` at server.py L1228. Currently has `conn`, `query_service`, `graph_store`, `ingest_pipeline`, `source_store`, plus optional enrichment fields. No `vector_store`.

`app_lifespan` builds `vs = QdrantVectorStore(location=qdrant_path)` at L1287 but only passes it to `KnowledgeQueryService` and `DocumentStore` — never to `AppContext` directly.

**Change:** Add `vector_store: QdrantVectorStore | None = None` field. Wire `vs` in the `AppContext(...)` constructor call. Backward-compatible (default None, slots=True means field order matters — place after existing optional fields).

### 3.2 Tool Implementation (AC-2)

SQL to collect chunk IDs:
```sql
SELECT c.id FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.source_id = ?
```

Count queries (run before cascade):
```sql
SELECT COUNT(*) FROM documents WHERE source_id = ?
SELECT COUNT(*) FROM chunks c JOIN documents d ON c.document_id = d.id WHERE d.source_id = ?
SELECT COUNT(*) FROM entities e JOIN documents d ON e.document_id = d.id WHERE d.source_id = ?
```

`delete_embedding(chunk_id)` returns `True` (deleted) or `False` (not found). Both are acceptable — missing vectors are not errors. Only Qdrant client exceptions trigger abort.

After successful vector cleanup: call `source_store.delete_cascade(source_id)` which handles the full SQL cascade with commit.

**Tool signature:** `remove_source(ctx: Context, source_id: str) -> dict` with `ToolAnnotations(readOnlyHint=False, destructiveHint=True)`.

### 3.3 Abort Semantics (AC-3)

`document_store.delete_chunk_embeddings` catches all exceptions (best-effort). This tool must NOT follow that pattern — it needs strict abort.

**Pattern:** Iterate chunk IDs, call `delete_embedding` inside a try block. On any exception, raise `ToolError` with the failed chunk ID and error details. Since no SQLite changes happen before cascade, abort is clean — no rollback needed.

### 3.4 Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Large source with many chunks — slow sequential deletion | Low | Qdrant local is fast; no batch API available on `QdrantVectorStore` |
| Qdrant orphan vectors if cascade fails after vector cleanup | Low | `delete_cascade` is a single SQLite transaction; failure is rare |
| `vector_store` is None at runtime | Low | Tool checks for None and raises `ToolError` |

## 4. Recommendation

Proceed with implementation as specified in the brief. No alternative approaches needed — the design aligns with existing patterns, KISS, and the codebase's error-handling conventions.

Challenge: skipped — implementation follows pre-approved brief with no design alternatives.

Confidence: **0.92** — straightforward extension of existing patterns with clear FK relationships and well-defined APIs.

## 5. Follow-up Tasks

No new follow-up tasks needed — #1652 itself is the implementation task. Advancing to backlog for architecture review and TDD.
