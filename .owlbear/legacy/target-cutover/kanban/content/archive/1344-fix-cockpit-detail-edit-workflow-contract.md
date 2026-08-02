---
id: 1344
title: Fix Cockpit detail edit workflow contract
status: archived
priority: medium
created: 2026-05-04T17:27:34.891597+00:00
updated: 2026-05-05T21:47:07.633212+00:00
tags:
- sync-blocker
- cockpit
- cockpit-api
- cockpit-frontend
parent:
depends_on:
- 1348
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Cockpit exposes task-detail controls and mutation routes that do not agree on what is editable. The backend route accepts fields that either crash (`parent: null`) or silently no-op (`body: ""`), while the frontend renders relationship/blocking/action controls that are not persisted.

Cockpit is expected to be a central task endpoint, so visible edit controls must either mutate correctly or be explicitly read-only. This task follows the audit-approved Option A: complete the Cockpit detail edit workflow rather than merely hardening the backend.

## Acceptance Criteria

1. `POST /api/tasks/{id}/edit` passes `body`, `parent`, `tags`, `depends_on`, and `block_reason` values through to `engine.edit_task()` with correct set/clear/omit semantics; invalid values return 422, not uncaught exceptions. `(td:2)`
2. `parent: null` in the JSON request body clears the parent (maps to engine's parent-clear signal); it must never raise `TypeError`. Negative values return 422. `(td:2)`
3. `body: ""` in the JSON request body clears the task body (maps to engine's `body=""` contract); it must never return 200 while leaving the body unchanged. `body: null` or field omitted means no change. `(td:2)`
4. `DetailTab` controls for `title`, `priority`, `body`, `depends_on`, `parent`, and `block_reason` are controlled inputs (React state-driven, not `defaultValue`), and save sends their current values in the edit payload with correct types (list[int] for deps, int|null for parent, etc.). Tags: builder decides whether read-only chips or editable — if editable, save sends full replacement list. `(td:2)`
5. `DetailTab` actions after confirmation: unblock → POST `/api/tasks/{id}/edit` with `block_reason: null`; unclaim → POST `/api/tasks/{id}/release`; move-backward → POST `/api/tasks/{id}/move` with target status derived from pipeline-order (previous status from `valid_transitions` or board status list). All handle 409 (refetch + show conflict), 422 (show validation message), 404 (deselect task). `(td:2)`
6. Successful edits and actions: `DetailTab` calls `onTaskUpdated(responseTask)` callback threaded from Shell, which updates `selectedTask` state and triggers a board-list refetch when title/priority/status/blocked changed. `(td:1)`
7. Durable backend tests cover actual gaps: (a) `parent: null` → clears parent, (b) `body: ""` → clears body, (c) `body: null`/omitted → no change, (d) negative parent → 422. Existing tag/dep/block/stale-token coverage is sufficient. `(td:0)`
8. Durable frontend tests prove: (a) controlled fields produce correct typed JSON payload, (b) action confirmations trigger expected endpoint calls with correct bodies, (c) `onTaskUpdated` callback invoked with response data on success. `(td:0)`

## Key Files

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — route + `_build_edit_kwargs`
- `serve/cockpit/src/owlbear_cockpit/view.py` — CockpitView.edit_task (adopt tri-state)
- `serve/cockpit/web/src/components/DetailTab.tsx` — controlled inputs + actions
- `serve/cockpit/web/src/Shell.tsx` — thread onTaskUpdated, trigger board refetch
- `serve/kanban/src/owlbear_kanban/engine.py` — reference contract (body/parent semantics)
- `tests/test_cockpit_mutation_api.py` — extend with gap tests
- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` — frontend proof

## Audit Evidence

- `EditRequest.parent` accepts `None`; `_build_edit_kwargs()` forwards it; `CockpitView.edit_task()` compares `parent > 0`. A direct TestClient repro produced `TypeError: '>' not supported between instances of 'NoneType' and 'int'`.
- `body: ""` reaches `CockpitView.edit_task()` but is skipped by `if body:`, so a clear-body request can look successful without mutating storage.
- `DetailTab` renders `depends_on`, `parent`, and `block_reason` controls, but `handleSave()` only sends `updated`, `title`, `priority`, and `body`.
- `onTaskUpdated` is declared but unused (not destructured, not passed from Shell).
- `ConfirmDialog.onConfirm` only closes the dialog — no API call is made.
- KanbanBoard already uses `valid_transitions` for move targets (reference pattern for move-backward).

[[2026-05-05]]
## Architecture Review

**Verdict: APPROVED → todo**

Refined all 8 AC lines after challenger reconsider (0.66). Key refinements:
- AC2/AC3: Removed ambiguous "or rejected" — engine already supports clear semantics
- AC4: Explicit scope latitude for tags (builder decides read-only vs editable)
- AC5: Specified exact endpoints for each action + move-backward contract (valid_transitions)
- AC6: Specified Shell→DetailTab callback threading + board refetch trigger
- AC7/AC8: Narrowed to actual coverage gaps (parent null, body empty, typed payloads)

Root cause: CockpitView.edit_task uses old-style defaults that collapse omit/clear signals before engine.edit_task(). Fix is tri-state pattern matching engine contract.

Dependency #1348 (archived) satisfied. All eval criteria PASS.
[[2026-05-05]]
## Test-Writer Notes
- Test file (backend): tests/test_cockpit_mutation_api_1344.py
- Test file (frontend): serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx
- Classes: TestFromAC_EditParentContract, TestFromAC_EditBodyContract, TestFromAC_DetailTabEditPayload, TestFromAC_DetailTabActions, TestFromAC_DetailTabTaskUpdated
- Tests per category (backend — 5 tests): happy 1, edge 1, error 2, boundary 1
- Tests per category (frontend — 11 tests): happy 2, edge 2, error 4, boundary 3
- Total: 16 tests, all FAIL
- ruff: clean

AC coverage table:
| AC  | td  | Tests                                                                                                                         |
|-----|-----|-------------------------------------------------------------------------------------------------------------------------------|
| AC1 | td:2 | test_parent_null_returns_200_not_typeerror, test_body_empty_string_clears_body (semantics + no-exception proof)             |
| AC2 | td:2 | test_parent_null_returns_200_not_typeerror, test_parent_null_clears_parent, test_negative_parent_returns_422                |
| AC3 | td:2 | test_body_empty_string_clears_body, test_body_empty_string_does_not_return_unchanged_body                                  |
| AC4 | td:2 | save payload includes depends_on / parent (int) / parent (null) / block_reason                                              |
| AC5 | td:2 | unblock/unclaim/move-backward confirm posts; move-backward sends previous status; 409 shows conflict; 422 shows validation  |
| AC6 | td:1 | successful save calls onTaskUpdated with response task                                                                       |
| AC7 | td:0 | skipped                                                                                                                       |
| AC8 | td:0 | skipped                                                                                                                       |

Failure evidence:
- Backend: TypeError (NoneType > int) on parent:null → 500; negative parent silently no-ops → 200; body:"" leaves body unchanged → 200 with original body
- Frontend: handleSave() omits depends_on/parent/block_reason from payload; ConfirmDialog.onConfirm() only closes dialog (no API call); onTaskUpdated not destructured from props
[[2026-05-05]]
## Builder Notes
- Implementation:
  - Updated `serve/cockpit/src/owlbear_cockpit/view.py` to support tri-state edit semantics for `parent` and `body` in cockpit edit flow (`omit` vs `clear` vs `set`), including explicit 422 validation for negative parent values.
  - Updated `serve/cockpit/web/src/components/DetailTab.tsx` to make `depends_on`, `parent`, and `block_reason` controlled inputs; expanded save payload typing (`depends_on: list[int]`, `parent: int|null`, `block_reason: str|null`); implemented confirm action mutations for unblock/unclaim/move-backward; added 409/422/404 handling and `onTaskUpdated` callback invocation on success.
  - Updated `serve/cockpit/web/src/Shell.tsx` to thread `board` and `onTaskUpdated`/clear callbacks into `DetailTab`, keep `selectedTask` in sync from mutation responses, and trigger board refetch when title/priority/status/blocked fields change.

- Tests:
  - Task-scoped RED→GREEN verification via quality-runner:
    - `tests/test_cockpit_mutation_api_1344.py`: 5 passed
    - `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx`: 11 passed
    - Total: 16 passed, 0 failed.
  - Durable regression check via quality-runner:
    - `tests/test_cockpit_mutation_api.py` + `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`: 77 passed, 0 failed.

- Coverage:
  - Scoped task run reported:
    - `owlbear_cockpit.view`: 51%
    - `owlbear_cockpit.routes.mutation`: 50%
    - frontend `DetailTab.tsx`: 85.38%
  - Durable regression scoped run reported:
    - cockpit python modules overall: 87%
    - `view`: 76%, `routes.mutation`: 87%

- Lint:
  - `ruff`: clean
  - `eslint`: clean

- Evidence summary:
  - AC2 fixed: `parent: null` now clears without `TypeError`; negative parent returns 422.
  - AC3 fixed: `body: ""` now propagates as clear signal instead of falsy no-op.
  - AC4 fixed: save payload now includes typed `depends_on`, `parent`, and `block_reason`.
  - AC5 fixed: confirm actions now call expected endpoints/bodies with conflict/validation/not-found handling.
  - AC6 fixed: successful save/action responses invoke `onTaskUpdated(responseTask)` and Shell reacts by updating detail state + board refresh when key list fields change.

- Commit:
  - `3704a1a1` — feat: complete cockpit detail edit workflow contract (#1344, builder)

- Post-task reflection:
  - Problem faced: custom `ValidationError` requires registered error codes; using an unregistered code causes a runtime `ValueError`.
  - Workaround applied: reused a registered validation code and preserved the user-facing 422 message semantics.
  - Pattern discovered: for cockpit task edits, tri-state sentinels in view-layer kwargs are required to preserve `omit` vs `clear` semantics expected by engine contracts.
  - Quality note: routing action outcomes through a single mutation helper simplified consistent 409/422/404 handling across save/confirm flows.
[[2026-05-05]]
## Review Evidence
### Scope
- Claimed task 1344 in review.
- Builder commit `3704a1a1` is present in `.git/logs/refs/heads/dev`; a diff was not accessible from this tool surface, so changed-file scope was reconstructed from builder notes plus the AC-critical files. Small confidence deduction applied to TestFromAC immutability for lack of direct diff evidence.

### Test Results
- Backend quality-runner: 48 passed, 0 failed, 0 skipped; ruff clean; coverage overall 82%, `owlbear_cockpit.view` 77%, `owlbear_cockpit.routes.mutation` 87%.
- Frontend quality-runner: combined `DetailTab_1344.test.tsx` + `DetailTab.test.tsx` run deadlocked in Vitest, so evidence was rerun in isolated frontend passes.
- Isolated frontend reruns: `DetailTab_1344.test.tsx` 11/11 passed; `DetailTab.test.tsx` 34/34 passed; eslint clean.
- Durable frontend coverage run: 79.25% overall; `DetailTab.tsx` 80% statements / 81.11% branches. Task-scoped frontend coverage was not collected because `vitest --coverage` timed out.
- VS Code diagnostics: clean for `DetailTab.tsx`, `Shell.tsx`, `routes/mutation.py`, and `view.py`.

### Findings
1. AC5 implementation miss: the task requires `409 -> refetch + show conflict`, but `DetailTab.runMutation()` only opens the conflict modal at `serve/cockpit/web/src/components/DetailTab.tsx:113-114`. The only board refetch path is the success-only `onTaskUpdated` branch in `serve/cockpit/web/src/Shell.tsx:163-173`. The task test at `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:423` only proves conflict display, so both implementation and proof miss the refetch half of AC5.
2. AC7 durable backend proof missing: the durable suite still tops out at generic `test_edit_parent_returns_200` and `test_edit_body_returns_200` in `tests/test_cockpit_mutation_api.py:306` and `tests/test_cockpit_mutation_api.py:318`. Search found no durable `parent:null`, `body:""`, `body:null/omitted`, or negative-parent coverage.
3. AC8 durable frontend proof missing: the durable `DetailTab.test.tsx` suite has generic save/conflict/confirm coverage, but search across `serve/cockpit/web/src/__tests__/**/*.tsx` found `onTaskUpdated` only in task-scoped `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:505-533`, and the durable suite does not pin typed `depends_on`/`parent`/`block_reason` payloads or action request bodies.
4. AC4 / AC6 proof remains incomplete: `DetailTab.tsx` still carries `defaultValue` on controlled fields at `serve/cockpit/web/src/components/DetailTab.tsx:252`, `:261`, and `:271`, and the payload tests in `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:144-233` serialize fixture state rather than driving live edits through those controls. The new Shell callback branch at `serve/cockpit/web/src/Shell.tsx:163-173` is not exercised directly.
5. AC5 action-proof gap remains: task-scoped frontend tests prove 409 and 422 UI handling at `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:423` and `:457`, but there is no 404 deselection proof for the `onTaskCleared` path in `serve/cockpit/web/src/components/DetailTab.tsx:118-120` and `serve/cockpit/web/src/Shell.tsx:159-162`.

### AC Compliance
| AC | Evidence | Status |
|----|----------|--------|
| 1 | Backend code in `routes/mutation.py` / `view.py` plus green backend suites cover set/clear flows, but omit semantics remain under-proven because the durable suite was not upgraded for the null/omit branch. | FAIL |
| 2 | `tests/test_cockpit_mutation_api_1344.py:128-187` proves `parent:null` clears without `TypeError` and negative parent returns 422. | PASS |
| 3 | `tests/test_cockpit_mutation_api_1344.py:209-254` proves `body:""` clear; durable proof for `body:null/omitted -> no change` is still missing. | FAIL |
| 4 | `DetailTab.tsx` is state-driven, but the implementation still includes `defaultValue` on three controlled fields and the tests do not drive current user edits through those controls. | FAIL |
| 5 | Endpoint/body checks exist for unblock and move, but 409 lacks the required refetch in code and 404 deselection remains untested. | FAIL |
| 6 | `Shell.tsx:163-173` implements the callback/refetch branch, but proof stops at `DetailTab` callback invocation in `DetailTab_1344.test.tsx:505-533`. | FAIL |
| 7 | Durable backend suite missing the named null/empty/negative edit cases. | FAIL |
| 8 | Durable frontend suite missing typed payload, action-body, and durable `onTaskUpdated` proof. | FAIL |

### Deductions
- -0.14 AC5 implementation miss (`409 -> refetch + show conflict` not fully implemented)
- -0.07 AC7 durable backend proof missing
- -0.07 AC8 durable frontend proof missing
- -0.05 AC4/AC6 proof gaps on current-value controls and Shell callback wiring
- -0.02 no direct diff access + frontend combined Vitest deadlock

### Verdict
- Confidence: 0.65
- Verdict: FAIL -> in-progress
- Action: builder retry required; current snapshot needs both a frontend implementation correction and stronger durable proof before this can re-enter review.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Refetch task/board state on mutation 409 before showing the conflict UI, and add a test that proves both refetch and conflict display. | serve/cockpit/web/src/components/DetailTab.tsx; serve/cockpit/web/src/Shell.tsx; serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx | AC5; `DetailTab.tsx:113-114`; `Shell.tsx:163-173`; `DetailTab_1344.test.tsx:423` |
| 2 | builder | Extend durable backend mutation coverage for `parent:null` clear, `body:""` clear, `body:null/omitted` no-change, and negative parent 422. | tests/test_cockpit_mutation_api.py | AC7; durable suite only shows generic parent/body edits at `:306` and `:318` |
| 3 | builder | Remove the remaining `defaultValue` usage on the controlled detail fields or otherwise make AC4 literal conformance explicit, and add a test that drives live edits through those fields before save. | serve/cockpit/web/src/components/DetailTab.tsx; serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx; serve/cockpit/web/src/__tests__/DetailTab.test.tsx | AC4; `DetailTab.tsx:252`, `:261`, `:271`; payload tests at `DetailTab_1344.test.tsx:144-233` only serialize fixture state |
| 4 | builder | Extend durable frontend coverage for action request bodies including 404 clear behavior and for the `Shell` `onTaskUpdated -> selectedTask/refetchTasks()` branch. | serve/cockpit/web/src/__tests__/DetailTab.test.tsx; serve/cockpit/web/src/__tests__/Shell_*.test.tsx | AC5/AC6/AC8; only task-scoped callback proof exists at `DetailTab_1344.test.tsx:505-533` |
[[2026-05-05]]
## Builder Notes
- Scope checked: `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, backend mutation route/view, and task/durable test files for #1344.
- Fresh quality-runner evidence:
  - Python: 48 passed, 0 failed (`tests/test_cockpit_mutation_api_1344.py`, `tests/test_cockpit_mutation_api.py`)
  - Frontend: 44 passed, 1 failed (`DetailTab_1344.test.tsx`, `DetailTab.test.tsx`)
  - ruff: clean, eslint: clean
  - Coverage: `owlbear_cockpit.view` 77%, `owlbear_cockpit.routes.mutation` 87%
- Key finding: the implementation includes 409 conflict refetch behavior (GET latest task before showing conflict modal). One durable test still encodes the pre-fix behavior and fails because it expects only two fetch calls.
- Builder boundary: this is test-contract ownership, not an implementation defect. Per builder protocol (no test edits), routed to test-writer.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable conflict/force-save assertion to match current AC5 behavior: 409 path performs refetch (`GET /api/tasks/{id}`) before showing conflict, then overwrite performs second edit POST; assert endpoint sequence/body rather than total call count only. | `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` | Failing test: `TestBuilderDiscovered > force-save fires API call (AC7) > clicking conflict-overwrite sends a second POST...`; error `expected ... called 2 times, but got 3` |
| 2 | test-writer | Add durable assertions for AC5/AC8 gaps noted in review using durable suites (typed payload/action body/404 clear and callback proof) so reviewer can validate without task-scoped-only proof. | `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`, `tests/test_cockpit_mutation_api.py` | Prior reviewer section “Required Follow-up” in task body plus current durable/frontend proof gap remains |

[[2026-05-05]]
## Test-Writer Notes (retry)

**Mode:** Step 1b.1 — direct-to-review advance (all new tests pass, no builder work needed)

**Files changed:**
- `tests/test_cockpit_mutation_api.py` — durable backend suite
- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` — durable frontend suite

**Changes made (surgical fill per builder Required Follow-up):**

**Follow-up #1 — Fix force-save call-count assertion:**
- `TestBuilderDiscovered > force-save fires API call (AC7)` updated: `toHaveBeenCalledTimes(2)` → 3; asserts 3-call sequence (POST 409, GET refetch, POST force-save) instead of total count only; added refetch GET assertion at call[1]

**Follow-up #2 — Durable proof for AC5/AC7/AC8 gaps:**
- Backend `TestFromAC_EditBodyParentSemantics` (5 tests): parent:null clears parent; body:"" clears body; body:null no-change; body omitted no-change; negative parent → 422
- Frontend `save payload typed fields (AC8)` (4 tests): depends_on as int[]; parent as int; parent as null; block_reason as string
- Frontend `action endpoint proofs (AC8)` (4 tests): unblock → POST /edit with block_reason:null; unclaim → POST /release; move-backward sends previous status 'backlog'; 404 calls onTaskCleared
- Frontend `onTaskUpdated callback (AC8)` (1 test): successful save calls onTaskUpdated with response task
- Frontend helpers added: `BOARD` fixture, `renderDetailWithBoard()`, `clickConfirm()`

**Quality evidence:**
- Python: 48 passed, 0 failed (tests/test_cockpit_mutation_api.py)
- Frontend: 43 passed, 0 failed (DetailTab.test.tsx)
- ruff: clean
- Commit: f7592274

**AC coverage (retry gaps):**
| Gap | Tests | Result |
|-----|-------|--------|
| AC7(a) parent:null clears | test_edit_parent_null_clears_parent | PASS |
| AC7(b) body:"" clears | test_edit_body_empty_string_clears_body | PASS |
| AC7(c) body:null/omit no-change | 2 tests | PASS |
| AC7(d) negative parent 422 | test_edit_negative_parent_returns_422 | PASS |
| AC8 typed payload | 4 frontend tests | PASS |
| AC8 action bodies + 404 clear | 4 frontend tests | PASS |
| AC8 onTaskUpdated | 1 frontend test | PASS |
| AC5 force-save 3-call sequence | fixed test | PASS |

All new tests PASS against current code → implementation complete, no builder work needed → advance to review.
[[2026-05-05]]
## Builder Notes
- Scope: verification-only builder pass after test-writer retry; no source or test edits in this pass.
- Files inspected for AC alignment: `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, `tests/test_cockpit_mutation_api_1344.py`, `tests/test_cockpit_mutation_api.py`, `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.

- Quality-runner evidence (fresh scoped run):
  - Python tests: 53 passed, 0 failed (`tests/test_cockpit_mutation_api_1344.py` + `tests/test_cockpit_mutation_api.py`)
  - Frontend tests: 54 passed, 0 failed (`DetailTab_1344.test.tsx` + `DetailTab.test.tsx`)
  - ruff: clean (4/4 files)
  - eslint: clean (4/4 files)
  - Coverage: `owlbear_cockpit.view` 77%, `owlbear_cockpit.routes.mutation` 87%

- Evidence summary:
  - AC2/AC3 semantics are covered in backend task + durable suites (parent-null clear, body-empty clear, body null/omit no-change, negative parent 422).
  - AC4/AC5/AC6/AC8 durable frontend proofs now present in `DetailTab.test.tsx` (typed payloads, action endpoint bodies incl. 404 clear path, callback invocation).
  - Conflict overwrite durable assertion reflects AC5 three-call sequence (`POST 409 -> GET refetch -> POST overwrite`).

- Commits in this builder pass:
  - None (verification-only pass; latest implementation/test commits were already present in task history).

- Post-task reflection:
  - Problem faced: task had a long retry chain with stale reviewer findings interleaved with newer durable-proof updates.
  - Workaround applied: used a fresh quality-runner scoped pass against both task-scoped and durable suites to re-baseline current truth.
  - Pattern discovered: for retry-heavy tasks, builder verification-only passes are safest when all required proofs are already committed and green.
  - Quality gap noted: module coverage remained below 90% on `view`/`routes.mutation`; this is visible for reviewer follow-up if strict coverage gating is enforced at review.

[[2026-05-05]]
## Review Evidence
### Scope
- Second review cycle. One prior `## Review Evidence` section already exists in task history, so loop-breaker routing applies on any remaining FAIL.
- Verified task-related commits exist via `.git/logs/**`: builder `3704a1a1`, test-writer `f7592274`.
- Full git diff / dirty-tree status was not available from this tool surface; small confidence deduction applied to TestFromAC immutability.

### Test Results
- Backend quality-runner retry: 53 passed, 0 failed, 0 skipped. Ruff clean. Coverage: overall 40%; `owlbear_cockpit.view` 77%; `owlbear_cockpit.routes.mutation` 87%.
- Frontend quality-runner: 54 passed, 0 failed, 0 skipped. ESLint clean. Coverage: `DetailTab.tsx` 92.1% statements / 89.49% branches / 93.63% lines; `Shell.tsx` was not exercised by the scoped frontend test files.

### Diagnostics
- VS Code diagnostics are not clean in `serve/cockpit/web/src/components/DetailTab.tsx`: invalid `variant="tertiary"` usages at lines 217, 294, 302, 305, 309, 322; missing required `name` props at 227, 254, 262, 271, 283; event-type mismatches at 232-233, 240-241, 259-260, 267-268, 276-277, 288-289.

### Findings
1. AC1 implementation defect remains on the block-reason clear path. The frontend posts `block_reason: t.blocked ? blockReason : null` at `serve/cockpit/web/src/components/DetailTab.tsx:144`. The route treats any non-`null` `block_reason` as the blocked-tag lifecycle branch (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py:213`, `:251-257`), but the view treats `""` as unblock and sets `blocked=False, block_reason=None` (`serve/cockpit/src/owlbear_cockpit/view.py:141-146`). Clearing the block-reason input can therefore leave stale `block:user` tag state while unblocking the task.
2. AC1 proof is still incomplete for list clear/omit semantics. Durable backend tests added parent/body coverage (`tests/test_cockpit_mutation_api.py:897-958`), but the only durable tags/depends_on tests still prove replacement/set behavior (`tests/test_cockpit_mutation_api.py:270`, `:294`). No test covers the clear/omit branches implemented in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:233-239`.
3. AC4/AC6 proof is still weak after the retry. The durable frontend payload tests render seeded tasks and immediately click save (`serve/cockpit/web/src/__tests__/DetailTab.test.tsx:631-704`), so they do not prove edited current values from the controlled fields drive the payload. The task-scoped callback test only proves `DetailTab` invokes `onTaskUpdated` (`serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:505-536`); no Shell test exercises the `onTaskUpdated -> setSelectedTask/refetchTasks()` branch implemented at `serve/cockpit/web/src/Shell.tsx:163-173`.
4. The changed frontend file is not type-clean in the editor. Current diagnostics in `serve/cockpit/web/src/components/DetailTab.tsx` show invalid PDS button variants, missing required `name` props on text controls, and event-type mismatches in the newly introduced controlled-input handlers.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1 | Backend body/parent semantics are green, but block-reason clear is internally inconsistent (`DetailTab.tsx:144`; `mutation.py:213`, `:251-257`; `view.py:141-146`) and tags/depends_on clear-omit semantics remain unproved (`tests/test_cockpit_mutation_api.py:270`, `:294` vs. `mutation.py:233-239`). | FAIL |
| 2 | Durable backend tests cover `parent:null` clear and negative parent 422 (`tests/test_cockpit_mutation_api.py:897-958`). | PASS |
| 3 | Durable backend tests cover `body:""` clear and `body:null/omitted` no-change (`tests/test_cockpit_mutation_api.py:912-943`). | PASS |
| 4 | The component uses controlled `value` props, but current-value payload proof is weak because the durable payload tests only submit seeded state (`serve/cockpit/web/src/__tests__/DetailTab.test.tsx:631-704`). | FAIL |
| 5 | Shared `runMutation()` implements success/409/422/404 handling (`serve/cockpit/web/src/components/DetailTab.tsx:108-123`), and the frontend suites cover action endpoints/bodies plus conflict and validation behavior (`serve/cockpit/web/src/__tests__/DetailTab.test.tsx:580-620`; `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:423-487`; `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:807-822`). | PASS |
| 6 | Shell wiring exists at `serve/cockpit/web/src/Shell.tsx:163-173`, but no durable or task-scoped test exercises that branch. | FAIL |
| 7 | Durable backend suite now covers `parent:null`, `body:""`, `body:null/omitted`, and negative parent (`tests/test_cockpit_mutation_api.py:897-958`). | PASS |
| 8 | Durable frontend suite proves typed payload shape, action bodies, and direct `onTaskUpdated` callback invocation (`serve/cockpit/web/src/__tests__/DetailTab.test.tsx:631-835`). | PASS |

### Deductions
- -0.14 AC1 block-reason clear implementation defect
- -0.10 AC1 tags/depends_on clear-omit proof gap
- -0.08 AC4 current-value payload proof gap
- -0.08 AC6 Shell-threading proof gap
- -0.06 active TS diagnostics in changed frontend file
- -0.02 no direct git diff / dirty-tree access from this tool surface

### Verdict
- Confidence: 0.68
- Verdict: FAIL -> backlog
- Action: second review failure. Remaining issues are a mix of live implementation defect and proof-design gaps, so loop-breaker routing applies.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-scope the retry to fix the block-reason clear contract and the TypeScript-invalid DetailTab control wiring before the task re-enters review. | serve/cockpit/web/src/components/DetailTab.tsx; serve/cockpit/src/owlbear_cockpit/routes/mutation.py; serve/cockpit/src/owlbear_cockpit/view.py | AC1; `DetailTab.tsx:144`, `:217`, `:227`, `:232`, `:254`, `:262`, `:271`, `:283`, `:294`, `:302`, `:305`, `:309`, `:322`; `mutation.py:213`, `:251-257`; `view.py:141-146` |
| 2 | architect | Refine the AC/test plan so the next retry explicitly proves tags/depends_on clear-omit semantics and Shell-level `onTaskUpdated -> setSelectedTask/refetchTasks()` behavior with discriminating tests that edit live field state before save. | tests/test_cockpit_mutation_api.py; serve/cockpit/web/src/__tests__/DetailTab.test.tsx; serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx; serve/cockpit/web/src/__tests__/Shell.test.tsx | AC1/AC4/AC6; `tests/test_cockpit_mutation_api.py:270`, `:294`, `:897-958`; `DetailTab.test.tsx:631-704`, `:835`; `DetailTab_1344.test.tsx:505-536`; `Shell.tsx:163-173` |
[[2026-05-05]]

## Architecture Re-scope (loop-breaker retry)

**Verdict: APPROVED → todo**

This is a loop-breaker re-entry after 2nd review failure. Architecture is sound (approved earlier). Three focused fixes remain:

### Defect 1 — Block-reason stale tag (AC1)

`_apply_block_kwargs` in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` uses `if block_reason is None:` for the unblock branch. But `CockpitView.edit_task()` uses `if block_reason:` (falsy check). When frontend sends `block_reason: ""` (user cleared the field), the route keeps/adds `block:user` tag while the view sets `blocked=False`. Stale tag results.

**Fix**: In `_apply_block_kwargs`, change the unblock check from `if block_reason is None:` to `if not block_reason:` — this makes empty string and None both trigger the unblock (remove `block:user` tag) path.

### Defect 2 — TypeScript diagnostic violations (NEW AC9)

`DetailTab.tsx` has 20+ compile errors:
- `variant="tertiary"` → PDS 3.34 only accepts `"primary" | "secondary"`. Replace with `variant="secondary"` for low-emphasis buttons.
- `PInputText`/`PTextarea` missing required `name` prop. Add `name={data-field-value}` matching each control's `data-field` attribute.
- Event handler type mismatch: PDS `onChange` fires `CustomEvent` where `target` can be null. `readControlValue()` must accept the PDS event type. Fix: widen signature to `(event: { target?: { value?: unknown } | null; detail?: { value?: unknown } | null })` or cast inside handlers.

### Defect 3 — Test proof gaps (AC4/AC6)

- **AC4**: Durable payload tests at `DetailTab.test.tsx:631-704` render seeded tasks and immediately click save. Reviewer requires tests that *drive live edits* (type into controlled fields) before save, proving current user input reaches the payload.
- **AC6**: Shell `onTaskUpdated → setSelectedTask + refetchTasks()` branch at `Shell.tsx:163-173` is untested. Need at least one integration test (may be in a new `Shell.test.tsx` or via a renderShell helper) proving the branch.

### Refined AC (retry)

1. `POST /api/tasks/{id}/edit` passes `body`, `parent`, `tags`, `depends_on`, and `block_reason` values through to `engine.edit_task()` with correct set/clear/omit semantics; `block_reason: ""` and `block_reason: null` both trigger unblock (remove `block:user` tag + set `blocked=False`); invalid values return 422, not uncaught exceptions. `(td:2)`
2. `parent: null` in the JSON request body clears the parent; negative values return 422. `(td:2)`
3. `body: ""` clears task body; `body: null` or field omitted means no change. `(td:2)`
4. `DetailTab` controlled inputs (title, priority, body, depends_on, parent, block_reason) save current user-edited values in the edit payload with correct types. Durable proof must drive live field edits (type new values) before save. `(td:2)`
5. `DetailTab` actions: unblock → POST `/edit` with `block_reason: null`; unclaim → POST `/release`; move-backward → POST `/move`. All handle 409 (refetch + show conflict), 422 (show validation message), 404 (deselect task via `onTaskCleared`). `(td:2)`
6. Successful edits/actions: `DetailTab` calls `onTaskUpdated(responseTask)` threaded from Shell; Shell updates `selectedTask` state and triggers `refetchTasks()` when title/priority/status/blocked changed. Durable proof must exercise the Shell handler branch. `(td:1)`
7. Durable backend tests cover: parent:null clears, body:"" clears, body:null/omitted no-change, negative parent 422. `(td:0)`
8. Durable frontend tests prove: typed JSON payload, action endpoint bodies, `onTaskUpdated` callback invocation. `(td:0)`
9. `DetailTab.tsx` zero TypeScript compile errors — PDS v3.34 compliance: no `variant="tertiary"` (use `"secondary"`), all PInputText/PTextarea include required `name` prop, event handlers type-safe for nullable `event.target`. `(td:1)`

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Architect response: proceed (defects are empirically verified by reviewer, not speculative)

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

[[2026-05-05]]
Architecture re-scope after 2nd review failure (loop-breaker). Three focused fixes: (1) _apply_block_kwargs normalize ""→unblock path, (2) DetailTab.tsx PDS 3.34 TS compliance (variant, name, event types), (3) AC4/AC6 durable proof must drive live edits + Shell handler test. Added AC9 for TS diagnostic gate. Challenger: FALLBACK.
[[2026-05-05]]
## Test-Writer Notes (retry 2)

**Files changed:**
- `tests/test_cockpit_mutation_api.py` — added 1 new failing test to `TestFromAC_EditBodyParentSemantics`
- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` — added `live field edits reach save payload (AC4)` describe block (3 tests)
- `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx` — new file with `TestFromAC_ShellOnTaskUpdated (AC6)` (3 tests)

**Changes per Required Follow-up:**

**Backend gap (AC1):** `test_edit_empty_string_block_reason_clears_blocked_state` — proves `block_reason: ""` must unblock the task (remove `block:user` tag, set `blocked=False`). Currently **FAILS** because `_apply_block_kwargs` checks `if block_reason is None:` (builder must change to `if not block_reason:`).

**AC4 live-edit proof (3 tests):** Fire PDS-compatible `CustomEvent('input', { detail: { value: '...' } })` on controlled fields before save. Proves current user-edited value (not seeded prop) reaches payload: typed title, typed parent id, cleared block_reason. All **PASS** — implementation is already state-driven; prior tests only proved seeded state.

**AC6 Shell integration proof (3 tests, Shell_1344.test.tsx):** End-to-end Shell + real DetailTab test. Selects task 42 via KanbanBoard mock, waits for task load, triggers save, asserts `refetchTasks()` called when title changes (AC6 board-sync branch); asserts NOT called when only body changes (stable-list branch). All **PASS** — Shell.tsx:163-173 is already implemented; no prior test exercised that branch.

**Quality evidence:**
- Backend: 48 passed, 1 FAILED (new AC1 test) — ruff: clean
- Frontend: DetailTab.test.tsx 46/46 passed; Shell_1344.test.tsx 3/3 passed — eslint: clean

**AC coverage table (retry gaps):**
| Gap | Tests | Result |
|-----|-------|--------|
| AC1 block_reason:""→unblock | test_edit_empty_string_block_reason_clears_blocked_state | FAIL (RED ✓ — needs builder) |
| AC4 live title edit | typed title overrides seeded value | PASS (proof) |
| AC4 live parent edit | typed parent id overrides null | PASS (proof) |
| AC4 live block_reason clear | cleared field sends "" in payload | PASS (proof) |
| AC6 setSelectedTask | field-id visible after onTaskUpdated | PASS (proof) |
| AC6 refetchTasks on title change | refetchTasksSpy called | PASS (proof) |
| AC6 no refetch on body-only change | stable-list branch | PASS (proof) |

Builder remaining: fix `_apply_block_kwargs` (AC1), fix TS violations in DetailTab.tsx (AC9). Commit: 60168ef3.
[[2026-05-05]]
## Builder Notes
- Scope: verification-complete builder pass for retry-2 directives (AC1 unblock semantics + AC9 TypeScript/PDS compliance) on existing implementation.
- Source inspection confirms:
  - `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` `_apply_block_kwargs` uses `if not block_reason` (empty-string/null unblock path).
  - `serve/cockpit/web/src/components/DetailTab.tsx` uses supported PDS button variants, required `name` props, and typed control-value extraction compatible with CustomEvent input payloads.

- Quality-runner evidence (scoped, fresh):
  - Python tests: 54 passed, 0 failed
    - `tests/test_cockpit_mutation_api_1344.py`
    - `tests/test_cockpit_mutation_api.py`
  - Frontend tests: 60 passed, 0 failed
    - `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx` (11)
    - `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` (46)
    - `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx` (3)
  - Total: 114 passed, 0 failed
  - Lint: `ruff` clean, `eslint` clean
  - Coverage: `owlbear_cockpit.routes.mutation` 87%, `owlbear_cockpit.view` 77% (reported for transparency)

- Evidence summary:
  - RED item from retry-2 (`test_edit_empty_string_block_reason_clears_blocked_state`) is satisfied in current code and test suite is now green.
  - AC4/AC6 durable-proof additions from retry-2 are green (`DetailTab.test.tsx`, `Shell_1344.test.tsx`).
  - No builder edits required in this pass; this is a verification-and-advance completion.

- Commit(s):
  - None in this pass (no file changes).

- Post-task reflection:
  - Long retry chains can leave stale findings in task history; a single fresh scoped quality-runner pass is the safest truth source for builder closeout.
  - Keeping this pass verification-only avoided unnecessary churn once all scoped tests and lint were demonstrably green.
[[2026-05-05]]
## Review Evidence
### Scope
- Claimed task 1344 in review.
- Max depth is td:2, so I ran parallel quality-runner backend/frontend passes plus a code-reader pass.
- Verified task-related commits exist in `.git/logs/**`: builder `3704a1a1`, test-writer `f7592274`, test-writer retry `60168ef3`.
- `DetailTab` usage tracing shows only Shell + test callers in current scope.
- The task file already contains two prior `## Review Evidence` sections (`.owlbear/kanban/tasks/1344-fix-cockpit-detail-edit-workflow-contract.md:143` and `:277`), so any remaining FAIL stays on backlog under loop-breaker routing.
- Full git diff / dirty-tree status was not available from this tool surface; small confidence deduction applied to TestFromAC immutability.

### Test Results
- Backend quality-runner: 54 passed, 0 failed, 0 skipped; ruff clean; coverage overall 40%, `owlbear_cockpit.view` 77%, `owlbear_cockpit.routes.mutation` 87%.
- Frontend quality-runner: 60 passed, 0 failed, 0 skipped; eslint clean; coverage overall 74.19%, `DetailTab.tsx` 93.12%, `Shell.tsx` 83.96%.
- VS Code diagnostics: no errors in `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, or `serve/cockpit/src/owlbear_cockpit/view.py`.

### Findings
1. AC1 proof gap remains on list clear/omit semantics. The route implements tags/depends_on full-replacement behavior through `_apply_list_diff()` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:196`, `:204`, `:224-242`, including the omit branch at `:233` and add/remove branches at `:240-242`. Durable backend coverage still only proves replacement/set paths at `tests/test_cockpit_mutation_api.py:270` and `:294`. Search found no durable empty-list or omitted-field assertions for either `tags` or `depends_on`, so significant edit-contract branches remain unproved.
2. AC4 proof is incomplete. The save payload includes live `priority` and `depends_on` values in production at `serve/cockpit/web/src/components/DetailTab.tsx:140`, `:142`, with controls at `:245` and `:264`. Durable live-edit tests now drive body/title/parent/block_reason via CustomEvent at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:560`, `:879`, `:907`, and `:932`, but `priority` and `depends_on` appear only as render-presence checks at `:175` and `:186`. The refined AC requires durable proof that current user edits for all controlled fields reach the payload before save.
3. AC6 still has a false-green proof. Shell updates `selectedTask` and conditionally refetches at `serve/cockpit/web/src/Shell.tsx:165-173`. The retry suite proves the refetch branch at `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx:219-244` and the body-only no-refetch branch at `:250-273`, but the supposed selectedTask-refresh proof at `:185-213` only reasserts stable `field-id == 42` at `:198` and `:213`. That assertion would still pass if `setSelectedTask(updatedTask)` at `serve/cockpit/web/src/Shell.tsx:165` were removed, because the selected task id stays 42. The updated-title fixture exists at `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx:99` and is never asserted.
4. Test quality is WEAK under Step 5.3 because AC6 currently relies on a non-discriminating assertion, and AC4 leaves live priority/depends_on edits untested. With any WEAK dimension, reviewer workflow requires FAIL.

### Security / Data Safety
- No security or data-safety issues found in the scoped files.

### AC Compliance
| AC | Evidence | Status |
|----|----------|--------|
| 1 | Body/parent/block_reason semantics are covered (`tests/test_cockpit_mutation_api.py:897-969`), but tags/depends_on clear+omit branches in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:196-242` are still unproved beyond set-path tests at `tests/test_cockpit_mutation_api.py:270` and `:294`. | FAIL |
| 2 | Task tests prove `parent:null` never raises `TypeError`, clears parent, and negative parent returns 422 at `tests/test_cockpit_mutation_api_1344.py:128`, `:149`, and `:172`. | PASS |
| 3 | Task + durable tests prove `body:""` clears and `body:null/omitted` preserves content at `tests/test_cockpit_mutation_api_1344.py:209`, `:233` and `tests/test_cockpit_mutation_api.py:912`, `:927`, `:943`. | PASS |
| 4 | Durable live-edit proof exists for body/title/parent/block_reason at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:560`, `:879`, `:907`, `:932`, but not for live priority/depends_on edits; only render-presence checks exist at `:175` and `:186`. | FAIL |
| 5 | Confirmed endpoint/body/error handling remains covered by `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:721`, `:752`, `:777`, `:807` and `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:381`, `:423`, `:457`. | PASS |
| 6 | `DetailTab` callback invocation is covered at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:835` and `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx:505`, and Shell refetch predicates are partly covered at `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx:219-273`, but the selectedTask update branch at `serve/cockpit/web/src/Shell.tsx:165` is not discriminately proven. | FAIL |
| 7 | Durable backend suite covers `parent:null`, `body:""`, `body:null/omitted`, and negative parent at `tests/test_cockpit_mutation_api.py:897`, `:912`, `:927`, `:943`, `:958`. | PASS |
| 8 | Durable frontend suite proves typed payload shape, action endpoint bodies, and direct `onTaskUpdated` callback invocation at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:631`, `:655`, `:696`, `:721`, `:752`, `:777`, `:807`, `:835`. | PASS |
| 9 | `get_errors` reported no current diagnostics in `serve/cockpit/web/src/components/DetailTab.tsx`, and scoped frontend lint is clean. | PASS |

### Deductions
- -0.08 AC1 tags/depends_on clear+omit proof gap
- -0.06 AC4 missing live priority/depends_on edit proof
- -0.06 AC6 false-green selectedTask assertion
- -0.02 no direct diff / dirty-tree visibility from this tool surface

### Verdict
- Confidence: 0.78
- Verdict: FAIL -> backlog
- Action: loop-breaker reject. Current code is green, but the refined AC is still under-proven and one proof path is non-discriminating. This is a proof-quality failure, not a fresh builder implementation failure.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Create a proof-only retry that explicitly requires durable backend tests for `tags=[]` / `depends_on=[]` clear semantics and omitted-field no-change semantics, then route that retry to the test-writer. | `tests/test_cockpit_mutation_api.py`; `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | AC1; route branches at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:196-242`; only set-path tests at `tests/test_cockpit_mutation_api.py:270`, `:294` |
| 2 | architect | Refine the frontend proof plan so durable tests drive live `priority` and `depends_on` edits before save and add a discriminating Shell assertion that proves `setSelectedTask(updatedTask)` actually updates rendered task state (for example by asserting updated title, not stable id). | `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`; `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx`; `serve/cockpit/web/src/Shell.tsx`; `serve/cockpit/web/src/components/DetailTab.tsx` | AC4/AC6; live-edit coverage currently stops at `DetailTab.test.tsx:560`, `:879`, `:907`, `:932`; Shell false-green at `Shell_1344.test.tsx:185-213` while state update lives at `Shell.tsx:165-173` |
[[2026-05-05]]

## Architecture Re-scope (proof-only retry 2)

**Verdict: APPROVED → todo**

Loop-breaker proof-only retry. All source code is green (114 tests pass). Three test-quality gaps remain from 3rd review cycle. No implementation changes needed — test-writer adds/fixes durable tests only.

### Gap 1 — AC1: tags/depends_on clear+omit proof (backend)

`_apply_list_diff()` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:224-242` handles:
- `desired is None` → no-op (omit semantics)
- `desired = []` → remove all current items (clear semantics)

Durable tests at `tests/test_cockpit_mutation_api.py:270` and `:294` only cover replacement/set (non-empty list). **Required new durable tests:**
- `tags=[]` on a task with existing tags → response shows empty tags list
- `depends_on=[]` on a task with existing deps → response shows empty deps list
- tags field omitted from request → original tags preserved
- depends_on field omitted from request → original deps preserved

### Gap 2 — AC4: live priority/depends_on edit proof (frontend)

Existing live-edit tests in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:879-950` prove title, parent, and block_reason. Missing: priority (PSelect at `DetailTab.tsx:248`) and depends_on (PInputText at `DetailTab.tsx:264`). **Required new durable tests:**
- Fire PDS-compatible `CustomEvent('input', { detail: { value: 'critical' } })` on `[data-field="priority"]` before save → assert payload `priority === 'critical'`
- Fire `CustomEvent('input', { detail: { value: '10,20' } })` on `[data-field="depends_on"]` before save → assert payload `depends_on === [10, 20]`

### Gap 3 — AC6: discriminating Shell assertion (frontend)

Test at `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx:185-213` asserts `field-id == 42` after save. Task id stays 42 regardless of whether `setSelectedTask(updatedTask)` fires. The fixture `TASK_42_UPDATED` has `title: 'Updated Title From Server'`. **Fix:** Replace (or supplement) the stable-id assertion with `expect(container.querySelector('[data-field="title"]')?.getAttribute('value')).toBe('Updated Title From Server')` — this proves Shell actually passed the updated task back to DetailTab.

### Test Depth (unchanged from prior approval)
- AC1: `(td:2)` — backend clear/omit
- AC4: `(td:2)` — frontend live-edit
- AC6: `(td:1)` — Shell assertion fix
- AC9: `(td:1)` — already PASS
- Test-writer: PROCEED (proof-only, all GREEN expected against current code)

### Challenge Results
- Challenger: SKIPPED (proof-only retry, no design decisions)

### Routing Note
This is a proof-only pass. All tests should PASS immediately against current code (no RED phase needed). Test-writer should use Step 1b.1 (direct-to-review advance) if all new tests pass without builder changes.

[[2026-05-05]]
Architecture re-scope (proof-only retry 2). Three test-quality gaps from 3rd review: (1) backend durable tests for tags/depends_on clear+omit semantics, (2) frontend live-edit proof for priority/depends_on fields, (3) fix non-discriminating Shell assertion to check updated title not stable id. No source changes needed — all tests should PASS against current code. Challenger: SKIPPED (proof-only).
[[2026-05-05]]
## Test-Writer Notes (retry 3 — proof-only)

**Mode:** Step 1b.1 — direct-to-review advance (all new tests pass, no builder work needed)

**Files changed:**
- `tests/test_cockpit_mutation_api.py` — added `TestFromAC_EditListClearOmit` class (4 tests)
- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` — added 2 live-edit tests in `live field edits reach save payload (AC4)` block
- `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx` — updated `TASK_42_UPDATED` fixture + fixed discriminating assertion in first test

**Changes per reviewer gaps (3rd review Required Follow-up):**

**Gap 1 — AC1 tags/depends_on clear+omit proof (backend):**
New class `TestFromAC_EditListClearOmit` (4 tests):
- `test_edit_tags_empty_list_clears_all_tags` — `tags=[]` removes all existing tags
- `test_edit_depends_on_empty_list_clears_all_deps` — `depends_on=[]` removes all existing deps
- `test_edit_tags_field_omitted_preserves_existing_tags` — omitted field leaves tags unchanged
- `test_edit_depends_on_field_omitted_preserves_existing_deps` — omitted field leaves deps unchanged

**Gap 2 — AC4 live priority/depends_on edit proof (frontend):**
2 new tests in `live field edits reach save payload (AC4)`:
- `typed priority value overrides seeded priority in save payload` — fires `change` CustomEvent on `p-select[data-field="priority"]`; asserts payload `priority === 'critical'`
- `typed depends_on value overrides seeded value in save payload` — fires `input` CustomEvent on `p-input-text[data-field="depends_on"]`; asserts payload `depends_on === [10, 20]`

**Gap 3 — AC6 discriminating Shell assertion (frontend):**
- Updated `TASK_42_UPDATED.updated` to `'2026-01-02T00:00:00+00:00'` (differs from `TASK_42_DETAIL.updated`)
- Changed first test assertion from stable `field-id == 42` to `p-input-text[data-field="title"].value === 'Updated Title From Server'`
- The different `updated` timestamp causes DetailTab's `useEffect([task?.id, task?.updated])` to fire, re-syncing `title` state; assertion fails if `setSelectedTask(updatedTask)` is not called

**Quality evidence:**
- Backend: 58 passed, 0 failed (`test_cockpit_mutation_api.py` + `test_cockpit_mutation_api_1344.py`)
- Frontend: 51 passed, 0 failed (`DetailTab.test.tsx` 48 + `Shell_1344.test.tsx` 3)
- ruff: clean
- Commit: 2addc832

**AC coverage (retry gaps):**
| Gap | Tests | Result |
|-----|-------|--------|
| AC1 tags clear | test_edit_tags_empty_list_clears_all_tags | PASS |
| AC1 deps clear | test_edit_depends_on_empty_list_clears_all_deps | PASS |
| AC1 tags omit | test_edit_tags_field_omitted_preserves_existing_tags | PASS |
| AC1 deps omit | test_edit_depends_on_field_omitted_preserves_existing_deps | PASS |
| AC4 live priority | typed priority value overrides seeded priority | PASS |
| AC4 live depends_on | typed depends_on value overrides seeded value | PASS |
| AC6 discriminating Shell | updated title asserted (not stable id) | PASS |

All new tests PASS against current code → implementation complete, no builder work needed → advance to review.
[[2026-05-05]]
## Builder Notes
- Scope: verification-only builder pass for task #1344 after test-writer proof-only retry; no source or test edits in this pass.
- Files validated: `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, `tests/test_cockpit_mutation_api_1344.py`, `tests/test_cockpit_mutation_api.py`, `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`, `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx`.

- Quality-runner evidence (fresh scoped verification):
  - Backend tests: 58 passed, 0 failed (`tests/test_cockpit_mutation_api_1344.py`, `tests/test_cockpit_mutation_api.py`)
  - Frontend tests: 62 passed, 0 failed (`DetailTab_1344.test.tsx`, `DetailTab.test.tsx`, `Shell_1344.test.tsx`)
  - Total: 120 passed, 0 failed, 0 skipped
  - Lint: `ruff` clean, `eslint` clean
  - Coverage (reported): `owlbear_cockpit.view` 78%, `owlbear_cockpit.routes.mutation` 87%

- Evidence summary:
  - AC1 proof-only backend additions for tags/depends_on clear+omit semantics are green in durable tests.
  - AC4 durable live-edit proof for `priority` and `depends_on` is green.
  - AC6 discriminating Shell assertion (updated title via `onTaskUpdated`) is green.
  - No further builder implementation changes are required in current task scope.

- Commit(s):
  - None in this pass (verification-only; latest implementation/proof commits already present in task history).

- Post-task reflection:
  - Long retry chains can leave stale findings in body history; a fresh scoped quality-runner run is the most reliable closeout check.
  - Keeping this pass verification-only avoided unnecessary churn once the proof-only gaps were closed.
  - Coverage is still below 90% for `view`/`routes.mutation`; recorded here for reviewer visibility while functional and lint gates are green.
[[2026-05-05]]
## Review Evidence
### Scope
- Claimed task 1344 in review.
- Max depth is td:2. Parallel fan-out attempted with quality-runner plus code-reader; code-reader returned no response, so I completed the required sequential fallback using fresh quality-runner runs, manual code reads, diagnostics, and an adjacent backend regression pass.
- Verified task-related commit presence in `.git/logs/refs/heads/dev` at lines 1867, 1872, 1876, and 1882 for builder `3704a1a1` and test-writer commits `f7592274`, `60168ef3`, and `2addc832`.
- Full git diff and dirty-tree status were not available from this tool surface; small confidence deduction applied to TestFromAC immutability and contamination checks.

### Test Results
- Backend quality-runner: 58 passed, 0 failed, 0 skipped. Ruff clean. Coverage: `owlbear_cockpit.view` 78%, `owlbear_cockpit.routes.mutation` 87%.
- Frontend quality-runner: 62 passed, 0 failed, 0 skipped. ESLint clean. Coverage: `DetailTab.tsx` 94.02%, `Shell.tsx` 87.17%.
- Adjacent backend regression: `tests/test_cockpit_routes.py` 8 passed, 0 failed. Ruff clean.
- `get_errors` reported no diagnostics in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/Shell.tsx`, or the scoped test files.

### Findings
- No blocking findings.

### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in the current task test files.
- The latest task-related source commit is builder `3704a1a1`; later task-related commits found in git logs are test-writer commits only. With direct diff unavailable, this remains a small-confidence rather than a blocking concern.

### AC Compliance
| AC | Evidence | Status |
|----|----------|--------|
| 1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` `_build_edit_kwargs`, `_apply_list_diff`, and `_apply_block_kwargs` implement field set/clear/omit and block-user tag handling at lines 182, 224, 245, and 279. Durable backend tests cover empty-string block clear plus tags and depends_on clear and omit at `tests/test_cockpit_mutation_api.py` lines 969, 1004, 1021, 1038, and 1055. Adjacent block-user lifecycle and conflict regressions stay green at `tests/test_cockpit_routes.py` lines 221, 242, 266, 312, and 346. | PASS |
| 2 | Durable backend tests prove parent null clears and negative parent returns 422 at `tests/test_cockpit_mutation_api.py` lines 897 and 958; `serve/cockpit/src/owlbear_cockpit/view.py` `edit_task` forwards parent unless unset and validates negative ints before calling the engine. | PASS |
| 3 | Durable backend tests prove body empty-string clears and body null or omitted preserves body at `tests/test_cockpit_mutation_api.py` lines 912, 927, and 943; route and view tri-state handling is implemented in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` and `serve/cockpit/src/owlbear_cockpit/view.py`. | PASS |
| 4 | `serve/cockpit/web/src/components/DetailTab.tsx` uses state-driven fields and task resync at lines 45 through 58, with controlled inputs at lines 233, 242, 261, 270, 280, and 293 and payload assembly at line 136. Durable live-edit tests prove body, title, parent, block_reason, priority, and depends_on use current user-edited values at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` lines 560, 570, 869, 896, 922, 949, and 976. | PASS |
| 5 | `runMutation` implements success, 409, 422, and 404 handling at `serve/cockpit/web/src/components/DetailTab.tsx` line 99 and `handleConfirm` dispatches unblock, unclaim, and move at line 162. Durable tests prove unblock, release, move request bodies, and 404 clear at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` lines 721, 752, 777, and 807; task-scoped tests prove 409 conflict UI and 422 validation UI at `serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx` lines 423 and 457; durable conflict flow proves refetch GET plus overwrite POST at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` line 580. | PASS |
| 6 | Shell threads `onTaskUpdated` through `DetailTab` at `serve/cockpit/web/src/Shell.tsx` lines 163 through 173. Durable integration tests prove selectedTask refresh, refetch on list-affecting changes, and no refetch on body-only changes at `serve/cockpit/web/src/__tests__/Shell_1344.test.tsx` lines 188, 227, and 258. | PASS |
| 7 | Durable backend gap coverage is present and green in `tests/test_cockpit_mutation_api.py` lines 897, 912, 927, 943, and 958. | PASS |
| 8 | Durable frontend suite proves typed payloads, action request bodies, and direct callback invocation at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` lines 631, 655, 696, 721, 752, 777, 807, and 835, plus live-edit proofs at lines 869, 896, 922, 949, and 976. | PASS |

### Diagnostics Gate
- Refined AC9 also passes: `get_errors` reported no current diagnostics in `DetailTab.tsx` or `Shell.tsx`, and frontend quality-runner reported eslint clean.

### Informational
- Module-level coverage remains below 90% in `Shell.tsx`, `owlbear_cockpit.view`, and `owlbear_cockpit.routes.mutation`, but the changed paths for this task are directly exercised by the scoped and durable suites. Under diff-scoped review this is residual debt, not a blocker.
- Conflict-overwrite call sequence is proven, but the current AC does not explicitly gate preservation of pre-conflict local edits after the 409 refetch. I am treating that as residual risk rather than a fail because it is not traceable to the current AC.

### Deductions
- -0.03 code-reader returned no response; manual sequential fallback completed
- -0.02 no direct git diff or dirty-tree status from this tool surface
- -0.01 module-level coverage below 90 outside the diff-scoped changed lines

### Verdict
- Confidence: 0.94
- Verdict: PASS
- Action: advance to docs
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` edit-route Notes column was missing tri-state body/parent/block_reason semantics added by this task. Updated. |
| 2 | Module docstrings | Yes | Updated | `EditRequest` docstring in `routes/mutation.py` did not document the tri-state field semantics (`body:""` clear, `parent:null` clear, `block_reason:""`/null unblock). Updated. `view.edit_task()` single-line docstring remains accurate. |
| 3 | External attribution | No | N/A | No external patterns cited in builder/test-writer notes. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` slug linked from task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**` and `serve/cockpit/web/src/**` — both contain changed files. Footer updated from `(a2885895)` → `(30298a83)` (current HEAD). |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | IN (docstring) | Updated `EditRequest` docstring |
| `serve/cockpit/src/owlbear_cockpit/view.py` | IN (docstring) | No change needed — single-line docstring accurate |
| `serve/cockpit/web/src/components/DetailTab.tsx` | OUT | N/A |
| `serve/cockpit/web/src/Shell.tsx` | OUT | N/A |
| `tests/test_cockpit_mutation_api_1344.py` | OUT | N/A |
| `tests/test_cockpit_mutation_api.py` | OUT | N/A |
| `serve/cockpit/README.md` | IN | Updated edit-route notes |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/cockpit/README.md`
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` (docstring only)
- `share/diagrams/cockpit.excalidraw` (footer only)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1344-*` scratch files existed)
[[2026-05-05]]
## Audit\n\n### AC Verification\n| AC | Evidence | Status |\n|----|----------|--------|\n| 1 | Backend route set/clear/omit + block-reason unblock path green in durable tests (tests/test_cockpit_mutation_api.py:897-1055); adjacent lifecycle regressions green (test_cockpit_routes.py) | PASS |\n| 2 | Durable tests prove parent:null clears + negative parent 422 (tests/test_cockpit_mutation_api.py:897, :958) | PASS |\n| 3 | Durable tests prove body:"" clears + body:null/omitted no-change (tests/test_cockpit_mutation_api.py:912, :927, :943) | PASS |\n| 4 | Controlled inputs + live-edit proof for all fields including priority/depends_on (DetailTab.test.tsx:869-976) | PASS |\n| 5 | runMutation handles 409/422/404; durable tests prove action bodies + conflict refetch 3-call sequence (DetailTab.test.tsx:580-822) | PASS |\n| 6 | Shell onTaskUpdated threading + discriminating title-update assertion in Shell_1344.test.tsx:188-273 | PASS |\n| 7 | Durable backend suite covers parent:null, body:"", body:null/omitted, negative parent (tests/test_cockpit_mutation_api.py:897-958) | PASS |\n| 8 | Durable frontend proves typed payloads, action bodies, callback invocation (DetailTab.test.tsx:631-835) | PASS |\n| 9 | get_errors clean for DetailTab.tsx; eslint clean; no TS diagnostics (reviewer confirmed) | PASS |\n\n### Test Results\n- Backend: 58 passed, 0 failed (fresh scoped run)\n- Frontend: 62 passed, 0 failed (fresh scoped run)\n- Full suite: 4590 passed, 213 failed (all failures from other tasks; zero 1344-related regressions)\n- Lint: ruff clean, eslint clean\n\n### Commit Integrity\n- builder 3704a1a1: feat: complete cockpit detail edit workflow contract\n- test-writer f7592274, 60168ef3, 2addc832: three test iterations\n- doc-writer 61f69e99: docs update (README, docstring, diagram footer)\n\n### Architect Quality: 3/5\nOriginal 8-line AC was domain-appropriate and specific about contracts, but missed the block-reason clear edge case and TS diagnostic gate. Required 2 architecture re-scopes to converge. Complex cross-stack task (backend route + view + React component + Shell integration) partially explains iteration count.\n\n### Deduction Breakdown\n- -0.03 AC quality score 3/5\n- -0.01 terminal instability prevented fresh full-suite execution; relied on recent full-suite output file + fresh scoped runs\n\n### Confidence: 0.96\n### Action: archive