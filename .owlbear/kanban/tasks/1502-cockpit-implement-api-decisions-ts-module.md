---
id: 1502
title: 'Cockpit: Implement api/decisions.ts module'
status: in-progress
priority: needed
created: 2026-05-12T02:43:28.721141+00:00
updated: 2026-05-12T09:31:39.708532+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on:
  - 1501
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Create `serve/cockpit/web/src/api/decisions.ts` with `resolveDR()` function following the established API client pattern.

## Acceptance Criteria
- Exports `resolveDR()` async function
- Function is typed (request/response types exported)
- Uses `getResponseErrorMessage` for error parsing, throws `ApiError` with `.status`
- Unit tests cover success and error paths

## Implementation Notes
- Depends on `ApiError` from #1501 (either from `api/tasks.ts` or shared `api/errors.ts`)
- Follow same pattern as `api/repair.ts`
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC needs refinement (B3, numbering). Proof bundle needs assignment.
2026-05-12T09:10:43+00:00


## Refined Acceptance Criteria
_Supersedes original AC. Numbered, B3-clean, challenger-validated._

- AC-1: `api/decisions.ts` exports async function `resolveDR(id: string, request: ResolveRequest)` that sends `POST /api/decisions/{id}/resolve` with JSON body containing `request` fields, returns parsed JSON as `ResolveResponse` on 2xx, throws `ApiError` on non-ok
- AC-2: `api/decisions.ts` exports interface `ResolveRequest` with fields: `response: 'approved' | 'needs-info' | 'rejected'`, optional `notes?: string`
- AC-3: `api/decisions.ts` exports interface `ResolveResponse` with fields: `id: string`, `response: 'approved' | 'needs-info' | 'rejected'`
- AC-4: On non-ok response, `resolveDR` extracts error message via `getResponseErrorMessage(response, fallback)` before throwing `ApiError`; network errors (fetch rejection) propagate unwrapped
- AC-5: `resolveDR` imports `ApiError` from `api/errors.ts` (shared module created by #1501)

Proof bundle: behavioral

## Implementation Notes (updated)
- Follow `api/cleanup.ts` pattern for function structure (no catch-all error wrapping — let network errors propagate)
- Backend route: `POST /decisions/{decision_id}/resolve` — returns `{id, response}` on success
- Backend error envelopes: 404 `{detail}`, 409 `{code, message}` (ConcurrencyError), 422 `{detail}`
- `ResolveRequest.response` and `ResolveResponse.response` use identical closed union matching backend `Literal["approved", "needs-info", "rejected"]`
- `notes` is optional (backend default: `null`)

2026-05-12T09:11:08+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single function (`resolveDR`) + 2 interfaces — one concern |
| Interface clarity | PASS | AC-1..AC-5 specify exact function signature, request/response fields with closed unions, and error semantics |
| Dependency correctness | PASS | Depends on #1501 for `ApiError` in `api/errors.ts` — correctly declared |
| Module layering | PASS | `api/` sits between components and backend; no upward imports; `ApiError` from shared `api/errors.ts` |
| TDD compliance | PASS | Behavioral proof bundle assigned; test-writer derives RED tests from AC-1..AC-5 |
| KISS/YAGNI | PASS | Follows established cleanup.ts pattern; single function, minimal scope |
| Premise challenge | PASS | ResolveModal.tsx lines 59-78 has raw fetch with error handling — centralization justified by parent #1493 research |
| Pattern consistency | PASS | Matches cleanup.ts structure (no catch-all wrapping); ApiError upgrade consistent with #1501 |
| Security surface | PASS | Internal SPA→backend fetch; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: behavioral
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single viable approach (established cleanup.ts pattern + ApiError from #1501)

### Challenge Results
- Challenger: reconsider (0.58)
- Findings addressed:
  1. **Contract precision** — Accepted. AC-3 `ResolveResponse.response` tightened from `string` to closed union `'approved' | 'needs-info' | 'rejected'` matching backend `Literal`.
  2. **Pattern divergence** — Accepted as context. AC-4 specifies exact error semantics (cleanup.ts style). Implementation notes updated to reference cleanup.ts, not repair.ts.
  3. **Consumer-boundary mismatch** — Scoped to #1503. API module throws `ApiError`; consumer status→retryability mapping is migration scope.
  4. **Dependency readiness** — Standard pipeline ordering. #1501 is `todo`; dependency correctly declared.
  5. **Workflow evidence drift** — Standard architect workflow; refined AC written during review.
  6. **Consolidation-test gap** — #1503 (consumer migration) serves as integration verification for the 3-task set.
- Architect response: revised AC-3 per finding 1; updated implementation notes per finding 2; other findings noted without action

### AC Refinement Summary
Original AC had B3 violations ("Function is typed" — vague, "Unit tests cover success and error paths" — meta-AC), no numbering, no proof bundle. Refined to 5 numbered, B3-clean AC lines with exact function signature, closed-union typed interfaces, explicit error semantics, and shared module import path.

### Verdict: APPROVE (REFINE + approve)
### Action Taken: Refined AC (B3 fix, numbering, challenger-driven contract precision), assigned proof bundle behavioral, advanced to todo
2026-05-12T09:31:39+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/decisions_1502.test.ts
- Classes: TestFromAC_ResolveDR, TestFromAC_ResolveRequest, TestFromAC_ResolveResponse
- Tests per category: happy 7, edge 2, error 9, boundary/structural 5
- Total: 23 tests, all FAIL (suite fails to load — import resolution error for `api/decisions.ts` and `api/errors.ts`; expected RED phase behavior)
- ruff: N/A (TypeScript); eslint: clean
- AC coverage:
  - AC-1 (resolveDR function, POST /api/decisions/{id}/resolve, JSON body, 2xx → ResolveResponse, throws ApiError on non-ok): covered by TestFromAC_ResolveDR happy + error tests
  - AC-2 (ResolveRequest: response union + optional notes): covered by TestFromAC_ResolveRequest (6 tests)
  - AC-3 (ResolveResponse: id string + response union): covered by TestFromAC_ResolveResponse (5 tests)
  - AC-4 (getResponseErrorMessage for error extraction, network errors propagate unwrapped): covered by 4 dedicated AC-4 tests in TestFromAC_ResolveDR
  - AC-5 (imports ApiError from api/errors.ts): covered by structural import test in TestFromAC_ResolveDR