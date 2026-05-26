---
id: 1875
title: 'Knowledge: EnrichmentStore — queue state machine'
status: backlog
priority: needed
created: 2026-05-25T19:03:53.062341+02:00
updated: 2026-05-26T03:41:21.119618+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on: []
ac:
  - enqueue_chunks(chunk_ids, source_id) transitions chunks to PENDING; returns 
    count enqueued; idempotent (already-completed/in-progress not re-enqueued); 
    FAILED items are revived to PENDING with attempts count preserved and 
    last_error cleared; raises ValueError if chunk_ids is empty
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
    max_retries (stored at claim time) transitions to FAILED (not retried by 
    mark_failed; may be explicitly re-enqueued via enqueue_chunks per AC1); 
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

[[2026-05-26T02:44:55+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1875 -> backlog | AC/protocol wording leaves FAILED re-enqueue behavior ambiguous, and current tests do not prove the disputed boundary.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 + AC5 | Cross-method contract is not independently verifiable: the protocol says only COMPLETED and IN_PROGRESS items are not re-enqueued, AC5 says mark_failed transitions to FAILED permanently, and the implementation revives FAILED items back to PENDING. Review cannot determine PASS or FAIL for this behavior from the written contract alone. | [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L28), [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L64), [serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py](serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py#L213), [serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py](serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py#L310), [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py#L100) | backlog |
| 2 | AC5 proof | The task tests prove non-reenqueue only for IN_PROGRESS and COMPLETED items and prove FAILED can be reached, but they never assert whether enqueue_chunks may or may not revive a FAILED item. The current green proof would pass under either interpretation. | [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L83), [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L90), [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L281) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Clarify whether enqueue_chunks may revive FAILED items after mark_failed reaches max_retries, and rewrite the AC/protocol wording so the chosen behavior is independently verifiable. | .owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md, serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py | Finding #1 |
| 2 | architect | Reissue proof expectations after the contract is explicit so downstream tests can assert the chosen FAILED-item behavior without guessing author intent. | .owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md, tests/test_enrichment_store_1875.py | Finding #2 |

## Observations
- Builder evidence was otherwise sufficient: the task body includes scoped tests, coverage, and lint, and there are no current editor errors in [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py) or [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py).
- The challenger cross-check did not support treating FAILED revival as a settled builder defect under the current wording, which is why this review routes to backlog rather than in-progress.

[[2026-05-26T10:45:00+02:00]]
## Architecture Review (Re-review)

### Context
Returning from review with FAIL: reviewer identified cross-method ambiguity between AC1 (re-enqueue) and AC5 (mark_failed \"permanently\") — current tests don't prove whether enqueue_chunks may revive FAILED items.

### Design Decision: FAILED Re-enqueue Semantics

**Chosen interpretation:** enqueue_chunks MAY revive FAILED items to PENDING.

**Reasoning:**
1. Protocol `enqueue_chunks` explicitly excludes only COMPLETED and IN_PROGRESS — FAILED is not excluded
2. `discard_chunks` handles FAILED items (removes them) — proving FAILED is a reachable, manageable state, not truly terminal
3. System purpose: operator should be able to retry after fixing root cause
4. `attempts` preserved on revival (not reset): simpler semantics, tracks total failure history, operator uses higher `max_retries` at next claim_batch for more retries
5. `source_id` preserved on revival: chunk's source document doesn't change

**AC changes from first review:**
- AC1: added explicit \"FAILED items are revived to PENDING with attempts count preserved and last_error cleared\"
- AC5: replaced \"permanently\" with \"not retried by mark_failed; may be explicitly re-enqueued via enqueue_chunks per AC1\"

### Builder Fix Required
Implementation already revives FAILED→PENDING but test coverage is missing:
- Add test: `enqueue_chunks` on a FAILED item → returns count=1, state becomes PENDING, attempts preserved
- Ensure existing test suite passes under the explicit contract

### Protocol Follow-up
Protocol file `mark_failed` docstring says \"transitions to FAILED permanently\" which conflicts with the re-enqueue permission. This is a documentation-level fix for a separate task (protocol wording cleanup). This task's AC is self-contained and independently verifiable.

### Challenge Results
- Challenger: reconsider (confidence 0.39)
- Key findings: protocol contradiction, vague \"claim cycle\" boundary, unjustified attempts-reset
- Architect response: accepted key findings — dropped attempts-reset (preserve instead), dropped \"claim cycle\" phrasing, replaced with concrete cross-reference between AC1 and AC5. Protocol contradiction acknowledged as out-of-scope follow-up.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (new test for FAILED re-enqueue boundary)

### Verdict: APPROVE
### Action Taken: AC refined to explicitly resolve FAILED re-enqueue ambiguity (the reviewer-identified gap). Attempts preserved, cross-references between AC1↔AC5 make behavior independently verifiable. Advanced to todo for test-writer to add the missing boundary test.

[[2026-05-26T03:06:55+02:00]]
Architecture re-review complete. Resolved reviewer-identified ambiguity: FAILED items ARE re-enqueueable (attempts preserved, last_error cleared). AC1 and AC5 now cross-reference each other for independent verifiability. Builder needs one new boundary test (FAILED re-enqueue). Proof bundle: behavioral.

[[2026-05-26T03:20:28+02:00]]
## Test-Writer Notes
- Retry: added 3 tests for reviewer gap (AC1 x AC5 FAILED re-enqueue boundary). All 3 PASS against current implementation.
- Builder skip: test-only retry, all new tests green — implementation already correct.
- Test file: tests/test_enrichment_store_1875.py
- New tests: TestFromAC_EnrichmentStore (3 additions to existing class)
  - test_enqueue_revives_failed_item_to_pending_and_returns_count_one
  - test_enqueue_preserves_attempts_count_on_failed_item_revival
  - test_enqueue_clears_last_error_on_failed_item_revival
- Total test suite: 42 tests, all PASS
- ruff: clean
- AC coverage gap filled: AC1 x AC5 cross-method contract now independently verifiable

[[2026-05-26T03:41:21+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1875 -> backlog | AC4 says stale claims are reclaimed only after the age exceeds 600s, but `claim_batch` currently reclaims at the 600s boundary and the tests do not prove that exact edge.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | Literal AC mismatch: the task contract requires reclaim only when the claim timestamp exceeds 600s, but `claim_batch` uses `started_at <= datetime('now', ?)` with `-600 seconds`, which reclaims an item exactly at the 600s boundary too. | [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L25), [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py#L148), [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py#L152), [serve/knowledge/src/owlbear_knowledge/stores/enrichment.py](serve/knowledge/src/owlbear_knowledge/stores/enrichment.py#L157) | backlog |
| 2 | AC4 proof | The proof surface does not lock down the exact TTL edge: tests cover reclaim at 701 seconds stale and non-reclaim for a fresh item, but nothing asserts the exact 600-second boundary. The suite would pass under either `>` or `>=` semantics. | [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L236), [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L252), [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L260) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reissue the stale-claim boundary explicitly as either `>600s` or `>=600s` for `claim_batch`, because this repeated review cycle cannot pass with the current literal AC-to-code mismatch. | .owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md, serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py | Finding #1 |
| 2 | architect | Reissue proof expectations that require an exact 600-second boundary test before the task returns to review. | .owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md, tests/test_enrichment_store_1875.py | Finding #2 |

## Observations
- The earlier AC1 x AC5 FAILED-item revival ambiguity is resolved for this task: the task AC now explicitly allows revival, and the retry tests prove count, attempts preservation, and `last_error` clearing at [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L397), [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L412), and [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L427).
- Builder evidence was otherwise sufficient for review: prior scoped quality-runner evidence reported 39 passing tests, 94% coverage, and clean lint, and the test-writer retry added 3 more passing tests for the AC1 x AC5 gap at [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L161), [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L162), [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L163), [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L234), and [.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md](.owlbear/kanban/tasks/1875-knowledge-enrichmentstore-queue-state-machine.md#L241).
- Non-blocking: the test header still says "FAILED permanent" at [tests/test_enrichment_store_1875.py](tests/test_enrichment_store_1875.py#L14), which no longer matches the clarified AC.
