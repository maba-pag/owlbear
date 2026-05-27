---
id: 1902
title: 'Knowledge: add EnrichmentStore.reset_failed() Protocol method'
status: archived
priority: needed
created: 2026-05-27T21:12:15.484583+02:00
updated: 2026-05-27T22:15:15.735101+02:00
tags:
  - knowledge
  - layer-4
parent:
depends_on: []
ac:
  - 'EnrichmentResetResult BoundaryModel added to protocols/enrichment.py with fields:
    reset: int = 0, remaining_failed: int = 0'
  - 'EnrichmentStore Protocol defines reset_failed(self, chunk_ids: tuple[str, ...]
    | None = None, limit: int = 100, scopes: tuple[str, ...] | None = None) -> EnrichmentResetResult
    with standard 4-section docstring (Guarantees, Non-guarantees, Side effects, Raises:
    Never)'
  - When chunk_ids is provided it is the exclusive filter — limit and scopes are
    ignored; each matching FAILED item transitions to PENDING
  - 'When chunk_ids is None, bulk path applies: only items from enabled+enrich-flagged
    sources are eligible; scopes filters by document scope; limit caps reset count;
    selection order is implementation-defined'
  - Reset clears error tracking state (last_error/enrichment_error, attempt 
    counters, claim fields) for each transitioned item
  - remaining_failed counts items still in FAILED state after the operation 
    completes, scoped to the same state source the implementation uses for the 
    reset
  - 'Idempotent: calling with already-pending chunk_ids or no matching FAILED items
    returns reset=0, remaining_failed=current count, no error'
  - SQLite EnrichmentStore in stores/enrichment.py implements reset_failed 
    reconciling the dual-table state (enrich_queue vs chunks.enrichment_state) 
    per implementation choice documented in method comments
  - EnrichmentResetResult exported from protocols/enrichment.py (added to 
    module-level imports and the protocols package re-export in 
    protocols/__init__.py)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Add a `reset_failed(chunk_ids, limit, scopes)` method to the EnrichmentStore Protocol in `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py`. This enables `retry_failed_enrichment` to be cleanly routed through the Protocol instead of using raw SQL.

## Context

Discovered during #1901 research — `retry_failed_enrichment` currently bypasses the Protocol and uses raw SQL directly. Adding the Protocol method unblocks clean routing in MCP_TOOL_ROUTING.

[[2026-05-27T21:17:51+02:00]]
## Research
- Research doc: .owlbear/research/1902-enrichmentstore-reset-failed.md
- Sources: 6 studied, 4 high-relevance (all internal codebase)
- Recommendation: Add `EnrichmentResetResult` BoundaryModel + `reset_failed(chunk_ids, limit, scopes)` method to Protocol (confidence: 0.90)
- Follow-up tasks created: none needed — task itself IS the implementation unit
- Decision requests: none (T1 — standard Protocol method addition)

## Challenge Results
- Challenger: FALLBACK — trivial Protocol addition mirroring existing MCP behavior
- Confidence in original: 0.90
- Key findings: dual-table gap (enrich_queue vs chunks.enrichment_state); implementation must reconcile
- Method signature: `reset_failed(chunk_ids: tuple[str, ...] | None, limit: int, scopes: tuple[str, ...] | None) -> EnrichmentResetResult`

[[2026-05-27T21:33:18+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One Protocol method + one return type |
| Interface clarity | PASS | Signature, parameter exclusivity, and semantics specified in AC |
| Dependency correctness | PASS | No dependencies; standalone Protocol addition |
| Module layering | PASS | Enrichment Protocol owns enrichment state; no upward imports |
| TDD compliance | PASS | No preceding test task needed — behavioral bundle handles it |
| KISS/YAGNI | PASS | Directly needed for MCP tool routing (#1901); not speculative |
| Premise challenge | PASS | MCP tool currently bypasses Protocol with raw SQL — this gap is real |
| Pattern consistency | PASS | Follows existing Protocol patterns (enqueue_chunks, discard_chunks, mark_failed) |
| Security surface | PASS | No new system boundary |
| Single domain | PASS | Knowledge domain only |

### Design Diverge
- Trigger: skipped — single clear approach (add Protocol method mirroring existing MCP behavior)

### Challenge Results
- Challenger: reconsider (0.61)
- Findings: AC ambiguity around cleared fields, remaining_failed source of truth, parameter exclusivity, export target, and relationship to enqueue_chunks
- Architect response: revised — rewrote AC to address all challenger concerns (9 specific AC lines covering exclusivity, cleared state, dual-table reconciliation, and precise export target)

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Wrote 9 AC lines addressing challenger feedback, set proof_bundle=behavioral, advanced to todo

[[2026-05-27T21:40:12+02:00]]
## Test-Writer Notes
- Test file: tests/test_enrichment_reset_1902.py
- Classes: TestFromAC_EnrichmentResetResult, TestFromAC_ResetFailedSignature, TestFromAC_ResetFailedChunkIdsPath, TestFromAC_ResetFailedBulkPath, TestFromAC_ResetFailedErrorClearing, TestFromAC_ResetFailedRemainingFailed, TestFromAC_ResetFailedIdempotency
- Tests per category: happy 14, edge 8, error 3, boundary 8
- Total: 33 tests, all FAIL (collection-level ImportError — EnrichmentResetResult not yet in protocols/enrichment.py)
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 — EnrichmentResetResult BoundaryModel, fields | test_importable_from_protocols_enrichment, test_default_reset_field_is_zero, test_default_remaining_failed_field_is_zero, test_fields_accept_explicit_values |
| AC2 — Protocol method signature, Raises: Never | test_store_has_reset_failed_method, test_returns_enrichment_reset_result, test_callable_with_no_arguments, test_callable_with_all_parameters, test_never_raises_on_empty_queue |
| AC3 — chunk_ids exclusive filter | test_failed_chunk_transitions_to_pending, test_reset_count_matches_matching_failed_chunks, test_resets_only_specified_chunks, test_limit_ignored_when_chunk_ids_provided, test_scopes_ignored_when_chunk_ids_provided, test_non_failed_chunks_not_counted |
| AC4 — bulk path, limit | test_bulk_resets_all_failed_items_by_default, test_bulk_limit_caps_reset_count, test_bulk_limit_two_resets_two, test_bulk_remaining_reflects_uncapped_items, test_bulk_default_limit_is_100 |
| AC5 — error state cleared | test_last_error_cleared_in_queue, test_claim_fields_cleared_after_reset, test_reset_chunk_claimable_in_next_batch |
| AC6 — remaining_failed | test_remaining_zero_when_all_reset, test_remaining_counts_items_not_covered, test_remaining_zero_when_no_failed_items, test_remaining_reflects_failed_after_bulk_limit |
| AC7 — idempotency | test_already_pending_chunk_ids_reset_zero, test_nonexistent_chunk_id_reset_zero, test_second_call_same_chunk_ids_is_zero, test_remaining_failed_still_accurate_on_noop, test_bulk_empty_queue_never_raises, test_bulk_only_pending_queue_reset_zero |
| AC8 — SQLite store implements | covered by store-level behavioral tests throughout |
| AC9 — re-export from protocols package | test_importable_from_protocols_package, test_same_class_from_both_import_paths |

[[2026-05-27T21:48:27+02:00]]
## Builder Notes
- Implementation files changed:
  - serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py
  - serve/knowledge/src/owlbear_knowledge/protocols/__init__.py
  - serve/knowledge/src/owlbear_knowledge/stores/enrichment.py
- RED verification (quality-runner): expected collection ImportError confirmed before implementation (`EnrichmentResetResult` missing).
- Tests (quality-runner, scoped):
  - tests/test_enrichment_reset_1902.py: 35 passed, 0 failed
  - tests/test_enrichment_store_1875.py + tests/test_enrichment_store_1876.py + task file: 125 passed, 0 failed
- Coverage (quality-runner):
  - owlbear_knowledge.stores.enrichment: 90%
  - owlbear_knowledge.protocols.enrichment: 100%
- ruff: clean (scoped to touched files + task test)
- Evidence summary: AC1-AC9 implemented via new `EnrichmentResetResult` boundary model, protocol signature/docs, package re-export, and SQLite `reset_failed()` implementation with chunk_ids-exclusive behavior, bulk-limit behavior, state clearing, remaining_failed reporting, and documented dual-table reconciliation.
- Fixes applied during verification: replaced ambiguous Unicode punctuation in protocol docstrings with ASCII to satisfy RUF002.
- Commit: `16de5a16 feat: add enrichment reset_failed protocol/store (#1902, builder)`

### Post-task Reflection
- Problems faced: package-wide lint paths surfaced unrelated baseline violations, obscuring task-specific evidence.
- Workarounds applied: switched lint evidence to touched-file scope for precise builder proof.
- Patterns discovered: optional table-existence checks let enrichment reset reconcile modern queue state with legacy `chunks` state safely.
- Time sinks: single-file task tests under-covered a large store module until adjacent enrichment regressions were included.
- Quality gaps: no canonical module-level durable enrichment test file is present yet; legacy root enrichment tests were used for regression signal.

[[2026-05-27T21:58:48+02:00]]
## Review Evidence
- Verdict: FAIL
- Summary: Builder evidence is internally consistent and the implementation appears to satisfy the contract by inspection, but the task-local proof is incomplete for AC-critical branches, so this is a test-proof rejection rather than an implementation rejection.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | Bulk-path proof does not cover the enabled+enrich source filter or document-scope filter. The implementation applies those predicates in _select_failed_for_bulk_reset, but the task tests only exercise the default ensure_tables fixture and generic bulk-reset counts. A regression in source eligibility or scope filtering would still pass. | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:598-605; tests/test_enrichment_reset_1902.py:49-51; tests/test_enrichment_reset_1902.py:203-239; tests/test_enrichment_reset_1902.py:365-374 | todo |
| 2 | AC5 | Queue-side reset proof is incomplete for attempt-counter clearing. The implementation resets attempts to 0 together with last_error and claim fields, but the tests only assert last_error clearing and batch_id/started_at clearing. A broken attempts reset would still pass. | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:222-223; tests/test_enrichment_reset_1902.py:251-281 | todo |
| 3 | AC5, AC8 | Mixed-schema reconciliation is unproved. The implementation syncs legacy chunks fields (enrichment_state, claimed_at, claimed_by, claim_token, enrichment_error, enrichment_attempts) when a chunks table exists, but the task fixture only calls ensure_tables and ensure_tables creates only enrich_* tables. No test creates chunks rows, so a broken _sync_legacy_chunk_state path would still pass. | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:49-79; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:638-643; tests/test_enrichment_reset_1902.py:49-51 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add bulk-reset tests that create source_registry and content_chunks fixtures, then prove reset_failed(chunk_ids=None, ...) excludes disabled/non-enrich sources and honors scopes filtering. | tests/test_enrichment_reset_1902.py | AC4 finding #1; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:598-605 |
| 2 | test-writer | Add a reset_failed assertion that the queue-row attempts column is reset to 0 after FAILED -> PENDING transition. | tests/test_enrichment_reset_1902.py | AC5 finding #2; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:222-223 |
| 3 | test-writer | Add a mixed-schema reset_failed test that creates legacy chunks rows and proves legacy state, claim, and error fields are cleared alongside the queue reset. | tests/test_enrichment_reset_1902.py | AC5/AC8 finding #3; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:638-643 |

## Observations
- AC1, AC2, AC3, AC6, AC7, and AC9 are covered sufficiently by the current code plus task-local tests.
- AC8's documentation portion is present in the reset_failed method comment block; the blocker is the missing runtime proof for the legacy-sync branch, not the presence of comments.
- Repo search for reset_failed( found only the protocol, store, and task test file, so there are no additional production call sites to validate in this review cycle.
- I did not dispatch quality-runner because the builder's scoped test/lint/coverage evidence was internally consistent and the blocking issue is missing proof, not contradictory execution evidence.

[[2026-05-27T22:03:32+02:00]]
## Test-Writer Notes
- Retry: added 12 tests for reviewer proof gaps. All 45 tests pass against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: tests/test_enrichment_reset_1902.py
- New classes: TestFromAC_ResetFailedAttemptsClearing, TestFromAC_ResetFailedBulkSourceScope, TestFromAC_ResetFailedLegacyChunks
- Tests added: happy 4, edge 4, boundary 4 (total 12 new, 45 total)
- ruff: clean

Gap coverage:
| Reviewer Finding | Tests Added |
|-----------------|-------------|
| AC5 attempts counter clearing | test_attempts_reset_to_zero_chunk_ids_path, test_attempts_reset_to_zero_bulk_path |
| AC4 source_registry filter (disabled/non-enrich) | test_bulk_excludes_inactive_source, test_bulk_excludes_non_enrich_source, test_bulk_resets_only_active_enrich_source |
| AC4 content_chunks scope filter | test_bulk_scope_filter_limits_to_matching_chunks, test_bulk_scope_filter_ignores_non_matching_scope |
| AC5/AC8 legacy chunks reconciliation | test_legacy_enrichment_state_reset_to_pending, test_legacy_error_and_claim_fields_cleared, test_legacy_attempts_reset_to_zero |

[[2026-05-27T22:12:04+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1902 -> docs | AC mapped to code and evidence sufficient.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py:159-163 adds EnrichmentResetResult(reset, remaining_failed). | tests/test_enrichment_reset_1902.py:67-111 proves defaults, explicit values, and importability. | PASS |
| AC2 | serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py:254-280 defines reset_failed signature and 4-section docstring. | tests/test_enrichment_reset_1902.py:113-142 proves zero-arg call, full-arg call, result type, and Raises: Never on empty/no-match. | PASS |
| AC3 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:178-212 uses chunk_ids as the exclusive filter and routes bulk selectors away from that path. | tests/test_enrichment_reset_1902.py:145-197 proves transition, exclusivity, limit/scopes ignored, and no-op on non-FAILED. | PASS |
| AC4 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:578-628 implements bulk selection, source eligibility, optional scope filter, and limit ordering. | tests/test_enrichment_reset_1902.py:200-245 proves default/limited bulk behavior; tests/test_enrichment_reset_1902.py:429-559 proves inactive/non-enrich sources are excluded and scope filtering is honored. | PASS |
| AC5 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:201-212 clears queue attempts, last_error, and claim state; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:630-645 clears legacy chunks error, claim, and attempt fields. | tests/test_enrichment_reset_1902.py:248-296, 384-417, 562-650 prove queue last_error/claim/attempt clearing and legacy chunks reconciliation. | PASS |
| AC6 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:214-217 returns remaining FAILED count from the canonical queue state after reset. | tests/test_enrichment_reset_1902.py:299-325 proves full reset, partial reset, empty queue, and limited bulk remaining_failed counts. | PASS |
| AC7 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:190-217 returns zero/no error for already-pending and no-match inputs. | tests/test_enrichment_reset_1902.py:336-381 proves idempotent chunk_ids and bulk no-op behavior. | PASS |
| AC8 | serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:178-189 documents canonical enrich_queue plus best-effort legacy sync; serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:210-212 and 630-645 perform the dual-table reconciliation. | tests/test_enrichment_reset_1902.py:562-650 proves legacy chunks state, error, claim, and attempts are updated alongside queue reset. | PASS |
| AC9 | serve/knowledge/src/owlbear_knowledge/protocols/__init__.py:33-45 and 139-177 import and re-export EnrichmentResetResult. | tests/test_enrichment_reset_1902.py:67-95 proves both import paths resolve the same class. | PASS |

- Independent verification:
  - quality-runner rerun: uv run pytest tests/test_enrichment_reset_1902.py -q --tb=short -> 45 passed, 0 failed.
  - quality-runner lint: uv run ruff check serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py serve/knowledge/src/owlbear_knowledge/protocols/__init__.py serve/knowledge/src/owlbear_knowledge/stores/enrichment.py tests/test_enrichment_reset_1902.py -> clean.
  - quality-runner scoped coverage: protocols/enrichment.py 100%, protocols/__init__.py 100%, stores/enrichment.py 57% on the task-local suite. Builder's earlier behavioral-bundle evidence still supplies the broader unchanged-source baseline (stores/enrichment.py 90%, protocols/enrichment.py 100%).

## Observations
- Challenger raised two non-blocking concerns: AC4's "enabled" wording vs source_registry active state, and unspecified non-positive limit semantics. I did not treat either as blocking because serve/knowledge/src/owlbear_knowledge/protocols/sources.py:44-48 establishes active/inactive as the concrete source-state model, and the AC does not specify limit<1 behavior beyond Raises: Never.
- Repo search for reset_failed( still finds no production call sites beyond the protocol, store, and task test surface, so there is no downstream usage proof required in this cycle.

[[2026-05-27T22:13:31+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | serve/knowledge/README.md read in full. EnrichmentResetResult is re-exported from protocols/__init__.py only — it is not in the top-level owlbear_knowledge/__init__.py, so the Module groups table (which lists top-level exports) is unaffected. Existing two TODO markers (#1886) are pre-existing and outside task scope. No update required. |
| 2 | External attribution | No | N/A | Builder noted "Sources: 6 studied, 4 high-relevance (all internal codebase)" — no external attribution needed. |
| 3 | Research doc | Yes | N/A | .owlbear/research/1902-enrichmentstore-reset-failed.md exists; task body links it explicitly. |
| 4 | Deletion detection | No | N/A | No files deleted. Three files modified/extended only (protocols/enrichment.py, protocols/__init__.py, stores/enrichment.py). |

### Verification Layers
- Layer 1 — grep: `EnrichmentResetResult` absent from top-level `owlbear_knowledge/__init__.py` (grep confirmed 0 matches); present only in `protocols/__init__.py` and `protocols/enrichment.py` and `stores/enrichment.py`. No removed symbols in README.
- Layer 2 — editorial: README Module groups table accurately describes top-level package exports. No contradictions with task changes. Two pre-existing TODO markers (#1886) noted and passed through unchanged.

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch/1902-* files existed)

[[2026-05-27T22:15:15+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 147 passed, 0 failed, lint clean
- Domains covered: serve/knowledge/tests/, tests/test_enrichment_*
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (all changed files in serve/knowledge/ enrichment protocol+store domain)
- Purpose match: PASS (adds Protocol method and store implementation for reset_failed, matching stated purpose)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was revised after challenger feedback to address 9 specific concerns. Reviewer initially found proof gaps in AC4/AC5/AC8 that required test-writer retry, suggesting AC could have been slightly more explicit about mixed-schema test requirements. Overall adequate with minor gaps filled downstream.

### Commit Integrity
- Upstream commit presence: PASS (16de5a16 feat, 605f1bc6 test, 7e4089ad test-retry)
- Commit format: proper conventional commits with task ref and agent attribution
- Kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
