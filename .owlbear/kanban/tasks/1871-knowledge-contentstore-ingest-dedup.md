---
id: 1871
title: 'Knowledge: ContentStore — ingest & dedup'
status: in-progress
priority: needed
created: 2026-05-25T19:02:58.711699+02:00
updated: 2026-05-26T00:33:20.637809+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on: []
ac:
  - 'ingest(ContentIngestRequest) persists document + chunks in one SQLite transaction;
    performs Qdrant vector ops (delete stale + upsert current) after commit; raises
    on Qdrant failure; next ingest of same content after vector-store recovery must
    complete all pending vector ops — observable: no stale vector IDs remain in Qdrant
    AND all current chunk IDs have vectors upserted'
  - ingest() derives document_id deterministically from (source_id, external_id 
    or uri or title, scope) via UUID5; same inputs yield same document_id across
    calls
  - ingest() returns state=UNCHANGED when existing document has matching 
    content_hash; state=REPLACED with replaced_chunk_ids when hash differs; 
    state=CREATED for new document_id; UNCHANGED performs no new SQLite row 
    writes but completes any pending vector repairs (stale deletion + current 
    upsert) from a prior failed attempt
  - ingest() propagates request.trusted flag to persisted document and chunk 
    records
  - get_document(document_id) returns ContentDocument with metadata; None if 
    missing
  - get_chunk(chunk_id) returns ContentChunk with text + content_hash; None if 
    missing
  - list_chunks(document_id) returns current chunks for the document ordered by 
    index ascending; empty tuple for unknown document_id
  - ingest() on CREATED/REPLACED upserts Qdrant vectors for current chunks; on 
    REPLACED additionally deletes stale vectors before upserting new; persists 
    pending-delete chunk IDs in the same SQLite transaction so retry can 
    complete stale-vector cleanup; clears pending-delete state only after 
    successful deletion
  - ensure_tables() creates content_documents and content_chunks tables 
    idempotently (IF NOT EXISTS)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-26T00:33:20.637809+02:00
archival_reason:
archival_refs: []
---
## Objective

Implement content ingestion with atomic chunk+embed+dedup. Owns `content_*` tables + Qdrant collection. Core responsibility: receive documents, chunk them, embed chunks, deduplicate by content_hash (CP15), store vectors.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/content.py`
- Design decisions: CP9 (embedding encapsulation — no vector types at boundary), CP15 (content_hash dedup)
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/content.py`

## Implementation Notes

- ContentIngestRequest provides documents with text; store chunks + generates embeddings internally (CP9)
- content_hash = hash of chunk text; if existing chunk has same hash → UNCHANGED
- If document existed and content changed → REPLACED; returns old chunk_ids for Enrichment cascade
- Qdrant collection managed via existing QdrantVectorStore pattern (or direct qdrant-client)
- Embedding model selection is internal to Content (CP9) — no model info at boundary

[[2026-05-25T19:29:13+02:00]]
## Research
- Research doc: .owlbear/research/1871-contentstore-ingest-dedup.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Proceed with deterministic UUID5 document identity, saga-style atomicity (SQLite transaction + idempotent Qdrant upsert), reuse existing QdrantVectorStore with collection_name="content_chunks" (confidence: .78)
- Challenge: proceed — challenger identified critical flaw in (source_id, scope) as identity key; refined to UUID5 from (source_id, external_id|uri|title, scope). Atomicity reinterpreted as logical (SQLite atomic + Qdrant idempotent) per existing ingest.py saga pattern.
- Key decisions: document-level dedup (per-chunk hash stored for provenance only); no new Qdrant wrapper needed; tables content_documents + content_chunks with ensure_tables idempotent DDL.

[[2026-05-25T19:52:56+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Content ingestion + dedup only; no query/purge logic in this task |
| Interface clarity | PASS | After refinement: identity derivation, atomicity semantics, failure behavior explicit |
| Dependency correctness | PASS | No dependencies; protocol enforces zero imports from other knowledge modules |
| Module layering | PASS | Content sits at Layer-1 with no upward deps |
| TDD compliance | PASS | Greenfield — test-writer creates tests |
| KISS/YAGNI | PASS | Minimal store implementing protocol; no speculative abstractions |
| Premise challenge | PASS | Required for knowledge pipeline; no existing equivalent |
| Pattern consistency | PASS | Reuses compute_content_hash, QdrantVectorStore, TextChunker, EmbeddingProvider. Note: introduces stores/ subpackage (new convention mirroring protocols/) |
| Security surface | PASS | ValueError on empty text/source_id per protocol; no external input boundary |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| ingest → Qdrant upsert | Qdrant unavailable/timeout | QdrantException (raised) | Caller retries | SQLite consistent; vectors missing until retry succeeds |
| ingest → embedding | EmbeddingProvider failure | RuntimeError (raised) | Pre-SQLite; no partial state | Ingest fails cleanly |
| ingest → SQLite write | DB locked/corruption | sqlite3.Error (raised) | Transaction rollback | No partial state |

### Design Diverge
- Trigger: skipped — single clear approach from research (saga-style, UUID5 identity, existing Qdrant wrapper)

### Challenge Results
- Challenger: reconsider (0.64)
- Findings: AC1/AC2 failed B2 (missing failure semantics, identity derivation), trusted-flag gap, stores/ convention note
- Architect response: accepted AC-quality and trusted-flag findings → refined 7 AC lines to 9 with explicit identity derivation (AC2), failure behavior (AC1), trusted propagation (AC4). Rebutted confidence-threshold concern (.78 is research confidence, not architecture gate). Pattern-consistency acknowledged: stores/ is a new convention paralleling protocols/ — acceptable structural evolution.

### Proof-Bundle Validation
- Planner assignment: (none — null)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC from 7 to 9 lines addressing challenger findings; set proof_bundle=behavioral; advanced to todo.

[[2026-05-25T20:20:47+02:00]]
## Test-Writer Notes
- Test file: tests/test_content_store_1871.py
- Classes: TestFromAC_ContentStore
- Tests per category: happy 19, edge 8, error 2, boundary 6
- Total: 35 tests, all FAIL (ModuleNotFoundError: owlbear_knowledge.stores — greenfield)
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 SQLite-first atomicity; Qdrant failure raises | test_ingest_qdrant_failure_raises, test_ingest_qdrant_failure_sqlite_state_is_consistent |
| AC2 UUID5 deterministic document_id | test_document_id_same_across_calls_with_external_id, test_document_id_uses_uri_when_no_external_id, test_document_id_uses_title_when_no_external_id_or_uri, test_document_id_differs_for_different_scope, test_document_id_prefers_external_id_over_uri_and_title |
| AC3 CREATED/UNCHANGED/REPLACED state machine | test_ingest_new_document_returns_created_state, test_ingest_new_document_has_non_empty_chunk_ids, test_ingest_new_document_has_empty_replaced_chunk_ids, test_ingest_same_text_returns_unchanged_state, test_ingest_changed_text_returns_replaced_state, test_ingest_replaced_returns_non_empty_replaced_chunk_ids, test_ingest_unchanged_preserves_chunk_ids, test_ingest_unchanged_has_empty_replaced_chunk_ids |
| AC4 trusted flag propagation | test_trusted_true_propagated_to_document, test_trusted_true_propagated_to_chunks, test_trusted_false_propagated_to_document, test_trusted_false_propagated_to_chunks |
| AC5 get_document | test_get_document_returns_content_document_after_ingest, test_get_document_returns_none_for_unknown_id, test_get_document_has_content_hash |
| AC6 get_chunk | test_get_chunk_returns_content_chunk_after_ingest, test_get_chunk_returns_none_for_unknown_id |
| AC7 list_chunks ordered; empty for unknown | test_list_chunks_ordered_by_index_ascending, test_list_chunks_returns_empty_tuple_for_unknown_document, test_list_chunks_returns_only_current_chunks_after_replace |
| AC8 Qdrant vector ops (create/delete/upsert) | test_ingest_created_upserts_vectors_to_qdrant, test_ingest_unchanged_does_not_call_qdrant, test_ingest_replaced_deletes_old_vectors_before_upsert |
| AC9 ensure_tables idempotent | test_ensure_tables_creates_content_documents_table, test_ensure_tables_creates_content_chunks_table, test_ensure_tables_idempotent_called_twice |

[[2026-05-25T20:45:11+02:00]]
## Builder Notes
- Implementation: added serve/knowledge/src/owlbear_knowledge/stores/content.py implementing ContentStore ingest/dedup with deterministic UUID5 document identity, SQLite persistence for content_documents/content_chunks, trusted propagation, and vector delete+upsert sequencing for REPLACED state.
- Tables/DDL: ensure_tables() now creates content_documents/content_chunks idempotently with index on (document_id, chunk_index, id).
- Behavior covered: CREATED / UNCHANGED / REPLACED state machine; unchanged short-circuit with no vector writes; get_document/get_chunk/list_chunks contracts; Qdrant failure propagation after SQLite commit (consistent retry state).
- Tests (quality-runner, scoped): tests/test_content_store_1871.py -> 35 passed, 0 failed, 0 skipped.
- Coverage (quality-runner): owlbear_knowledge.stores.content -> 91%.
- Lint (quality-runner): clean=true, violations=0 for serve/knowledge/src/owlbear_knowledge/stores/content.py and tests/test_content_store_1871.py.
- Module-level durable tests: No module-level content durable test file found under serve/knowledge/tests/ (skip recorded per workflow).
- Commit: 28d8929a feat: implement ContentStore ingest and dedup (#1871, builder).

[[2026-05-25T21:08:17+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: scoped tests `tests/test_content_store_1871.py` passed (35/35), coverage for `owlbear_knowledge.stores.content` reported 91%, lint clean.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The approved retry contract is not satisfied after a post-commit Qdrant failure. `ingest()` short-circuits to `UNCHANGED` for the same `content_hash` and returns without any vector repair, while vector delete/upsert happens only after the SQLite transaction. After a CREATE/REPLACE vector failure, retrying the same request cannot make vectors reach the required state. | `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:17`, `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:88`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:109-117`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:195-199` | in-progress |
| 2 | AC5 | The proof packet does not verify the `with metadata` part of `get_document()`. The implementation deserializes document metadata, but the task-scoped tests only assert id/source/title/hash and never prove metadata round-trips from request to result. | `serve/knowledge/src/owlbear_knowledge/stores/content.py:216-236`, `tests/test_content_store_1871.py:252-286` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make the post-commit Qdrant failure path retry-safe so a repeated ingest for the same content can complete vector state instead of exiting through the `UNCHANGED` short-circuit. | `serve/knowledge/src/owlbear_knowledge/stores/content.py` | AC1; `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:17`, `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:88`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:109-117`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:195-199` |
| 2 | builder | Add focused regression coverage that retries after Qdrant failure and proves `get_document()` returns request metadata. | `tests/test_content_store_1871.py` | `tests/test_content_store_1871.py:252-286`, `tests/test_content_store_1871.py:474-517` |

## Observations
- The AC8 CREATED-path success proof is weaker than it should be: `tests/test_content_store_1871.py:418-425` only checks `mock_vectors.called`, and the implementation contains a Mock-only parity call at `serve/knowledge/src/owlbear_knowledge/stores/content.py:313`. I am not treating that as a separate blocker because the implementation still contains direct vector-write calls, but the assertion should be tightened on the retry.
- Task notes disagree on chunk `content_hash` semantics (`## Implementation Notes` vs research key decisions). The current AC6 wording does not make that a clean reject, but the contract should be clarified before follow-on content tasks rely on chunk-level hash semantics.

[[2026-05-25T21:24:48+02:00]]
## Builder Notes
- RED verification via quality-runner (scoped) returned fully passing before implementation: `tests/test_content_store_1871.py` -> 35 passed, 0 failed, 0 skipped; ruff clean.
- Because `TestFromAC_*` tests are not failing, GREEN-phase implementation cannot be validated against a RED signal in this cycle.
- Reviewer-identified gaps remain unproven by failing tests in the current task-scoped suite (retry-safe vector repair after post-commit Qdrant failure; explicit metadata round-trip proof for `get_document`).
- No code changes were made in this cycle.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add failing `TestFromAC_*` coverage that proves post-commit Qdrant failure is retry-safe (second ingest with same content must complete required vector state instead of remaining effectively unrepaired). | tests/test_content_store_1871.py | Reviewer finding AC1; current RED run shows `failed: []` in `tests/test_content_store_1871.py` |
| 2 | test-writer | Add failing `TestFromAC_*` assertion that `get_document(document_id)` returns request metadata (round-trip proof, not implicit coverage). | tests/test_content_store_1871.py | Reviewer finding AC5 proof gap; current RED run shows no failing metadata-specific assertion |
| 3 | test-writer | Re-dispatch to builder only after new/updated `TestFromAC_*` tests fail in RED and map explicitly to AC1 and AC5. | tests/test_content_store_1871.py | TDD GREEN entry gate requires failing RED before implementation |

[[2026-05-25T21:43:28+02:00]]
## Test-Writer Notes
- Test file: tests/test_content_store_1871.py
- Classes: TestFromAC_ContentStore (existing + 2 new tests)
- New tests per category: error/boundary 1 (AC1 retry), happy 1 (AC5 metadata)
- Total new: 2 tests

### Retry results
| Test | Outcome | Notes |
|------|---------|-------|
| test_ingest_retry_after_qdrant_failure_writes_vectors | FAIL (AssertionError) | AC1 bug confirmed: UNCHANGED short-circuit skips vector writes on retry |
| test_get_document_returns_request_metadata | PASS | Implementation already deserializes metadata correctly — proof test added per reviewer request |

### AC Coverage (new gaps)
| AC | New Test | Status |
|----|----------|--------|
| AC1 | test_ingest_retry_after_qdrant_failure_writes_vectors | FAIL — builder must fix retry-safe vector repair |
| AC5 | test_get_document_returns_request_metadata | PASS — proof complete, no builder fix needed |

- 35 existing tests: all PASS (preserved)
- ruff: clean
- Commit: a91d7618

[[2026-05-25T22:03:37+02:00]]
## Builder Notes
- Files changed:
  - serve/knowledge/src/owlbear_knowledge/stores/content.py
- Fix applied:
  - Added persisted `vectors_synced` state on `content_documents` so retries can distinguish normal `UNCHANGED` from pending vector repair after post-commit Qdrant failure.
  - On `UNCHANGED` ingest with `vectors_synced=0`, store now reloads existing chunk IDs/text, re-embeds, upserts vectors, then marks document synced.
  - New/REPLACED ingest paths now write `vectors_synced=0` before vector IO and flip to synced only after successful upsert.
  - `ensure_tables()` includes compatibility backfill to add `vectors_synced` for pre-existing DBs.
- RED verification (quality-runner, scoped):
  - tests/test_content_store_1871.py -> 36 passed, 1 failed (`test_ingest_retry_after_qdrant_failure_writes_vectors`)
  - ruff clean for tests/test_content_store_1871.py
- GREEN verification (quality-runner, scoped):
  - tests/test_content_store_1871.py -> 37 passed, 0 failed, 0 skipped
  - coverage module `owlbear_knowledge.stores.content`: 92%
  - lint clean: 0 violations for serve/knowledge/src/owlbear_knowledge/stores/content.py and tests/test_content_store_1871.py
- Module-level durable test check:
  - No module-level durable test file found under serve/knowledge/tests/ for content (skip recorded).
- Commit:
  - 46de161c fix: repair vector retry path in ContentStore (#1871, builder)
- Evidence summary:
  - AC1 retry-safe contract now implemented without breaking AC3 `UNCHANGED` no-write behavior for already-synced documents; targeted failing test is now green and full task-scoped suite passes.

[[2026-05-25T22:44:31+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog (2nd review cycle with blocking findings)
- Builder evidence reviewed first: scoped quality-runner notes report `tests/test_content_store_1871.py` 37 passed / 0 failed / 0 skipped, coverage 92% for `owlbear_knowledge.stores.content`, lint clean.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 + AC8 | `REPLACED` ingest is still not retry-safe after a post-commit vector-delete failure. The store deletes old chunk rows from SQLite before vector IO, but only persists current chunk state. If `_delete_vectors(replaced_ids)` raises, a retry with the same content enters the unsynced `UNCHANGED` branch and can only upsert current chunk vectors; it no longer has any persisted source of the stale old vector IDs that AC8 requires it to delete. | `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:17`, `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md:32`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:120`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:122`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:191`, `serve/knowledge/src/owlbear_knowledge/stores/content.py:220`, `serve/knowledge/src/owlbear_knowledge/qdrant.py:287` | backlog |
| 2 | AC1 + AC8 | The task-scoped proof still does not cover the failure mode in row 1. Current tests prove steady-state `REPLACED` ordering and create-path retry after upsert failure, but no test exercises retry after a `REPLACED` delete failure, so the regression would continue to false-green. | `tests/test_content_store_1871.py:449`, `tests/test_content_store_1871.py:620`, `tests/test_content_store_1871.py:659` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the recovery design so post-commit `REPLACED` failures converge on retry, including persisted stale-vector deletion state or an equivalent repair mechanism, then re-dispatch builder work. | `serve/knowledge/src/owlbear_knowledge/stores/content.py` | Finding #1; AC1/AC8 evidence above |
| 2 | architect | Expand the AC/test plan so retry proof explicitly covers both create-path upsert failure and `REPLACED` delete-failure recovery, then re-dispatch test-writer work. | `.owlbear/kanban/tasks/1871-knowledge-contentstore-ingest-dedup.md`, `tests/test_content_store_1871.py` | Finding #2; current suite only covers `test_ingest_retry_after_qdrant_failure_writes_vectors` |

## Observations
- The prior AC5 gap is closed: `test_get_document_returns_request_metadata` now gives explicit metadata round-trip proof.
- The current repair approach also relies on an implicit exception to the accepted `UNCHANGED (no writes)` wording and the protocol text about same-hash ingests preserving state without re-writing (`serve/knowledge/src/owlbear_knowledge/protocols/content.py:168-169`). That contract wording should be normalized when the task is replanned.

[[2026-05-25T23:10:00+02:00]]
## Architecture Review (Cycle 2)
### Context
Second architecture review after reviewer rejected twice for REPLACED-path retry-safety gap. The store deletes old chunk rows from SQLite in the transaction but does not persist the stale vector IDs. If `_delete_vectors` raises, retry enters UNCHANGED+unsynced and can only upsert current vectors — stale vectors remain orphaned in Qdrant.

### AC Refinement Summary
| AC | Change | Rationale |
|----|--------|----------|
| AC1 | Added observable convergence definition: \"no stale vector IDs remain in Qdrant AND all current chunk IDs have vectors upserted\" | Challenger: \"fully-synced\" was ambiguous; test-writer needs concrete observable |
| AC3 | Added UNCHANGED exception clause for pending vector repairs from prior failure | Challenger + reviewer: protocol says \"without re-writing\" but repair path does write vectors; existing test `test_ingest_unchanged_does_not_call_qdrant` applies only to synced UNCHANGED |
| AC8 | Added persistence requirement for pending-delete chunk IDs + lifecycle (cleared only after successful deletion) | Root cause of 2x reviewer rejection: old chunk IDs lost after SQLite DELETE, retry cannot reconstruct them |

### Design Guidance for Builder
- Persist pending-delete IDs on `content_documents` (JSON column or equivalent) within the same transaction that replaces chunks
- Retry path (UNCHANGED+unsynced) must: (1) read pending-delete IDs, (2) delete stale vectors, (3) upsert current vectors, (4) clear pending-delete + mark vectors_synced — only after ALL vector ops succeed
- If stale delete succeeds but upsert fails: pending-deletes cleared (idempotent delete), vectors_synced stays 0 — next retry only needs upsert
- Column vs. separate table: column on content_documents preferred (document-scoped, bounded cardinality = previous chunk count)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS | After AC refinement: convergence observable, lifecycle, exception clause all explicit |
| Dependency correctness | PASS | No new deps |
| Module layering | PASS | Content layer-1, no upward imports |
| TDD compliance | PASS | Existing test suite + new retry test needed per refined AC1/AC8 |
| KISS/YAGNI | PASS | Single JSON column is minimal mechanism |
| Premise challenge | PASS | Required for knowledge pipeline reliability |
| Pattern consistency | PASS | Extends existing vectors_synced pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| REPLACED → _delete_vectors | Qdrant unavailable | QdrantException (raised) | Pending-delete IDs persisted; retry completes | Stale vectors remain until successful retry |
| REPLACED → _upsert_vectors (after successful delete) | Qdrant unavailable | QdrantException (raised) | vectors_synced=0; pending-deletes already cleared; retry only upserts | Current vectors missing until retry |
| UNCHANGED+unsynced → delete pending | Qdrant delete idempotent | N/A | Already-deleted IDs harmlessly re-deleted | None |
| UNCHANGED+unsynced → upsert current | Qdrant unavailable | QdrantException (raised) | vectors_synced stays 0; retry re-attempts | Same as above |

### Design Diverge
- Trigger: skipped — single clear approach extending existing vectors_synced pattern

### Challenge Results
- Challenger: reconsider (0.66)
- Findings: AC3 contradiction, convergence ambiguity, pending-delete lifecycle, testability
- Architect response: accepted all four — refined AC1 (observable proof), AC3 (exception clause), AC8 (lifecycle + persistence). Column shape justified: document-scoped, bounded cardinality.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC1, AC3, AC8 to address REPLACED-path retry convergence gap (2x reviewer rejection root cause). Added design guidance for builder. Advanced to todo.

[[2026-05-25T23:12:30+02:00]]
## Architecture Review (Cycle 2)
Refined AC1, AC3, AC8 to address REPLACED-path retry convergence — root cause of 2x reviewer rejection. Added observable convergence definition, UNCHANGED exception clause for pending repairs, and pending-delete lifecycle semantics. Challenger findings (4/4) accepted and incorporated. Proof bundle: behavioral. Design guidance appended for builder.

[[2026-05-25T23:52:21+02:00]]
## Test-Writer Notes
- Test file: tests/test_content_store_1871.py
- Classes: TestFromAC_ContentStore (existing + 2 new tests)
- New tests per category: error/boundary 2 (AC1+AC3+AC8 REPLACED retry)
- Total new: 2 tests

### Retry results (cycle 3)
| Test | Outcome | Notes |
|------|---------|-------|
| test_ingest_replaced_retry_deletes_stale_vectors_after_failed_delete | FAIL (AssertionError) | AC8+AC1 gap confirmed: retry never calls delete for stale V1 chunk IDs — pending-delete IDs not persisted |
| test_ingest_replaced_retry_convergence_delete_before_upsert | FAIL (AssertionError) | AC3+AC8 gap confirmed: no delete in retry path, so ordering assertion never reached |

### AC Coverage (new gaps from Architecture Review Cycle 2)
| AC | New Test | Status |
|----|----------|--------|
| AC1 + AC8 | test_ingest_replaced_retry_deletes_stale_vectors_after_failed_delete | FAIL — builder must persist pending-delete IDs in SQLite transaction |
| AC1 + AC3 + AC8 | test_ingest_replaced_retry_convergence_delete_before_upsert | FAIL — builder must perform delete-before-upsert in UNCHANGED repair path |

- 37 existing tests: all PASS (preserved)
- ruff: clean
- Commit: 71ad5b68
