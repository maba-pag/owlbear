# IngestCoordinator — Delete Cascade

> **Owning task:** #1878 — Knowledge: IngestCoordinator — delete cascade
> **Date:** 2026-05-26 **Status:** Complete

## 1. Context and Question

How should `IngestCoordinator.delete_source` orchestrate the 5-step deletion cascade while tracking progress, handling partial failures gracefully, and supporting idempotent re-runs?

## 2. Sources Studied

| # | Source | What was taken | Relevance |
|---|--------|---------------|-----------|
| 1 | `protocols/ingest.py` — `IngestCoordinator.delete_source` docstring | Full behavioral contract: cascade order, guarantees, idempotency, error semantics | 1.0 |
| 2 | `ingest_coordinator.py` — `_process_document` method | Intra-codebase precedent for Content→Enrichment→Graph mini-cascade on replacement | 0.9 |
| 3 | `stores/content.py` — `purge_source` impl | Confirms chunk_ids returned for downstream cascade; idempotent (returns empty if already purged) | 0.9 |
| 4 | [py-saga-orchestration (GitHub)](https://github.com/cdddg/py-saga-orchestration) | Orchestrator-based saga pattern; confirms sequential step tracking with failure capture | 0.7 |
| 5 | [OneUptime — Saga Pattern Python](https://oneuptime.com/blog/post/2026-01-23-saga-pattern-python/view) | Forward-recovery saga without compensating transactions; matches our idempotent-steps model | 0.7 |

## 3. Analysis

### Why NOT a full saga (no compensation needed)

Full saga patterns require compensating transactions to undo prior steps on failure. Our cascade doesn't need this because:
- Each step is **independently idempotent** by protocol contract
- Partial failure is resolved by **re-running the entire cascade** — completed steps return empty/no-op results
- No cross-module atomicity requirement (PurgeResult.PARTIAL is an acceptable outcome)

This reduces to a **forward-recovery sequential cascade** — simpler than a full saga.

### Implementation approach comparison

| Approach | Complexity | Lines | Matches codebase style | KISS |
|----------|-----------|-------|----------------------|------|
| Sequential try/except per step | Low | ~45 | Yes (`_process_document` precedent) | Yes |
| Step list + loop dispatch | Medium | ~60 | No (new pattern) | No |
| Decorator/context-manager wrapper | High | ~80 | No (over-abstraction) | No |

### Idempotency for step 1 (Sources.delete)

On re-run after partial failure, `Sources.delete_source` raises `LookupError` (source already removed). Solution: catch `LookupError` from step 1, construct synthetic `SourceDeletionInfo`, continue cascade. All downstream steps are already idempotent by contract (return empty on unknown source_id).

### Step naming for `completed_steps`

Proposed: `"sources.delete"`, `"content.purge"`, `"enrichment.discard"`, `"enrichment.purge"`, `"graph.invalidate"` — matches the module.method convention used in the cascade docstring.

### Error capture scope

Catch broad `Exception` per step (matching existing `refresh` method pattern with `# noqa: BLE001`). Any failure becomes `failed_step` + `error` in PurgeResult rather than bubbling up untracked.

## 4. Recommendation

**Sequential try/except cascade** with per-step tracking. Confidence: **0.92**

Rationale: Protocol fully prescribes behavior. All 4 dependency stores are implemented and archived. The pattern has intra-codebase precedent. Implementation is ~45 lines with zero new abstractions.

Challenge: skipped — protocol-prescribed behavior with single viable approach. No trade-offs to evaluate.

## 5. Follow-up Tasks

Task #1878 itself is ready for architect review — no additional research tasks needed. All dependencies (1870, 1872, 1874, 1876) are completed and archived.

Testing strategy: Mock all 4 stores, verify cascade order, step tracking, partial failure at each step, and idempotent re-run (step 1 LookupError → continue).
