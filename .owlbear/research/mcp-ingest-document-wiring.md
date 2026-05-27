# MCP `ingest_document` → IngestCoordinator Wiring

> **Owning task:** #1893 — Knowledge: MCP wire ingest_document to IngestCoordinator.ingest
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task 1893 asks to replace the old `IngestPipeline.ingest_text()` call inside the MCP `ingest_document` tool with a delegation to `IngestCoordinator.ingest(IngestRequest)`. The key questions: (A) how to resolve/create an inline source via `SqliteSourceStore`, (B) how to map existing tool parameters to `IngestRequest`/`IngestDocument`, and (C) how to surface `IngestResult` fields.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/…/server.py` L714–746 | Codebase — current tool impl | 0.95 |
| `serve/knowledge/…/ingest_coordinator.py` L43–96 | Codebase — target API | 0.95 |
| `serve/knowledge/…/protocols/ingest.py` L38–86 | Codebase — IngestRequest/Document/Result | 0.95 |
| `serve/knowledge/…/protocols/sources.py` L26–216 | Codebase — SourceKind, SourceRegistration, SourceRecord | 0.90 |
| `serve/knowledge/…/stores/sources.py` register_source | Codebase — SqliteSourceStore impl | 0.90 |
| `serve/knowledge/…/ingest.py` L297–360 | Codebase — old ingest_text for comparison | 0.85 |

## 3. Analysis

### 3.1 Parameter Mapping

| Tool param | Maps to | Notes |
|---|---|---|
| `text` | `IngestDocument.text` | Direct |
| `metadata` | `IngestDocument.metadata` + `IngestRequest.metadata` | Split: doc-level vs request-level |
| `scope` | Source scope (used in source resolution) | Not on IngestRequest directly |
| `source_url` | `IngestDocument.uri` + title derivation | Optional; also used as source name |

### 3.2 Source Resolution Strategy

`IngestCoordinator.ingest` requires `source_id` pointing to an existing source. Options:

| Strategy | Pros | Cons | Confidence |
|---|---|---|---|
| **A: Shared inline source per scope** — well-known name `mcp-inline-{scope}` | Simple, no proliferation, idempotent | All ad-hoc docs share one source | .80 |
| **B: Per-document source** — unique name per call | Clear provenance per document | Proliferates source records | .55 |
| **C: source_url-based** — use URL as name when provided, shared fallback otherwise | Best provenance when URL given | Dual-path logic | .72 |

**Recommendation: Strategy A** — a single shared inline source per scope. Rationale:
- KISS: one predictable source per scope, no orphans
- Matches `InlineConfig` semantics (config carries no per-doc state)
- Provenance is captured in `IngestDocument.uri` (from `source_url`) not the source record

### 3.3 Source Resolution Implementation

No public `find_by_name_scope` exists on `SourceStore` protocol. Options:

| Approach | Code complexity | Protocol purity |
|---|---|---|
| Try `register_source`, catch `IntegrityError` → `list_sources` + filter | ~8 LOC | ✓ Protocol-only |
| Call `list_sources(scope=scope, state=ACTIVE)` + filter by name | ~5 LOC | ✓ Protocol-only |
| Use private `_get_row_by_name_scope_any` on concrete store | ~3 LOC | ✗ Breaks abstraction |

**Recommendation:** `list_sources` + filter by name + `kind == INLINE`. The source list per scope is small; O(n) filter is fine. If not found, call `register_source` to create. Clean and protocol-compliant.

### 3.4 IngestDocument Construction

```python
IngestDocument(
    title=metadata.get("title", source_url or "Untitled inline document"),
    text=text,
    uri=source_url,  # None is valid
    external_id=None,
    metadata=metadata or {},
)
```

### 3.5 Response String Mapping

Current response: `"Ingested: {doc_id}, {chunk_count} chunks, {entity_count} entities, {edge_count} edges (status: {status})"`

New `IngestResult` fields to surface per AC:

```python
f"Ingested: documents_processed={r.documents_processed}, "
f"chunks_created={r.chunks_created}, chunks_enqueued={r.chunks_enqueued}"
```

Entity/edge counts are no longer tracked by IngestCoordinator (enrichment is async now). The response must reflect what IngestResult actually provides.

### 3.6 Error Handling

- `IngestCoordinator.ingest` raises `LookupError` if source_id invalid → shouldn't happen if resolution succeeds
- No `status == "failed"` field on IngestResult — failures surface as exceptions or zero counts
- Wrap in try/except like current impl

## 4. Recommendation

**Direct wiring with shared inline source per scope** (confidence: .82).

Implementation pseudocode:
1. Get `ingest_coordinator` and `source_store_v2` from AppContext
2. Resolve inline source: `list_sources(scope=scope, state=ACTIVE)` → filter `kind==INLINE and name==f"mcp-inline-{scope}"`
3. If not found: `register_source(SourceRegistration(name=f"mcp-inline-{scope}", kind=INLINE, fetch_method=NONE, config=InlineConfig(), scope=scope, enrich=True, refreshable=False))`
4. Build `IngestRequest(source_id=source.id, documents=(IngestDocument(...),), enrich=True, metadata=metadata or {})`
5. `result = await coordinator.ingest(request)`
6. Return formatted string with `documents_processed`, `chunks_created`, `chunks_enqueued`

Challenge: FALLBACK — T1 task, single clear path, low architectural risk.

## 5. Follow-up Tasks

This IS the builder task — no further decomposition needed. Task 1893 is ready for `backlog`.
