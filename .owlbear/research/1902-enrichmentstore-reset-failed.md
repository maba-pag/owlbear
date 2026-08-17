# EnrichmentStore.reset_failed() Protocol Method Design

> **Owning task:** #1902 — Knowledge: add EnrichmentStore.reset_failed() Protocol method
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task #1901 research identified that `retry_failed_enrichment` MCP tool bypasses the EnrichmentStore Protocol, using raw SQL on the `chunks` table. This task designs the Protocol method signature, return type, and semantics for `reset_failed()`.

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py` L196–400 | Protocol contract — existing method patterns (0.95) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L331–430 | MCP tool implementation (raw SQL) (0.95) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_types.py` L104–108 | `RetryEnrichmentResult` TypedDict (0.90) |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` L37–175 | Protocol implementation — queue tables (0.90) |
| `serve/knowledge/src/owlbear_knowledge/schema.py` L80–97 | `chunks` table schema with enrichment columns (0.90) |
| `.owlbear/research/enrichment-tools-registry.md` | Prior art from #1901 research (0.85) |

## 3. Analysis

### Dual-Table Architecture Gap

| Aspect | Protocol store (`enrich_queue`) | MCP server raw SQL (`chunks`) |
|--------|------|------|
| State column | `enrich_queue.state` | `chunks.enrichment_state` |
| Lease tracking | `enrich_queue.batch_id`, `started_at` | `chunks.claimed_at`, `claimed_by`, `claim_token` |
| Error tracking | `enrich_queue.last_error`, `attempts` | `chunks.enrichment_error`, `enrichment_attempts`, `last_enrichment_error_at` |
| Used by `claim_batch` | ✅ | ❌ |
| Used by `retry_failed_enrichment` | ❌ | ✅ |

The Protocol store uses `enrich_queue`; the MCP tool uses `chunks` directly. The `reset_failed()` implementation must reconcile this — but that's an implementation concern, not a Protocol concern.

### Proposed Method Signature

Derived from MCP tool parameters (`chunk_ids`, `limit`, `scopes`) and return (`reset`, `remaining_failed`):

```python
def reset_failed(
    self,
    chunk_ids: tuple[str, ...] | None = None,
    limit: int = 100,
    scopes: tuple[str, ...] | None = None,
) -> EnrichmentResetResult:
```

### New Return Type

```python
class EnrichmentResetResult(BoundaryModel):
    """Result of resetting failed enrichment chunks to pending."""

    reset: int = 0
    remaining_failed: int = 0
```

### Semantic Contract (following existing patterns)

| Attribute | Value |
|-----------|-------|
| Guarantees | Resets failed → pending; returns counts; idempotent for already-pending |
| Non-guarantees | Selection order among failed items (implementation-defined) |
| Side effects | Writes only enrichment-owned state |
| Raises | Never (returns zero counts on empty match) |

### Comparison with Existing Methods

| Method | Similar aspect | Difference |
|--------|---------------|------------|
| `enqueue_chunks` | Resets FAILED→PENDING for explicit chunk_ids | No limit/scope filtering, no remaining count |
| `discard_chunks` | Operates on PENDING+FAILED items | Removes vs resets |
| `mark_failed` | State transition on individual chunk | Opposite direction (IN_PROGRESS→FAILED) |

### Tier Classification

**T1 — Autonomous.** Adding a Protocol method signature + return type + implementation is a standard code addition within existing architecture. No new capability, no architectural change, no security/breaking implications.

## 4. Recommendation

Add `EnrichmentResetResult` BoundaryModel and `reset_failed()` method to the Protocol with the signature above. Implementation should reconcile the dual-table gap by operating on whichever table(s) the store owns. Confidence: **0.90**.

Challenge: FALLBACK — trivial Protocol method addition mirroring existing MCP behavior; no design trade-offs requiring adversarial review.

## 5. Follow-up Tasks

Implementation task at `todo` status (Protocol method + store implementation + tests) — delegated to planner.
