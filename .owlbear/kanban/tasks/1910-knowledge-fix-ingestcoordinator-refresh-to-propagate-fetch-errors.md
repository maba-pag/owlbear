---
id: 1910
title: 'Knowledge: Fix IngestCoordinator.refresh() to propagate fetch errors'
status: review
priority: needed
created: 2026-05-28T01:41:35.456164+02:00
updated: 2026-05-28T03:50:47.322107+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent: 1904
depends_on: []
ac:
  - 'AC1: IngestCoordinator.refresh() maps each FetchError in fetch_result.errors
    to a RefreshError(source_id=source.id, error=string incorporating FetchError.uri
    and FetchError.error, timestamp=current UTC) appended to RefreshResult.errors'
  - 'AC2: When fetch_result.documents is non-empty (partial success), refresh() still
    calls update_source(source.id, SourceUpdate(last_refreshed_at=...)) and increments
    sources_refreshed, regardless of fetch_result.errors content'
  - 'AC3: When fetch_result.documents is empty AND fetch_result.errors is non-empty
    (total failure), refresh() skips update_source for that source and does not increment
    sources_refreshed'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
In `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py`, the refresh() method currently ignores `fetch_result.errors`. Propagate them into the RefreshResult.errors list.

## Details
- After `fetch_result = await self._fetcher.fetch_source(source)`, if fetch_result.errors is non-empty, propagate them into the RefreshResult.errors list
- ~5 LOC change
- Research: .owlbear/research/source-fetcher-adapter-b2b.md §3.2

[[2026-05-28T02:10:45+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single method fix in one file |
| Interface clarity | PASS | After AC refinement — observables named (update_source, sources_refreshed) |
| Dependency correctness | PASS | No dependencies; sibling #1909 is independent |
| Module layering | PASS | All within knowledge module, no cross-module imports |
| TDD compliance | PASS | Test-writer will create new test cases; existing tests unaffected (they use empty errors) |
| KISS/YAGNI | PASS | ~5 LOC conditional propagation, no abstractions |
| Premise challenge | PASS | fetch_result.errors is genuinely ignored today; SourceFetcher protocol guarantees item-level failures captured there |
| Pattern consistency | PASS | Follows existing RefreshError creation pattern from the except block |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| fetch_result.errors mapping | FetchError with empty uri/error | None (Pydantic validated) | N/A | Benign empty RefreshError.error string |
| AC3 total-failure branch | Source has errors but also unexpected documents from race | None | AC2 covers partial success | Source correctly marked refreshed |

### Design Diverge
- Trigger: skipped — single clear approach, no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.33)
- Findings: AC quality B1/B2 failures (target/observable not named); claimed contract contradiction with #1886
- Architect response: ACCEPTED B1/B2 — refined AC to name IngestCoordinator.refresh() and observables (update_source, sources_refreshed). REBUTTED contract contradiction — existing #1886 tests all use FetchResult(documents=()) with default empty errors; AC3 only triggers when errors is non-empty, which is a distinct untested scenario. DISMISSED consolidation-test-gap — #1911 IS the integration/wiring task with its own test surface.

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC for B1/B2 precision (named target method and observables), set proof_bundle=smoke, advanced to todo.

[[2026-05-28T02:48:08+02:00]]
## Test-Writer Notes
- Test file: tests/test_ingest_coordinator_1910.py
- Class: TestFromAC_FetchErrorPropagation
- Proof bundle: smoke — 1 test per AC line
- Tests written: 3 (all FAIL confirmed via quality-runner)
- Lint: clean (ruff)

| AC | Test | Assertion | Fails because |
|----|------|-----------|---------------|
| AC1 | test_fetch_errors_appear_in_refresh_result_errors | len(result.errors) == 1 | errors ignored → result.errors is empty |
| AC2 | test_partial_success_errors_captured_in_result | len(result.errors) >= 1 | errors ignored even in partial success |
| AC3 | test_total_failure_does_not_increment_sources_refreshed | result.sources_refreshed == 0 | code always increments sources_refreshed |

Total: 3 tests, all FAIL

[[2026-05-28T03:11:41+02:00]]
## Builder Notes
- Implementation: updated serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py
- Fixes applied:
  - Propagated each fetcher item error (`fetch_result.errors`) into `RefreshResult.errors` as `RefreshError(source_id=source.id, error="{uri}: {error}", timestamp=UTC now)`.
  - Added total-failure guard: when `mapped_documents` is empty and `fetch_result.errors` is non-empty, skip `update_source(...)` and do not increment `sources_refreshed`.
  - Preserved partial-success behavior: when documents exist, ingestion + source refresh still occur even if item errors are present.
- Tests:
  - Task-scoped RED->GREEN proof: `tests/test_ingest_coordinator_1910.py` (3 passed, 0 failed)
  - Expanded scoped regression for module coverage: `tests/test_ingest_coordinator_1877.py`, `tests/test_ingest_coordinator_1878.py`, `tests/test_ingest_coordinator_1886.py`, `tests/test_ingest_coordinator_1910.py` (153 passed, 0 failed)
- Coverage:
  - `owlbear_knowledge.ingest_coordinator`: 100% (expanded scoped verification)
- Lint:
  - ruff clean (`clean: true`, no violations)
- Durable module-level test file check:
  - `serve/knowledge/tests/test_ingest_coordinator.py` and `tests/test_ingest_coordinator.py` not present; skipped per workflow guidance.
- Commit:
  - `fcbca007085e2f4266b964a47bbdde1546de9b4a`
  - Message: `fix: propagate fetch errors in refresh (#1910, builder)`

### Post-task Reflection
- problems_faced: initial quality-runner invocation failed at API layer with `invalid_request_error` before test execution.
- workarounds_applied: retried quality-runner with a simplified prompt format; execution then succeeded with identical test scope.
- patterns_discovered: task-scoped smoke tests may under-represent module coverage; adding adjacent task-scoped module tests can satisfy coverage gating without full-suite execution.
- time_sinks: coverage gate required one extra quality-runner pass after the initial task-scoped verification.
- quality_gaps: no canonical durable `test_ingest_coordinator.py` exists yet; verification relied on task-scoped files only.

[[2026-05-28T03:19:21+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Summary: Builder evidence is internally consistent and the implementation in serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:302-339 appears to satisfy AC1-AC3, but the task-scoped smoke tests in tests/test_ingest_coordinator_1910.py do not adequately prove the contract.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The task test only proves that one error object exists; it does not prove item-level field mapping (`source_id`, `uri` + `error` string, timestamp) or that every `FetchError` is propagated. This would false-green if only the first fetch error were mapped or if mapped fields were wrong. | Code maps fields at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:302-306. Task proof is only `assert len(result.errors) == 1` at tests/test_ingest_coordinator_1910.py:177. Adjacent exception-path proofs at tests/test_ingest_coordinator_1886.py:631-632 and :673 do not exercise `fetch_result.errors`. | todo |
| 2 | AC2 | The partial-success test does not prove the named observables from the AC. It checks only that an error is present, but not that `update_source(...)` still runs and `sources_refreshed` increments when documents and fetch errors coexist. | Mixed branch is controlled by serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:321, :335, :339. Task proof is only `assert len(result.errors) >= 1` at tests/test_ingest_coordinator_1910.py:204. Existing success-path proofs at tests/test_ingest_coordinator_1886.py:560 and :696 cover success without item errors, not the mixed branch. | todo |
| 3 | AC3 | The total-failure test proves `sources_refreshed == 0` but does not prove the second named observable: `update_source(...)` must be skipped for that source. | Total-failure guard is at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:321. Task proof is only `assert result.sources_refreshed == 0` at tests/test_ingest_coordinator_1910.py:230. Adjacent `update_source.assert_not_called()` checks at tests/test_ingest_coordinator_1886.py:602 and :614 cover raised-exception paths, not the item-error total-failure branch. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC1 proof to assert mapped `RefreshError` fields for item-level fetch errors, including `source_id`, `uri` + `error` content, and timestamp presence/current-time behavior; add a multi-error case or equivalent proof that all fetch errors are propagated. | tests/test_ingest_coordinator_1910.py | Review finding #1; tests/test_ingest_coordinator_1910.py:177; serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:302-306 |
| 2 | test-writer | Strengthen AC2 proof to assert the partial-success branch still calls `update_source(...)` and increments `sources_refreshed` when `documents` and `errors` coexist. | tests/test_ingest_coordinator_1910.py | Review finding #2; tests/test_ingest_coordinator_1910.py:204; serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:321, :335, :339 |
| 3 | test-writer | Strengthen AC3 proof to assert `update_source(...)` is not called for the total-failure branch, in addition to `sources_refreshed == 0`. | tests/test_ingest_coordinator_1910.py | Review finding #3; tests/test_ingest_coordinator_1910.py:230; serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:321 |

## Observations
- Builder evidence was sufficient for review: scoped task tests, expanded scoped regression, 100% module coverage, and clean lint were all reported consistently with the touched control path.
- The implementation appears root-cause correct for this task; the rejection is about proof quality, not an observed implementation defect.
- No additional safety/security issue was observed in this slice; the changed path only maps structured fetch errors into refresh results and gates source refresh bookkeeping.

[[2026-05-28T03:50:47+02:00]]
## Test-Writer Notes
- Retry: added 7 new tests to tests/test_ingest_coordinator_1910.py addressing all 3 reviewer gaps.
- Builder skip: test-only retry — all 10 tests (3 original + 7 new) pass against current implementation.

| AC | New Tests | Assertion | Status |
|----|-----------|-----------|--------|
| AC1 | test_ac1_refresh_error_source_id_matches_source | source_id == "src-1" | PASS |
| AC1 | test_ac1_refresh_error_string_incorporates_uri_and_error | uri and error msg both in error string | PASS |
| AC1 | test_ac1_refresh_error_timestamp_is_datetime | isinstance(ts, datetime) and before <= ts <= after | PASS |
| AC1 | test_ac1_all_fetch_errors_propagated_for_multiple_errors | 2 FetchErrors → 2 RefreshErrors with both URIs | PASS |
| AC2 | test_ac2_partial_success_update_source_still_called | update_source.assert_called_once() | PASS |
| AC2 | test_ac2_partial_success_sources_refreshed_increments | sources_refreshed == 1 | PASS |
| AC3 | test_ac3_total_failure_update_source_not_called | update_source.assert_not_called() | PASS |

Total: 10 tests, all PASS. Lint: clean. Commit: e87c9797.
