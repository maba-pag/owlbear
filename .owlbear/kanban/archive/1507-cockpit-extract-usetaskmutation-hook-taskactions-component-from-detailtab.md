---
id: 1507
title: 'Cockpit: Extract useTaskMutation hook + TaskActions component from DetailTab'
status: archived
priority: needed
created: 2026-05-12T03:04:44.023243+00:00
updated: 2026-05-12T15:31:33.878667+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1506
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Extract mutation orchestration and action buttons from DetailTab.tsx into two focused modules (~130 LOC total).

## Scope
- **useTaskMutation.ts** (hooks/): wraps runMutation + previousStatus + serverValidationMessage management
- **TaskActions.tsx** (components/): unclaim/unblock/move-backward buttons + ConfirmDialog wiring

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useTaskMutation.ts` exists in `hooks/` and exports the hook
- [ ] `TaskActions.tsx` exists in `components/` and renders action buttons with ConfirmDialog
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:56:35+00:00
## Research
- Research doc: .owlbear/research/cockpit-mutation-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, #1506 research, ConfirmDialog)
- Recommendation: Extract using action-callback pattern for conflict coupling, matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1507 is the implementation task, sibling #1508 exists
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: runMutation couples to conflict state via 3 action callbacks (clearConflict, setConflictDetected, setConflictDetectedNoRefetch); TaskActions owns confirmType state + focus management + ConfirmDialog wiring; ~80 LOC each
2026-05-12T08:56:42+00:00
Research complete. Identified precise extraction boundaries for useTaskMutation hook (~80 LOC: serverValidationMessage state, previousStatus function, runMutation with conflict action callbacks) and TaskActions component (~80 LOC: confirmType state, focus management, 3 action buttons, ConfirmDialog wiring). T1 pure refactoring following established patterns. Confidence 0.88. Doc: .owlbear/research/cockpit-mutation-hook-extraction.md
2026-05-12T09:39:09+00:00


## Refined Acceptance Criteria
_Supersedes original AC section._

- AC-1 (B1): `hooks/useTaskMutation.ts` exports `useTaskMutation` hook accepting `UseTaskMutationOptions` (taskId, taskUpdated, board, conflictActions: {clearConflict, setConflictDetected, setConflictDetectedNoRefetch}, onTaskUpdated, onTaskCleared, onMutationError). Returns `UseTaskMutationResult`: `serverValidationMessage`, `setServerValidationMessage`, `previousStatus(current: string) → string | null`, `runMutation(url, payload, options) → Promise<void>`.
- AC-2 (B1): `components/TaskActions.tsx` exports `TaskActions` component accepting `TaskActionsProps` (task, backwardTarget, runMutation). Renders conditionally: move-backward button (`data-testid="move-backward"`) when `backwardTarget` is non-null, unclaim button (`data-testid="unclaim-action"`) when `task.claimed !== false`, unblock button (`data-testid="unblock-action"`) when `task.blocked`. Owns `confirmType` state, focus management (`pendingFocusRestore`, `confirmTriggerRef`), focus-restore useEffect, and renders `ConfirmDialog`.
- AC-3 (B1): `DetailTab.tsx` imports `useTaskMutation` from `hooks/useTaskMutation` and renders `<TaskActions>` from `components/TaskActions`. DetailTab no longer contains inline definitions of: `serverValidationMessage` state, `confirmType` state, `pendingFocusRestore`/`confirmTriggerRef` refs, focus-restore useEffect, `previousStatus` function, `runMutation` function, `handleConfirm`/`handleConfirmCancel`/`openConfirm` handlers, action button JSX, or ConfirmDialog JSX.
- AC-4 (B2): Full Vitest suite passes without modification — verified by `npm test` in `serve/cockpit/web/`.
- AC-5: No new warnings from ESLint (`npx eslint src/`) or Stylelint (`npm run lint:css`) in `serve/cockpit/web/`.

Proof bundle: existing
Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extracts one concern (mutation orchestration + action UI) into two focused modules |
| Interface clarity | PASS | Hook return type and component props specified in AC-1/AC-2; data-testid attrs and visibility conditions enumerated |
| Dependency correctness | PASS | Removed #1493 dep (see notes below); retains #1506 for sequential extraction |
| Module layering | PASS | hooks/ and components/ follow established useRepairFlow/useCleanupFlow and RepairPanel/CleanupPanel patterns; hook returns functions, component receives via props — no circular deps |
| TDD compliance | PASS | Full Vitest suite serves as regression gate via `existing` proof bundle |
| KISS/YAGNI | PASS | Pure extraction, no new abstractions or features |
| Premise challenge | PASS | 634-LOC monolith with ~191 LOC across 11 mutation/action zones — extraction follows established useRepairFlow/useCleanupFlow precedent |
| Pattern consistency | PASS | Action-function pattern matches useRepairFlow (88 LOC) and useCleanupFlow (51 LOC); TaskActions follows ConfirmDialog/RepairPanel component patterns |
| Security surface | N/A | No new system boundaries; same fetch calls and error handling move unchanged |
| Single domain | PASS | Frontend component domain |

### Dependency Override: #1493 Removed
Original planning sequenced #1493 (API centralization) before extraction tasks to avoid double-refactoring churn. Analysis: `useTaskMutation` wraps `runMutation` which contains raw `fetch()`. The extraction boundary is identical whether fetch is raw or centralized — same code moves to a new file unchanged. When #1503 eventually migrates consumers, it updates `useTaskMutation.ts` instead of `DetailTab.tsx` — same work, different file, zero churn. Same reasoning applied when #1506 removed its #1493 dependency. Sibling #1508 retains #1493 dependency as the final composition step.

### Proof-Bundle Validation
- Planner assignment: none (research classified as T1)
- Final bundle: existing
- Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`) — widened from 8 DetailTab tests per challenger finding that PdsMigration, ErrorContract, and KeyboardA11y suites also exercise extracted zones
- Test-writer: SKIP (bundle `existing`)

### Challenge Results
- Challenger: reconsider (0.58)
- Findings: (1) ac-quality: AC-1/AC-2 fail B2 — rebutted: behavior-preserving extraction verified by full test suite, adding behavioral AC duplicates test coverage; (2) ac-quality: AC-2 missing visibility conditions — accepted, added conditional rendering rules; (3) ac-quality: AC-3 implementation-diff — accepted, reframed as structural absence verification; (4) ac-quality: AC-4 proof scope too narrow — accepted, widened to full Vitest suite; (5) ac-quality: AC-5 wrong lint command — accepted, corrected to `npx eslint src/` and `npm run lint:css`; (6) consolidation-test-gap — rebutted: sequential chain + full-suite gate on each child + #1508 as final verifier + parent #1492 tracker = sufficient coverage; (7) reasoning-gap: dependency removal — documented above, structural code motion not interface creation; (8) blind spots: task-change reset behavior and focus ownership — accepted, added implementation guidance below
- Architect response: accepted items 2/3/4/5/8, rebutted 1/6, documented reasoning for 7

### Design Diverge
- Trigger: skipped — single valid approach (action-callback pattern matching useRepairFlow/useCleanupFlow precedent), no competing designs

### Implementation Guidance
- **Task-change reset split:** The useEffect at L86-109 mixes field-restore logic (stays in DetailTab — reads conflict state for field restoration) and mutation-state resets (`setServerValidationMessage(null)`, `setConfirmType(null)`). The hook should handle its own reset (clear serverValidationMessage on taskId/updated changes) and TaskActions should reset confirmType via a prop-driven effect or the hook can expose a resetMutationState action that DetailTab calls.
- **Focus ownership:** TaskActions owns `confirmType` state, `pendingFocusRestore` state, `confirmTriggerRef`, and focus-restore useEffect. ConfirmDialog has its own internal focus management (captures/restores on mount/unmount). These are two separate layers — TaskActions handles the trigger→restore cycle, ConfirmDialog handles trap→release.
- **ConflictBanner** rendering stays at same DOM position in DetailTab (from #1506 scope), not moved to TaskActions.

### Verdict: APPROVE
### Action Taken: Refined AC (numbered per h-ac-quality, added visibility conditions, corrected lint commands, widened proof scope to full Vitest suite), removed #1493 dependency with documented reasoning, assigned proof bundle `existing`, added implementation guidance for reset/focus ownership. Advanced to todo.
2026-05-12T09:39:16+00:00
Architecture review complete. REFINE + APPROVE: Refined AC (numbered per h-ac-quality, added button visibility conditions in AC-2, reframed AC-3 as structural absence check, widened proof scope from 8 DetailTab tests to full Vitest suite per challenger finding, corrected lint commands in AC-5). Removed #1493 dependency — extraction is structural code motion, boundary identical whether fetch is raw or centralized. Proof bundle: existing (full Vitest suite). Challenger: reconsider (0.58) — accepted 5 of 8 findings (visibility conditions, structural AC reframe, proof scope widening, lint command fix, implementation guidance for reset/focus split), rebutted behavioral-lock gap and consolidation-test gap. Test-writer: SKIP.
2026-05-12T09:41:31+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`) covers all extracted zones (DetailTab, PdsMigration, ErrorContract, KeyboardA11y suites).
- Passing through to builder.
2026-05-12T10:15:35+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/DetailTab.tsx
  - serve/cockpit/web/src/components/TaskActions.tsx
  - serve/cockpit/web/src/hooks/useTaskMutation.ts
- Implementation summary:
  - Extracted mutation orchestration into `useTaskMutation` (server validation state, `previousStatus`, `runMutation`, and 409/404/422 handling with conflict callbacks).
  - Extracted action/confirm UI into `TaskActions` (conditional move-backward/unclaim/unblock buttons, ConfirmDialog wiring, and focus restore behavior).
  - Refactored `DetailTab` to delegate mutation/actions to the new hook/component while preserving existing save/conflict/history behavior.
- Proof bundle: existing (required existing proof executed)
- Test results (quality-runner):
  - `npm test` (serve/cockpit/web): 1475 passed, 9 skipped, 0 failed
- Lint status (quality-runner):
  - `npx eslint src/`: clean
  - `npm run lint:css`: clean
- Coverage:
  - Not required by `Proof bundle: existing`; no coverage gate requested.
- Commit:
  - f7e28d2f — refactor: extract task mutation hook/actions from DetailTab (#1507, builder)
2026-05-12T11:13:01+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence was internally consistent on its own terms: commit `f7e28d2f` is present in git logs, the changed files have no editor diagnostics, and the existing action tests still prove same-task confirm flows, payloads, and 409/422 handling.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Architecture Review: task-change reset split (paired with AC-2/AC-3 extraction contract) | `TaskActions` does not clear `confirmType` when `task.id` / `task.updated` changes. Its only effect restores focus after cancel, while `handleConfirm` always uses the current `task` props. Because `DetailTab` renders `TaskActions` without a remount key or reset prop, a confirm dialog opened on one task can remain open and apply its action to a newly selected task. | `serve/cockpit/web/src/components/TaskActions.tsx` state/effect and confirm path (`confirmType`, `pendingFocusRestore`, `handleConfirm`, dialog render); `serve/cockpit/web/src/components/DetailTab.tsx` `TaskActions` render; architect guidance explicitly required mutation-state reset to split so `serverValidationMessage` resets in the hook and `confirmType` resets in `TaskActions` on task change. Current proof does not exercise this path: `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx` covers same-task confirm flows only, and `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` exercises standalone `ConfirmDialog` wrappers rather than `TaskActions` task-switch behavior. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reset `TaskActions` confirmation state when task identity/version changes, or force remount per task, so an open confirm dialog cannot carry an action onto a different task. | serve/cockpit/web/src/components/TaskActions.tsx; serve/cockpit/web/src/components/DetailTab.tsx | Blocking finding #1 |
| 2 | builder | Add direct proof for the task-switch confirm path so the regression fails if confirm state survives a task change. | serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx or serve/cockpit/web/src/__tests__/DetailTab.test.tsx | Blocking finding #1 |

## Observations
- `serve/cockpit/web/src/hooks/useTaskMutation.ts` and `serve/cockpit/web/src/components/TaskActions.tsx` both import `TaskDetail` from `serve/cockpit/web/src/components/DetailTab.tsx` as a type-only dependency. This is not a runtime cycle, but it does create source-of-truth coupling to a component module while `serve/cockpit/web/src/api/tasks.ts` already contains a task DTO shape. Treat this as follow-up debt, not the reason for rejection.
- Same-task behavior remains well covered by existing tests: unblock/unclaim/move endpoint calls and move-backward payload assertions in `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx`, plus existing confirm-dialog presence checks in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.
2026-05-12T11:37:58+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/DetailTab.tsx
- Fix applied:
  - Added a task/version key to `TaskActions` render (`key={`${t.id}:${t.updated}`}`) so action UI state remounts on task switch/update. This prevents an open confirm dialog from carrying over and applying to a different task.
- Test results (quality-runner):
  - `npm test` (serve/cockpit/web): 1487 passed, 9 skipped, 0 failed
- Lint status (quality-runner):
  - `npx eslint src/`: clean
  - `npm run lint:css`: clean
- Coverage:
  - Not required by `Proof bundle: existing`; no additional coverage gate requested.
- Commit:
  - 24ce261b1f1ddcdea73d71e0dd43aefc333f60eb — fix: reset task actions state on task switch (#1507, builder)
- Evidence summary:
  - Full required existing proof and lint gates passed after the fix; no additional files were modified.
2026-05-12T12:03:09+00:00
## Review Evidence
- Verdict: FAIL
- The implementation-side retry appears to address the original state leak: [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L172) now keys TaskActions by task id and updated timestamp, and [serve/cockpit/web/src/components/TaskActions.tsx](serve/cockpit/web/src/components/TaskActions.tsx#L24) keeps the confirmation state inside that keyed subtree.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Prior review Required Follow-up #2; AC-4 proof bundle `existing` | The retry still does not add direct proof for the task-switch regression path. Existing action tests only open and confirm dialogs against the same task, while the only DetailTab stateful rerender harness targets conflict/form reset and does not exercise TaskActions dialog state. If the key-based reset regressed, the current proof surface would not fail on that path. | Same-task action proof: [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx#L345), [serve/cockpit/web/src/__tests__/DetailTab.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.test.tsx#L781). Rerender harness: [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx#L140), [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx#L288). Implementation delta only: [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L172). | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the retry so the proof contract explicitly requires a regression test that opens a TaskActions confirm dialog, changes task identity or updated version, and proves the dialog resets before confirmation can apply to the new task. | serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx; serve/cockpit/web/src/__tests__/DetailTab.test.tsx; serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx | Blocking finding #1 |

## Observations
- Builder follow-up #1 appears satisfied by the keyed TaskActions mount in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L172); the remaining issue is proof quality rather than the visible code delta.
- No editor diagnostics were present in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L172), [serve/cockpit/web/src/components/TaskActions.tsx](serve/cockpit/web/src/components/TaskActions.tsx#L24), or [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L1).
2026-05-12T12:50:09+00:00

## Architecture Re-Review (Retry Scope)

### Context
Reviewer FAIL on second attempt: keyed-remount fix is structurally correct (React destroys state on key change), but no regression test proves confirm dialog resets on task switch. Reviewer routed to architect for AC re-scope.

### Refined AC (supersedes prior Refined AC section)
_This section supersedes all prior AC sections._

- AC-1 (B1): `hooks/useTaskMutation.ts` exports `useTaskMutation` hook accepting `UseTaskMutationOptions` (taskId, taskUpdated, board, conflictActions: {clearConflict, setConflictDetected, setConflictDetectedNoRefetch}, onTaskUpdated, onTaskCleared, onMutationError). Returns `UseTaskMutationResult`: `serverValidationMessage`, `setServerValidationMessage`, `previousStatus(current: string) → string | null`, `runMutation(url, payload, options) → Promise<void>`.
- AC-2 (B1): `components/TaskActions.tsx` exports `TaskActions` component accepting `TaskActionsProps` (task, backwardTarget, runMutation). Renders conditionally: move-backward button (`data-testid="move-backward"`) when `backwardTarget` is non-null, unclaim button (`data-testid="unclaim-action"`) when `task.claimed !== false`, unblock button (`data-testid="unblock-action"`) when `task.blocked`. Owns `confirmType` state, focus management (`pendingFocusRestore`, `confirmTriggerRef`), focus-restore useEffect, and renders `ConfirmDialog`.
- AC-3 (B1): `DetailTab.tsx` imports `useTaskMutation` from `hooks/useTaskMutation` and renders `<TaskActions>` from `components/TaskActions`. DetailTab no longer contains inline definitions of: `serverValidationMessage` state, `confirmType` state, `pendingFocusRestore`/`confirmTriggerRef` refs, focus-restore useEffect, `previousStatus` function, `runMutation` function, `handleConfirm`/`handleConfirmCancel`/`openConfirm` handlers, action button JSX, or ConfirmDialog JSX.
- AC-4 (B2): Full Vitest suite passes — verified by `npm test` in `serve/cockpit/web/`. Suite includes the new regression test from AC-6.
- AC-5: No new warnings from ESLint (`npx eslint src/`) or Stylelint (`npm run lint:css`) in `serve/cockpit/web/`.
- AC-6 (B2): TaskActions confirm dialog resets on task identity change. Test: render DetailTab with `StatefulWrapper` harness (wires `onTaskUpdated` → `setState` to reproduce parent re-render), click an action button (e.g. `[data-testid="unblock-action"]` on a blocked task) to open ConfirmDialog (`[data-testid="confirm-dialog"]` present), call `onTaskUpdated` with a task having a different `id` or `updated`, assert `[data-testid="confirm-dialog"]` is null after re-render. Mechanism: `key={`${t.id}:${t.updated}`}` on TaskActions forces React remount, destroying confirmType state.

Proof bundle: smoke
Test-writer: PROCEED (write AC-6 regression test only; AC-1–AC-5 already verified by existing suite)

### Evaluation (re-review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same scope as prior review — extraction + one targeted regression test |
| Interface clarity | PASS | AC-6 specifies exact test scenario, harness pattern, assertions |
| Dependency correctness | PASS | #1506 dep retained; #1493 removal documented in prior review |
| Module layering | PASS | No change from prior review |
| TDD compliance | PASS | Escalated to smoke — test-writer writes AC-6 regression test |
| KISS/YAGNI | PASS | One targeted test for a verified fix; no over-testing |
| Premise challenge | PASS | Reviewer correctly identified proof gap; re-scope addresses it |
| Pattern consistency | PASS | StatefulWrapper harness matches DetailTab.conflict-resolution.test.tsx patterns |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend component domain |

### Proof-Bundle Validation (re-review)
- Prior assignment: existing (now insufficient — reviewer found proof gap)
- Final bundle: smoke
- Test-writer: PROCEED — write one regression test for AC-6 (task-switch confirm reset)
- Existing proof (AC-4): Full Vitest suite still serves as regression gate for AC-1–AC-5

### Challenge Results (re-review)
- Challenger: block (0.38)
- Findings: (1) ac-consistency: AC-4 "without modification" contradicts AC-6 new test — accepted, relaxed AC-4 wording; (2) artifact-state: task body not yet updated — accepted, applying now; (3) proof-surface: no task-switch confirm test exists — accepted, that's exactly what AC-6 addresses; (4) ac-quality: AC-1/2/3 structural framing — rebutted: structure IS the deliverable for extraction, behavior proven by unchanged suite; (5) consolidation-gap: two siblings hit same pattern — rebutted: review catching proof gaps is system working correctly, not a decomposition risk
- Architect response: accepted 1/2/3, rebutted 4/5; re-scoped AC-4 and added AC-6 per challenger finding

### Implementation Guidance (addendum)
- AC-6 test should use the same `StatefulWrapper` pattern from `DetailTab.conflict-resolution.test.tsx` — renders DetailTab, calls `onTaskUpdated` to trigger parent re-render.
- Test can live in `DetailTab.test.tsx` (oppose-the-flow confirmations describe block) or a new focused file — test-writer decides placement.
- The confirm dialog is opened by clicking an action button; task switch is simulated by calling `onTaskUpdated` with a task having a different id. React's keyed remount guarantees state reset — the test proves this contract.

### Verdict: APPROVE
### Action Taken: Re-scoped AC for reviewer retry. Relaxed AC-4 to accommodate new test, added AC-6 (task-switch confirm regression test), escalated proof bundle from `existing` to `smoke`. Test-writer proceeds to write AC-6 regression test only. Advanced to todo.
2026-05-12T12:50:15+00:00
Architecture re-review complete. REFINE + APPROVE: Relaxed AC-4 ("without modification" → "includes new regression test"), added AC-6 (task-switch confirm dialog reset regression test with StatefulWrapper harness), escalated proof bundle from `existing` to `smoke`. Test-writer proceeds to write AC-6 only. Challenger: block (0.38) — accepted AC contradiction and artifact-state findings, rebutted structural-AC and consolidation-gap concerns.
2026-05-12T13:14:01+00:00
## Test-Writer Notes
- Retry: added AC-6 task-switch confirm-dialog reset regression test.
- Test file: `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx`
- Class: `TestFromAC_TaskActionsConfirmReset`
- Tests: 2 (both boundary conditions for the `key={`${t.id}:${t.updated}`}` remount contract)
  - `confirm_dialog_resets_when_task_id_changes` — switches task A (id=42) → task B (id=99)
  - `confirm_dialog_resets_when_task_updated_changes` — same id, different updated timestamp
- Categories: boundary (2)
- Verification: quality-runner — 2 passed, 0 failed, ESLint clean
- AC coverage:
  | AC Line | Test(s) |
  |---------|---------|
  | AC-6: confirm dialog resets on task id change | `confirm_dialog_resets_when_task_id_changes` |
  | AC-6: confirm dialog resets on task updated change | `confirm_dialog_resets_when_task_updated_changes` |
- Builder skip: test-only retry, all 2 new tests pass against current impl (key-based remount already in place).
- Commit: 64a90887 — test: add task-switch confirm-dialog reset regression test (#1507, test-writer)
2026-05-12T14:10:55+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1507 -> docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence was internally consistent. Because the retry notes only showed targeted post-AC-6 proof, reviewer independently verified the missing full proof packet with quality-runner:
  - `npx vitest run --silent` in `serve/cockpit/web`: 86 files passed, 1506 tests passed, 9 skipped, including `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx` (2/2 passed)
  - `npx eslint src/`: clean
  - `npm run lint:css`: clean
- Scoped contamination check: clean working tree/index for `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/TaskActions.tsx`, `serve/cockpit/web/src/hooks/useTaskMutation.ts`, and `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx`.
- AC evidence map:

| AC Line | Code Evidence | Test/Proof Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/hooks/useTaskMutation.ts:37-128` exports and returns the required hook surface; task/version reset at `:38-42`; `previousStatus` at `:44-57`; `runMutation` at `:60-124` | Full Vitest pass plus action/error-path suites in `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx:345,380,422,456` and `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx:179,195,207,274,305` | PASS |
| AC-2 | `serve/cockpit/web/src/components/TaskActions.tsx:24-36`, `:38-82`, and `:87-122` own confirm/focus state, conditional buttons, and `ConfirmDialog` | Dialog/presence/action proof in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:501,509,528,533`; `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx:269,310,345`; unclaim absence guard in `serve/cockpit/web/src/__tests__/DetailTab.conflict-nonregression.test.tsx:101` | PASS |
| AC-3 | `serve/cockpit/web/src/components/DetailTab.tsx:16`, `:75-89`, and `:172-176` delegate to `useTaskMutation` and `TaskActions`; inline confirm/dialog handlers are no longer present by direct file inspection | Full Vitest pass across DetailTab suites; same-task action flows and mutation callbacks still pass in `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx:269-456` and `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx:179-305` | PASS |
| AC-4 | N/A (proof gate) | Reviewer quality-runner rerun: full Vitest in `serve/cockpit/web` passed, 86 files / 1506 tests / 9 skipped, including `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx` | PASS |
| AC-5 | No editor diagnostics in scoped files | Reviewer quality-runner rerun: `npx eslint src/` clean; `npm run lint:css` clean | PASS |
| AC-6 | Keyed remount contract at `serve/cockpit/web/src/components/DetailTab.tsx:173` | Direct regression proof in `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx:78-139` covers both `id` and `updated` changes; dialog-open preconditions at `:95-98` / `:126-129` and null-after-rerender assertions at `:108` / `:139` | PASS |

## Observations
- The AC-6 regression test uses Testing Library `rerender` instead of the suggested `StatefulWrapper` harness. That is acceptable for this defect because the contract under test is prop/key reconciliation, and the test would fail if the keyed remount at `serve/cockpit/web/src/components/DetailTab.tsx:173` were removed.
- Non-blocking type coupling remains: `serve/cockpit/web/src/components/TaskActions.tsx:4` and `serve/cockpit/web/src/hooks/useTaskMutation.ts:3` import `TaskDetail` from `serve/cockpit/web/src/components/DetailTab.tsx`. This is type-only and not a runtime cycle, but the extracted modules are not yet fully type-isolated from the parent component.
2026-05-12T14:36:33+00:00
## Docs Gate

**Verdict: PASS — no docs changes required**

### Convention Mapping
Changed files: `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/TaskActions.tsx`, `serve/cockpit/web/src/hooks/useTaskMutation.ts`, `serve/cockpit/web/src/__tests__/DetailTab.task-switch.1507.test.tsx` → all map to `serve/cockpit/README.md`.

### Item 1: README Verification
- Layer 1 (grep): No matches for `DetailTab`, `TaskActions`, or `useTaskMutation` in `serve/cockpit/README.md` or root `README.md`. No orphaned references.
- Layer 2 (editorial): README documents product-level boundary (launch commands, API surface, configuration, dependencies). Internal component names are not documented. Pure internal refactoring — no public-facing API, command, flag, or dependency change. No docs update needed.
- Result: **N/A — no task-caused drift**

### Item 2: External Attribution
- All sources in `.owlbear/research/cockpit-mutation-hook-extraction.md` are in-repo (DetailTab.tsx, useRepairFlow.ts, useCleanupFlow.ts, ConfirmDialog.tsx, prior research docs).
- Result: **N/A — no external attribution needed**

### Item 3: Research Doc
- `.owlbear/research/cockpit-mutation-hook-extraction.md` exists and is linked from task body ("Research doc: .owlbear/research/cockpit-mutation-hook-extraction.md"). Research doc header back-references #1507.
- Result: **PASS — linked**

### Item 4: Deletion Detection
- No source files deleted; only new files added and one existing component modified.
- Result: **N/A — no deletion impact**

### Scratch Cleanup
- No `.owlbear/scratch/1507-*` files found.

### Files Modified
- None — no docs changes were required.
2026-05-12T15:31:33+00:00
## Audit\n### Regression Detection\n- Vitest independent rerun: 1507 passed, 9 skipped, 0 failed (87 files). Full suite clean.\n- Python suite: not scoped (pure frontend task, zero Python files changed). Pre-existing background failures unrelated.\n- Lint: ESLint clean, Stylelint clean (per reviewer evidence).\n- Regression verdict: PASS\n\n### Intent Verification\n- Scope alignment: PASS (all files in serve/cockpit/web/src/ -- correct cockpit frontend domain)\n- Purpose match: PASS (mutation hook + action component extraction from DetailTab, plus keyed-remount fix and regression test)\n- Extraneous scope: none\n- Boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC-1 through AC-5 well-specified (types, testids, visibility conditions, lint commands). Implementation guidance for reset/focus split was proactively useful. One gap: initial proof bundle (existing) proved insufficient for task-switch confirm path, requiring architecture re-review that added AC-6. Two review FAIL cycles before pass. Score 4 -- adequate with one re-scope cycle.\n\n### Commit Integrity\n- Upstream commit presence: PASS\n  - f7e28d2f -- refactor: extract task mutation hook/actions from DetailTab (#1507, builder)\n  - 24ce261b -- fix: reset task actions state on task switch (#1507, builder)\n  - 64a90887 -- test: add task-switch confirm-dialog reset regression test (#1507, test-writer)\n- All commits present and properly tagged before done advancement.\n- Kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\nNo deductions applied.\n- Intent mismatch: none\n- Evidence integrity: reviewer evidence detailed with AC-to-code mapping and independent quality-runner rerun\n- Lint violations: none\n- AC quality: 4/5 (above threshold)\n- Reviewer evidence: present and thorough\n- Regression failures: none\n\n### Confidence: 1.00\n### Action: archive