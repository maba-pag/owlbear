# MCP get_next_batch → EnrichmentStore.claim_batch Wiring

> **Owning task:** #1891 — Knowledge: MCP wire get_next_batch to EnrichmentStore.claim_batch
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Replace the direct SQL claiming logic in `get_next_batch` (MCP tool) with delegated calls to `EnrichmentStore.claim_batch()` + `ContentStore.get_chunk()` for text hydration. The response shape (`EnrichmentChunk` TypedDict) must remain identical.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/.../server.py` L132-197 | Codebase — current impl | 0.95 |
| `serve/knowledge/src/.../stores/enrichment.py` L177-256 | Codebase — target `claim_batch` | 0.95 |
| `serve/knowledge/src/.../stores/content.py` L255, L283 | Codebase — `get_document`, `get_chunk` | 0.90 |
| `serve/knowledge/src/.../stores/sources.py` L158 | Codebase — `get_source` | 0.85 |
| `serve/mcp-knowledge/src/.../_types.py` L93-113 | Codebase — `EnrichmentChunk` TypedDict | 0.90 |
| `.owlbear/research/mcp-knowledge-write-ops-wiring.md` | Prior research | 0.80 |

## 3. Analysis

### 3.1 Field Mapping: Old SQL → New Store Calls

| Response field | Old source (SQL JOIN) | New source |
|---|---|---|
| `chunk_id` | `c.id` | `EnrichmentQueueItem.chunk_id` |
| `text` | `c.content` | `ContentChunk.text` via `get_chunk()` |
| `doc_title` | `d.title` | `ContentDocument.title` via `get_document()` |
| `section_path` | `c.metadata` (parsed) | `ContentChunk.section_path` (tuple→`"/".join()`) |
| `source_name` | `ks.name` | `SourceRecord.name` via `get_source()` |
| `document_id` | `d.id` | `ContentChunk.document_id` |
| `source_id` | `d.source_id` | `EnrichmentQueueItem.source_id` |
| `scope` | `d.scope` | `ContentChunk.scope` |
| `claim_token` | generated UUID (`uuid4().hex`) | `EnrichmentBatch.batch_id` |
| `claimed_at` | `now.isoformat()` | `EnrichmentQueueItem.started_at` |

### 3.2 Implementation Pattern

```python
enrichment_store = app_ctx.enrichment_store
content_store = app_ctx.content_store
source_store_v2 = app_ctx.source_store_v2

batch = enrichment_store.claim_batch(EnrichmentParams(batch_size=limit))
# Hydrate per-item with dedup caches for documents/sources
doc_cache: dict[str, ContentDocument] = {}
source_cache: dict[str, SourceRecord] = {}
results: list[EnrichmentChunk] = []
for item in batch.items:
    chunk = content_store.get_chunk(item.chunk_id)
    # ... hydrate doc_title, source_name from caches
    results.append({...})
return results
```

### 3.3 Performance: N+1 Concern

| Approach | Calls for 10 items | Latency | Complexity |
|----------|-------------------|---------|------------|
| Per-item calls (with local caches) | 10 get_chunk + ~2 get_document + ~1 get_source | <5ms total (same SQLite conn) | Low |
| Bulk helper methods (not in protocol) | 1-3 calls | <2ms | Medium (protocol addition) |
| Keep SQL JOIN (status quo) | 1 query | <1ms | N/A |

Verdict: per-item with dedup caches is acceptable. Max batch size is 100; all calls hit the same in-process SQLite connection (no network hop). Adding bulk protocol methods is YAGNI for now.

### 3.4 Behavioral Differences (Risks)

| Concern | Old behavior | New behavior | Risk |
|---------|-------------|-------------|------|
| Source `enrich` filter | Checked at claim time (`ks.enrich=1 AND ks.enabled=1`) | Not checked — items only enter queue if source had `enrich=True` at ingest time | Low — toggling enrich off post-ingest is rare; items drain naturally |
| Stale claim TTL | 600s hardcoded in SQL `WHERE` | `_CLAIM_TTL_SECONDS` constant in EnrichmentStore | None — same value (600s) |
| Table schema | `chunks` + `documents` + `knowledge_sources` | `enrich_queue` + `content_chunks` + `content_documents` + `source_registry` | Medium — data must exist in new tables |
| Empty chunk | SQL always returns rows with content | `get_chunk()` can return `None` if chunk deleted between claim and hydration | Low — handle gracefully (skip or empty text) |

### 3.5 Prerequisites

AppContext already has `enrichment_store`, `content_store`, `source_store_v2` instantiated and tables ensured (verified in lifespan L434-510). No additional setup needed.

## 4. Recommendation

**Direct replacement** (confidence: .85). Replace the SQL block in `get_next_batch` with:
1. `enrichment_store.claim_batch(EnrichmentParams(batch_size=limit))`
2. Per-item hydration via `content_store.get_chunk()` / `get_document()` / `source_store_v2.get_source()`
3. Assemble into same `EnrichmentChunk` TypedDict shape

Builder notes:
- Handle `get_chunk()` returning `None` (skip item or use empty text)
- Use `"/".join(chunk.section_path)` or `None` for section_path serialization
- Use `batch.batch_id` as `claim_token`, `item.started_at.isoformat()` as `claimed_at`
- Cache `get_document()` and `get_source()` results by ID to avoid redundant lookups
- Remove old `_extract_section_path()` helper if unused after change
- The `_normalize_batch_limit()` helper stays (validates input)

Challenge: FALLBACK — T1 refactor with clear 1:1 mapping, no architectural decision needed.

## 5. Follow-up Tasks

No decomposition needed — AC is coherent single-task scope. Task advances to backlog as-is.
