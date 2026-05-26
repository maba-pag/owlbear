# IngestCoordinator — Ingest & Refresh Implementation Research

> **Owning task:** #1877 — Knowledge: IngestCoordinator — ingest & refresh
> **Date:** 2026-05-26  **Status:** Complete

## 1. Context and Question

Implement `IngestCoordinator` as a concrete class satisfying the protocol at `protocols/ingest.py`. Core concerns: (1) orchestration across 4 leaf stores with no table ownership, (2) per-document atomicity with partial-failure reporting, (3) replacement cascade (Content→Enrichment→Graph), (4) refresh staleness detection.

The legacy `IngestPipeline` (ingest.py) mixed all concerns in one class. The new design separates modules behind protocols; IngestCoordinator purely delegates.

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| IngestCoordinator Protocol | `protocols/ingest.py` | 1.0 |
| ContentStore Protocol | `protocols/content.py` | .95 |
| EnrichmentStore Protocol | `protocols/enrichment.py` | .95 |
| SourceStore Protocol | `protocols/sources.py` | .90 |
| GraphStore Protocol | `protocols/graph.py` | .90 |
| ContentStore impl | `stores/content.py` | .85 |
| EnrichmentStore impl | `stores/enrichment.py` | .85 |
| #1871 research (ContentStore ingest) | `.owlbear/research/1871-contentstore-ingest-dedup.md` | .80 |
| Saga orchestration patterns | github.com/cdddg/py-saga-orchestration | .70 |
| Async RAG Ingestion Engine | github.com/winsongr/async-rag-ingestion-engine | .65 |

## 3. Analysis

### 3.1 Ingest Flow (per document)

Protocol-defined sequence from docstring:
1. Validate `IngestRequest.documents` (min_length=1 enforced by Pydantic)
2. Verify `source_id` exists via `Sources.get_source()`
3. For each document → `Content.ingest(ContentIngestRequest)`
4. Based on `ContentIngestResult.state`:
   - **CREATED**: `Enrichment.enqueue_chunks(chunk_ids, source_id)` if `enrich=True`
   - **REPLACED**: `Enrichment.discard_chunks(replaced_chunk_ids)` + `Graph.invalidate_evidence_by_chunks(replaced_chunk_ids)` + `Enrichment.enqueue_chunks(chunk_ids, source_id)` if `enrich=True`
   - **UNCHANGED**: no action
5. Aggregate counters into `IngestResult`

### 3.2 Delete Cascade

Protocol defines strict ordering (R31):
1. `Sources.delete_source(source_id)` → `SourceDeletionInfo`
2. `Content.purge_source(source_id)` → `ContentPurgeResult` (has `chunk_ids`)
3. `Enrichment.discard_chunks(chunk_ids)` → remove pending queue items
4. `Enrichment.purge_source(source_id)` → remove extraction records
5. `Graph.invalidate_evidence_by_chunks(chunk_ids)` → remove evidence + orphans

Step ordering matters: Sources first (marks deletion), Content provides chunk_ids needed downstream.

### 3.3 Refresh Strategy

| Approach | Complexity | Accuracy | Fit |
|----------|-----------|----------|-----|
| A) Compare `last_refreshed_at` to fixed interval | Low | Coarse | KISS ✓ |
| B) Source-specific `refresh_interval` config field | Medium | Precise | Over-engineering |
| C) File mtime / HTTP ETag comparison | High | Best | Requires fetch layer |

**Recommendation (.85):** Approach A — identify stale sources via `list_sources(state=ACTIVE)` filtered to `refreshable=True`, pass `source_ids` and `force` flag from `RefreshRequest`. The coordinator doesn't decide *what* changed; it re-ingests all documents. Content's dedup (hash-check → UNCHANGED) handles no-ops efficiently. The caller/scheduler determines staleness externally.

For v1: `refresh()` lists active+refreshable sources, calls the ingest pipeline for each. Actual content fetching is NOT in scope (that's a fetch-layer concern above IngestCoordinator). Refresh accepts pre-fetched documents or signals re-fetch to an external fetcher.

### 3.4 Atomicity Decision

| Strategy | Pros | Cons |
|----------|------|------|
| All-or-nothing transaction | Simple mental model | Impossible across Qdrant + SQLite |
| Per-document saga with compensation | Correct rollback | Complex; compensating actions multiply code |
| Per-document best-effort + audit | Simple; aligns with protocol | Partial state possible |

**Decision (.85):** Per-document best-effort. The protocol explicitly states "Atomicity across modules is implementation-defined. Partial failure returns status=PARTIAL." Each store operation is individually idempotent (Content hash-checks, Enrichment skips duplicates, Graph invalidate is idempotent). Re-running ingest with the same data converges to correct state. No compensating transactions needed.

### 3.5 Constructor Injection

```python
class IngestCoordinator:
    def __init__(self, *, sources: SourceStore, content: ContentStore,
                 enrichment: EnrichmentStore, graph: GraphStore) -> None:
```

All 4 stores injected. No defaults, no optional deps. Testable via mocks implementing the protocols.

### 3.6 Error Handling

- `LookupError` if `source_id` not found (per protocol contract)
- Per-document errors captured in result counters; batch continues
- Delete cascade: step failure → `PurgeResult(status=PARTIAL, failed_step=...)`
- Source health updated via `Sources.record_health()` post-ingest

### 3.7 Challenger Findings (Critical)

| Finding | Severity | Response |
|---------|----------|----------|
| AC 6 "atomic" vs eventual consistency in Enrichment | Critical | Reinterpreted: "guaranteed-together" not distributed txn. IN_PROGRESS stale work is enrichment-internal |
| Refresh needs content fetcher (5th dep) | Critical | Accepted: split refresh to follow-up task |
| SourceUpdate lacks `last_refreshed_at` setter | Critical | Accepted: protocol extension needed before refresh |
| Partial-failure audit trail incomplete | Moderate | IngestResult.content_results carries per-doc results; delete uses PurgeResult.completed_steps |
| Source health update blind spot | Moderate | Accepted: added to implementation plan |

## 4. Recommendation (Revised Post-Challenge)

**Scope narrowing:** Implement `ingest()`, `delete_source()`, and `stats()` in this task. Split `refresh()` to a follow-up — it requires a content fetcher protocol and a `last_refreshed_at` write path that `SourceUpdate` doesn't currently expose.

Implement as a single-file `ingest_coordinator.py` (~200 LOC) with:
- Constructor DI of 4 stores + optional content fetcher (for future refresh)
- `ingest()`: validate source exists, sequential per-document loop, per-doc cascade (Content→Enrichment→Graph), aggregate counters, source health update
- `delete_source()`: sequential cascade with step tracking + `PurgeResult(status=PARTIAL)` on failure
- `stats()`: aggregate from all 4 stores
- `refresh()`: raise `NotImplementedError` with clear message (blocked on fetch layer + protocol gap)

**AC 6 interpretation ("atomic per document"):** Coordinator guarantees that if `Content.ingest` succeeds for a document, `Enrichment.enqueue_chunks` is always called in the same logical operation. If enqueue fails, the error is captured and surfaced. This is "guaranteed-together" semantics, not distributed-transaction atomicity. The known eventual-consistency window (IN_PROGRESS enrichment work on stale chunks completing after replacement) is an enrichment-internal system invariant, not a coordinator defect.

**Source health:** After ingest batch completes, call `Sources.record_health()` with OK/DEGRADED/FAILED based on outcome ratios.

Confidence: .80. Protocol gaps in refresh are real but scoped out.

Challenge: reconsider — confidence in original: .39 (challenger)
Researcher response: revised — narrowed scope to exclude refresh (critical gaps confirmed), clarified AC 6 atomicity semantics (accepted reinterpretation), added source health updates (blind spot accepted), revised LOC estimate upward.

## 5. Follow-up Tasks

1. **#1884** — SourceStore protocol: add `last_refreshed_at` write path
2. **#1885** — ContentFetcher protocol: fetch abstraction for refresh
3. **#1886** — IngestCoordinator.refresh() implementation (depends on #1884, #1885)
