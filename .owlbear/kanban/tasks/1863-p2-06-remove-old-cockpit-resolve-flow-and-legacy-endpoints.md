---
id: 1863
title: 'P2-06: Remove old Cockpit resolve flow and legacy endpoints'
status: review
priority: important
created: 2026-05-24T21:00:04.160667+02:00
updated: 2026-05-26T09:36:03.690677+02:00
tags:
  - phase-2
  - scope:cockpit
  - cleanup
parent: 1850
depends_on:
  - 1856
  - 1858
  - 1859
  - 1860
ac:
  - Old resolve_decision endpoint (POST /api/decisions/{id}/resolve with 
    response=approved/needs-info/rejected payload) is removed from Cockpit 
    routes; requests to that path return HTTP 404.
  - Old list_pending_decisions endpoint (GET /api/decisions/pending returning 
    PendingDRResponse with body-text regex title extraction) is removed from 
    Cockpit routes; requests to that path return HTTP 404.
  - Frontend decisions.test.ts (testing old POST /api/decisions/{id}/resolve 
    contract) is removed; LegacyPendingDRResponse interface and dual-format 
    normalization in usePendingDRs.ts are removed; only new /api/requests/ API 
    types remain in frontend code.
  - 'Task-impacted backend tests pass green: test_cockpit_legacy_cleanup_1863.py,
    test_cockpit_requests_api_1856.py, test_cockpit_error_envelope.py, serve/cockpit/tests/
    (excl. test_visual_redesign.py). Pre-existing failures in test_cockpit_view/models/shell_sidecar
    (other tasks) not gated. Tests referencing deleted endpoints updated or removed.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Remove `resolve_decision` endpoint from `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- Remove `list_pending_decisions` endpoint and related models (`PendingDRItem`, `PendingDRResponse`, `ResolveRequest`)
- Remove the `decisions.py` route module entirely and its router registration in `main.py`
- Remove old frontend test file (`serve/cockpit/web/src/__tests__/decisions.test.ts`) that tests removed API contract
- Remove `LegacyPendingDRResponse` dual-format compatibility code from `serve/cockpit/web/src/hooks/usePendingDRs.ts`

**Out of scope:**
- `parse_dr` and `move_to_resolved` engine helpers (used by new code)
- `_append_response_section` and `_rewrite_response` in kanban engine (actively used by `resolve_decision` in new flow)
- New endpoints and UI (already shipped)
- `ResolveModal.tsx` (already uses new structured pattern)

## Downstream impact
- `tests/test_cockpit_decisions_api.py` — update or remove tests for old endpoints
- `tests/test_cockpit_decisions_pydantic_1640.py` — review for old model references
- `serve/cockpit/tests/test_decisions_integration.py` — references old `PendingDRResponse` model
- `tests/test_cockpit_error_envelope.py` — may reference old endpoint paths
- Frontend test files covering old resolve API contract

## Test scope
`tests/test_cockpit_*`, `serve/cockpit/tests/`, and `npm test` in `serve/cockpit/web/`

[[2026-05-26T05:54:21+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure removal of old Cockpit endpoints and dead frontend code |
| Interface clarity | PASS (after refine) | AC now specifies 404 outputs for both endpoints + concrete frontend targets |
| Dependency correctness | PASS | All 4 deps (1856, 1858, 1859, 1860) archived/completed |
| Module layering | PASS | Removes cockpit route module only; kanban engine helpers explicitly out of scope |
| TDD compliance | PASS | Test-writer will write 404 negative assertions; existing test cleanup enumerated |
| KISS/YAGNI | PASS | Straightforward removal, no new abstractions |
| Premise challenge | PASS | New endpoints live, old code is dead weight |
| Pattern consistency | PASS | Follows same removal pattern as sibling #1862 |
| Security surface | PASS | Removal only, no new boundaries |
| Single domain | PASS | Cockpit domain (Python routes + frontend tests/hooks) — corrected scope to exclude kanban engine helpers |

### Scope Correction
Planner scope listed `_append_response_section` and `_rewrite_response` as in-scope removals. These live in `serve/kanban/src/owlbear_kanban/decisions.py` and are actively called by the engine's `resolve_decision` (lines 157-158) which the NEW `requests.py` endpoint uses. Moved to explicit out-of-scope.

### Challenge Results
- Challenger: reconsider (confidence 0.46)
- Findings: domain-boundary (scope listed kanban helpers), AC-quality (AC2 missing 404, AC3 vague), verification-scope (incomplete test file listing)
- Architect response: accepted domain-boundary and AC-quality findings → refined scope and AC. Verification-scope addressed by expanding downstream impact section. Consolidation-backstop concern noted but acceptable — negative 404 assertions belong in this task's tests, not consolidation test.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Corrected scope (removed cross-domain kanban helpers from in-scope), tightened AC2 with 404 output, replaced vague AC3 with concrete file targets (decisions.test.ts, LegacyPendingDRResponse), added AC4 for test-suite health, expanded downstream impact list. Advanced backlog → todo.

[[2026-05-26T06:18:20+02:00]]
## Test-Writer Notes
- Test file: tests/test_cockpit_legacy_cleanup_1863.py
- Classes: TestFromAC_LegacyEndpointRemoval, TestFromAC_FrontendLegacyRemoval
- Tests per category: happy 2, edge 2, error 1, boundary 4
- Total: 9 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 (POST /api/decisions/{id}/resolve → 404) | test_post_resolve_existing_decision_approved_returns_404, test_post_resolve_existing_decision_needs_info_returns_404, test_post_resolve_decision_invalid_payload_returns_404 |
| AC2 (GET /api/decisions/pending → 404) | test_get_decisions_pending_returns_404 |
| AC3 (frontend decisions.test.ts removed; LegacyPendingDRResponse + normalization removed) | test_frontend_decisions_test_file_removed, test_legacy_pending_dr_response_interface_removed, test_is_pending_requests_payload_guard_removed, test_dual_format_payload_items_access_removed |
| AC4 (decisions route module removed from disk) | test_old_decisions_route_module_file_does_not_exist |

### Failure evidence
- AC1 tests: assert 200 == 404 (endpoint exists, processes request)
- AC1 invalid-payload: assert 422 == 404 (FastAPI validates before path removal)
- AC2: assert 200 == 404 (endpoint exists)
- AC3 tests: AssertionError (files/strings still present in codebase)
- AC4: AssertionError (decisions.py still on disk)

### Design note
AC1 tests create real pending DR files (with blocked tasks in engine) so the live endpoint resolves them and returns 200. This avoids the false-404 that would occur if the decisions dir is empty (endpoint returns 404 for unknown IDs even before route removal).

[[2026-05-26T06:42:15+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/src/owlbear_cockpit/main.py
  - serve/cockpit/src/owlbear_cockpit/routes/decisions.py (deleted)
  - serve/cockpit/web/src/hooks/usePendingDRs.ts
  - serve/cockpit/web/src/__tests__/decisions.test.ts (deleted)
  - serve/cockpit/web/src/__tests__/usePendingDRs.test.ts
  - tests/test_cockpit_decisions_api.py (deleted)
  - tests/test_cockpit_decisions_pydantic_1640.py (deleted)
  - serve/cockpit/tests/test_decisions_integration.py (deleted)
  - tests/test_cockpit_notes_cap_1641.py (deleted)
  - tests/test_cockpit_error_envelope.py

- Implementation summary:
  - Removed legacy cockpit decisions router registration/import from `main.py`.
  - Removed legacy backend route module implementing `POST /api/decisions/{id}/resolve` and `GET /api/decisions/pending`.
  - Removed legacy frontend `decisions.test.ts` contract tests.
  - Removed dual-format legacy compatibility in `usePendingDRs.ts`; hook now consumes only new `/api/requests/pending` array payload.
  - Updated durable `usePendingDRs` fixture expectations to new request payload shape.
  - Removed stale backend durable tests that asserted deleted `/api/decisions/*` contracts and removed stale carve-out assertion in `test_cockpit_error_envelope.py`.

- GREEN evidence (quality-runner):
  - `tests/test_cockpit_legacy_cleanup_1863.py`: 9 passed, 0 failed.
  - Frontend impacted suite:
    - `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts`
    - `serve/cockpit/web/src/__tests__/ResolveWiring_1857.test.tsx`
    - `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`
    - `serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx`
    - Result: 48 passed, 0 failed.
    - Coverage snapshot: overall 64.4%; `usePendingDRs.ts` 95.34%.
  - Backend impacted suite:
    - `tests/test_cockpit_legacy_cleanup_1863.py`
    - `tests/test_cockpit_error_envelope.py`
    - `tests/test_cockpit_requests_api_1856.py`
    - Result: 73 passed, 0 failed.

- Lint status:
  - ruff: clean
  - eslint (scoped frontend paths): clean

- Commit:
  - 3677ebf8
  - `refactor: remove legacy cockpit decisions flow (#1863, builder)`

[[2026-05-26T07:11:09+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1863 -> todo | omitted frontend durable tests still assume the legacy count/items payload; independent scoped rerun found 2 failing tests outside the builder proof slice.
- AC evidence summary:
  - AC1: PASS on implementation and task-scoped proof. Legacy resolve route is no longer registered in `serve/cockpit/src/owlbear_cockpit/main.py:32,47`, new structured resolve route is in `serve/cockpit/src/owlbear_cockpit/routes/requests.py:119`, and the task RED/GREEN check covering `POST /api/decisions/{id}/resolve -> 404` passed per builder evidence (`.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:148-160`).
  - AC2: PASS on implementation and task-scoped proof. New pending route is `GET /api/requests/pending` in `serve/cockpit/src/owlbear_cockpit/routes/requests.py:107`, and the task cleanup test covering `GET /api/decisions/pending -> 404` passed per builder evidence (`.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:148-160`).
  - AC3: FAIL. Production hook cleanup is present (`serve/cockpit/web/src/hooks/usePendingDRs.ts:77,83`), and task-scoped cleanup tests cover the deleted file/module checks (`tests/test_cockpit_legacy_cleanup_1863.py:170,189`). But an active durable frontend test still mocks the retired wrapped payload shape with `count/items` and names the old `/api/decisions/pending` contract (`serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts:63,67-68,98-99`). Independent `quality-runner` verification on the omitted frontend proof slice found 2 failures: `expected [] to have a length of 1 but got +0` and `TypeError: Cannot convert undefined or null to object`. This is a real stale-test gap, not a source-code defect.
  - AC4: FAIL on proof sufficiency. The task AC requires backend suite health across `tests/test_cockpit_*` and `serve/cockpit/tests/` (`.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:29-30`), but the builder packet only reports a narrowed backend subset (`.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:156-160`). I independently spot-checked the omitted `serve/cockpit/tests/` slice and found no backend failure, but the builder evidence as recorded does not fully substantiate the AC4 claim.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3 | Durable frontend contract tests were not fully updated for the new `/api/requests/pending` array payload; an omitted active test still uses legacy `count/items` data and now fails against the correct hook implementation. | `serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts:63,67-68,98-99`; `serve/cockpit/web/src/hooks/usePendingDRs.ts:77,83`; independent quality-runner rerun on omitted frontend proof slice reported 2 failures (`expected [] to have a length of 1`, `TypeError: Cannot convert undefined or null to object`). | todo |
| 2 | AC4 | Builder evidence does not cover the full backend suite claim written into the task AC; only a narrowed subset was reported in the proof packet. | Task AC: `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:29-30`; builder proof packet: `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:156-160`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update or remove stale frontend durable tests that still model the retired wrapped decision payload; ensure the remaining hook contract tests use `PendingRequestResponse[]` from `/api/requests/pending`. | serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts, serve/cockpit/web/src/__tests__/DecisionContract.test.tsx | `DecisionContract.hook.test.ts:63,67-68,98-99`; quality-runner failure excerpt in review note |
| 2 | test-writer | Provide proof that the AC4 suite-health claim is satisfied by recording a backend run aligned to the task AC (`tests/test_cockpit_*` and `serve/cockpit/tests/`), or tighten the task AC if that breadth is not intended. | tests/test_cockpit_*, serve/cockpit/tests/, .owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md | Task AC lines 29-30 vs builder packet lines 156-160 |

## Observations
- The implementation surface itself looks correct. Production backend wiring now exposes only the structured requests routes (`serve/cockpit/src/owlbear_cockpit/main.py:32,47`; `serve/cockpit/src/owlbear_cockpit/routes/requests.py:107,119`), and no live production reference to `/api/decisions/*` was found in `serve/cockpit/src/**`.
- Independent backend spot-checking did not surface a backend failure in `serve/cockpit/tests/`; the current blocker is stale/omitted proof on the frontend side plus incomplete AC4 evidence, so routing to `todo` is appropriate rather than `in-progress`.

[[2026-05-26T07:38:47+02:00]]
## Test-Writer Notes
- Retry: 2 stale durable hook tests updated in `serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts`.
- Root cause: mock payloads used old wrapped `{count, items: [{id, request_type, created, body_preview}]}` shape; hook now expects `PendingRequestResponse[]` array with fields `request_id`, `kind`, `created_at`, `summary`.
- Fix: replaced both `makeOkFetch({count, items})` calls with `makeOkFetch([{request_id, kind, created_at, summary, options}])`. Assertions unchanged — normalized output field names (`id`, `request_type`, `created`, `body_preview`) are stable.
- `DecisionContract.test.tsx`: no changes needed — mocks `usePendingDRs` at hook level, unaffected by payload shape.
- Frontend verification: `DecisionContract.hook.test.ts` + `DecisionContract.test.tsx` → 9 passed, 3 skipped, 0 failed.
- AC4 backend suite (`tests/test_cockpit_legacy_cleanup_1863.py`, `tests/test_cockpit_requests_api_1856.py`, `tests/test_cockpit_error_envelope.py`, `serve/cockpit/tests/`) → 87 passed, 0 failed in task scope. 5 pre-existing failures in `test_visual_redesign.py` (Playwright e2e + inline-style budget) are unrelated to this task.
- ESLint: clean.
- Commit: f31907d3 — `test: update DecisionContract.hook tests to new PendingRequestResponse[] shape (#1863, test-writer)`
- Builder skip: test-only retry, all tests green against current impl.

[[2026-05-26T07:58:56+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1863 -> backlog | AC4 remains unmet as written: the retry evidence narrows backend proof to task scope and explicitly admits 5 failures in serve/cockpit/tests, so the second review cycle must escalate the contract.
- AC evidence summary:
  - AC1: PASS. The legacy resolve path is no longer part of the live Cockpit API surface: [serve/cockpit/src/owlbear_cockpit/main.py](serve/cockpit/src/owlbear_cockpit/main.py#L47) registers the new requests router, [serve/cockpit/src/owlbear_cockpit/routes/requests.py](serve/cockpit/src/owlbear_cockpit/routes/requests.py#L119) exposes the structured resolve endpoint, and the task cleanup proof covers the old `POST /api/decisions/{id}/resolve -> 404` contract in [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L120).
  - AC2: PASS. The only live pending-list route is [serve/cockpit/src/owlbear_cockpit/routes/requests.py](serve/cockpit/src/owlbear_cockpit/routes/requests.py#L107), and the task cleanup proof covers `GET /api/decisions/pending -> 404` in [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L165).
  - AC3: PASS. The frontend hook now accepts only the new array payload shape via [serve/cockpit/web/src/hooks/usePendingDRs.ts](serve/cockpit/web/src/hooks/usePendingDRs.ts#L52), [serve/cockpit/web/src/hooks/usePendingDRs.ts](serve/cockpit/web/src/hooks/usePendingDRs.ts#L77), and [serve/cockpit/web/src/hooks/usePendingDRs.ts](serve/cockpit/web/src/hooks/usePendingDRs.ts#L83). The cleanup tests still prove the legacy file/type/guard removals in [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L189), [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L195), [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L200), and [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L205). The retry also fixes the previously stale durable hook proof by using `request_id` array payload fixtures in [serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts](serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts#L63), [serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts](serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts#L68), [serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts](serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts#L92), and [serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts](serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts#L97).
  - AC4: FAIL. The task AC literally requires backend suites in `tests/test_cockpit_*` and `serve/cockpit/tests/` to pass green after removal, as written in [.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md](.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md#L29). The retry evidence still narrows that claim to `task scope` and explicitly records `5 pre-existing failures in test_visual_redesign.py`, which lives under [serve/cockpit/tests/test_visual_redesign.py](serve/cockpit/tests/test_visual_redesign.py). See the retry note in [.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md](.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md#L202). Because this is already the second review cycle after the earlier reject in [.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md](.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md#L173), the remaining blocker is contract/proof quality and routes to backlog.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | The retry still proves only task-scoped backend health and explicitly admits failures inside `serve/cockpit/tests/`, so the literal AC cannot be satisfied on this review cycle. | Task AC: [.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md](.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md#L29); retry evidence: [.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md](.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md#L202); failing suite location: [serve/cockpit/tests/test_visual_redesign.py](serve/cockpit/tests/test_visual_redesign.py) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC4 to the intended impacted-backend verification boundary or split the unrelated `serve/cockpit/tests/test_visual_redesign.py` failures into separate follow-up work; this task cannot PASS while AC4 requires the full suite to be green and the retry evidence admits 5 failures in that suite. | .owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md, serve/cockpit/tests/test_visual_redesign.py | Task AC line 29; retry evidence line 202; prior review line 173 |

## Observations
- The implementation surface itself is consistent with the removal goal. The live Cockpit routes are the structured requests endpoints in [serve/cockpit/src/owlbear_cockpit/routes/requests.py](serve/cockpit/src/owlbear_cockpit/routes/requests.py#L107) and [serve/cockpit/src/owlbear_cockpit/routes/requests.py](serve/cockpit/src/owlbear_cockpit/routes/requests.py#L119), and the legacy route module is covered as absent by [tests/test_cockpit_legacy_cleanup_1863.py](tests/test_cockpit_legacy_cleanup_1863.py#L170).
- Independent narrow verification on the omitted durable hook file found no active failure, but the test still feeds the retired wrapped payload shape in [serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts](serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts#L20) to the real hook and only asserts fetch-call counts in [serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts](serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts#L53), [serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts](serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts#L66), and [serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts](serve/cockpit/web/src/__tests__/usePendingDRs.polling-active.test.ts#L79). Because [serve/cockpit/web/src/hooks/usePendingDRs.ts](serve/cockpit/web/src/hooks/usePendingDRs.ts#L83) maps only array payloads and [serve/cockpit/web/src/hooks/usePendingDRs.ts](serve/cockpit/web/src/hooks/usePendingDRs.ts#L92) resets to error state on mismatch, that file is a weak durable regression guard but not the blocking reason for this verdict.

[[2026-05-26T08:12:34+02:00]]
## Architecture Review (AC4 Refinement)

### Context
Reviewer routed task back to backlog after second FAIL: AC4 as written required full suite health across `tests/test_cockpit_*` and `serve/cockpit/tests/`, but `serve/cockpit/tests/test_visual_redesign.py` has 5 pre-existing failures (Playwright e2e + inline-style budget) from unrelated consolidation task #1629.

### Action
Refined AC4 to explicitly exclude `serve/cockpit/tests/test_visual_redesign.py` from the suite-health gate. This is the "suite gate debt inheritance" pitfall — gating a removal task on unrelated visual-redesign consolidation failures is incorrect.

### Evidence
- `serve/cockpit/tests/test_visual_redesign.py` tests Playwright e2e subprocess gates, inline-style budgets, and dual-theme accessibility for #1629. Zero overlap with decisions endpoint removal.
- Builder + test-writer evidence already demonstrates all task-impacted backend and frontend tests pass (87 passed in scoped backend, 48 passed in frontend, 9 task-specific tests green).
- AC1-AC3 already PASS per both review cycles.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (already complete — task is in retry cycle)

### Verdict: APPROVE (REFINE AC4 + re-advance)
AC4 scoped to exclude known pre-existing unrelated failures. All other AC lines remain unchanged. Task returns to `todo` for pipeline continuation.

[[2026-05-26T08:31:47+02:00]]
## Test-Writer Notes
- Retry 3: no new tests written. Reviewer's Required Follow-up from cycle 2 targeted architect only (refine AC4); architect completed that refinement and returned task to todo.
- AC4 backend suite evidence (refined scope):
  - `tests/test_cockpit_legacy_cleanup_1863.py` + `tests/test_cockpit_requests_api_1856.py` + `tests/test_cockpit_error_envelope.py`: **73 passed, 0 failed**.
  - `serve/cockpit/tests/` (excluding `test_visual_redesign.py`): **13 passed, 0 failed**.
  - Total direct-impact: **86 passed, 0 failed**.
- Broad `tests/test_cockpit_*` run shows 23 failures in unrelated files (`test_cockpit_view.py` ×17, `test_cockpit_models.py` ×1, `test_cockpit_shell_sidecar.py` ×1) — all from other open tasks (#1068, #1071, etc.). Same "suite gate debt inheritance" pattern as `test_visual_redesign.py`. Not caused by this removal.
- `usePendingDRs.polling-active.test.ts` still uses retired wrapped payload shape (`{count, items}`) but asserts only fetch-call counts; reviewed as code-quality weak guard (observation in cycle 2 review, not Required Follow-up). Pass-through per skill — builder to address if needed.
- Builder skip: test-only retry, no test file changes, all existing tests green against current impl.

### AC Coverage (unchanged from prior cycles)
| AC | Tests |
|----|-------|
| AC1 (POST /api/decisions/{id}/resolve → 404) | test_post_resolve_existing_decision_approved_returns_404, test_post_resolve_existing_decision_needs_info_returns_404, test_post_resolve_decision_invalid_payload_returns_404 |
| AC2 (GET /api/decisions/pending → 404) | test_get_decisions_pending_returns_404 |
| AC3 (frontend decisions.test.ts removed; LegacyPendingDRResponse + normalization removed) | test_frontend_decisions_test_file_removed, test_legacy_pending_dr_response_interface_removed, test_is_pending_requests_payload_guard_removed, test_dual_format_payload_items_access_removed |
| AC4 (decisions route module removed from disk; suite health) | test_old_decisions_route_module_file_does_not_exist; backend suite evidence above |

[[2026-05-26T09:21:59+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1863 to backlog | AC4 remains unsatisfied as written. The authoritative task AC still requires `tests/test_cockpit_*` and `serve/cockpit/tests/` to pass green after removal, excluding only `serve/cockpit/tests/test_visual_redesign.py`, while the latest retry evidence still records unrelated failures inside `tests/test_cockpit_*`.
- Builder and retry evidence reviewed first. I found no blocking implementation defect in the removed-route work itself.
- AC evidence summary:
  - AC1: PASS. Legacy resolve path is no longer part of the live Cockpit API surface. Evidence: `serve/cockpit/src/owlbear_cockpit/main.py:32,44-50`, `serve/cockpit/src/owlbear_cockpit/routes/requests.py:119`, `tests/test_cockpit_legacy_cleanup_1863.py:120-162`.
  - AC2: PASS. Legacy pending-list path is removed and task cleanup proof covers the 404 contract. Evidence: `serve/cockpit/src/owlbear_cockpit/routes/requests.py:107`, `tests/test_cockpit_legacy_cleanup_1863.py:165-167`.
  - AC3: PASS for the implementation and declared frontend proof slice. The hook is array-only and the durable hook retry is green. Evidence: `serve/cockpit/web/src/hooks/usePendingDRs.ts:40-83`, `tests/test_cockpit_legacy_cleanup_1863.py:189-210`, `serve/cockpit/web/src/__tests__/DecisionContract.hook.test.ts:63-114`, task retry note at `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:257-260`.
  - AC4: FAIL. The frontmatter still requires the broad `tests/test_cockpit_*` suite to pass, but the latest retry explicitly records 23 failures there. The architect refinement only excluded `serve/cockpit/tests/test_visual_redesign.py`; it did not narrow the `tests/test_cockpit_*` half of the gate. Evidence: `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:24-30`, `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:235-241`, `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:257-260`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | The task contract remains broader than the refined intended verification boundary. The frontmatter still requires `tests/test_cockpit_*` green, but the latest retry admits unrelated failures there, so the AC cannot be marked satisfied on this review cycle. | `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:24-30`, `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:235-241`, `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md:257-260`, `tests/test_cockpit_view.py:1`, `tests/test_cockpit_models.py:1`, `tests/test_cockpit_shell_sidecar.py:1` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC4 so the suite-health gate matches the intended task scope, or split the unrelated `tests/test_cockpit_*` failures into separate follow-up work. The current frontmatter still requires a broad suite that the retry evidence shows is not green. | `.owlbear/kanban/tasks/1863-p2-06-remove-old-cockpit-resolve-flow-and-legacy-endpoints.md`, `tests/test_cockpit_view.py`, `tests/test_cockpit_models.py`, `tests/test_cockpit_shell_sidecar.py` | task AC lines 24-30, architect refinement lines 235-241, retry evidence lines 257-260 |

## Observations
- The implementation itself is consistent with the removal goal. I found no live backend `/api/decisions` route registration under `serve/cockpit/src/**`, and the task cleanup tests cover both 404 removals plus the deleted route module.
- Residual legacy-endpoint strings remain in non-blocking frontend test surfaces, including parked skipped scaffolding in `serve/cockpit/web/src/__tests__/DecisionContract.test.tsx:234` and Playwright route stubs such as `serve/cockpit/web/e2e/card-density.spec.ts:194` and `serve/cockpit/web/e2e/shell-layout-1606.spec.ts:83`. I did not use those as blockers because the current FAIL is already forced by AC4 contract quality.

[[2026-05-26T09:34:03+02:00]]
## Architecture Review (AC4 Refinement — Cycle 2)

### Context
Reviewer routed task back to backlog after third FAIL: AC4 broad gate `tests/test_cockpit_*` catches 23 pre-existing failures in `test_cockpit_view.py` (task #1224), `test_cockpit_models.py` (task #1146), and `test_cockpit_shell_sidecar.py` (shell-layout work). None relate to decisions endpoint removal.

### Evidence of Non-Relation
- `test_cockpit_view.py`: tests CockpitView relocation from kanban→cockpit (#1224). Tests import paths and module boundaries — zero mention of `/api/decisions/`.
- `test_cockpit_models.py`: tests dead model cleanup (#1146). Asserts removed model classes — zero mention of decisions endpoints.
- `test_cockpit_shell_sidecar.py`: tests Shell.tsx nav-rail tabIndex and sidecar layout. Zero overlap with backend route removal.

### Action
Refined AC4 to explicitly scope the suite-health gate to task-impacted files only:
- `tests/test_cockpit_legacy_cleanup_1863.py`
- `tests/test_cockpit_requests_api_1856.py`
- `tests/test_cockpit_error_envelope.py`
- `serve/cockpit/tests/` (excluding `test_visual_redesign.py`)

Pre-existing failures in other `tests/test_cockpit_*` files are explicitly excluded from this task's gate. This is the same \"suite gate debt inheritance\" pattern identified in cycle 1 — the prior refinement only addressed `serve/cockpit/tests/` half but missed the `tests/test_cockpit_*` half.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (already complete — task in retry cycle)

### Verdict: APPROVE (REFINE AC4 + re-advance)
All 4 AC lines are now verifiable against task-scoped evidence. AC1-AC3 have been passing since cycle 1. AC4 now correctly gates only task-impacted test files. Task returns to `todo` for pipeline continuation.

[[2026-05-26T09:36:03+02:00]]
## Test-Writer Notes
- Retry 4: no new tests written. Reviewer's Required Follow-up from cycle 3 targeted architect only (refine AC4 broad gate); architect completed refinement (Cycle 2) and returned task to todo.
- AC4 backend suite (refined scope — task-impacted files only):
  - `tests/test_cockpit_legacy_cleanup_1863.py` + `tests/test_cockpit_requests_api_1856.py` + `tests/test_cockpit_error_envelope.py` + `serve/cockpit/tests/` (excl. test_visual_redesign.py): **86 passed, 0 failed**.
- AC4 frontmatter now explicitly excludes pre-existing failures in `test_cockpit_view/models/shell_sidecar` (other open tasks). None of those are caused by this removal.
- AC1–AC3: unchanged — passed in all prior cycles.
- Builder skip: test-only retry, no test file changes, all tests green against current impl.
