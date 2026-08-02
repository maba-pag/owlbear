---
id: 1506
title: 'Cockpit: Extract useConflictDraft hook + ConflictBanner component from DetailTab'
status: archived
priority: medium
created: 2026-05-12T03:04:43.984524+00:00
updated: 2026-05-12T15:14:22.586246+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Extract conflict-detection state and UI from DetailTab.tsx into two focused modules (~120 LOC total).

## Scope
- **useConflictDraft.ts** (hooks/): manages conflictLocalDraft, conflictRemoteTask, showConflict, showConflictOverwrite, conflictChangedFields, conflictRemoteValues/conflictLocalValues
- **ConflictBanner.tsx** (components/): conflict diff display, acknowledge/discard/force-save buttons

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useConflictDraft.ts` exists in `hooks/` and exports the hook
- [ ] `ConflictBanner.tsx` exists in `components/` and renders conflict diff + action buttons
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:28:18+00:00
## Research
- Research doc: .owlbear/research/cockpit-conflict-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, conflict test files)
- Recommendation: Extract using action-function pattern (not raw setters), matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1506 is the implementation task, siblings #1507/#1508 exist
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: useEffect boundary split (field-restore vs conflict-cleanup) is the main implementation subtlety; hook exposes clearConflictIfTaskChanged(taskId) action for DetailTab's effect to call; ConflictBanner preserves all data-testid attributes for zero test impact
2026-05-12T09:26:37+00:00

## Refined Acceptance Criteria
_Supersedes original AC section._

- AC-1 (B1): `hooks/useConflictDraft.ts` exports `useConflictDraft` hook returning conflict state (`showConflict`, `showConflictOverwrite`, `conflictLocalDraft`, `conflictRemoteTask`, `conflictChangedFields`, `conflictRemoteValues`, `conflictLocalValues`) and action functions (`setConflictDetected`, `clearConflict`, `acknowledgeOverwrite`, `dismissConflict`, `clearConflictIfTaskChanged`). `ConflictLocalDraft` interface defined in or re-exported from the hook module.
- AC-2 (B1): `components/ConflictBanner.tsx` accepts conflict state via props and renders conflict diff display with action buttons. Preserves data-testid attributes: `conflict-modal`, `conflict-acknowledge`, `conflict-refresh`, `conflict-overwrite`, and per-field pairs `conflict-remote-{f}` / `conflict-local-{f}` for fields `title`, `priority`, `body`, `depends_on`, `parent`, `block_reason`.
- AC-3 (B1): `DetailTab.tsx` imports `useConflictDraft` from `hooks/useConflictDraft` and renders `ConflictBanner` from `components/ConflictBanner`, replacing inline conflict state declarations, computed values, and conflict JSX.
- AC-4 (B2): 8 existing DetailTab test files pass without modification: `DetailTab.test.tsx`, `DetailTab.valid-edits.test.tsx`, `DetailTab.invalid-parent.test.tsx`, `DetailTab.edit-payload.test.tsx`, `DetailTab.conflict-resolution.test.tsx`, `DetailTab.conflict-nonregression.test.tsx`, `DetailTab.pbanner-1498.test.tsx`, `DetailTab.gfm-plugins.test.tsx`.
- AC-5: No new ESLint or Stylelint warnings — verified by `npm run lint` and `npm run lint:css` in `serve/cockpit/web/`.

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files enumerated in AC-4)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extracts one concern (conflict state + UI) into two modules |
| Interface clarity | PASS | Hook return type and component props specified in AC-1/AC-2; data-testid attrs enumerated |
| Dependency correctness | PASS | Removed #1493 dep (see notes below); siblings #1507/#1508 retain it |
| Module layering | PASS | hooks/ and components/ follow established useRepairFlow/useCleanupFlow and RepairPanel/CleanupPanel patterns |
| TDD compliance | PASS | 8 existing test files serve as regression gate via `existing` proof bundle |
| KISS/YAGNI | PASS | Pure extraction, no new abstractions or features |
| Premise challenge | PASS | 634-LOC monolith with 5 scattered conflict zones (~94 LOC) — extraction justified |
| Pattern consistency | PASS | Action-function pattern matches useRepairFlow (92 LOC) and useCleanupFlow (69 LOC) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend component domain |

### Dependency Override: #1493 Removed
Original planning sequenced #1493 (API centralization) before all three extraction tasks to avoid double-refactoring churn. Analysis shows this concern applies to #1507 (wraps `runMutation` which contains fetch calls) and #1508 (container reduction touching mutation paths), but NOT to #1506: the conflict hook manages `useState`/`useMemo` state only — zero fetch calls, zero API surface. Removing the dependency unblocks #1506 while #1493's children (#1501-#1503) complete their pipeline. Siblings #1507 and #1508 retain their #1493 dependency.

### Proof-Bundle Validation
- Planner assignment: none (research classified as T1)
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files)
- Test-writer: SKIP (bundle `existing`)

### Challenge Results
- Challenger: reconsider (0.67)
- Findings: (1) ac-quality: behavioral lock gaps — rebutted: AC-4 gates on 8 tests that already cover async-gap, dismiss-preservation, 409→404 paths; (2) ac-quality: field enumeration — accepted, AC-2 refined with exact 6 fields; (3) proof-scope: 7→8 drift — accepted, corrected; (4) dependency: planning override — accepted, documented reasoning above; (5) consolidation-test-gap: no explicit consolidation task — noted: sequential chain + identical 8-test gate on each child + #1508 as final composition verifier + parent #1492 tracker provides sufficient coverage
- Architect response: accepted items 2/3, rebutted 1, documented override reasoning for 4, justified coverage for 5

### Design Diverge
- Trigger: skipped — single valid approach (action-function pattern matching useRepairFlow/useCleanupFlow precedent), no competing designs

### Implementation Guidance
- useEffect at L89-109 mixes field-restore (stays in DetailTab) and conflict-cleanup (moves to hook). Hook exposes `clearConflictIfTaskChanged(taskId)` action; DetailTab's effect reads `conflictLocalDraft` for field restoration, then delegates cleanup to the hook action.
- `runMutation` coupling: hook exposes focused action functions, not raw setters. `runMutation` stays in DetailTab (moves to #1507 scope).
- ConflictBanner must render at the same DOM position to preserve test selectors.

### Verdict: APPROVE
### Action Taken: Refined AC (enumerated fields, corrected test count 7→8, added verification method for lint, numbered AC lines), removed #1493 dependency with documented reasoning, assigned proof bundle `existing` with 8-file scope, advanced to todo.

2026-05-12T09:26:43+00:00
Architecture review complete. REFINE + APPROVE: Refined AC (corrected test count 7→8, enumerated 6 conflict fields in AC-2, added lint verification method in AC-5, numbered AC lines per h-ac-quality). Removed #1493 dependency — conflict hook has zero API surface; churn concern applies to siblings #1507/#1508 only. Proof bundle: existing (8 DetailTab*.test.tsx files). Challenger: reconsider (0.67) — accepted field enumeration + proof-scope corrections, rebutted behavioral-lock gap (AC-4 gates on tests that already cover those paths), documented dependency override. Test-writer: SKIP.
2026-05-12T09:40:13+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files per AC-4).
- Passing through to builder.
2026-05-12T10:08:04+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/hooks/useConflictDraft.ts
  - serve/cockpit/web/src/components/ConflictBanner.tsx
  - serve/cockpit/web/src/components/DetailTab.tsx
- Implementation summary:
  - Extracted conflict state/computed diff logic into `useConflictDraft` hook with action-function API: `setConflictDetected`, `clearConflict`, `acknowledgeOverwrite`, `dismissConflict`, `clearConflictIfTaskChanged`.
  - Extracted conflict UI into `ConflictBanner` component preserving required data-testid attributes: `conflict-modal`, `conflict-acknowledge`, `conflict-refresh`, `conflict-overwrite`, and per-field `conflict-remote-{f}` / `conflict-local-{f}` for `title`, `priority`, `body`, `depends_on`, `parent`, `block_reason`.
  - Updated `DetailTab` to delegate conflict state and rendering to the new modules while keeping mutation flow and behavior intact.
- Test results (existing proof scope):
  - Vitest (`src/__tests__/DetailTab*.test.tsx` 8 files): 125 passed, 0 failed, 1 skipped.
- Lint status:
  - ESLint (changed files): clean.
  - Stylelint (`npm run lint:css`): clean.
- Coverage:
  - Not required by bundle (`Proof bundle: existing`); no coverage gate executed.
- Evidence summary:
  - Baseline proof run before edits: green.
  - Post-change proof run: unchanged green on the same 8-file scope plus clean lint/stylelint.
- Fixes applied during build:
  - Stabilized hook action callbacks (`useCallback`) so `DetailTab` effect dependencies remain safe.
  - Replaced direct conflict setter usage in force-save path with extracted hook action.
2026-05-12T10:55:14+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1506 -> in-progress | `clearConflictIfTaskChanged` does not fully clear conflict UI when the selected task changes.
- Builder evidence reviewed first: builder notes report `src/__tests__/DetailTab*.test.tsx` 8-file scope green (`125 passed, 0 failed, 1 skipped`) plus clean ESLint/Stylelint. That evidence is internally consistent, but it does not prove the task-switch cleanup path.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 / Implementation Guidance | `clearConflictIfTaskChanged(taskId)` clears `conflictLocalDraft`, `conflictRemoteTask`, and `showConflictOverwrite`, but leaves `showConflict` true. When `DetailTab` switches from the conflicted task to a different task, the effect resets form fields and calls this partial cleanup, so `ConflictBanner` still renders with no diff rows and stale action buttons. That is incomplete conflict cleanup in the exact boundary the architect called out. | `serve/cockpit/web/src/hooks/useConflictDraft.ts:99-106`; `serve/cockpit/web/src/components/DetailTab.tsx:102-118`; `serve/cockpit/web/src/components/ConflictBanner.tsx:24-49` | in-progress |
| 2 | AC-1 proof sufficiency | Existing proof did not exercise task-switch cleanup while a conflict was active. The main conflict suite uses `StatefulWrapper` to replay same-task `onTaskUpdated -> setTask(updatedTask)` re-renders and dismissal/force-save flows, but no test switches to a different task id and asserts the banner disappears. That gap allowed the cleanup regression above to pass the 8-file gate unchanged. | `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:33-36`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:140-149`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:898-938` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make `clearConflictIfTaskChanged` fully clear conflict UI state, including hiding the banner when the active task id changes away from the conflicted task. | `serve/cockpit/web/src/hooks/useConflictDraft.ts`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/ConflictBanner.tsx` | Finding #1 |
| 2 | builder | Extend the existing conflict regression proof to cover `conflict open -> switch to different task -> banner disappears`, then rerun the same 8-file `DetailTab*.test.tsx` scope and lint checks. | `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` | Finding #2 |

## Observations
- AC-2 and the non-task-switch portions of AC-3 are implemented as specified: the extracted banner preserves `conflict-modal`, `conflict-acknowledge`, `conflict-refresh`, and `conflict-overwrite`, and `DetailTab` delegates to the hook/component split.
- No TypeScript/diagnostic errors were reported for the three changed source files.
- I could not independently run a scoped git dirty-tree check in this tool surface, so the verdict is based on task-body evidence plus direct source/test inspection.
2026-05-12T11:30:47+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/hooks/useConflictDraft.ts
- Implementation summary:
  - Fixed `clearConflictIfTaskChanged(taskId)` to fully clear conflict UI state (`showConflict`, `showConflictOverwrite`) when switching away from a known conflicted task.
  - Added a guard to avoid clearing no-refetch conflict state (`conflictRemoteTask === null`), preserving existing nonregression behavior.
- Test results (required existing proof scope):
  - Vitest (`serve/cockpit/web/src/__tests__/DetailTab*.test.tsx`, 8 files): 125 passed, 0 failed, 1 skipped.
- Lint status:
  - ESLint (scoped changed files): clean.
  - Stylelint (`npm run lint:css` via quality-runner): clean.
- Coverage:
  - Not required by bundle (`Proof bundle: existing`); no coverage gate executed.
- Evidence summary:
  - Quality-runner scoped run initially surfaced one nonregression failure; adjusted cleanup guard for no-refetch path.
  - Final quality-runner scoped run is fully green (tests/lint/stylelint).
- Commit:
  - 4ee3e058 — `fix: clear conflict banner on task switch (#1506, builder)`
2026-05-12T11:58:46+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1506 -> backlog | retry fixed the hook cleanup path, but the task contract still lacks valid proof for the task-switch boundary.
- Builder evidence reviewed first: the current builder notes report a green 8-file `DetailTab*.test.tsx` scope plus clean ESLint and Stylelint, and direct source inspection shows `clearConflictIfTaskChanged` now clears `showConflict` and `showConflictOverwrite` when switching away from a known conflicted task.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 / Proof bundle `existing` | The retry still does not prove the task-switch cleanup boundary that failed in the prior review. The prior review required adding task-switch coverage, but the retry changed only `serve/cockpit/web/src/hooks/useConflictDraft.ts`. At the same time, the approved task contract still says the 8 existing DetailTab test files must pass without modification and labels the bundle `existing` / `no new test writing required`. The current conflict harness only replays same-task `onTaskUpdated -> setTask(t)` updates or clear-to-null flows; it does not switch to a different task id and assert banner cleanup. On this second review cycle, the remaining blocker is therefore proof/AC quality, not implementation: the task needs architect-level re-scoping before it can be re-dispatched cleanly. | `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:56`; `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:59`; `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:107`; `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:149`; `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:158`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:33`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:147`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:148`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:167`; `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:171` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope #1506's proof contract so task-switch cleanup is explicitly guardable: either relax AC-4 / `Proof bundle: existing` to permit a regression test in `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx`, or split that proof into a follow-up task and re-dispatch implementation/test work against the corrected contract. | `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md`, `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` | Finding #1 |

## Observations
- The implementation-side defect from the prior review appears fixed: `clearConflictIfTaskChanged` now clears `showConflict` and `showConflictOverwrite` on known task switches in `serve/cockpit/web/src/hooks/useConflictDraft.ts:99-110`.
- Diagnostics are clean for the changed frontend source files (`useConflictDraft.ts`, `ConflictBanner.tsx`, `DetailTab.tsx`, `TaskFieldsEditor.tsx`).
- I did not dispatch `quality-runner` because the blocker is not contradictory execution evidence; it is the unresolved proof-contract gap documented above.
2026-05-12T12:34:23+00:00

## Architecture Re-Review (proof contract re-scope)

### Context
Reviewer returned #1506 to backlog after two review cycles. Implementation is correct (builder committed `4ee3e058` fixing `clearConflictIfTaskChanged`), but the proof contract prevents validating the fix: AC-4 requires 8 test files to pass "without modification," and proof bundle `existing` bars new test writing. The task-switch cleanup boundary — conflict active for task A, switch to task B, banner disappears — has no existing test coverage.

### Changes
1. **AC-4 relaxed:** Removed "without modification" constraint. Existing 8 test files must still pass, but `DetailTab.conflict-resolution.test.tsx` may be extended.
2. **AC-6 added:** Explicit task-switch cleanup regression test requirement with B2-compliant input/output.
3. **Proof bundle escalated:** `existing` → `smoke`. Test-writer writes one regression test; builder confirms full scope passes.

### Revised AC (supersedes prior Refined AC)

- AC-1 (B1): `hooks/useConflictDraft.ts` exports `useConflictDraft` hook returning conflict state (`showConflict`, `showConflictOverwrite`, `conflictLocalDraft`, `conflictRemoteTask`, `conflictChangedFields`, `conflictRemoteValues`, `conflictLocalValues`) and action functions (`setConflictDetected`, `clearConflict`, `acknowledgeOverwrite`, `dismissConflict`, `clearConflictIfTaskChanged`). `ConflictLocalDraft` interface defined in or re-exported from the hook module.
- AC-2 (B1): `components/ConflictBanner.tsx` accepts conflict state via props and renders conflict diff display with action buttons. Preserves data-testid attributes: `conflict-modal`, `conflict-acknowledge`, `conflict-refresh`, `conflict-overwrite`, and per-field pairs `conflict-remote-{f}` / `conflict-local-{f}` for fields `title`, `priority`, `body`, `depends_on`, `parent`, `block_reason`.
- AC-3 (B1): `DetailTab.tsx` imports `useConflictDraft` from `hooks/useConflictDraft` and renders `ConflictBanner` from `components/ConflictBanner`, replacing inline conflict state declarations, computed values, and conflict JSX.
- AC-4 (B2): 8 existing DetailTab test files pass: `DetailTab.test.tsx`, `DetailTab.valid-edits.test.tsx`, `DetailTab.invalid-parent.test.tsx`, `DetailTab.edit-payload.test.tsx`, `DetailTab.conflict-resolution.test.tsx`, `DetailTab.conflict-nonregression.test.tsx`, `DetailTab.pbanner-1498.test.tsx`, `DetailTab.gfm-plugins.test.tsx`.
- AC-5: No new ESLint or Stylelint warnings — verified by `npm run lint` and `npm run lint:css` in `serve/cockpit/web/`.
- AC-6 (B2): Given a conflict is active for task A (`conflict-modal` visible in DOM), when the active task changes to task B (different id), `ConflictBanner` no longer renders (`conflict-modal` absent from DOM). Verified by a regression test in `DetailTab.conflict-resolution.test.tsx`.

Proof bundle: smoke (escalated from existing — task-switch cleanup boundary requires regression test)
Existing proof scope: N/A (bundle is now smoke)
Test-writer: PROCEED

### Evaluation (delta from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| TDD compliance | PASS | Escalated to smoke; test-writer adds task-switch regression test |
| Proof bundle | ESCALATED | existing → smoke; justified by untested cleanup boundary |

All other criteria unchanged from prior architecture review (all PASS).

### Challenge Results
- Challenger: SKIPPED — re-review scope is proof-contract correction only; no design change, no new interfaces, implementation already committed and verified by reviewer as correct.

### Design Diverge
- Trigger: skipped — single correction path, no competing designs.

### Verdict: APPROVE (re-scoped)
### Action Taken: Escalated proof bundle existing → smoke, added AC-6 for task-switch regression test, relaxed AC-4 "without modification" constraint, re-dispatching to todo for test-writer.

2026-05-12T12:34:28+00:00
Architecture re-review complete. APPROVE (re-scoped): Escalated proof bundle existing → smoke, added AC-6 for task-switch cleanup regression test, relaxed AC-4 "without modification" constraint. Implementation is already committed (4ee3e058) and reviewer confirmed it correct — the only gap was proof contract preventing the regression test from being written. Test-writer: PROCEED (writes one task-switch test in DetailTab.conflict-resolution.test.tsx).
2026-05-12T13:09:09+00:00
## Test-Writer Notes
- Retry: added 1 smoke test for AC-6 (task-switch cleanup regression).
- Test file: `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx`
- New class: `TestFromAC_ConflictBannerTaskSwitch`
- Tests per category: 1 smoke (task-switch → banner disappears)
- Total new tests: 1
- All 25 tests in conflict-resolution suite PASS against current implementation (builder commit 4ee3e058 already fixed clearConflictIfTaskChanged).
- ESLint: clean.
- Builder skip: test-only retry, all new tests green — implementation was already correct.
- Commit: 0ff7e139 — `test: add task-switch cleanup regression test for useConflictDraft (#1506, test-writer)`

### AC Coverage (AC-6 only — AC-1 to AC-5 covered by existing 8-file scope)
| AC | Test | Status |
|----|------|--------|
| AC-6 | conflict_banner_disappears_when_active_task_switches_to_different_id | PASS (impl already fixed) |
2026-05-12T13:42:15+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1506 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: builder notes show the extracted hook/component landed with an 8-file DetailTab scope green (`125 passed, 0 failed, 1 skipped`) plus clean ESLint and Stylelint; the retry then added the missing AC-6 smoke proof in `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` against the already-fixed implementation commit `4ee3e058`.
- Independent verification: dispatched `quality-runner` because the post-retry packet needed an explicit full-scope confirmation after the new test was added. Result: `126 passed`, `0 failed`, `1 skipped`, `vitest=0`, `eslint=0`, `stylelint=0`, `Errors: none`. This confirms the full 8-file DetailTab scope is green with AC-6 included.
- Blocking findings: none.

| AC Line | Code Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/hooks/useConflictDraft.ts:3`, `:42`, `:73`, `:99` define/export `ConflictLocalDraft`, `useConflictDraft`, and the required action API including `clearConflictIfTaskChanged`. | Existing 8-file DetailTab proof green in builder notes; no diagnostics in `useConflictDraft.ts`. | PASS |
| AC-2 | `serve/cockpit/web/src/hooks/useConflictDraft.ts:40`, `:48`, `:59`, `:68` enumerate the 6 conflict fields and compute remote/local diff values; `serve/cockpit/web/src/components/ConflictBanner.tsx:3`, `:29`, `:32`, `:38`, `:45`, `:49` render the banner and required `data-testid` attributes. | Existing conflict-resolution coverage remains green under the 8-file rerun (`quality-runner`: 126 passed, 1 skipped). | PASS |
| AC-3 | `serve/cockpit/web/src/components/DetailTab.tsx:4`, `:13`, `:163`, `:166`, `:185` import/wire `ConflictBanner` and `useConflictDraft`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:114`, `:131` delegates task-switch cleanup through `clearConflictIfTaskChanged`. | Builder notes plus independent 8-file rerun confirm the delegation path is green. | PASS |
| AC-4 | Task contract at `.owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md:211` requires the 8 DetailTab files to pass. | Independent `quality-runner` rerun after the AC-6 test addition confirmed the full 8-file scope is green: `126 passed`, `0 failed`, `1 skipped`. | PASS |
| AC-5 | No source/CSS diagnostics in the changed frontend files. | Builder notes reported clean ESLint and Stylelint; independent `quality-runner` rerun confirmed `eslint=0` and `stylelint=0` with no violations. | PASS |
| AC-6 | `serve/cockpit/web/src/hooks/useConflictDraft.ts:99` now clears conflict UI on task-id change; `serve/cockpit/web/src/components/ConflictBanner.tsx:24` returns `null` when `showConflict` is false; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:131` calls the cleanup on task switch. | `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx:1112`, `:1117`, `:1141`, `:1164` add and pass the task-switch regression: conflict open for task A, switch to task B, `conflict-modal` disappears. Included in the independent 8-file rerun. | PASS |
- Safety & security: PASS. This task remains a frontend-local refactor with no new auth, storage, shell, path, or network boundary; I found no new injection or secrets-handling surface.

## Observations
- The earlier implementation defect is now closed at the root: `clearConflictIfTaskChanged` clears both visibility flags and state when the active task changes away from a known conflicted task, while preserving the no-refetch nonregression guard (`serve/cockpit/web/src/hooks/useConflictDraft.ts:99`).
- Builder-skip on the retry was valid here: the implementation fix was already present, and the new smoke test in `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` supplied the missing falsifiable proof.
- I could not independently perform a path-scoped git dirty-tree check in this tool surface, so that portion of Step 1 remains based on task-body evidence rather than a direct `git status` read.
2026-05-12T14:32:53+00:00
## Docs Gate

**Verdict: DONE** — no docs changes required.

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no drift | `serve/cockpit/README.md` grep: no matches for `DetailTab`, `ConflictBanner`, `useConflictDraft`. README covers public surface only (launch, APIs, config, frontend stack table). Pure internal refactor — no public interface changed. |
| External Attribution | N/A | Pure extraction of existing logic using in-repo patterns (`useRepairFlow`/`useCleanupFlow`). No external sources used. |
| Research Doc | Linked ✓ | `.owlbear/research/cockpit-conflict-hook-extraction.md` referenced in task body Research section. |
| Deletion Detection | N/A | No source files deleted. Two new files added (`useConflictDraft.ts`, `ConflictBanner.tsx`); three existing files modified. |

### Scratch Cleanup
No `.owlbear/scratch/1506-*` files found.

### Upstream Evidence
Review Evidence present — PASS verdict with full AC-by-AC table and independent `quality-runner` confirmation (126 passed, 0 failed, 1 skipped, eslint=0, stylelint=0).
2026-05-12T15:14:22+00:00
## Audit
### Regression Detection
- quality-runner env fallback (2x no-response): Python 4421 passed / 205 failed (pre-existing: cockpit_view, ideation_diagram, server, engine_accessor_migration — all unrelated to frontend refactor) / ruff clean; Frontend 1507 passed / 0 failed / 9 skipped / ESLint clean / Stylelint clean
- regression verdict: PASS — zero task-attributable failures

### Intent Verification
- scope alignment: PASS (4 files changed, all within serve/cockpit/web/src/ — components, hooks, tests)
- purpose match: PASS (conflict state/UI extracted from DetailTab into useConflictDraft hook + ConflictBanner component; task-switch cleanup bug fixed; regression test added)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC-1 through AC-6 are specific with B1/B2 levels, enumerated fields, data-testid attributes, and file paths. One gap: initial proof bundle `existing` with "without modification" constraint was too restrictive, blocking the regression test that the reviewer correctly identified as needed. Architect re-scoped promptly (existing → smoke, added AC-6). Design guidance (useEffect split, action-function pattern) was helpful. Score: 4/5 — adequate, one re-scoping cycle needed.

### Commit Integrity
- upstream commit presence: PASS — 3 commits verified: d140cfec (refactor: extract conflict draft hook/banner, builder), 4ee3e058 (fix: clear conflict banner on task switch, builder), 0ff7e139 (test: add task-switch cleanup regression test, test-writer)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive