# EnrichmentStore — Extractions & Purge Research

> **Owning task:** #1876 — Knowledge: EnrichmentStore — extractions & purge
> **Date:** 2026-05-26 **Status:** Complete

## 1. Context and Question

Implement `submit_extractions`, `suggest_intra_doc_edges`, and `purge_source` on the existing `EnrichmentStore` class. Key questions:
1. How does EnrichmentStore access GraphStore for entity/edge upserts?
2. What table schema supports extraction tracking for purge audit?
3. How does suggest_intra_doc_edges discover entities across chunks?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `protocols/enrichment.py` — full protocol | 1.0 | Authoritative interface, types, guarantees |
| 2 | `protocols/DESIGN_DECISIONS.md` CP20, CP21, CP22 | 1.0 | local_ref mechanism, read-only suggestions, claim_ttl invariant |
| 3 | `stores/graph.py` — SqliteGraphStore | 1.0 | upsert_entity, upsert_edge, add_evidence signatures and semantics |
| 4 | `stores/enrichment.py` — existing queue impl | 1.0 | Constructor pattern, table layout, _now_iso helper |
| 5 | `stores/content.py` — content_chunks schema | 0.9 | chunk→document_id mapping for intra-doc edges |
| 6 | `protocols/ARCHITECTURE.md` — cascade sequences | 0.9 | purge_source role in deletion cascade (step 4) |
| 7 | microsoft/graphrag — entity extraction workflow | 0.8 | Name-based entity dedup, co-occurrence pattern |
| 8 | `protocols/ingest.py` — IngestCoordinator | 0.8 | Cross-module coordination pattern at impl layer |

## 3. Analysis

### 3.1 Constructor Dependency Pattern

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: GraphStore via constructor | `__init__(self, *, db, graph: GraphStore)` | Type-safe, testable, follows DI | Adds coupling at init |
| B: Shared db, raw SQL to graph_* | Direct INSERT/UPDATE on graph tables | No extra dependency | Violates table ownership (graph_* is Graph-owned) |
| C: Protocol-typed dependency | `graph: GraphStoreProtocol` parameter | Loose coupling | Same as A in practice |

**Recommendation: Option A** (confidence: .92). The protocol explicitly states "implementation layer may import Graph protocols for coordination." Table ownership rules forbid raw SQL on graph_* tables. GraphStore provides idempotent upsert_entity/upsert_edge/add_evidence — exactly what submit_extractions needs.

### 3.2 Extraction Tracking Table

`EnrichmentPurgeResult` has separate `queue_items_removed` and `extractions_removed` fields. The deletion cascade (ARCHITECTURE.md) separates `discard_chunks` (step 3, queue only) from `purge_source` (step 4, extraction records). This confirms a separate tracking table.

```sql
CREATE TABLE IF NOT EXISTS enrich_extractions (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    batch_id TEXT,
    entity_count INTEGER NOT NULL DEFAULT 0,
    edge_count INTEGER NOT NULL DEFAULT 0,
    submitted_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_enrich_extractions_source ON enrich_extractions(source_id);
CREATE INDEX IF NOT EXISTS idx_enrich_extractions_chunk ON enrich_extractions(chunk_id);
```

Confidence: .85. Alternative: use COMPLETED queue entries as implicit extraction records. Rejected because purge_source deletes queue items AND extraction records as separate counts.

### 3.3 submit_extractions Algorithm

```
1. Verify chunk_id in enrich_queue with state=IN_PROGRESS (else LookupError)
2. For each ExtractedEntity: graph.upsert_entity(EntityInput) → EntityRecord
   Build mapping: local_ref → entity_id
3. For each ExtractedRelation: resolve source_ref/target_ref via mapping
   (ValueError if unresolved); graph.upsert_edge(EdgeInput) → EdgeRecord
4. For each entity: graph.add_evidence(chunk_id, ENTITY, entity_id)
   For each edge: graph.add_evidence(chunk_id, EDGE, edge_id)
5. INSERT INTO enrich_extractions (audit record)
6. UPDATE enrich_queue SET state=COMPLETED, completed_at=now WHERE chunk_id=?
7. Return ExtractionResult(chunk_id, entity_ids, edge_ids, evidence_ids)
```

Steps 1–5 are idempotent per D52: upsert_entity deduplicates by canonical name, upsert_edge by (src, tgt, type), add_evidence by (chunk, claim_type, target_id). Step 6 is the commit gate.

### 3.4 suggest_intra_doc_edges Algorithm

Per CP21 (read-only). Cross-module reads allowed at impl layer.

```
1. SELECT chunk_id FROM content_chunks WHERE document_id = ?
   (LookupError if no chunks found)
2. For each chunk_id: SELECT entity_id FROM graph_evidence
   WHERE chunk_id = ? AND claim_type = 'entity'
3. Build entity → set[chunk_id] reverse map
4. For each entity pair (A, B) appearing in different chunks:
   Emit SuggestedEdge(source=A, target=B, relation_type=RELATED_TO,
   confidence=overlap_count/total_chunks, reason="co-occurrence across N chunks")
5. Deduplicate (unordered pair), return sorted by confidence desc
```

Confidence: .85. The RELATED_TO type is the correct general-purpose relation.

### 3.5 purge_source Implementation

```
1. DELETE FROM enrich_queue WHERE source_id = ? → count queue_items_removed
2. DELETE FROM enrich_extractions WHERE source_id = ? → count extractions_removed
3. Return EnrichmentPurgeResult(source_id, queue_items_removed, extractions_removed)
```

Idempotent, never raises per protocol.

## 4. Recommendation

Implement as specified. No architectural decisions required — protocol and design decisions are authoritative.

- Constructor: add `graph: SqliteGraphStore` parameter (concrete type, internal impl)
- New table: `enrich_extractions` in `ensure_tables()`
- Three new methods: `submit_extractions`, `suggest_intra_doc_edges`, `purge_source`

Challenge: FALLBACK — trivial implementation of an existing authoritative protocol; no novel design decisions to challenge.

Confidence in approach: .90. The protocol is fully specified; the only implementation choice is the extraction tracking table schema.

## 5. Follow-up Tasks

Task #1876 itself is the implementation task — advance to backlog for architect.

### Testing Strategy

- submit_extractions: test local_ref resolution, idempotency, LookupError on wrong state, ValueError on bad local_ref
- suggest_intra_doc_edges: test co-occurrence detection, LookupError on unknown document, empty result for single-chunk documents
- purge_source: test removal counts, idempotency on unknown source_id
- Integration: full flow enqueue→claim→submit→suggest→purge
