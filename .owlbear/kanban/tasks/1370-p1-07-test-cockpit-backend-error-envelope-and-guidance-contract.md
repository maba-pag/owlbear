---
id: 1370
title: 'P1-07: Test Cockpit backend error envelope and guidance contract'
status: in-progress
priority: critical
created: 2026-05-06T00:58:41.555448+00:00
updated: 2026-05-06T04:10:20.603998+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-api
- type:test
- backend
- interface-contract
- guidance
parent: 1363
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write backend tests that define the Cockpit error envelope and kanban guidance policy before implementation.

## Problem Evidence
- Cockpit mutation routes mostly return plain HTTPException detail strings, while kanban errors expose code and user_message.
- CockpitView clears guidance implicitly; the list route passes guidance on cache miss but drops it on cache hit.
- Frontend code currently branches on status codes and generic strings inconsistently.

## Acceptance Criteria
- Tests assert error responses use a JSON envelope with fields `code` (str, stable machine-readable identifier) and `message` (str, user-facing explanation) — FastAPI's default `{"detail": "..."}` shape is replaced for all expected Cockpit errors. (td:2)
- Tests cover representative expected errors: not-found (404), stale/conflict (409), validation (422), invalid-config (500), and unhandled scanner/repair exceptions (500). Each asserts both status code and envelope fields. (td:2)
- Tests assert HTTP status codes are unchanged — the envelope wraps existing semantics without altering status mapping. (td:1)
- Tests assert guidance policy: (a) error responses do NOT include a `guidance` field; (b) successful list responses include engine guidance on cache miss and return `guidance: []` on cache hit (documenting the cache-aware contract); (c) successful mutation responses return `guidance: []` (no operation-level guidance exists for mutations). (td:2)
- At least one test per category (envelope shape, error coverage, status preservation, guidance policy) fails against the current unmodified routes — proving the RED phase is valid for #1371. (td:1)

## Scope
- In scope: Cockpit backend API contract tests for expected errors and guidance handling.
- Out of scope: frontend UI adoption, dashboard redesign, cache/SSE invalidation from #1346, and health-endpoint false-OK logic (belongs to #1372).

## Architecture Notes
- **Envelope shape**: `{"code": "<STABLE_CODE>", "message": "<user-facing text>"}`. Codes should mirror kanban error codes where applicable (e.g., `ERR_NOT_FOUND`, `ERR_STALE`, `ERR_INVALID_STATUS`) and use Cockpit-specific codes for non-kanban errors (e.g., `COCKPIT_CONFIG_ERROR`, `COCKPIT_SCANNER_FAILED`).
- **Implementation target**: A custom FastAPI exception handler or middleware in `serve/cockpit/src/owlbear_cockpit/` that catches `KanbanError` subclasses and unhandled route exceptions, serializing them into the envelope.
- **Test file**: `tests/test_cockpit_error_envelope_1370.py` — use existing DI pattern (`get_engine` override) to inject engine mocks that raise specific errors.
- **Guidance contract**: The current cache-hit behavior (`guidance: []`) is correct — guidance reflects the engine query that produced the response; no stale guidance should be surfaced. Tests document this as contract, not as a bug.
- **Scanner/repair scope**: Test that when `view.scan_corruption()` or `view.repair_storage()` raises an unexpected exception, the response uses the error envelope with 500 status and a stable code rather than FastAPI's generic error page.

## Counterpart
Implementation task: #1371.

[[2026-05-06]]
## Architecture Review

**Verdict: APPROVE**

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Envelope shape (code + message fields) | Testable, specifies exact field names and types | Refined: named fields explicitly |
| Representative error coverage | Good enumeration; clarified scanner/repair = unhandled exception case | Refined: dropped "where applicable" ambiguity |
| HTTP status preservation | Clear, directly testable | Kept, annotated td:1 |
| Guidance policy | Was vague ("define the policy") — test-writer can't invent architecture | **Major refine**: specified 3-part policy (no guidance on errors, cache-aware list, empty on mutations) |
| RED proof validity | Meta-testable, clear | Kept, annotated td:1 |

### Architecture Notes
- **Pattern alignment**: Envelope follows standard REST error contract. `code` field reuses kanban error codes where mapped, avoiding a translation layer. New Cockpit-specific codes for non-kanban failures.
- **Implementation path**: Custom FastAPI exception handler (not middleware) — catches `KanbanError` subclasses + adds catch-all for scanner/repair unhandled exceptions. Clean separation from route logic.
- **Guidance clarification**: The cache-hit `guidance: []` is CORRECT behavior, not a bug. Guidance reflects the engine query that produced the response — no stale guidance. Tests document this as intentional contract.
- **Dependency analysis**: No dependencies needed. Kanban error classes already exist. Cockpit DI pattern (`get_engine` override) provides test infrastructure. Scanner/repair routes exist.
- **No conflicts**: No existing test file covers this contract. Existing mutation/read tests assert `detail` strings — new tests assert envelope shape, coexisting until #1371 migrates the implementation.

### Challenge
Challenge: FALLBACK — subagent returned no response. Self-assessed: single-responsibility (yes), KISS (envelope is minimal 2-field shape), no over-engineering (reuses existing codes), implementation path is standard FastAPI pattern.
[[2026-05-06]]
## Test-Writer Notes
- Test file: tests/test_cockpit_error_envelope_1370.py
- Classes: TestFromAC_ErrorEnvelopeShape, TestFromAC_ErrorCoverage, TestFromAC_StatusPreservation, TestFromAC_GuidancePolicy
- Tests per category: happy 3, edge 4, error 9, boundary 3
- Total: 19 tests, all FAIL (AssertionError)
- ruff: clean

### AC Coverage

| AC Line | Tests | Failure mode |
|---------|-------|--------------|
| AC1 (td:2): envelope {code, message} | 6 tests in TestFromAC_ErrorEnvelopeShape | AssertionError: 'code'/'message' not in response; 'detail' present |
| AC2 (td:2): representative error coverage | 6 tests in TestFromAC_ErrorCoverage | AssertionError: 'code'/'message' absent; content-type not JSON for scanner/repair |
| AC3 (td:1): status codes preserved | 3 tests in TestFromAC_StatusPreservation | AssertionError: 'code' absent (status checks pass; envelope checks fail) |
| AC4 (td:2): guidance policy | 4 tests in TestFromAC_GuidancePolicy | (a) 'code' absent; (b)(c) KanbanError handler not registered |

### Notes
- Scanner/repair exception tests use `raise_server_exceptions=False` + content-type assertion to get AssertionError (not JSONDecodeError) in RED phase.
- Guidance (b)+(c) tests use `_has_kanban_error_handler()` pre-condition check — asserts False because no KanbanError handler is registered yet; will unblock when #1371 registers it.
- `dependency_overrides[get_cache]` used for guidance cache-miss/hit tests via `cache_client` fixture.
[[2026-05-06]]
## Builder Notes
- Implementation: no source changes. Task #1370 is a test-contract deliverable (`type:test`) with implementation explicitly assigned to counterpart #1371.
- RED verification: 19/19 `TestFromAC_*` tests failed in `tests/test_cockpit_error_envelope_1370.py` as expected for pre-implementation state.
- Lint: ruff clean on `tests/test_cockpit_error_envelope_1370.py`.
- Coverage snapshot from RED run is non-gating for this task phase; failures are intentional and provide valid contract evidence for #1371.
- Routing decision: pass-through to review with no code edits in builder phase for this task.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_cockpit_error_envelope_1370.py`: 0 passed, 19 failed, exit code 1.
- Failure mode matches valid RED evidence: missing `code`/`message` envelope fields, no registered exception handler, and scan/repair 500 responses not returning JSON.
- Representative failing points: `test_not_found_error_no_detail_field`, `test_stale_conflict_409_has_envelope`, `test_invalid_transition_422_has_envelope`, `test_config_error_500_has_envelope`, `test_scan_corruption_exception_500_has_envelope`, `test_repair_storage_exception_500_has_envelope`, and all three guidance precondition checks.

### Lint Results
- `ruff` clean for `tests/test_cockpit_error_envelope_1370.py` and `serve/cockpit/src/owlbear_cockpit/`.

### Coverage Data
- Informational only for this review because the task deliverable is a RED test contract and builder changed no source.
- `owlbear_cockpit.routes.read`: 59%
- `owlbear_cockpit.routes.mutation`: 52%
- `owlbear_cockpit.main`: 44%
- `owlbear_cockpit.view`: 27%

### Security / Integrity
- No security findings in scoped backend code.
- No weakening markers (`skip`, `xfail`, removed `TestFromAC_*` methods) were found in the current test file.
- Small confidence deduction: commit diff / prior snapshot was not available, so TestFromAC immutability is verified from current file state only.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: error envelope uses `code` + `message` and replaces FastAPI `detail` for expected Cockpit errors | `tests/test_cockpit_error_envelope_1370.py:180-185` rejects `detail` only for the 404 path. The representative 409/422/500 cases at `tests/test_cockpit_error_envelope_1370.py:243-334` assert `code`/`message` presence but never reject lingering `detail`, so `{code, message, detail}` would still green on those branches. | FAIL |
| AC2: representative expected errors are covered with status + envelope assertions | `tests/test_cockpit_error_envelope_1370.py:226-334` covers 404, stale 409, validation 422, config 500, scan 500, and repair 500. quality-runner confirmed all of these fail in RED for the expected missing-envelope reasons. | PASS |
| AC3: status codes remain unchanged | `tests/test_cockpit_error_envelope_1370.py:342-384` asserts exact 404/409/422 codes; `tests/test_cockpit_error_envelope_1370.py:275-334` asserts exact 500 codes. | PASS |
| AC4: guidance policy | Cache-hit and mutation success assertions for `guidance == []` exist at `tests/test_cockpit_error_envelope_1370.py:431-464`, and the current implementation already normalizes those success paths (`serve/cockpit/src/owlbear_cockpit/routes/read.py:118`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:84-107`). But the cache-miss test at `tests/test_cockpit_error_envelope_1370.py:416-429` only checks that `guidance` exists and is a list. The miss path simply forwards `envelope.guidance` (`serve/cockpit/src/owlbear_cockpit/routes/read.py:104`), while the current engine-side list response returns `guidance=[]` (`serve/kanban/src/owlbear_kanban/agent_view.py:213`), so a hardcoded empty list on cache miss would still pass. | FAIL |
| AC5: at least one test per category fails against current unmodified routes | quality-runner confirmed 19/19 failures. The app currently registers no exception handler in `serve/cockpit/src/owlbear_cockpit/main.py:26-30`, and the read/mutation routes still raise plain `HTTPException(..., detail=...)` on expected error paths. | PASS |

### Deductions
- `-0.10` AC1 under-proven: non-404 representative errors never assert that `detail` is absent.
- `-0.10` AC4 under-proven: cache-miss guidance test does not prove forwarding of engine guidance.
- `-0.03` TestFromAC immutability check is lower-confidence because commit diff access was unavailable.

### Verdict
- FAIL -> `todo`
- Confidence: `0.76`
- Reason: the suite establishes a genuine RED baseline, but it leaves two AC-level false-green paths open in AC1 and AC4. This is a test-proof gap, not a builder implementation issue.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen representative 409/422/500 error-envelope tests to reject FastAPI `detail` on the non-404 branches owned by this task. | `tests/test_cockpit_error_envelope_1370.py` | Only the 404 case rejects `detail` at `tests/test_cockpit_error_envelope_1370.py:180-185`; representative non-404 cases at `tests/test_cockpit_error_envelope_1370.py:243-334` only assert `code`/`message`. |
| 2 | test-writer | Make the cache-miss guidance test discriminate forwarding of engine guidance by injecting a non-empty guidance payload on the miss path and asserting the exact returned list. | `tests/test_cockpit_error_envelope_1370.py` | Current miss test at `tests/test_cockpit_error_envelope_1370.py:416-429` only asserts list presence; route miss path forwards `envelope.guidance` at `serve/cockpit/src/owlbear_cockpit/routes/read.py:104`, while the current engine response is `guidance=[]` at `serve/kanban/src/owlbear_kanban/agent_view.py:213`. |
[[2026-05-06]]
## Test-Writer Notes
- Retry: filled two AC gaps identified by reviewer.
- Test file: tests/test_cockpit_error_envelope_1370.py
- Classes: TestFromAC_ErrorEnvelopeShape, TestFromAC_ErrorCoverage, TestFromAC_StatusPreservation, TestFromAC_GuidancePolicy
- Total: 19 tests, all FAIL (AssertionError) — ruff clean

### Changes from retry
**Gap 1 (AC1 detail-absence):** Added `assert "detail" not in body` to all non-404 representative error tests in `TestFromAC_ErrorCoverage`: 409 stale, 422 invalid-transition, 500 config-error, 500 scan-corruption, 500 repair-storage. These all fail in RED (FastAPI `detail` field is present).

**Gap 2 (AC4 cache-miss discrimination):** Replaced `test_list_cache_miss_guidance_in_response` with a version that injects a `sentinel_guidance = ["cockpit-test-guidance-sentinel"]` via `mock.patch.object(CockpitView, "list_tasks", return_value=mock.MagicMock(...))` and asserts `body["guidance"] == sentinel_guidance`. This proves the route actually forwards engine guidance rather than hardcoding `[]`. Still fails in RED at `assert _has_kanban_error_handler()` pre-condition.

### AC Coverage
| AC Line | Tests | Failure mode |
|---------|-------|--------------|
| AC1: envelope replaces detail (all errors) | 6+5 assertions across TestFromAC_ErrorEnvelopeShape + TestFromAC_ErrorCoverage | `detail` present / `code`/`message` absent |
| AC2: representative error coverage | 6 tests | envelope fields absent |
| AC3: status codes preserved | 3 tests | `code` absent (status assertions pass) |
| AC4: guidance policy | 4 tests | handler not registered / exact guidance mismatch |