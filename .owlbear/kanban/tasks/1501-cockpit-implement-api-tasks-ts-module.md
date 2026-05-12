---
id: 1501
title: 'Cockpit: Implement api/tasks.ts module'
status: in-progress
priority: needed
created: 2026-05-12T02:43:28.689799+00:00
updated: 2026-05-12T09:17:04.227196+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Create `serve/cockpit/web/src/api/tasks.ts` with centralized API functions following the existing `repair.ts`/`cleanup.ts` pattern.

## Acceptance Criteria
- Exports `getTask()`, `moveTask()`, `editTask()`, `releaseTask()` async functions
- Exports `ApiError` class with `.status` property
- All functions use `getResponseErrorMessage` for error parsing and throw `ApiError` on non-ok responses
- Request/response types exported and match backend contract
- Unit tests cover success and error paths for each function

## Implementation Notes
- Follow existing pattern in `api/repair.ts` and `api/cleanup.ts`
- `ApiError` may live in a shared `api/errors.ts` if cleaner
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC has B3 violations ("All functions") that need refinement. Proof bundle needs assignment.
2026-05-12T08:50:22+00:00

## Refined Acceptance Criteria
_Supersedes original AC. Numbered, B3-clean, challenger-validated._

- AC-1: `api/errors.ts` exports class `ApiError` extending `Error` with readonly `status: number`; `new ApiError(409, "conflict")` produces `.status === 409` and `.message === "conflict"`
- AC-2: `getTask(id, options?)` in `api/tasks.ts` sends `GET /api/tasks/{id}`, forwards `options.signal` to `fetch` when provided, returns parsed JSON as `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-3: `moveTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/move` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-4: `editTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/edit` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-5: `releaseTask(id, request)` in `api/tasks.ts` sends `POST /api/tasks/{id}/release` with JSON body, returns `TaskDetail` on 2xx, throws `ApiError` on non-ok
- AC-6: On non-ok response, `getTask`, `moveTask`, `editTask`, and `releaseTask` extract error message via `getResponseErrorMessage(response, fallback)` before throwing `ApiError`; network errors (fetch rejection) propagate unwrapped
- AC-7: `api/tasks.ts` exports request interfaces: `MoveRequest` (`status: string`, `updated: string`, optional `archival_reason: string | null`, `archival_refs: number[] | null`), `EditRequest` (`updated: string`, optional `title: string | null`, `tags: string[] | null`, `priority: string | null`, `depends_on: number[] | null`, `parent: number | null`, `block_reason: string | null`, `body: string | null`), `ReleaseRequest` (`updated: string`)
- AC-8: `api/tasks.ts` exports response interface `TaskDetail` with fields: `id: number`, `title: string`, `status: string`, `priority: string`, `updated: string`, `created: string`, `body: string | null`, `tags: string[]`, `blocked: boolean`, `block_reason: string | null`, `claimed: boolean`, `claimed_at: string | null`, `dep_status: string | null`, `parent: number | null`, `depends_on: number[]`

Proof bundle: behavioral

## Implementation Notes (updated)
- `ApiError` in `api/errors.ts` (shared with #1502 api/decisions.ts)
- Follow `api/repair.ts` / `api/cleanup.ts` pattern for function structure
- `TaskDetail` is a frontend-scope interface covering consumer-needed fields; backend `SingleTaskResponse` and `ShowTaskResponse` share this subset — extra server fields (e.g. `guidance`, `missing_sections`) are silently dropped by TypeScript structural typing
- `EditRequest` optional fields use `T | null` types to support backend tri-state (omit = no change, null = clear, value = set) semantics
- Network errors (fetch throws) propagate as-is; `ApiError` wraps HTTP-level errors only
- `getTask` accepts optional `{ signal?: AbortSignal }` — Shell.tsx passes abort signals to task fetches; mutation functions do not need signal support (no current callers pass signals)
2026-05-12T08:50:49+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module (api/tasks.ts) + shared error class (api/errors.ts) — single domain concern |
| Interface clarity | PASS | AC-1..AC-8 specify exact function signatures, input types with nullability, response fields, and error semantics |
| Dependency correctness | PASS | No depends_on needed; #1502 correctly depends on #1501 for ApiError; #1503 depends on both |
| Module layering | PASS | api/ sits between components and backend; no upward imports; ApiError in shared api/errors.ts |
| TDD compliance | PASS | Behavioral proof bundle assigned; test-writer derives RED tests from AC-1..AC-8 |
| KISS/YAGNI | PASS | Follows established repair.ts/cleanup.ts pattern; AbortSignal only on getTask (evidence: Shell.tsx); no signal on mutations (no callers use it) |
| Premise challenge | PASS | 8+ raw fetch sites across 5 components justify centralization; pattern already proven by repair.ts/cleanup.ts |
| Pattern consistency | PASS | Matches existing api/ module pattern; ApiError upgrade is additive (justified by DetailTab 409/404/422 branching) |
| Security surface | PASS | Internal SPA→backend fetch calls; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Challenger Results
- Challenger: reconsider (0.62)
- Findings addressed:
  1. **ShowTaskResponse vs SingleTaskResponse divergence** — Accepted. TaskDetail scoped to consumer-needed fields (subset); extra server fields dropped by TypeScript structural typing. AC-8 enumerates exact fields. Implementation note added.
  2. **AC-7 nullability/tri-state** — Accepted. EditRequest fields now explicitly typed as `T | null`. Implementation note added about tri-state semantics.
  3. **AbortSignal for getTask** — Accepted. AC-2 now includes `options.signal` forwarding. Mutations kept signal-free (no callers pass signals).
  4. **Error handling divergence** — Accepted as minor. AC-6 now specifies network errors propagate unwrapped (only HTTP errors become ApiError).
  5. **Consolidation-test gap** — Noted, minor. #1503 (consumer migration with behavioral-preservation AC) serves as integration verification.
- Architect response: revised AC based on findings 1-4; noted finding 5 without action

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: behavioral
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single viable approach (established repair.ts/cleanup.ts pattern + ApiError); no competing designs

### AC Refinement Summary
Original AC had B3 violations ("All functions"), no numbering, vague "match backend contract", and meta-AC about test existence. Refined to 8 numbered, B3-clean AC lines with exact function signatures, enumerated field types with nullability, explicit error semantics, and AbortSignal support where needed.

### Verdict: APPROVE (REFINE + approve)
### Action Taken: Refined AC (B3 fix, numbering, challenger-driven improvements), assigned proof bundle behavioral, advanced to todo
2026-05-12T09:17:04+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/tasks_1501.test.ts
- Classes: TestFromAC_ApiError, TestFromAC_GetTask, TestFromAC_MoveTask, TestFromAC_EditTask, TestFromAC_ReleaseTask, TestFromAC_RequestInterfaces, TestFromAC_TaskDetailInterface
- Tests per category: happy 22, edge 4, error 16, boundary 8 (interface structural 15)
- Total: 65 tests, all FAIL (module resolution error — api/errors.ts and api/tasks.ts do not exist)
- eslint: clean
- AC coverage: AC-1 (8 tests), AC-2 (12 tests), AC-3 (8 tests), AC-4 (8 tests), AC-5 (8 tests), AC-6 covered in each function group, AC-7 (5 tests), AC-8 (14 tests)