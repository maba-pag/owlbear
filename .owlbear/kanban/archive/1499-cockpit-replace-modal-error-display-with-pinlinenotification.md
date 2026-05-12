---
id: 1499
title: 'Cockpit: Replace modal error display with PInlineNotification'
status: archived
priority: needed
created: 2026-05-12T02:38:27.712681+00:00
updated: 2026-05-12T09:53:15.758801+00:00
tags:
  - cockpit
  - frontend
  - ux
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Swap plain PText error rendering in ArchivalModal and ResolveModal for PDS PInlineNotification with retry action button.

## Acceptance Criteria
- ArchivalModal renders PInlineNotification (state='error') on 409/422/500/network failure
- ResolveModal renders PInlineNotification (state='error') on submission failure
- PInlineNotification shows actionLabel='Retry' with actionIcon='reset' for retryable errors (409, network)
- PInlineNotification shows no action button for non-retryable errors (422 validation)
- actionLoading=true while retry is in progress
- Notification dismissed on successful retry or manual dismiss
- Existing error test assertions updated for new component selectors

## Source
Research doc: .owlbear/research/cockpit-mutation-error-banner.md (task #1494)
2026-05-12T05:52:57+00:00
## Research
- Research doc: .owlbear/research/cockpit-inline-notification-modal.md
- Sources: 6 studied, 4 high-relevance (PDS API/examples docs, PDS React wrapper source, local modal implementations)
- Recommendation: Component swap with structured error state {message, retryable}; PInlineNotification props-based rendering; 5 test files need migration from .textContent to JS property access (confidence: 0.72)
- Follow-up tasks created: none — task #1499 itself is the implementation task, AC already concrete
- Decision requests: none (T1 — component swap within existing patterns)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.43)
- Key challenges: (1) 409 retry semantics — expectedUpdated prop stale after refresh, retry would 409 again; (2) test blast radius understated — 5 files not 3, PdsMigration.test.tsx missed; (3) focus trap blind spot — getFocusableElements() needs p-inline-notification added; (4) ResolveModal needs new state machine, not just component swap
- Researcher response: accepted all four — revised confidence 0.82→0.72, added §3f focus trap section, expanded §3e test file inventory, documented 409 mitigation options in §3d
2026-05-12T06:08:54+00:00

## Refined Acceptance Criteria

_Replaces original AC. Refined by architect after codebase inspection and challenger review._

- AC-1: `ArchivalModal.handleSubmit()` renders `<PInlineNotification state="error" data-testid="archival-error">` on HTTP 409, 422, 500+, catch(network), or client-side validation failure (invalid refs); `description` prop carries the error detail from `getResponseErrorMessage()` or validation string
- AC-2: `ResolveModal.handleSubmit()` renders `<PInlineNotification state="error" data-testid="resolve-error">` on HTTP 404, 409, 422, 500+, or catch(network); `description` prop carries the error detail from `getResponseErrorMessage()`
- AC-3: Retryable errors in both modals show `actionLabel="Retry"`, `actionIcon="reset"`, `onAction` re-invokes `handleSubmit()`: ArchivalModal (500+, network); ResolveModal (500+, network)
- AC-4: Non-retryable errors render PInlineNotification without action button: ArchivalModal (409, 422, client-side validation); ResolveModal (404, 409, 422)
- AC-5: `ArchivalModal` and `ResolveModal` set `actionLoading={isSubmitting}` on PInlineNotification while retry `handleSubmit()` is in-flight
- AC-6: `ArchivalModal` and `ResolveModal` dismiss notification on (a) successful mutation (`setError(null)`), (b) `onDismiss` click (`setError(null)`); ArchivalModal also clears error on reason-change (existing behavior)
- AC-7: `ArchivalModal.getFocusableElements()` selector adds `p-inline-notification` to enable Tab traversal to the notification host element
- AC-8: Test assertions migrate to PInlineNotification: ArchivalModal.test.tsx and ArchivalModal.error-body.test.tsx switch `.textContent` to JS property access (`description`, `state`); ErrorContract.test.tsx switches `.textContent` to property access; ResolveModal.test.tsx updates element selector; PdsMigration.test.tsx updates tag-name checks from `p-text` to `p-inline-notification`

## Builder Guidance

- **ResolveModal status-code branching:** Current code treats all `!res.ok` identically. Add status-code branching (mirror ArchivalModal pattern) to support AC-2/AC-3/AC-4 differentiation. Endpoint contract (routes/decisions.py): 404 (not found/file error), 409 (already resolved), 422 (invalid ID), 500+ (server error).
- **409 is NON-retryable in ArchivalModal:** `expectedUpdated` prop is frozen at menu-open time in KanbanBoard.tsx (line ~199-202). Board tests assert this frozen behavior. Retry with stale OCC token → 409 again. Show dismiss-only notification.
- **409 is NON-retryable in ResolveModal:** 409 means DR is already resolved — retry is semantically meaningless.
- **Error state shape:** Replace `useState<string | null>` with `useState<{ message: string; retryable: boolean } | null>` or equivalent discriminated state to drive actionLabel rendering.
- **Focus trap limitation:** PInlineNotification renders buttons inside Shadow DOM. Adding host element to `getFocusableElements()` enables Tab to reach the component; internal button focus is managed by PDS.

Proof bundle: behavioral

2026-05-12T06:09:24+00:00
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two modals, same error-display pattern swap — single UX concern |
| Interface clarity | PASS (refined) | Original AC had 5 issues: vague ResolveModal scope, 409 incorrectly retryable, missing focus trap, missing client-side validation migration, underspecified test migration. All addressed in Refined AC. |
| Dependency correctness | PASS | No cross-deps needed; #1498 (Shell PBanner) is independent per parent arch review |
| Module layering | PASS | PInlineNotification imported from PDS; no upward imports; error state stays component-local |
| TDD compliance | PASS | Sibling #1500 (tests) exists; AC-8 covers existing test migration; behavioral bundle ensures TDD cycle |
| KISS/YAGNI | PASS | Component swap + error state shape change; no new modules, abstractions, or wrappers |
| Premise challenge | PASS | Current PText error display lacks retry affordance, dismiss, and loading state. PInlineNotification provides all three out-of-box. PDS 4.1.0 already installed. |
| Pattern consistency | PASS | Follows existing error-handling pattern in ArchivalModal (status-code branching); extends to ResolveModal |
| Security surface | PASS | No new system boundaries. Error messages already sanitized via getResponseErrorMessage() |
| Single domain | PASS | Frontend/UX only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| ArchivalModal 409 retry | Stale OCC token → 409 loop | N/A | Yes — AC-4 makes 409 non-retryable | User sees dismiss-only error, re-opens modal |
| ResolveModal 409 | DR already resolved | N/A | Yes — AC-4 makes 409 non-retryable | User sees error, closes modal |
| ResolveModal 404 | DR file not found | N/A | Yes — AC-4 non-retryable | User sees error |
| Shadow DOM focus | PInlineNotification buttons unreachable from light DOM | N/A | Partial — AC-7 adds host to selector; PDS manages internal focus | Tab reaches component; PDS handles internal traversal |

### Design Diverge

- Trigger: skipped — single valid approach (component swap with structured error state). Research already evaluated alternatives in parent #1494.

### Challenge Results

- Challenger: ac-quality / reconsider (confidence: 0.46)
- Key findings: (1) 409 NOT retryable — OCC token frozen at menu-open, board tests assert this; (2) ResolveModal endpoint returns 404/409 in addition to 422/500+; (3) AC-5/AC-6 lacked B1 component scoping; (4) client-side validation errors missing from migration scope; (5) test migration surface overstated
- Architect response: accepted all 5 findings. Rewrote AC-1 through AC-8 with full status-code matrices, component-scoped naming, and precise test-file migration descriptions. 409 reclassified from retryable to non-retryable in both modals.

### Proof-Bundle Validation

- Planner assignment: (none)
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined all 7 original AC lines into 8 precise, B1/B2-compliant lines. Reclassified 409 as non-retryable (critical fix from challenger). Added ResolveModal status-code matrix (404/409/422/500+/network). Added focus trap update (AC-7). Added builder guidance for implementation details. Assigned proof bundle: behavioral. Advanced backlog → todo.
2026-05-12T06:20:55+00:00
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`

**Class:** `TestFromAC_PInlineNotificationModals`

**Tests per category (34 total, all FAIL — RED phase confirmed):**

| Category | Count | Notes |
|----------|-------|-------|
| Happy path / render | 13 | AC-1 (7) + AC-2 (6): tag is `p-inline-notification`, `state='error'`, `description` carries error message |
| Retryable action | 7 | AC-3: `actionLabel='Retry'`, `actionIcon='reset'` for 500/network on both modals |
| Non-retryable | 6 | AC-4: `actionLabel` empty/absent for 409/422/404/client-validation on both modals |
| Loading state | 2 | AC-5: `actionLoading=true` while retry `handleSubmit()` is in-flight |
| Dismiss / clear | 5 | AC-6: cleared on success, `onDismiss`, and ArchivalModal reason-change |
| Focus trap | 1 | AC-7: `querySelectorAll` selector includes `p-inline-notification` |

**AC coverage:**

| AC line | Tests |
|---------|-------|
| AC-1 (ArchivalModal PInlineNotification + description) | 7 |
| AC-2 (ResolveModal PInlineNotification + description) | 6 |
| AC-3 (retryable: actionLabel/actionIcon) | 7 |
| AC-4 (non-retryable: no action) | 6 |
| AC-5 (actionLoading during retry) | 2 |
| AC-6 (dismiss on success/click/reason-change) | 5 |
| AC-7 (focus trap selector) | 1 |

**Note for builder:** AC-8 (existing test migration) requires updates to `ArchivalModal.test.tsx`, `ArchivalModal.error-body.test.tsx`, `ErrorContract.test.tsx`, `ResolveModal.test.tsx`, and `PdsMigration.test.tsx` — switching `.textContent` to JS property access and updating tag-name selectors from `p-text` to `p-inline-notification`. Those existing tests will also break once PInlineNotification replaces PText.

**Lint:** clean (ESLint exit 0)
2026-05-12T06:31:49+00:00
## Builder Notes
- Implementation attempted: `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`
- AC-8 migration updates attempted in existing tests: `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal.error-body.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`
- RED verification (quality-runner): `PInlineNotification.modal-1499.test.tsx` failed as expected pre-implementation (34 fails)
- Baseline durable tests before implementation: `ArchivalModal.test.tsx` + `ResolveModal.test.tsx` passed (55)
- GREEN verification blocked: quality-runner reruns now fail 6 tests due test harness error `TypeError: act is not a function` at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx` lines 644, 689, 735, 752, 804, 820
- Lint: clean on scoped files
- Coverage: not produced (verification did not reach passing test state)

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Fix `act` usage/import in the task test file so AC-5/AC-6 tests execute (currently runtime TypeError before assertions). Re-run RED/GREEN proof for #1499 after fix. | serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx | quality-runner scoped run: `TypeError: act is not a function` at lines 644/689/735/752/804/820 |
| 2 | test-writer | Re-dispatch builder only after the corrected `TestFromAC_PInlineNotificationModals` suite can execute without harness/runtime errors. | serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx | two quality-runner attempts (including frontend hint) failed identically with same runtime error |


2026-05-12T06:38:17+00:00
## Test-Writer Notes

**Retry: fixed `act` import — AC-5/AC-6 tests now execute with proper assertion failures**

- File: `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- Change: moved `act` import from `vitest` (not exported) → `@testing-library/react` (correct source)
- Commit: `cd876897`

**Post-fix state (34 total):**

| AC | Tests | Outcome |
|----|-------|---------|
| AC-1 | 7 | PASS (builder implemented) |
| AC-2 | 6 | PASS (builder implemented) |
| AC-3 | 7 | PASS (builder implemented) |
| AC-4 | 6 | PASS (builder implemented) |
| AC-5 | 2 | **FAIL** — `expected false to be true` for `actionLoading` (builder gap) |
| AC-6 | 6 | 3 PASS (reason-change + AC-6 test 5), **3 FAIL** — `onDismiss` not clearing error + retry callbacks not firing |

**Builder gaps for AC-5/AC-6:**
1. `actionLoading={isSubmitting}` not wired on PInlineNotification
2. `onDismiss` prop not bound to `setError(null)` in both modals
3. Retry `onAction` handler not calling `onClose`/`onResolved` on success

**Lint:** clean (ESLint exit 0)
2026-05-12T06:44:28+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/src/components/ArchivalModal.tsx`
  - `serve/cockpit/web/src/components/ResolveModal.tsx`
- Fixes applied (AC-5/AC-6):
  - Preserved error notification during retry (`handleSubmit(retrying = true)`) so `actionLoading` can render while retry is in-flight.
  - Added explicit retry/dismiss handlers and bound them on notification host refs (`onAction`, `onDismiss`) to satisfy retry + manual-dismiss behavior under web-component property assertions.
  - Kept existing retryability matrices intact (Archival: 500+/network retryable; Resolve: 500+/network retryable; 409/422/404 non-retryable as previously implemented).
- Quality evidence (quality-runner scoped):
  - Tests: 89 passed, 0 failed, 0 skipped
  - Lint: clean (`eslint` violations: none)
  - Coverage: not reported in this scoped frontend run
- Commit:
  - `09110656`
  - `feat: wire inline notification retry/dismiss state for modals (#1499, builder)`
2026-05-12T07:04:42+00:00
## Review Evidence
- Verdict: FAIL
- FAIL signal: FAIL #1499 -> in-progress | behavioral proof is insufficient: AC-6 archival success remains false-green and the builder proof packet omits required coverage evidence.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-6 | The archival success path is not directly proven against the refined dismissal contract. `ArchivalModal` closes on success without an explicit error clear in the success branch, while the task test only waits for `onClose`, so review cannot distinguish `setError(null)` from parent unmount as the reason the notification disappears. | AC-6 in `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:45`; success branch in `serve/cockpit/web/src/components/ArchivalModal.tsx:211-213`; current archival success proof in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:707-740`; parent unmount path in `serve/cockpit/web/src/KanbanBoard.tsx:333-341` | in-progress |
| 2 | Proof bundle: behavioral | The final builder proof packet is incomplete for a behavioral bundle because it reports tests and lint but no coverage summary. Review cannot PASS without the required coverage evidence. | Behavioral bundle in `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:57`; builder note `Tests: 89 passed` and `Coverage: not reported` in `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:190-192` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make the archival AC-6 success-path behavior directly provable. Either clear the notification state before close or tighten the task-local success assertion so review no longer relies on close-driven unmount as the proof mechanism. | serve/cockpit/web/src/components/ArchivalModal.tsx; serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx | AC-6 at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:45`; source at `serve/cockpit/web/src/components/ArchivalModal.tsx:211-213`; current test at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:707-740` |
| 2 | builder | Re-run the behavioral proof bundle and append the missing coverage summary before returning the task to review. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Behavioral bundle at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:57`; missing coverage at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:190-192` |

## Observations
- AC-1/AC-2/AC-3/AC-4/AC-5/AC-7 source and task-test coverage otherwise line up: `PInlineNotification` render/action props are implemented in `serve/cockpit/web/src/components/ArchivalModal.tsx:309-325` and `serve/cockpit/web/src/components/ResolveModal.tsx:237-253`, and the task suite covers the error matrices plus focus-trap selector in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:192-602` and `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:832-849`.
- AC-8 migration work is present in the durable suites: `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx:384`, `serve/cockpit/web/src/__tests__/ArchivalModal.error-body.test.tsx:121`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx:407`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx:220`, and `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:540-575`.
- Challenger cross-check returned `reconsider` (confidence 0.63 in the original FAIL). I adjusted the rationale accordingly: this reject is based on proof insufficiency and incomplete behavioral evidence, not on a confidently demonstrated live UX regression from the current source alone.
2026-05-12T07:09:08+00:00
## Builder Notes
- Files changed: `serve/cockpit/web/src/components/ArchivalModal.tsx`
- Fix applied: explicit `setError(null)` in `ArchivalModal.handleSubmit()` success branch before `onClose()`/`onRefresh()` so AC-6 success-path dismissal is source-provable instead of unmount-implied.
- Scoped quality evidence (`quality-runner`, behavioral retry proof):
  - Tests: 89 passed, 0 failed, 0 skipped
  - Lint: clean (`eslint` violations: none)
  - Coverage: overall 91.23%; `ArchivalModal.tsx` 92.92% (touched module), `ResolveModal.tsx` 87.69%
- Commit: `253b3d2a03cc788c31b77c45fb094742872d9392` — `fix: explicitly clear archival inline error on success (#1499, builder)`
- Evidence summary: reviewer blocking point addressed (AC-6 success path now explicitly clears notification state) and missing behavioral coverage evidence appended.
2026-05-12T07:20:14+00:00
## Review Evidence
- Verdict: FAIL
- FAIL signal: FAIL #1499 -> backlog | AC-6 success-path proof remains insufficient; both task-local success tests only assert callbacks, so they would still pass if `setError(null)` were removed.
- Builder evidence check: the latest proof packet closes the prior coverage gap (89 passed, 0 failed, lint clean, coverage overall 91.23%; `ArchivalModal.tsx` 92.92%, `ResolveModal.tsx` 87.69%), and current source explicitly clears error on success in both modals.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-6 | `ArchivalModal` success-path proof is still false-green. The task-local test labeled "error absent after successful retry" triggers `el.onAction?.()` and only waits for `onClose`, so it would still pass if the success branch stopped clearing the notification but still called close. | Success clear in `serve/cockpit/web/src/components/ArchivalModal.tsx:211-214`; current callback-only proof in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:707-740` | backlog |
| 2 | AC-6 | `ResolveModal` success-path proof is also callback-only. The task-local test labeled "error absent after successful retry" waits for `onResolved` but never proves the notification disappears, so it would not catch regression of `setError(null)` in the success branch. | Success clear in `serve/cockpit/web/src/components/ResolveModal.tsx:72-74`; current callback-only proof in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:777-808` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the second-cycle retry so AC-6 success dismissal is proven directly before another build/review pass. Require task-local assertions that the notification disappears after successful retry in both modals, not just that callbacks fire. | `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx` | Callback-only success assertions at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:707-740` and `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:777-808` |

## Observations
- AC-1/AC-2/AC-3/AC-4/AC-5/AC-7 source mapping remains consistent: `serve/cockpit/web/src/components/ArchivalModal.tsx:123-132`, `serve/cockpit/web/src/components/ArchivalModal.tsx:176-248`, `serve/cockpit/web/src/components/ArchivalModal.tsx:309-326`, `serve/cockpit/web/src/components/ResolveModal.tsx:44-75`, and `serve/cockpit/web/src/components/ResolveModal.tsx:237-253`.
- AC-8 migration work is still present in the durable suites: `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx:381-384`, `serve/cockpit/web/src/__tests__/ArchivalModal.error-body.test.tsx:118-121`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx:405-407`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx:220-243`, and `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:540-575`.
- Challenger cross-check returned `reconsider`; I retained FAIL because the live issue is proof sufficiency, and the task-local success tests still would not fail on regression of the AC-6 dismissal behavior.
2026-05-12T07:31:43+00:00
## AC-6 Refinement (Cycle 3)

_Reviewer rejected AC-6 success-path proof twice: task-local success tests only assert callbacks fire, would still pass if `setError(null)` were removed. AC-6 is replaced by AC-6a through AC-6d:_

- AC-6a: `ArchivalModal.handleSubmit()` success path: `setError(null)` before `onClose()`; task-local test proves `p-inline-notification[data-testid="archival-error"]` absent from container DOM after successful retry — callback assertion (`onClose` called) alone is NOT sufficient proof
- AC-6b: `ResolveModal.handleSubmit()` success path: `setError(null)` before `onResolved()`; task-local test proves `p-inline-notification[data-testid="resolve-error"]` absent from container DOM after successful retry — callback assertion (`onResolved` called) alone is NOT sufficient proof
- AC-6c: `ArchivalModal` and `ResolveModal` dismiss notification on `onDismiss` event; element absent from DOM (already proven — no changes needed)
- AC-6d: `ArchivalModal` clears error on reason selection change (already proven — no changes needed)

## Builder Guidance (Cycle 3)

**Source code: NO CHANGES NEEDED.** Both modals already call `setError(null)` before close callbacks (`ArchivalModal.tsx:211-214`, `ResolveModal.tsx:72-74`). The reviewer's rejection is about test assertions, not source behavior.

**Test fix required (2 tests only in `PInlineNotification.modal-1499.test.tsx`):**
1. "ArchivalModal: error absent after successful retry" (~line 707): after the `onClose` callback assertion, add DOM-absence assertion proving `p-inline-notification[data-testid="archival-error"]` is null. Use `waitFor` wrapper (async settle).
2. "ResolveModal: error absent after successful retry" (~line 777): after the `onResolved` callback assertion, add DOM-absence assertion proving `p-inline-notification[data-testid="resolve-error"]` is null. Use `waitFor` wrapper.

**Pattern reference:** The onDismiss tests at lines 742-762 and 810-826 already use the exact `waitFor(() => expect(get*Error(container)).toBeNull())` pattern successfully.

Proof bundle: behavioral (unchanged)

2026-05-12T07:31:59+00:00
## Architecture Review (Cycle 3)

### Context
Reviewer rejected to backlog twice for AC-6 false-green: success-path task-local tests only assert callbacks (`onClose`/`onResolved`) without verifying notification DOM absence. Source code is correct — both modals call `setError(null)` before close. Test-only gap.

### Evaluation (Cycle 3 — targeted re-review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged — same UX concern |
| Interface clarity | PASS (refined) | AC-6 split into 6a-6d per B1 scoping; success-path proof requirement now explicit |
| Dependency correctness | PASS | No new deps |
| Module layering | PASS | Unchanged |
| TDD compliance | PASS | Test fix is 2 assertions in existing test file; pattern already demonstrated in onDismiss tests |
| KISS/YAGNI | PASS | Minimal fix — 2 assertions added, no source changes |
| Premise challenge | PASS | Source behavior verified correct; only test proof gap |
| Pattern consistency | PASS | Uses existing `waitFor(() => expect(get*Error(container)).toBeNull())` pattern |
| Security surface | PASS | Unchanged |
| Single domain | PASS | Frontend-only |

### Challenge Results
- Challenger: reconsider (confidence: 0.76)
- Findings: (1) AC-6 over-composed per B1 — ACCEPTED, split into 6a-6d; (2) durable suites also callback-only — REJECTED as out-of-scope; (3) async settle underspecified — ACCEPTED, added `waitFor` pattern reference; (4) helper names in AC — ACCEPTED, reworded to data-testid selectors
- Consolidation-test-gap: checked — 2 siblings (#1499, #1500), no gap

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC-6 into AC-6a/6b/6c/6d with explicit DOM-absence proof requirements for success-path tests. Added cycle-3 builder guidance specifying the 2 test assertions needed (no source changes). Advanced backlog → todo.
2026-05-12T07:38:00+00:00
## Test-Writer Notes

**Retry (Cycle 3): added DOM-absence assertions for AC-6a/AC-6b success-path proof — builder skipped**

- File: `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- Commit: `c23a25de`

**Changes (2 assertions added, no tests removed):**

| AC | Test | Change |
|----|------|--------|
| AC-6a | "ArchivalModal: error absent after successful retry" | Added `waitFor(() => expect(getArchivalError(container)).toBeNull())` after `onClose` callback assertion |
| AC-6b | "ResolveModal: error absent after successful retry" | Added `waitFor(() => expect(getResolveError(container)).toBeNull())` after `onResolved` callback assertion |

**Quality evidence (quality-runner scoped):**
- Tests: 34 passed, 0 failed, 0 skipped
- Lint: clean (ESLint exit 0)

**Builder skip rationale:** Both new DOM-absence assertions PASS against current source — `ArchivalModal.tsx:211-214` and `ResolveModal.tsx:72-74` already call `setError(null)` before close callbacks. The reviewer's gap was test-proof only (as documented by the architect in Cycle 3 builder guidance). No source changes required. Advancing directly to review per Step 1b.1.
2026-05-12T08:41:54+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1499 -> docs | AC mapped to code and evidence sufficient.
- Active dismissal contract for this review is the cycle-3 replacement AC-6a..6d at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:266-269`; the earlier combined AC-6 at line 58 is superseded.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `ArchivalModal.handleSubmit()` sets structured error state for 409/422/500+/network/client-validation in `serve/cockpit/web/src/components/ArchivalModal.tsx:183-239`; notification render is in `serve/cockpit/web/src/components/ArchivalModal.tsx:310-326` | Task suite `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:192-312` covers 409/422/500/network/client-validation and description assertions | PASS |
| AC-2 | `ResolveModal.handleSubmit()` uses one shared non-ok branch in `serve/cockpit/web/src/components/ResolveModal.tsx:50-84` and renders the notification in `serve/cockpit/web/src/components/ResolveModal.tsx:237-253` | Task suite `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:313-405` covers 404/409/422/500/network presence/state and 500 description; durable Resolve error-body tests in `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx:394-430` prove body-message/detail extraction on the same branch | PASS |
| AC-3 | Retryability matrix is implemented in `serve/cockpit/web/src/components/ArchivalModal.tsx:219-236` and `serve/cockpit/web/src/components/ResolveModal.tsx:60-69`; conditional retry props are in `serve/cockpit/web/src/components/ArchivalModal.tsx:322-324` and `serve/cockpit/web/src/components/ResolveModal.tsx:249-251` | Task suite `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:407-515` proves Retry/reset on 500/network; retry callbacks are exercised again by AC-5/AC-6 tests at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:611-812` | PASS |
| AC-4 | Non-retryable states set `retryable=false` in `serve/cockpit/web/src/components/ArchivalModal.tsx:200-231` and `serve/cockpit/web/src/components/ResolveModal.tsx:60-69`; `actionLabel`/`actionIcon`/`onAction` props are gated from that same boolean in `serve/cockpit/web/src/components/ArchivalModal.tsx:322-324` and `serve/cockpit/web/src/components/ResolveModal.tsx:249-251` | Task suite `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:516-609` proves no action label for 409/422/client-validation and 404/409/422 | PASS |
| AC-5 | `actionLoading={isSubmitting}` is wired in `serve/cockpit/web/src/components/ArchivalModal.tsx:325` and `serve/cockpit/web/src/components/ResolveModal.tsx:252`; retry path preserves the notification while in-flight in `serve/cockpit/web/src/components/ArchivalModal.tsx:194-196` and `serve/cockpit/web/src/components/ResolveModal.tsx:54-56` | Task suite `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:611-704` stalls the retry fetch and asserts `actionLoading === true` in both modals | PASS |
| AC-6a | Archival success path clears error before callbacks in `serve/cockpit/web/src/components/ArchivalModal.tsx:212-215` | Direct render helper with spy callbacks in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:112-140` plus DOM-absence assertion at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:742` prove dismissal is local state clear, not parent unmount | PASS |
| AC-6b | Resolve success path clears error before callbacks in `serve/cockpit/web/src/components/ResolveModal.tsx:72-75` | Direct render helper in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:133-140` plus DOM-absence assertion at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:812` prove notification removal after successful retry | PASS |
| AC-6c | `onDismiss` clears error in `serve/cockpit/web/src/components/ArchivalModal.tsx:247-248` and `serve/cockpit/web/src/components/ResolveModal.tsx:90-91`; props are wired at `serve/cockpit/web/src/components/ArchivalModal.tsx:326` and `serve/cockpit/web/src/components/ResolveModal.tsx:253` | Task suite asserts DOM absence after `onDismiss` at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:744-759` and `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:814-829` | PASS |
| AC-6d | Reason change clears archival error in `serve/cockpit/web/src/components/ArchivalModal.tsx:170-178` | Task suite regression guard at `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:761-775` | PASS |
| AC-7 | Focus-trap selector includes `p-inline-notification` in `serve/cockpit/web/src/components/ArchivalModal.tsx:123-132` | Task suite spy assertion in `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:836-853` | PASS |
| AC-8 | Durable migrated suites now query inline-notification hosts and read web-component properties in `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx:384,448`, `serve/cockpit/web/src/__tests__/ArchivalModal.error-body.test.tsx:103-121`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx:394-430`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx:206-245`, and `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:539-575` | Builder/test-writer evidence plus current file inspection show the named durable suites no longer rely on the old `p-text[data-testid="*-error"]` assumptions | PASS |

- Quality evidence sufficiency: cycle 3 reran the task-local retry suite only (`34 passed, 0 failed, 0 skipped`, lint clean at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:329-332`) because no source changed after the last builder pass; prior builder coverage evidence remains applicable for the unchanged source (`ArchivalModal.tsx` 92.92%, `ResolveModal.tsx` 87.69% at `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:237`).
- Safety/security: PASS — frontend-only state/UI change, no new dependencies, and response-body extraction continues through the existing helper in `serve/cockpit/web/src/api/errorMessage.ts:1-20`.

## Observations
- Challenger returned `reconsider`. I overrode that to PASS because the original blocker was AC-6 false-green, and cycle 3 closes it: these tests mount the modals directly with spy callbacks (no parent unmount), then assert the notification host is absent from the container after successful retry.
- The remaining challenger concern on Resolve description coverage is not a blocking gap in the current code shape. `ResolveModal` has a single shared non-ok branch (`serve/cockpit/web/src/components/ResolveModal.tsx:50-69`) and the shared helper is directly covered for both `message` and `detail` extraction in `serve/cockpit/web/src/__tests__/ArchivalModal.error-body.test.tsx:238-253`, while Resolve durable tests prove description plumbing on that branch in `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx:394-430`.
- The task body still contains the superseded combined AC-6 at line 58. This review used the explicit replacement AC-6a..6d at lines 266-269.
2026-05-12T09:16:00+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no doc impact | `serve/cockpit/README.md` documents backend API, engine surface, and configuration only; no mention of individual UI components, modal error rendering, or PText/PInlineNotification. No task-caused drift detected. Layer 1 (grep): zero matches for `PInlineNotification`, `ArchivalModal`, `ResolveModal`. Layer 2 (editorial): README coherent and accurate. |
| External Attribution | Updated | Research doc studied PDS Inline Notification examples (v3) — new source not yet in overview. Added section "PInlineNotification Modal Error Research (Task #1499)" to `.owlbear/sources/overview.md`. Commit: `d3969adb`. |
| Research Doc | Present and linked | `.owlbear/research/cockpit-inline-notification-modal.md` linked in task body under `## Research`. |
| Deletion Detection | N/A — no deletions | No source files removed; only `ArchivalModal.tsx`, `ResolveModal.tsx`, and test files modified. |

### Files Updated
- `.owlbear/sources/overview.md` — added PDS inline notification examples source entry

### Scratch Cleanup
No scratch files created for this task.

### Upstream Review Evidence
Present: `## Review Evidence` PASS verdict at end of task body. All AC-1 through AC-8 mapped.
2026-05-12T09:53:15+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: Frontend 1444 passed, 9 skipped, 1 suite failed (decisions_1502.test.ts — RED-phase import error for task #1502, not #1499). Python 781 passed, 5 failed — all pre-existing and unrelated to #1499 (frontend-only task: missing file references in test_cockpit_view/test_mcp_kanban, assertion text mismatch in test_ideation_diagram, TypeError in test_server, mock issue in test_cockpit_mutation_api). Lint clean (ruff exit 0, eslint exit 0).\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (all changes in serve/cockpit/web/ — ArchivalModal.tsx, ResolveModal.tsx, PInlineNotification.modal-1499.test.tsx, AC-8 migration updates to durable test suites, .owlbear/sources/overview.md attribution)\n- purpose match: PASS (replaces PText error rendering with PInlineNotification in both modals, adds retry/dismiss/loading state per AC)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nInitial AC had notable gaps: 409 incorrectly classified as retryable, missing focus trap AC, vague ResolveModal scope, underspecified test migration surface. Challenger caught all issues; architect refined comprehensively. AC-6 required cycle-3 split into 6a-6d after two reviewer rejections for test-proof insufficiency. Final AC precise with status-code matrices, component-scoped naming, explicit DOM-absence proof requirements. Score 4: adequate — iterative refinement worked but initial draft needed significant rework.\n\n### Commit Integrity\n- upstream commit presence: PASS (builder: 09110656, 253b3d2a; test-writer: cd876897, c23a25de; doc-writer: d3969adb; all verified via git log)\n- kanban commit packaging: pending (this audit cycle)\n\n### Deduction Breakdown\nNo deductions applied:\n- Regression: PASS (0 task-attributable failures)\n- Intent: PASS (correct domain, no extraneous scope)\n- Lint: PASS (clean)\n- AC quality: 4/5 (>3, no deduction)\n- Reviewer evidence: present and thorough (cycle 3 PASS with full AC mapping)\n- Evidence integrity: no concerns\n\n### Confidence: 1.00\n### Action: archive