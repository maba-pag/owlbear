---
id: 1875
title: 'Knowledge: EnrichmentStore — queue state machine'
status: review
priority: needed
created: 2026-05-25T19:03:53.062341+02:00
updated: 2026-05-26T01:52:39.874012+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on: []
ac:
  - enqueue_chunks(chunk_ids, source_id) transitions chunks to PENDING; returns 
    count enqueued; idempotent (already-completed/in-progress not re-enqueued); 
    raises ValueError if chunk_ids is empty
  - discard_chunks(chunk_ids) removes PENDING and FAILED items; leaves 
    IN_PROGRESS untouched; returns EnrichmentDiscardResult; idempotent (absent 
    chunks silently ignored)
  - claim_batch(EnrichmentParams) returns up to batch_size PENDING chunks 
    transitioned to IN_PROGRESS; assigns batch_id + claim timestamp; persists 
    max_retries from params per-item for mark_failed threshold
  - claim_batch also reclaims stale IN_PROGRESS items whose claim timestamp 
    exceeds 600s claim_ttl back to PENDING before selecting candidates (system 
    invariant, not caller-tunable)
  - mark_failed(chunk_id, error) increments attempts; if attempts >= per-item 
    max_retries (stored at claim time) transitions to FAILED permanently; 
    otherwise returns to PENDING for retry; raises LookupError if chunk_id not 
    IN_PROGRESS
  - stats() returns EnrichmentStats with counts per state (pending, in_progress,
    completed, failed)
  - ensure_tables() creates enrich_queue and enrich_batches tables idempotently;
    follows existing SQLite store pattern (ContentStore, SqliteGraphStore)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement the enrichment state machine: chunks flow through PENDING → IN_PROGRESS → COMPLETED/FAILED. Supports batch claiming with automatic retry on failure. Owns `enrich_*` tables.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py`
- Design decisions: CP10 (agent-external enrichment — state machine only, no LLM), D52 (submit_extractions idempotency), CP22 (claim_ttl = system invariant, 600s)
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py`

## Implementation Notes

- State machine: PENDING → IN_PROGRESS → COMPLETED/FAILED (EnrichmentState enum)
- claim_batch assigns a unique batch_id and claim timestamp; transitions items to IN_PROGRESS
- mark_failed(chunk_id, error): increments attempts; if attempts >= max_retries → FAILED; else → PENDING (automatic retry)
- Internal claim_ttl (600s default): stale IN_PROGRESS items auto-expire back to PENDING (system invariant, not caller-tunable)
- No release_claim method — crash recovery handled by claim_ttl; graceful release via mark_failed
- enqueue is idempotent — already-completed/in-progress chunks not re-enqueued
- discard removes PENDING and FAILED items; leaves IN_PROGRESS untouched

## DR Resolution (2026-05-25)

AC amended to match authoritative protocol. Protocol is source of truth per ARCHITECTURE.md Spec Amendment Process:
- State: IN_PROGRESS (not CLAIMED)
- Failure: mark_failed with retry semantics (not fail_chunk with permanent failure)
- No release_claim (claim_ttl handles crash recovery; mark_failed handles graceful release)"

[[2026-05-26T01:16:08+02:00]]


## Architecture Review

### Scope Correction

Removed `submit_extractions` from this task's AC — it belongs to #1876 (extractions & purge) which explicitly depends on #1875 for queue tables and state machine infrastructure. This task implements PENDING → IN_PROGRESS → FAILED transitions and the queue infrastructure. The COMPLETED transition is reached via submit_extractions in #1876.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Queue state machine only (enqueue, claim, fail, discard, stats, tables) |
| Interface clarity | PASS | All method signatures, returns, idempotency guarantees, and error conditions specified |
| Dependency correctness | PASS | No external task dependencies; Graph not needed (submit_extractions moved to #1876) |
| Module layering | PASS | Store implements protocol; no upward imports |
| TDD compliance | PASS | Greenfield; test-writer handles RED phase |
| KISS/YAGNI | PASS | Minimal state machine per protocol; no hypothetical features |
| Premise challenge | PASS | Required by enrichment pipeline; no existing implementation |
| Pattern consistency | PASS | Follows ContentStore/SqliteGraphStore pattern (sqlite3.Connection, ensure_tables) |
| Security surface | PASS | Internal SQLite only; no system boundaries |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| claim_batch concurrent | Race on same PENDING item | N/A | SQLite WAL + transaction serializes | None (one caller wins) |
| mark_failed non-IN_PROGRESS | Invalid state transition | LookupError | AC-specified | Caller error |
| claim_ttl expiry during processing | Item re-enters PENDING | N/A | By design (crash recovery) | Agent may double-process |

### Design Diverge
- Skipped: single clear approach (SQLite state machine following existing store pattern); no competing approaches.

### Challenge Results
- Challenger: reconsider (confidence 0.33)
- Key findings: submit_extractions scope overlap with #1876; max_retries source ambiguous; claim_ttl not testable as stated; missing error conditions
- Architect response: accepted — removed submit_extractions from scope, clarified max_retries persistence, made claim_ttl a verifiable claim_batch behavior, added error conditions to AC

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: AC refined (removed submit_extractions, added error conditions, clarified max_retries persistence, made claim_ttl testable via claim_batch behavior), proof_bundle set to behavioral, advanced to todo.

[[2026-05-26T01:16:13+02:00]]
Architecture review complete. Refined AC: removed submit_extractions (belongs to #1876), added error conditions (ValueError, LookupError), clarified max_retries persistence per-item at claim time, made claim_ttl testable as claim_batch behavior. Proof bundle: behavioral.

[[2026-05-26T01:33:08+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_enrichment_store_1875.py`
**Class:** `TestFromAC_EnrichmentStore`
**Total tests:** 37 — all FAIL (ImportError on greenfield `owlbear_knowledge.stores.enrichment`)
**Lint:** clean (ruff exit 0)

### Tests per category

| AC | Category | Tests |
|----|----------|-------|
| AC1 — enqueue_chunks | happy/edge/error | 7 |
| AC2 — discard_chunks | happy/edge/boundary | 6 |
| AC3 — claim_batch | happy/edge/boundary | 9 |
| AC4 — stale reclaim | happy/edge | 2 |
| AC5 — mark_failed | happy/edge/error | 6 |
| AC6 — stats | happy/edge | 6 |
| AC7 — ensure_tables | happy/boundary | 3 |

### AC coverage

| AC line | Tests covering it |
|---------|------------------|
| enqueue_chunks → PENDING, returns count, idempotent, ValueError on empty | test_enqueue_returns_count_*, test_enqueue_transitions_*, test_enqueue_idempotent_*, test_enqueue_partial_dedup_*, test_enqueue_raises_value_error_* |
| completed/in-progress not re-enqueued | test_enqueue_does_not_reenqueue_in_progress_*, test_enqueue_does_not_reenqueue_completed_* |
| discard_chunks removes PENDING/FAILED, leaves IN_PROGRESS, idempotent | test_discard_removes_pending_*, test_discard_removes_failed_*, test_discard_leaves_in_progress_*, test_discard_absent_*, test_discard_idempotent_*, test_discard_mixed_states_* |
| claim_batch batch_size, batch_id, claim timestamp, max_retries | test_claim_batch_transitions_*, test_claim_batch_assigns_batch_id_*, test_claim_batch_assigns_unique_*, test_claim_batch_assigns_claim_timestamp_*, test_claim_batch_respects_batch_size_*, test_claim_batch_returns_fewer_*, test_claim_batch_empty_*, test_claim_batch_claimed_items_not_visible_*, test_claim_batch_max_retries_persisted_* |
| stale IN_PROGRESS (>600s) reclaimed, fresh untouched | test_claim_batch_reclaims_stale_*, test_claim_batch_does_not_reclaim_fresh_* |
| mark_failed retry/permanent/LookupError | test_mark_failed_returns_to_pending_*, test_mark_failed_increments_*, test_mark_failed_transitions_to_failed_*, test_mark_failed_uses_per_item_*, test_mark_failed_raises_lookup_error_if_chunk_is_pending_*, test_mark_failed_raises_lookup_error_if_chunk_not_found_* |
| stats counts per state | test_stats_returns_*, test_stats_zero_*, test_stats_counts_pending_*, test_stats_counts_in_progress_*, test_stats_counts_failed_*, test_stats_counts_completed_* |
| ensure_tables idempotent | test_ensure_tables_creates_enrich_queue_*, test_ensure_tables_creates_enrich_batches_*, test_ensure_tables_is_idempotent_* |

**Failure mode:** ImportError at collection (greenfield — no source file exists). All 37 tests fail.

[[2026-05-26T01:52:39+02:00]]
## Builder Notes
- Implementation: added [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py) (new SQLite-backed Enrichment queue state machine store).
- Files changed: [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py)
- Approach: implemented AC-scoped queue state machine only (`ensure_tables`, `enqueue_chunks`, `discard_chunks`, `claim_batch` with stale reclaim TTL=600s, `mark_failed`, `stats`) with per-item `max_retries` persisted at claim-time.
- Tests (RED baseline): quality-runner reported collection failure before implementation due to missing module import ([tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py)).
- Tests (GREEN verification): quality-runner scoped run passed `39` tests in [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py), failed `0`, skipped `0`.
- Coverage: `94%` for module `owlbear_knowledge.stores.enrichment`.
- Lint: `ruff clean` (`clean: true`, no violations) for [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py) and [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py).
- Module-level durable test file check: no existing module-level durable enrichment test file found (`serve/knowledge/tests/test_enrichment_store.py` absent; `tests/test_enrichment_store.py` absent) — skipped per workflow guidance.
- Commit: `e1b8ae28` (`feat: implement enrichment queue state machine (#1875, builder)`).
