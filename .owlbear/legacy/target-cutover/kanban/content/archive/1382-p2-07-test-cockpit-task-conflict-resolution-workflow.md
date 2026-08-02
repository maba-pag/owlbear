---
id: 1382
title: 'P2-07: Test Cockpit task conflict resolution workflow'
status: archived
priority: medium
created: 2026-05-06T01:04:39.067978+00:00
updated: 2026-05-10T00:38:43.090002+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- conflict-resolution
- error-handling
parent: 1363
depends_on:
- 1381
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for safe 409 conflict resolution in the task detail editor.

## Problem Evidence
- The conflict modal fetches the latest task and resets local form state.
- The modal still shows Force save, which can discard local edits while implying the local edit will be forced.
- Expected mutation errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Tests prove local edits (title, priority, body, depends_on, parent, block_reason) are preserved in the form when a 409 conflict response triggers a latest-task refresh. The test must re-render DetailTab with the server's refreshed task prop to verify form fields retain the user's entered values, not the server's refreshed values. (td:2)
- Tests prove the conflict modal renders identifiable remote (server) and local (user) values for fields that differ, enabling the user to compare their pending edits against the server's current state. Assert on data-testid patterns for remote and local field values. (td:2)
- Tests prove force-save requires an explicit overwrite acknowledgment step (not immediately available when the conflict modal first appears) and, when executed, sends the user's preserved local form values in the request payload — not the server's refreshed values. (td:2)
- Tests prove canceling or dismissing conflict resolution restores the form to the user's pre-conflict local edits — the available close affordances on the conflict modal must not discard pending edits. (td:2)
- Tests prove mutation errors in the conflict-resolution flow produce user-visible messages using the frontend error contract from #1375 (`getResponseErrorMessage()`): 409→refetch→404 (task deleted between save and refresh), force-save retry 422, and force-save retry generic unexpected errors. Direct mutation 404 clearing behavior and initial-save generic errors are not conflict-resolution scope. (td:2)
- Tests fail against the current reset-then-force behavior in DetailTab.tsx and are suitable as RED-phase targets for #1383. RED verification must reproduce the parent re-render path (prop update after 409 refetch) to avoid false-green. (td:1)

## Scope
- In scope: Cockpit frontend task detail conflict-resolution tests for edit conflicts.
- Out of scope: action gating from #1381, backend conflict semantics, decision resolution, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1383.

[[2026-05-09]]

## Builder Guidance

### Test Harness — False-Green Prevention
The reset-then-force bug lives in the `useEffect` on `[task?.id, task?.updated]` at [DetailTab.tsx L67–74](serve/cockpit/web/src/components/DetailTab.tsx#L67-L74). When `onTaskUpdated(latestTask)` fires after a 409 refetch, the parent component (Shell) updates the `task` prop. The new `task.updated` triggers the `useEffect`, which resets all form fields to server values — discarding the user's edits.

**To reproduce in tests:** After mocking the 409 → refetch → `onTaskUpdated` flow, the test MUST re-render `DetailTab` with the new (server) task prop to trigger the `useEffect` reset. Use RTL's `rerender()` or a stateful wrapper. Rendering `DetailTab` standalone without re-render will false-green because the form state was never reset.

### Existing Test Patterns
- PDS jsdom patch: `beforeAll` with `attachInternals` mock — see [DetailTab.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.test.tsx#L22-L29)
- react-markdown mock: factory mock — see same file
- Fetch mocking: `vi.stubGlobal('fetch', vi.fn())` pattern used in existing suites
- 409 flow: see [DetailTab.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.test.tsx#L581-L613) for the existing (insufficient) 409 test

### Adjacent Test Suites (Do Not Duplicate)
- [ErrorContract.test.tsx](serve/cockpit/web/src/__tests__/ErrorContract.test.tsx) — already covers generic error-envelope parsing
- [DetailTab.conflict-nonregression.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-nonregression.test.tsx) — AC7 guard for action-gating survival
- [DetailTab_1380.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1380.test.tsx) — action-side 409/404/422 paths for unclaim and move-backward

### 404 Scope Boundary
- Direct mutation 404 (`POST /edit` → 404`): clears selection via `onTaskCleared()` — this behavior is correct and out of scope.
- Conflict-refetch 404 (`POST → 409 → GET latest → 404`): task deleted between save and refresh — user loses edits silently. This path IS in scope for error contract coverage.

### File Placement
Test file: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`
[[2026-05-09]]

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Conflict-resolution tests only — one UI concern |
| Interface clarity | PASS | AC refined with test-depth, false-green prevention, 404 scope boundary, and data-testid assertion guidance |
| Dependency correctness | PASS | #1381 (action gating) and #1375 (error contract) both archived/done |
| Module layering | N/A | Test task — no production code |
| TDD compliance | PASS | This IS the RED phase test task; counterpart #1383 depends on it |
| KISS/YAGNI | PASS | Scoped to conflict-resolution paths only; excludes action gating, backend semantics, cache/SSE |
| Premise challenge | PASS | Bug is real — useEffect on [task?.id, task?.updated] resets form on prop change after 409 refetch; force-save then sends server values, not user edits |
| Pattern consistency | PASS | Follows DetailTab.test.tsx patterns (PDS jsdom patch, react-markdown mock, fetch stubbing) |
| Security surface | N/A | Test task |
| Single domain | PASS | Cockpit frontend only |

### Challenger Results
- Challenger verdict: reconsider (0.62 confidence)
- Key concerns addressed:
  1. **False-green risk** — AC1 and AC6 now require re-render with server's refreshed task prop. Builder Guidance section explains the useEffect reset mechanism and mandates RTL rerender() or stateful wrapper.
  2. **UI-contract ambiguity** — AC2 specifies data-testid assertion patterns for remote/local values. AC3 specifies explicit overwrite acknowledgment step (not immediately available).
  3. **404 ownership** — AC5 now scopes 404 to conflict-refetch path only (409→GET→404). Direct mutation 404 clearing is explicitly excluded.
  4. **Baseline undercount** — Builder Guidance lists adjacent suites to avoid duplication.
- Architect override: proceed with APPROVE after addressing all challenger concerns in refined AC.

### Test Depth
- AC1: td:2, AC2: td:2, AC3: td:2, AC4: td:2, AC5: td:2, AC6: td:1
- Max depth: 2
- Test-writer: type:test pass-through — builder writes the tests

### Verdict: APPROVE
### Action Taken: Refined 6 AC lines with test-depth annotations, false-green prevention guidance, 404 scope boundary, and data-testid assertion patterns. Task approved to `todo`.
[[2026-05-09]]
Refined 6 AC lines with test-depth annotations (5×td:2, 1×td:1). Key refinements: (1) false-green prevention — AC1/AC6 require parent re-render path reproduction; (2) UI testability — AC2 specifies data-testid patterns for remote/local values; (3) 404 scope — AC5 scopes to conflict-refetch 404 only; (4) overwrite gating — AC3 requires intermediate acknowledgment step. Challenger concerns (0.62 reconsider) fully addressed in refined AC and Builder Guidance section. Dependencies #1381/#1375 both done.
[[2026-05-09]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`
- Classes:
  - `TestFromAC_ConflictLocalEditsPreserved` (AC1 — 3 tests)
  - `TestFromAC_ConflictModalComparison` (AC2 — 3 tests)
  - `TestFromAC_ForceSaveAcknowledgmentGate` (AC3 — 4 tests)
  - `TestFromAC_ConflictCancelPreservesEdits` (AC4 — 2 tests)
  - `TestFromAC_ConflictErrorContract` (AC5 — 3 tests)
- Tests per category: happy 8, edge 5, error 3, boundary 0
- Total: 15 tests, all FAIL (0 pass)
- ESLint: clean

AC coverage table:
| AC | Tests | Failure reason |
|----|-------|----------------|
| AC1 | 3 | useEffect resets title/priority/block_reason to server values after re-render |
| AC2 | 3 | `conflict-remote-*` and `conflict-local-*` elements absent from conflict modal DOM |
| AC3 | 4 | `conflict-overwrite` immediately visible (should be absent); `conflict-acknowledge` element missing |
| AC4 | 2 | `conflict-dismiss` element absent; form shows server values after dismiss |
| AC5 | 3 | 409→404 no validation-message; `conflict-acknowledge` missing blocks force-save error paths |
| AC6 | — | Satisfied transitively — all 15 tests fail against current reset-then-force behavior |

Harness note: StatefulWrapper reproduces parent re-render path (onTaskUpdated → setState → useEffect reset). Tests without wrapper would false-green because form state never gets reset by useEffect in isolation.
[[2026-05-09]]
## Builder Notes
- Task type: test-pass-through (`type:test`); no implementation changes applied.
- Files changed: none.
- RED verification (quality-runner, scoped): `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` -> 15 failed, 0 passed, 0 skipped.
- Lint: clean (`eslint` on `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`).
- Evidence summary: failures match AC expectations for reset-then-force behavior and conflict-modal contract gaps; suite is ready as RED-phase target for #1383 implementation.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run on serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx: 0 passed, 15 failed, 0 skipped.
- Representative failures align with the current live conflict flow in serve/cockpit/web/src/components/DetailTab.tsx: title resets after 409 refetch, the conflict modal exposes only conflict-refresh/conflict-overwrite, and the 409->404 path never renders validation-message.
- This RED state is expected for a type:test task and is not the reason for rejection by itself.

### Lint Results
- Clean. quality-runner reported no lint violations for serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx or serve/cockpit/web/src/components/DetailTab.tsx.

### Coverage
- Unavailable from the scoped run because the suite remains intentionally RED. Non-blocking here; this review gates on AC proof quality and discriminating assertions.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: preserve title, priority, body, depends_on, parent, block_reason after 409 -> refetch -> parent rerender | Task AC explicitly names 6 fields. The suite covers only title at DetailTab_1382.test.tsx:231, priority at DetailTab_1382.test.tsx:252, and block_reason at DetailTab_1382.test.tsx:267. There are no body, depends_on, or parent preservation tests. | FAIL |
| AC2: render identifiable remote/local values for fields that differ | The suite asserts remote title at DetailTab_1382.test.tsx:292, local title at DetailTab_1382.test.tsx:309, and remote priority at DetailTab_1382.test.tsx:326. It does not prove local priority or broader non-title differing-field comparisons required by "fields that differ." | FAIL |
| AC3: overwrite requires explicit acknowledgment and sends preserved local values | Gate coverage exists at DetailTab_1382.test.tsx:354 and :369, but payload assertions inspect only title at :391 and priority at :432. Body, depends_on, parent, and block_reason are unproven. The suite also hardcodes conflict-acknowledge although AC3 specifies behavior, not a selector contract. | FAIL |
| AC4: available close affordances must not discard pending edits | The suite exercises only conflict-dismiss at DetailTab_1382.test.tsx:476 and :507. The live component currently exposes conflict-refresh at DetailTab.tsx:446, and the task AC does not specify a conflict-dismiss selector. The review evidence therefore proves neither the actual current affordance nor every available close path. | FAIL |
| AC5: user-visible getResponseErrorMessage paths for 409->404, 422, and generic unexpected errors on initial save and force-save retry | Task-local AC5 tests are only 409->404 at DetailTab_1382.test.tsx:541, force-save 422 at :582, and generic force-save error at :636. The initial-save generic error branch is missing. The 409->404 and generic assertions accept only non-empty text at :579 and :683, which is weaker than the exact-message proof already used in ErrorContract.test.tsx:341-387. Force-save 422/generic are also blocked upstream by the hardcoded conflict-acknowledge selector. | FAIL |
| AC6: RED verification reproduces the parent rerender path and fails against current reset-then-force behavior | The harness note documents the false-green risk at DetailTab_1382.test.tsx:32, StatefulWrapper implements the rerender path at :128, and quality-runner confirms 15/15 RED failures against the current DetailTab behavior. | PASS |

### Test Integrity
- Current snapshot still contains all expected TestFromAC blocks for AC1-AC5.
- Small confidence deduction: no task-local commit hash or diff was recorded, so I could not prove TestFromAC immutability against the original source beyond the current snapshot.

### Deductions
- -0.10: AC coverage drift. The test header/helpers/tests narrow the task contract well below the accepted AC surface.
- -0.05: Selector-contract drift. AC2 is the only place the task explicitly requires data-testid patterns, but the RED suite hardcodes conflict-acknowledge and conflict-dismiss for AC3/AC4.
- -0.05: Error-contract proof weakness. Two AC5 tests accept any non-empty message instead of proving the getResponseErrorMessage branch.
- -0.03: No commit/diff evidence for high-confidence TestFromAC immutability verification.

### Verdict
- FAIL. Confidence: 0.77.
- Route: todo. This is cycle 1, the defects are confined to the task test file, and the required retry belongs to the test-writer. The current record does not justify architect escalation to backlog.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Expand AC1 and AC3 coverage so the RED suite proves preservation and force-save payload correctness for body, depends_on, parent, and block_reason in addition to title/priority. | serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx | Task AC names those fields; current proof exists only at DetailTab_1382.test.tsx:231, :252, :267, :391, and :432. |
| 2 | test-writer | Rework AC2 and AC4 assertions to match the refined contract: prove remote/local comparison for the differing fields the task owns, and prove the available close-affordance behavior without inventing unsupported selector names. | serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx; serve/cockpit/web/src/components/DetailTab.tsx | conflict-dismiss is asserted at DetailTab_1382.test.tsx:494 and :519, while the live component exposes conflict-refresh at DetailTab.tsx:446. |
| 3 | test-writer | Strengthen AC5 with discriminating message assertions and add the missing initial-save generic-error path using the same exact-message proof style already present in ErrorContract.test.tsx. | serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx | Non-empty-only assertions at DetailTab_1382.test.tsx:579 and :683; current AC5 coverage limited to :541, :582, and :636. |
[[2026-05-09]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`
- Classes:
  - `TestFromAC_ConflictLocalEditsPreserved` (AC1 — 6 tests)
  - `TestFromAC_ConflictModalComparison` (AC2 — 4 tests)
  - `TestFromAC_ForceSaveAcknowledgmentGate` (AC3 — 8 tests)
  - `TestFromAC_ConflictCancelPreservesEdits` (AC4 — 2 tests)
  - `TestFromAC_ConflictErrorContract` (AC5 — 3 tests)
- Tests per category: happy 10, edge 11, error 2, boundary 0
- Total: 23 tests, all FAIL (0 pass)
- ESLint: clean

AC coverage table:
| AC | Tests | Failure reason |
|----|-------|----------------|
| AC1 | 6 | title/priority/block_reason: useEffect resets to server values after re-render; body: second-save payload sends 'Server body (Different)'; depends_on: reset to ''; parent: reset to '' |
| AC2 | 4 | `conflict-remote-*` and `conflict-local-*` elements absent from conflict modal DOM |
| AC3 | 8 | `conflict-acknowledge` element missing; force-save payload carries server-reset values for all 6 fields |
| AC4 | 2 | conflict-refresh affordance IS found (current code); modal closes; but form shows server-reset values |
| AC5 | 3 | 409→404: no validation-message; force-save 422/500: conflict-acknowledge gate missing |
| AC6 | — | Satisfied transitively — all 23 tests fail against current reset-then-force behavior |

Retry changes from reviewer:
1. AC1: Added body (via second-save payload — stencil async DOM timing makes `getFieldValue` on p-textarea unreliable), depends_on, parent preservation tests (3 new)
2. AC2: Added `conflict-local-priority` test (1 new)
3. AC3: Added body, depends_on, parent, block_reason force-save payload tests (4 new); all fail at conflict-acknowledge gate
4. AC4: Changed `conflict-dismiss` → `conflict-refresh` (actual available affordance); tests now fail at preservation assertion, not element-not-found
5. AC5: Strengthened weak assertions: 409→404 uses exact `.toContain('Task not found')`; force-save 500 uses `.toContain('Request failed with status 500')`

Note on initial-save generic error (AC5 reviewer gap): this path is already handled by current code (`runMutation` generic else branch calls `setServerValidationMessage`) and is covered by `ErrorContract.test.tsx`. Adding a test would create a green test (existing behavior) — excluded per workflow rules.

Note on body AC1 approach: `getFieldValue('p-textarea[data-field="body"]')` passes against current code due to stencil's deferred DOM updates (el.value reflects the change-event-set value, not yet updated to the server-reset value). Verified via second-save payload instead, which reads React state directly.
[[2026-05-09]]
## Builder Notes
- Task type: `type:test` pass-through; no production implementation changes applied in this builder cycle.
- Files changed: none.
- Quality evidence (quality-runner, scoped): `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` -> 0 passed, 23 failed, 0 skipped.
- Lint: clean (`eslint` exit 0 on `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`).
- Coverage: N/A for this frontend RED validation run.
- Evidence summary: The full `TestFromAC_*` suite remains intentionally RED against current `DetailTab` behavior, with failures aligned to AC1-AC5 conflict-resolution gaps; suite is ready as implementation target for #1383.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`: 0 passed, 23 failed, 0 skipped.
- All 23 failures are assertion failures against the current `DetailTab` behavior, not harness/runtime crashes.
- Representative failures match the live component: local edits still reset after the 409 refetch path, the conflict modal still renders immediate `conflict-overwrite` and no `conflict-acknowledge`, and the 409->404 path still never renders `validation-message`.
- VS Code diagnostics: no TypeScript errors in `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` or `serve/cockpit/web/src/components/DetailTab.tsx`.

### Lint Results
- Clean. quality-runner reported no ESLint violations for `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` or `serve/cockpit/web/src/components/DetailTab.tsx`.

### Coverage
- Not captured by the scoped frontend run. Non-blocking here because the suite remains intentionally RED and the rejection is based on AC proof, not execution breadth.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: preserve title, priority, body, depends_on, parent, and block_reason after 409 -> refetch -> parent rerender | `StatefulWrapper` reproduces the prop-update path at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:141-154`. The preservation block at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:260-404` now proves all six fields, and quality-runner shows those assertions fail against the current reset effect at `serve/cockpit/web/src/components/DetailTab.tsx:67-73`. | PASS |
| AC2: render identifiable remote/local values for differing fields | The comparison block at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:412-485` asserts the accepted `conflict-remote-*` / `conflict-local-*` pattern for title and priority. The live modal at `serve/cockpit/web/src/components/DetailTab.tsx:444-452` has none of those nodes, so the suite is genuinely RED on that contract. | PASS |
| AC3: explicit overwrite acknowledgment gate plus preserved local payload on force-save | The gating and payload block at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:498-741` now requires overwrite to be hidden initially, requires acknowledgment before overwrite appears, and asserts exact local payload values for all six editable fields. The current modal/force-save path at `serve/cockpit/web/src/components/DetailTab.tsx:224-230` and `serve/cockpit/web/src/components/DetailTab.tsx:444-452` still violates that contract. | PASS |
| AC4: available close affordances must not discard pending edits | The dismiss tests at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:752-807` use the actual live close affordance `conflict-refresh` from `serve/cockpit/web/src/components/DetailTab.tsx:446-448` and prove the current reset behavior still discards local edits. | PASS |
| AC5: getResponseErrorMessage coverage for 409->refetch->404, 422, and generic unexpected errors on initial save and force-save retry | The accepted task contract still requires generic unexpected errors on both initial save and force-save retry at `.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md:42`. The current suite covers only 409->404 at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:821`, force-save 422 at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:863`, and force-save generic 500 at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:917`. The initial-save generic branch still exists in `runMutation` / `handleSave` at `serve/cockpit/web/src/components/DetailTab.tsx:204` and `serve/cockpit/web/src/components/DetailTab.tsx:207`, but it remains untested. The retry note explicitly omits that proof because it would be green today at `.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md:217`. | FAIL |
| AC6: RED verification reproduces the parent rerender path and fails against current reset-then-force behavior | The harness note at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:34-38` and `StatefulWrapper` at `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx:141-154` reproduce the parent rerender path. quality-runner confirms 23/23 RED failures against the current implementation. | PASS |

### Test Integrity
- No current-snapshot evidence of weakened or removed `TestFromAC_*` assertions.
- Small confidence deduction: no diff-backed commit evidence was recorded, so TestFromAC immutability could only be checked from the present snapshot.

### Deductions
- -0.10: AC5 still lacks the initial-save generic-error proof required by the accepted task contract.
- -0.05: The task contract is internally inconsistent on retry: AC5 still requires that branch, while the retry note excludes it because it would be green against current code.
- -0.03: No diff/commit evidence for high-confidence TestFromAC immutability verification.

### Verdict
- FAIL. Confidence: 0.82.
- Route: backlog. This is the second review failure on the task (`## Review Evidence` already exists at `.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md:145`), and the remaining defect is now a contract/routing issue rather than a simple first-cycle test addition.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC5 with the RED-only task framing: either keep initial-save generic-error coverage in scope and explicitly allow that green proof, or narrow/move the requirement to the correct task/suite. | `.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md`; `serve/cockpit/web/src/components/DetailTab.tsx`; `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` | AC5 requires initial-save generic errors at task line 42; retry note excludes it at task line 217; live generic initial-save branch remains at `DetailTab.tsx:204` / `DetailTab.tsx:207`; current AC5 tests begin only at `DetailTab_1382.test.tsx:821`, `:863`, and `:917`. |
| 2 | architect | Update the task guidance so the next retry is validating a single coherent contract instead of choosing between RED purity and the written AC. | `.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md` | The task still requires both “generic unexpected errors on initial save and force-save retry” at line 42 and RED-phase failure suitability at line 43, which conflicts with the retry rationale at line 217. |
[[2026-05-09]]

## Architecture Review (Cycle 2)
### AC5 Reconciliation

**Issue:** AC5 required "generic unexpected errors on initial save and force-save retry," but the initial-save generic error path is (a) already implemented by #1375, (b) already tested by `ErrorContract.test.tsx:340-395` and `:674-687`, and (c) not conflict-resolution scope. Including it would produce a GREEN test in a RED-phase suite — contradicting AC6.

**Resolution:** Narrow AC5 to cover only errors occurring within the conflict-resolution flow:
- 409→refetch→404 (task deleted between save and refresh)
- Force-save retry 422
- Force-save retry generic unexpected error

The initial-save generic error path is explicitly excluded — it belongs to #1375's error-contract domain, not conflict-resolution.

**Refined AC5:** "Tests prove mutation errors in the conflict-resolution flow produce user-visible messages using the frontend error contract from #1375 (`getResponseErrorMessage()`): 409→refetch→404 (task deleted between save and refresh), force-save retry 422, and force-save retry generic unexpected errors. Direct mutation 404 clearing behavior and initial-save generic errors are not conflict-resolution scope. (td:2)"

### Verdict: APPROVE
AC5 narrowed to remove internal contradiction. All 23 existing tests remain valid. No other AC lines affected.

[[2026-05-09]]
AC5 narrowed: removed initial-save generic error requirement (already covered by ErrorContract.test.tsx from #1375, would produce GREEN test in RED suite). Scope now limited to conflict-resolution-flow errors only: 409→refetch→404, force-save 422, force-save generic. All 23 existing tests remain valid against refined AC. No other AC lines changed.
[[2026-05-09]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`
- Classes:
  - `TestFromAC_ConflictLocalEditsPreserved` (AC1 — 6 tests)
  - `TestFromAC_ConflictModalComparison` (AC2 — 4 tests)
  - `TestFromAC_ForceSaveAcknowledgmentGate` (AC3 — 8 tests)
  - `TestFromAC_ConflictCancelPreservesEdits` (AC4 — 2 tests)
  - `TestFromAC_ConflictErrorContract` (AC5 — 3 tests)
- Tests per category: happy 10, edge 11, error 2, boundary 0
- Total: 23 tests, all FAIL (0 pass)
- ESLint: clean (exit 0)

AC coverage table (against refined AC5 — initial-save generic error excluded per architect cycle-2 narrowing):
| AC | Tests | Failure reason |
|----|-------|----------------|
| AC1 | 6 | title/priority/block_reason: useEffect resets to server values after re-render; body: second-save payload sends server body; depends_on: reset to ''; parent: reset to '' |
| AC2 | 4 | `conflict-remote-*` and `conflict-local-*` elements absent from conflict modal DOM |
| AC3 | 8 | `conflict-acknowledge` element missing; force-save payload carries server-reset values for all 6 fields |
| AC4 | 2 | conflict-refresh IS found (real affordance); modal closes; form shows server-reset values |
| AC5 | 3 | 409→404: no validation-message; force-save 422/500: conflict-acknowledge gate missing |
| AC6 | — | Transitively satisfied — all 23 tests fail against current reset-then-force behavior |

No test file changes required this cycle. The 23-test suite written in the previous cycle satisfies all 6 refined ACs (including narrowed AC5). RED verification confirmed 0/23 pass. Suite is ready as implementation target for #1383.
[[2026-05-09]]
## Builder Notes
- Task classification: `type:test` pass-through; no production implementation required in this builder cycle.
- Files changed: none.
- Verification (quality-runner scoped): `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` -> 0 passed, 23 failed, 0 skipped.
- Lint: clean (`eslint` exit 0 for `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`).
- Coverage: not collected (frontend scoped RED verification run).
- Evidence summary: all failures remain aligned with known reset-then-force behavior in `DetailTab.tsx` and missing conflict-resolution UI contract; suite remains a valid RED implementation target for #1383.
- Routing: advancing to review per test-pass-through workflow (no builder source edits).
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx): 0 passed, 23 failed, 0 skipped.
- All 23 failures are assertion failures against the current conflict-resolution behavior in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx), not harness/runtime crashes.
- This RED state is expected for a `type:test` task and is not the rejection reason by itself.

### Lint Results
- Clean. quality-runner reported no ESLint violations for [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx) or [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx).
- VS Code diagnostics: no TypeScript errors in either file.

### Coverage
- quality-runner did not emit usable Vitest coverage text for the scoped RED run. Non-blocking here; the verdict is based on AC proof quality rather than execution breadth.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L38) | Preservation tests in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L265-L404) | No. The suite uses [StatefulWrapper](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L141) but only waits for modal visibility in [triggerConflictModal](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L246-L250); it never proves the refreshed task prop was actually applied. Suppressing [onTaskUpdated?.(latestTask)](serve/cockpit/web/src/components/DetailTab.tsx#L186) can leave local values untouched and these assertions still pass. | LAX |
| AC2 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L39) | Comparison tests at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L417), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L434), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L451), and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L469) | No. The suite proves comparison rows only for title and priority; an implementation that omits body, depends_on, parent, or block_reason comparison still passes. | LAX |
| AC3 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L40) | Gate and payload tests in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L498-L741) | No. The payload assertions are exact across all six fields, but they inherit AC1's false-green path because the suite never proves the latest-task refresh actually reached the child before overwrite. | LAX |
| AC4 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L41) | Dismiss tests at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L757) and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L786) | No. Only title and priority dismissal preservation are pinned; other editable fields can still be lost on dismiss while the suite stays green. | LAX |
| AC5 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L42) and refined at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L284) | Error-contract tests in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L821-L965) | Yes. The narrowed 409->refetch->404, force-save 422, and force-save generic error paths each require visible validation-message content using the current [runMutation](serve/cockpit/web/src/components/DetailTab.tsx#L174-L205) branches. | COVERED |
| AC6 at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L43) | Harness note at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L34-L38), wrapper at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L141-L154), helper at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L246-L250) | No. The comments describe the required parent rerender path, but no executable assertion proves that rerender occurred. | LAX |

#### Security Review
- No issues in the scoped files.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| Current `TestFromAC_*` blocks in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx) | No weakened or removed assertions are visible in the current snapshot. I confirmed two task-local test-writer commits in [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L2315) and [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L2318), but I could not run a diff-backed immutability check in this tool surface. | PRESERVED (low confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact field, payload, and message assertions across [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L265-L404), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L535-L741), and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L821-L965). |
| Negative/error-path coverage | STRONG | Acknowledgment-gate negatives plus narrowed conflict-flow error cases in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L498-L530) and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L821-L965). |
| Manual mutation reasoning | WEAK | A builder can suppress [onTaskUpdated?.(latestTask)](serve/cockpit/web/src/components/DetailTab.tsx#L186) and still satisfy AC1/AC3/AC6, and AC2/AC4 still go green with title/priority-only comparison or dismiss preservation. |
| Test independence | STRONG | Each describe block unstubs globals after execution in [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L261-L262), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L413-L414), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L494-L495), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L753-L754), and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L817-L818). |
| Descriptive names | STRONG | Test names map cleanly to the contract blocks. |

#### Data Safety
- No new data-safety issue is introduced by the suite itself. The local-edit-loss path in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L66-L74) plus the 409 refresh path in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L183-L190) is the intended RED target.

#### Implementation-Aware Gaps
- Missing executable proof that the latest-task refresh is applied before preservation assertions. The suite models the wrapper but never proves the refresh crossed the parent boundary.
- AC2 comparison coverage is limited to title/priority.
- AC4 dismiss-preservation coverage is limited to title/priority.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Approach variation | N/A — test-pass-through verification only |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The prior AC5 rejection basis is stale. The live task body narrowed AC5 in [Architecture Review (Cycle 2)](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L272-L284), and the current suite satisfies that refined scope.
- I could not independently run a scoped git-status contamination check in this tool surface. I treated that as a small confidence deduction rather than the gating defect.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | The contract explicitly requires a refreshed-task prop rerender at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L38); the suite uses [StatefulWrapper](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L141-L154) but only waits for modal visibility in [triggerConflictModal](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L246-L250). | Preservation block at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L265-L404) | FAIL |
| AC2 | Current proof covers only title/priority comparison nodes, not the broader differing-field contract at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L39). | Comparison tests at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L417), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L434), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L451), [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L469) | FAIL |
| AC3 | Payload assertions are exact, but they do not close AC1's false-green path. | Overwrite gate/payload block at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L498-L741) | FAIL |
| AC4 | The dismiss contract at [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L41) is only pinned for title/priority. | Dismiss tests at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L757) and [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L786) | FAIL |
| AC5 | The narrowed conflict-flow error scope is now correctly tested. | Error-contract tests at [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L821-L965) | PASS |
| AC6 | quality-runner proves the suite is RED, but the rerender-path proof required to avoid false-green is still only documented, not executable. | quality-runner report plus [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L34-L38) | FAIL |

### Confidence: 0.80
### Verdict: FAIL

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC1/AC6 and the task guidance so the suite must execute and prove that the 409 refetch applied the refreshed task prop before preservation assertions run. | [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md); [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx); [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx) | AC1 at [task line 38](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L38), wrapper at [test line 141](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L141), helper at [test line 246](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L246), refresh callback at [DetailTab.tsx line 186](serve/cockpit/web/src/components/DetailTab.tsx#L186). |
| 2 | architect | Clarify whether AC2 and AC4 require comparison and dismiss-preservation proof for all differing editable fields or explicitly narrow that contract, then re-dispatch test writing against the clarified scope. | [.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md); [serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx) | AC2 at [task line 39](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L39), AC4 at [task line 41](.owlbear/kanban/tasks/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L41), current proof only at [test line 417](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L417), [test line 434](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L434), [test line 451](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L451), [test line 469](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L469), [test line 757](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L757), and [test line 786](serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx#L786). |
[[2026-05-09]]

## Architecture Review (Cycle 3)

### Follow-up Resolution

**Follow-up 1 — AC1/AC6 false-green path (onTaskUpdated suppression):**
The reviewer identified that `triggerConflictModal` only waits for `conflict-modal` to appear. In the live 409 path (`DetailTab.tsx:182-191`), `setShowConflict(true)` runs unconditionally after the refetch — even if `onTaskUpdated?.(latestTask)` is removed. Since `StatefulWrapper` only re-renders (triggering the useEffect reset) when `onTaskUpdated` fires, a builder who removes that call would get a trivial false-green: the modal appears, but the form was never reset, so preservation assertions pass vacuously.

**Fix:** Require an `onTaskUpdated` spy assertion in AC1 tests. The spy proves the refetch delivery crossed the parent boundary, which means the useEffect reset path was exercised. Without this, the test harness documents the re-render path but never proves it executed.

**Follow-up 2 — AC2/AC4 field scope ambiguity:**
AC2 said "for fields that differ" (generic) but tests only prove title and priority comparison. AC4 said "must not discard pending edits" (generic) but tests only prove title and priority dismiss-preservation. The reviewer asked the architect to either expand coverage or narrow the contract.

**Decision: Narrow to representative fields.** Title (text input) and priority (select input) are two distinct input types that drive the implementation pattern. Once the conflict modal renders comparison rows for these two types, the pattern generalizes to all fields. AC1 already exhaustively tests all 6 fields for preservation via the 409 refetch path, so adding body/depends_on/parent/block_reason to AC2/AC4 would be redundant with AC1's proof. The narrowing makes the contract coherent with the existing 23-test suite.

### Refined AC Lines (supersede originals)

- AC1: Tests prove local edits (title, priority, body, depends_on, parent, block_reason) are preserved in the form when a 409 conflict response triggers a latest-task refresh. Each preservation test must assert that the `onTaskUpdated` callback was invoked with the server's refreshed task (proving the refetch delivery crossed the parent boundary and the useEffect reset path was exercised) AND that form fields retain the user's entered values, not the server's refreshed values. (td:2)
- AC2: Tests prove the conflict modal renders identifiable remote (server) and local (user) values for fields that differ. At minimum, assert `data-testid` patterns `conflict-remote-{field}` and `conflict-local-{field}` for title and priority — two distinct input types that drive the comparison-rendering pattern. (td:2)
- AC3: (unchanged) Tests prove force-save requires an explicit overwrite acknowledgment step (not immediately available when the conflict modal first appears) and, when executed, sends the user's preserved local form values in the request payload — not the server's refreshed values. (td:2)
- AC4: Tests prove canceling or dismissing conflict resolution via the available close affordance restores the form to the user's pre-conflict local edits. At minimum, assert title and priority preservation after dismiss — AC1 exhaustively covers all 6 fields via the 409 refetch path. (td:2)
- AC5: (unchanged, per cycle 2 narrowing) Tests prove mutation errors in the conflict-resolution flow produce user-visible messages using the frontend error contract from #1375 (`getResponseErrorMessage()`): 409→refetch→404 (task deleted between save and refresh), force-save retry 422, and force-save retry generic unexpected errors. Direct mutation 404 clearing behavior and initial-save generic errors are not conflict-resolution scope. (td:2)
- AC6: Tests fail against the current reset-then-force behavior in DetailTab.tsx and are suitable as RED-phase targets for #1383. RED verification must include an executable `onTaskUpdated` spy assertion proving the parent re-render path was exercised — not just a harness comment. (td:1)

### Builder Guidance Addition — onTaskUpdated Spy Pattern

The `StatefulWrapper` already accepts an `onTaskUpdated` prop that is called when `DetailTab` invokes the callback. To close the false-green path:

```tsx
const onTaskUpdatedSpy = vi.fn()
render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)
// ... edit + trigger conflict ...
expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
  expect.objectContaining({ updated: SERVER_TASK.updated })
)
// ... then assert form field preservation ...
```

This assertion must appear in AC1 preservation tests (all 6 field tests) and transitively satisfies AC6's executable false-green prevention requirement. AC3 force-save payload tests inherit the proof because they share the same `triggerConflictModal` → `onTaskUpdated` flow.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Targeted AC refinement only — one concern per follow-up |
| Interface clarity | PASS | AC lines now have verifiable, non-ambiguous scope |
| Dependency correctness | PASS | #1381 and #1375 still done |
| Module layering | N/A | Test task |
| TDD compliance | PASS | Existing 23-test suite needs only the onTaskUpdated spy addition |
| KISS/YAGNI | PASS | Narrowing AC2/AC4 removes redundant proof requirements |
| Premise challenge | PASS | False-green path confirmed via code read of DetailTab.tsx:182-191 |
| Pattern consistency | PASS | Spy pattern matches existing vitest conventions in the suite |
| Security surface | N/A | Test task |
| Single domain | PASS | Cockpit frontend only |

### Challenger
Skipped — cycle 3 AC reconciliation responding to specific reviewer follow-ups. Changes are scope-narrowing refinements and a harness-tightening addition, not architectural. Challenger was run in cycle 1 and all concerns were addressed.

### Verdict: APPROVE
AC1/AC6 refined with onTaskUpdated spy requirement closing the false-green path. AC2/AC4 narrowed to title+priority representative fields. Existing 23-test suite needs minimal additions (spy assertions in 6 AC1 tests). No other AC lines affected.
[[2026-05-09]]
Cycle 3 AC reconciliation: (1) AC1/AC6 refined — added onTaskUpdated spy assertion requirement closing the false-green path where suppressing the callback lets tests pass without exercising the useEffect reset; (2) AC2/AC4 narrowed to title+priority representative fields, matching existing 23-test suite and removing redundant proof requirements (AC1 already exhaustively covers all 6 fields). Existing suite needs only onTaskUpdated spy additions in 6 AC1 tests. No architectural changes.
[[2026-05-09]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`
- Classes:
  - `TestFromAC_ConflictLocalEditsPreserved` (AC1 — 6 tests)
  - `TestFromAC_ConflictModalComparison` (AC2 — 4 tests)
  - `TestFromAC_ForceSaveAcknowledgmentGate` (AC3 — 8 tests)
  - `TestFromAC_ConflictCancelPreservesEdits` (AC4 — 2 tests)
  - `TestFromAC_ConflictErrorContract` (AC5 — 3 tests)
- Tests per category: happy 10, edge 11, error 2, boundary 0
- Total: 23 tests, all FAIL (0 pass)
- ESLint: clean (exit 0)

Retry cycle 3 changes:
- Added `onTaskUpdatedSpy = vi.fn()` to all 6 AC1 preservation tests, passing it to `StatefulWrapper` and asserting `expect(onTaskUpdatedSpy).toHaveBeenCalledWith(expect.objectContaining({ updated: SERVER_TASK.updated }))` after `triggerConflictModal`.
- Spy closes the false-green path identified by reviewer: a builder who suppresses `onTaskUpdated?.(latestTask)` (DetailTab.tsx:186) would avoid the useEffect reset, making preservation assertions pass without fixing the bug. The spy assertion catches that shortcut.
- Body test (test 4) adds spy before the dismiss flow; the spy correctly calls `SERVER_TASK_BODY_ONLY.updated`.
- All 23 tests remain RED — spy assertion currently PASSES against live code (DetailTab does call `onTaskUpdated`), but preservation assertions FAIL due to the useEffect reset bug. Suite is a valid RED implementation target for #1383.

AC coverage table (refined AC5 per architect cycle-2, AC1/AC2/AC4 per architect cycle-3):
| AC | Tests | Failure reason |
|----|-------|----------------|
| AC1 | 6 | useEffect resets all 6 fields to server values after re-render; spy closes false-green path |
| AC2 | 4 | `conflict-remote-*` and `conflict-local-*` elements absent from conflict modal DOM |
| AC3 | 8 | `conflict-acknowledge` element missing; force-save payload carries server-reset values |
| AC4 | 2 | conflict-refresh IS found; but form shows server-reset values after dismiss |
| AC5 | 3 | 409→404: no validation-message; force-save 422/500: conflict-acknowledge gate missing |
| AC6 | — | Transitively satisfied — all 23 tests fail; spy proves re-render path is executable |
[[2026-05-09]]
## Builder Notes
- Task classification: `type:test` pass-through; no production implementation changes required.
- Files changed: none.
- Verification (quality-runner scoped): `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` -> 0 passed, 23 failed, 0 skipped.
- Failure type: assertion-level RED failures (no harness/runtime crashes). Representative evidence: local title/priority/body/block_reason and depends_on are reset to server values after 409 refetch parent re-render.
- Lint: clean (`eslint` violations: 0 on `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`).
- Coverage: not emitted by the scoped frontend run.
- Evidence summary: suite remains an intentional RED target for implementation task #1383 and includes the cycle-3 `onTaskUpdated` spy requirement to prevent false-green on callback suppression.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`: 0 passed, 23 failed, 0 skipped.
- One initial quality-runner attempt failed with an environment error (`HTMLElement is not defined`) because Vitest was launched outside `serve/cockpit/web/`; the required retry from the package directory succeeded and confirmed jsdom execution.
- All 23 failures are assertion-level RED failures against the current conflict-resolution behavior in `serve/cockpit/web/src/components/DetailTab.tsx`, not harness/runtime crashes. Representative failures: preserved fields reset to server values after 409 refetch, conflict comparison nodes absent, immediate `conflict-overwrite` with no `conflict-acknowledge`, and no `validation-message` on 409->refetch->404.

### Lint Results
- Clean. quality-runner reported 0 ESLint violations for `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` and `serve/cockpit/web/src/components/DetailTab.tsx`.
- VS Code diagnostics: no TypeScript errors in either file.

### Coverage
- Not emitted by the scoped frontend RED run. Non-blocking for this `type:test` pass-through review because the suite intentionally remains RED and the gate here is AC proof quality, not green-path coverage.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: preserve title, priority, body, depends_on, parent, and block_reason after 409 -> refetch -> parent rerender | `StatefulWrapper` reproduces the parent rerender path in `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`, and all 6 preservation cases now assert `onTaskUpdated` with the refreshed task before checking exact preserved local values or payloads. The live reset remains in `serve/cockpit/web/src/components/DetailTab.tsx` `useEffect([task?.id, task?.updated])`, so these tests are valid RED targets. | PASS |
| AC2: render identifiable remote/local values for differing fields | The suite asserts `conflict-remote-title`, `conflict-local-title`, `conflict-remote-priority`, and `conflict-local-priority` with exact content checks. The live conflict modal still renders none of those nodes. | PASS |
| AC3: explicit overwrite acknowledgment gate plus preserved local payload on force-save | The suite proves overwrite is absent initially, requires acknowledgment before overwrite appears, and asserts exact local payload values for title, priority, body, depends_on, parent, and block_reason. Current `DetailTab.tsx` still exposes immediate overwrite and reuses reset state in force-save payloads. | PASS |
| AC4: available close affordance must not discard pending edits | The suite uses the actual live close affordance `conflict-refresh` and asserts exact preservation for title and priority after dismiss. Current code still shows server-reset values after dismiss. | PASS |
| AC5: conflict-flow `getResponseErrorMessage()` coverage for 409->refetch->404, force-save 422, and force-save generic error | The suite contains dedicated tests for each refined AC5 path with exact `validation-message` assertions, matching the current `runMutation()` branches in `DetailTab.tsx`. Direct mutation 404 clearing and initial-save generic errors remain correctly out of scope after the cycle-2 AC narrowing. | PASS |
| AC6: RED verification reproduces parent rerender path and fails against current reset-then-force behavior | The AC1 spy-bearing preservation tests provide executable proof that the 409 refetch crossed the parent boundary before assertions ran. quality-runner confirms the current implementation still fails all 23 expectations. | PASS |

### Test Integrity
- code-reader found no weakened or removed `TestFromAC_*` assertions in the current snapshot.
- The static audit found no AC-owned test gaps under the refined cycle-2/cycle-3 contract. One non-blocking robustness note remains: AC3/AC4 inherit the rerender proof from AC1/AC6 rather than duplicating a local spy assertion, but the refined task contract explicitly allows that inheritance.

### Deductions
- -0.03: No diff-backed commit evidence was available in this tool surface for a high-confidence TestFromAC immutability check against the original test-writer snapshot.
- -0.02: I could not independently run the scoped `git status --porcelain` contamination check in this tool surface. No diagnostics or execution evidence suggested overlapping dirty-state contamination, but that check remains unverified.

### Verdict
- PASS. Confidence: 0.95.
- Action: advance to docs. The suite executes in the correct frontend environment, fails for the intended live defects, and satisfies the refined acceptance contract without remaining blocking proof gaps.
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only task; no behavior, API, CLI, or config changes — no prose docs reference test internals |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Task body cites no external patterns |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches `DetailTab_1382.test.tsx`; footer updated from `2026-05-09 (61cd4d6d)` → `2026-05-10 (819b56ed)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx | OUT (test file — not IN-scope doc) | N/A |
| share/diagrams/cockpit.excalidraw | IN (diagram, describes-match) | Footer updated |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: `Last verified: 2026-05-10 (819b56ed)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- .owlbear/scratch/qr-1382-output.txt
- .owlbear/scratch/qr-1382-run.txt
- .owlbear/scratch/qr-1382-scoped.txt
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: Python 4374 passed / 222 failed / 10 errors; Frontend 1194 passed / 23 failed / 9 skipped. The 23 frontend failures are all in DetailTab_1382.test.tsx (intentional RED). The 222 Python failures and 10 import errors are pre-existing — this task changed zero Python files (3 commits all touch only the frontend test file). All 74 other frontend test files pass.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (3 test-writer commits: 21852627, 618be6ec, 65dbedb2 — each touches only serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx. 1 doc-writer commit: 4af8d62b — touches only share/diagrams/cockpit.excalidraw. No extraneous files.)
- purpose match: PASS (RED-phase conflict-resolution tests for the cockpit task detail editor, matching stated purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Initial AC was specific and well-structured with test-depth annotations, false-green prevention guidance, and builder guidance. However, AC5 contained an internal contradiction (requiring both RED-only behavior and a test that would be GREEN against current code), and AC1/AC6 lacked the onTaskUpdated spy requirement to close the false-green path. Both issues required reviewer feedback across 3 architect cycles to resolve. The final refined AC is clean, specific, and complete — scoring 4 for requiring iterative correction rather than delivering a clean contract on first pass.

### Commit Integrity
- upstream commit presence: PASS (3 test-writer commits verified via git log and git diff --stat; 1 doc-writer commit for diagram footer update; git status --porcelain shows no uncommitted changes)
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
No deductions apply:
- Regression detection: no cross-task regressions (0)
- Intent verification: clean scope alignment (0)
- Lint: task file clean; pre-existing violations in unrelated files (0)
- AC quality: 4/5 (>3 threshold) (0)
- Reviewer evidence: present and detailed with AC compliance table (0)
- Commit integrity: all commits verified (0)

### Confidence: 1.00
### Action: archive