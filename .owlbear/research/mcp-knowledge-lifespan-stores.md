# MCP Knowledge: Lifespan — Add Protocol Stores to AppContext

> **Owning task:** #1888 — Knowledge: MCP lifespan — add protocol stores to AppContext
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1888 (follow-up from #1882 research) requires expanding the MCP knowledge server's `AppContext` dataclass and `app_lifespan()` to instantiate the new protocol-conformant stores (ContentStore, EnrichmentStore, SqliteSourceStore, IngestCoordinator). These stores power the downstream wiring tasks #1889–#1893. Question: what's the exact implementation approach, dependency order, and risk profile?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (lifespan, AppContext) | Codebase | 0.95 |
| `serve/knowledge/src/owlbear_knowledge/stores/content.py` (ContentStore) | Codebase | 0.95 |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` (EnrichmentStore) | Codebase | 0.95 |
| `serve/knowledge/src/owlbear_knowledge/stores/sources.py` (SqliteSourceStore) | Codebase | 0.90 |
| `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` (IngestCoordinator) | Codebase | 0.90 |
| `serve/knowledge/src/owlbear_knowledge/schema.py` (init_db) | Codebase | 0.80 |

## 3. Analysis

### 3.1 Dependency Graph (Instantiation Order)

```
conn, gs, vs, emb, chunker  (already exist in lifespan)
        │
        ├─→ SqliteSourceStore(conn)
        ├─→ ContentStore(db=conn, vector_store=vs, embedding_provider=emb, chunker=chunker)
        ├─→ EnrichmentStore(db=conn, graph=gs)
        │
        └─→ IngestCoordinator(sources=sqlite_source_store, content=content_store,
                              enrichment=enrichment_store, graph=gs)
```

All new stores depend only on primitives already instantiated. IngestCoordinator depends on the three new stores + `gs`. No circular deps.

### 3.2 Import Strategy

None of the new stores are exported from `owlbear_knowledge.__init__`. Direct submodule imports required:

```python
from owlbear_knowledge.stores.content import ContentStore
from owlbear_knowledge.stores.enrichment import EnrichmentStore
from owlbear_knowledge.stores.sources import SqliteSourceStore
from owlbear_knowledge.ingest_coordinator import IngestCoordinator
```

### 3.3 AppContext Extension

| New Field | Type | Optional? | Rationale |
|-----------|------|-----------|-----------|
| `content_store` | `ContentStore \| None` | Yes (None) | Graceful degradation if init fails |
| `enrichment_store` | `EnrichmentStore \| None` | Yes (None) | Same |
| `source_store_v2` | `SqliteSourceStore \| None` | Yes (None) | Distinct from existing `source_store` (old KnowledgeSourceStore) |
| `ingest_coordinator` | `IngestCoordinator \| None` | Yes (None) | Same |

All default `None` to maintain backwards compat with callers that only use old fields.

### 3.4 ensure_tables() Ordering

Must call before any store operations. Safe to call on same connection — each creates its own tables idempotently. Order:

1. `SqliteSourceStore.ensure_tables()` — creates `source_registry`
2. `ContentStore.ensure_tables()` — creates `content_documents`, `content_chunks`
3. `EnrichmentStore.ensure_tables()` — creates `enrich_queue`, `enrich_batches`, `enrich_extractions`

(`init_db()` does NOT create these tables — confirmed by grep.)

### 3.5 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Shared sqlite connection with WAL vs journal mode | Low | All stores use same conn; no cross-connection issues |
| `row_factory` override in stores | Low | ContentStore and EnrichmentStore set `row_factory = sqlite3.Row` on the shared conn; existing code also uses Row factory |
| New tables on existing DB file | None | CREATE IF NOT EXISTS is idempotent |
| Backwards compat | None | Old fields untouched; old stores still instantiated |

## 4. Recommendation

**Straightforward additive change** (confidence: .90). No design alternatives to evaluate — the architecture is prescribed by the parent research (#1882). Implementation is mechanical: 4 imports, 4 fields, 4 instantiations, 3 `ensure_tables()` calls inserted after existing store setup in lifespan.

Challenge: SKIPPED — T1 mechanical wiring with no design alternatives.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #1889–#1893 already exist as downstream wiring work gated on this task.
