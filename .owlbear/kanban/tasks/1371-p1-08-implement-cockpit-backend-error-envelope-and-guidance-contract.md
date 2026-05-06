---
id: 1371
title: 'P1-08: Implement Cockpit backend error envelope and guidance contract'
status: review
priority: critical
created: 2026-05-06T00:58:43.072416+00:00
updated: 2026-05-06T08:39:56.061729+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-api
- type:fix
- backend
- interface-contract
- guidance
parent: 1363
depends_on:
- 1370
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Implement a consistent Cockpit backend error envelope and explicit kanban guidance policy for expected API failures.

## Problem Evidence
- Mutation routes mostly return plain HTTPException detail strings, while kanban errors expose code and user_message.
- CockpitView clears guidance implicitly; the list route passes guidance on cache miss but drops it on cache hit.
- Frontend consumers cannot reliably distinguish expected failures from empty or successful states.

## Acceptance Criteria
- All domain error responses (KanbanError subclass or unexpected Exception) use the stable envelope `{code: str, message: str}` with NO `detail` field. (td:2)
- Mutation, read, and admin (scan/repair/compact) routes raise KanbanError subclasses for domain failures (not-found, stale, validation, config); the registered `handle_kanban_error` exception handler returns the envelope with correct HTTP status (404/409/422/500). (td:2)
- Unexpected exceptions (RuntimeError from scanner/repair, unhandled errors) are caught by `handle_unexpected_error` and return `{code: "COCKPIT_INTERNAL_ERROR", message: "An unexpected error occurred."}` with status 500 and content-type `application/json`. (td:2)
- Guidance policy concrete rules: (a) error responses contain NO `guidance` field; (b) GET /api/tasks list forwards `envelope.guidance` on cache miss, returns `guidance=[]` on cache hit; (c) successful mutation responses return `guidance=[]`; (d) GET /api/tasks/{id} returns `guidance` from engine response. (td:1)
- HTTP status codes preserved: 404 not-found, 409 stale/not-claimed, 422 validation/no-op, 500 config/unexpected. No existing status code changes. (td:1)
- All tests in `tests/test_cockpit_error_envelope_1370.py` pass. (td:0)
- Legacy durable-suite tests that assert `detail` format for domain errors (test_cockpit_mutation_api_1134, test_cockpit_mutation_api_1135, test_cockpit_read_api) are updated to assert envelope format. (td:1)
- Framework-level errors unchanged: Pydantic request-validation 422 retains FastAPI's `{"detail": [...]}` format; decisions route HTTPException errors retain `{"detail": "..."}` format. These are NOT converted to the domain envelope. (td:0)
- Frontend UI redesign is not part of this task; frontend adoption is handled by #1374/#1375. (td:0)

## Scope
- In scope: Cockpit backend API error envelope for domain failures (KanbanError paths + catch-all Exception handler), guidance policy enforcement, legacy test updates.
- Out of scope: frontend rendering changes, decisions route envelope migration (needs own test coverage), Pydantic request-validation error format, cache/SSE invalidation from #1346.

## Test Dependency
Satisfies #1370.

[[2026-05-06]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Error envelope consistency + guidance policy are one interface contract |
| Interface clarity | FAIL→FIXED | Original AC ambiguous on decisions routes, `detail` field, guidance sources. Refined below. |
| Dependency correctness | PASS | #1370 is archived (done); test file exists at `tests/test_cockpit_error_envelope_1370.py` |
| Module layering | PASS | Changes stay within cockpit backend; envelope handlers in main.py, errors raised in routes |
| TDD compliance | PASS | #1370 test file exists with proper RED-phase tests covering AC1–AC4 |
| KISS/YAGNI | PASS | Error envelope is minimal `{code, message}` — no over-engineering |
| Premise challenge | PASS | Consistent error contract is needed; current mixed `detail`/KanbanError format is a real problem |
| Pattern consistency | PASS | Extends existing `handle_kanban_error` pattern already in main.py |
| Security surface | PASS | No new input boundaries; error messages are controlled strings from domain errors |
| Single domain | PASS | Cockpit API only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Decisions route invalid ID | HTTPException 422 | HTTPException | YES (FastAPI default) | Returns `{"detail": "..."}` — NOT envelope. Out of scope. |
| Framework request validation | Pydantic 422 | RequestValidationError | YES (FastAPI default) | Returns `{"detail": [...]}` — NOT envelope. Unchanged. |
| Domain not-found (read/mutation) | KanbanError → 404 | NotFoundError | YES (handle_kanban_error) | Returns `{code, message}` |
| Domain stale/conflict | KanbanError → 409 | ConcurrencyError | YES (handle_kanban_error) | Returns `{code, message}` |
| Domain validation | KanbanError → 422 | ValidationError | YES (handle_kanban_error) | Returns `{code, message}` |
| Config error | KanbanError → 500 | ConfigError | YES (handle_kanban_error) | Returns `{code, message}` |
| Unexpected RuntimeError | Exception → 500 | RuntimeError | YES (handle_unexpected_error) | Returns `{code: "COCKPIT_INTERNAL_ERROR", message: "..."}` |

### Design Notes
- **Coexistence:** FastAPI's built-in HTTPException handler and RequestValidationError handler remain active for framework-level errors (decisions routes, Pydantic validation). The domain envelope only applies to `KanbanError` and generic `Exception`. This is intentional — decisions route envelope migration is out of scope (needs its own test coverage via a follow-up task).
- **Frontend compatibility:** Removing `detail` from domain error responses will break `ArchivalModal.tsx` and `DetailTab.tsx` which parse `payload.detail`. This is intentional and managed by #1374/#1375 (frontend error-contract adoption), which depends on this task.
- **Legacy test update:** Multiple durable-suite tests assert `detail` format (test_cockpit_mutation_api_1134, test_cockpit_mutation_api_1135, test_cockpit_read_api). Builder must update these to match envelope format.

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Architect response: Accepted 4 of 6 findings. (1) Removed ambiguous "field detail" clause. (2) Narrowed decisions routes out of scope — they use HTTPException, not KanbanError, and #1370 tests don't cover them. (3) Added explicit legacy test update AC. (4) Distinguished domain errors from framework validation. Rebutted: #1370 dependency is valid (archived/done, test file exists). Frontend break is intentionally managed by #1374/#1375 dependency chain.

### Test Depth
- Max depth: 2
- Test-writer: SKIP (tests already written in #1370 — this task satisfies them)

### Verdict: REFINE (approve after tightening)
### Action Taken: Rewrote AC with precise envelope shape, narrowed route scope, added legacy test update requirement, made guidance policy concrete. Approved to `todo`.

[[2026-05-06]]
Architecture review complete. Refined AC: removed ambiguous "field detail support" clause, narrowed route scope (decisions routes excluded — they use HTTPException not KanbanError, no #1370 test coverage), added explicit legacy test update requirement, made guidance policy concrete with 4 specific rules, distinguished domain errors from framework validation. Challenger raised valid scope drift issues (confidence 0.34) — accepted findings on ambiguity/scope, rebutted on dependency validity. Approved to todo.
[[2026-05-06]]
## Test-Writer Notes
- Test file: tests/test_cockpit_error_envelope_1371.py
- Classes: TestFromAC_LegacyTestMigration
- Tests per category: happy 0, edge 0, error 3, boundary 0
- Total: 3 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Status | Notes |
|----|--------|-------|
| AC1 (td:2) | Covered by #1370 | test_cockpit_error_envelope_1370.py — all 22 tests pass (impl done) |
| AC2 (td:2) | Covered by #1370 | exception handlers already registered in main.py |
| AC3 (td:2) | Covered by #1370 | handle_unexpected_error already present |
| AC4(a)(b)(c) (td:1) | Covered by #1370 | guidance policy tested there |
| AC4(d) (td:1) | Already correct | get_task route directly returns ShowTaskResponse with guidance; behavior already implemented |
| AC5 (td:1) | Covered by #1370 | status preservation tested there |
| AC6 (td:0) | Skip | all 1370 tests pass |
| AC7 (td:1) | **3 FAIL** | Meta-tests: 1134 line ~204, 1135 lines ~165/313, read_api line ~461 still assert `detail` format |
| AC8 (td:0) | Skip | framework errors unchanged |
| AC9 (td:0) | Skip | frontend out of scope |

### Notes
- Architect marked "Test-writer: SKIP (tests already written in #1370)". The 1370 tests all pass (implementation was done). AC7 (legacy test migration) was not covered by 1370 — added 3 meta-tests that fail until builder updates the legacy `detail` assertions to envelope format.
- Builder must update: `test_cockpit_mutation_api_1134.py` line 204, `test_cockpit_mutation_api_1135.py` lines 165 and 313, `test_cockpit_read_api.py` line 461.
- Commit: af912b44
[[2026-05-06]]
## Builder Notes
- Implementation: updated legacy envelope assertions in tests/test_cockpit_mutation_api_1134.py, tests/test_cockpit_mutation_api_1135.py, and tests/test_cockpit_read_api.py.
- Scope: AC7 only (legacy durable-suite migration from domain `detail` checks to `{code, message}` envelope checks).
- Fixes applied:
  - Replaced `response.json().get("detail")` / `response.json()["detail"]` domain assertions with envelope assertions.
  - Added explicit `"detail" not in body` checks at migrated sites.
  - Asserted stable domain codes where relevant (`ERR_STALE`, `ERR_NOT_FOUND`) and message content checks (including ID-in-message checks for not-found).
  - Adjusted two mocked ConcurrencyError message expectations to match handler behavior (`user_message` passthrough), resolving initial verification mismatches.
- Tests: 97 passed, 0 failed (quality-runner scoped run across task test + affected durable tests).
- Coverage (scoped evidence): owlbear_cockpit.main 53%, owlbear_cockpit.routes.read 98%, owlbear_cockpit.routes.mutation 61%.
- Ruff: clean on all touched/related test files.
- Commit: 9938524 (`test: migrate legacy cockpit error assertions to envelope (#1371, builder)`).

### Post-task Reflection
- The main failure mode was assuming legacy canonical `detail` message text survives the envelope migration for mocked ConcurrencyError paths; in this codepath, `user_message` is authoritative.
- Scoped quality-runner execution was useful to avoid suite-noise while still validating durable regressions in the three target files.
- Minimal-diff migration worked cleanly once assertions were aligned to actual handler semantics instead of pre-envelope message strings.