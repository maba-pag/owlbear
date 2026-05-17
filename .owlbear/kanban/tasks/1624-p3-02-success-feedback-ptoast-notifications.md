---
id: 1624
title: 'P3-02: Success feedback — PToast notifications'
status: todo
priority: important
created: 2026-05-16T03:37:44.703987+00:00
updated: 2026-05-17T09:21:32.515162+02:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on: []
ac:
  - "Successful task-move (drag-drop or context-menu) calls `useToastManager().addMessage({
    state: 'success', text })` where text contains the target status name; `PToast`
    is rendered in the Shell component tree within `PorscheDesignSystemProvider`.
    (Literal `p-toast-item` shadow-DOM timing assertion deferred to consolidation
    #1629.)"
  - After a successful edit-only mutation in TaskFieldsEditor (not 
    release/unblock/move via TaskActions), `[data-testid='save-confirmed']` 
    becomes visible and remains visible for 2000ms (±500ms) — surviving 
    CockpitProvider same-task refetch without component unmount. Does NOT appear
    on mutation failure (409 conflict, 404, or generic error). Resets on 
    task-switch (different task.id).
  - "Mutation error and warning paths unchanged: `p-banner[state='error'][open]` and
    `p-banner[state='warning'][open]` render after PToast addition; existing PBanner
    error/warning test suites pass without modification."
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

PToast for move/mutation success, inline confirmation for edits.

Scope: Success feedback only.
Out of scope: Dark mode, focus-visible, motion, accessibility sweep.

2026-05-16T15:44:01+00:00
## Research
- Research doc: .owlbear/research/ptoast-success-feedback.md
- Sources: 8 studied, 6 high-relevance (≥0.85)
- Recommendation: PToast singleton in App.tsx, wired via Shell callbacks; inline edit confirmation via saved state in TaskFieldsEditor (confidence: 0.82)
- Follow-up tasks created: none needed — this task is the implementation task
- Decision requests: none (T1 — config/integration change)

## Challenge Results
- Challenger: reconsider → proceed after revisions (original: 0.48, revised: 0.82)
- Key challenges: (1) inline save resolves on error too — need explicit onMutationSuccess in useTaskMutation, (2) proof target is p-toast-item not p-toast host, (3) callback signature change is backwards-compatible, (4) mount PToast in App.tsx for lifecycle safety, (5) AC quality gap addressed with DOM contracts
- Researcher response: accepted all 5 — revised recommendation with concrete DOM contracts and success signal architecture

## Implementation Guidance
### PToast Mount
- `App.tsx`: add `<PToast />` inside `PorscheDesignSystemProvider`, before `<BrowserRouter>`
- Import: `PToast` from `@porsche-design-system/components-react`

### Move Success Toasts
- Shell.tsx: call `useToastManager().addMessage({ text, state: 'success' })` from onMutationSuccess
- Enhance `onMutationSuccess` from `() => void` to `(message?: string) => void`
- KanbanBoard: pass target status in message, e.g. `onMutationSuccess?.(\`Task moved to ${targetStatus}\`)`

### Inline Edit Confirmation
- Add `onMutationSuccess?: () => void` to `UseTaskMutationOptions` (called only on true success, line 97)
- DetailTab/TaskFieldsEditor: on success callback, set brief "Saved" indicator (data-testid="save-confirmed")
- Auto-reset after ~2s; does NOT use PToast per task body scope

### Error No-Regression
- PBanner error paths unchanged
- PToast is additive (separate PDS component, separate top-layer)

### DOM Contracts for Testing
- AC1: `p-toast-item` inside `p-toast` shadow DOM appears with success text within 500ms after move
- AC2: `[data-testid="save-confirmed"]` visible after edit save, not visible after error
- AC3: `PBanner[open=true]` still shows on mutation errors

[[2026-05-16T17:44:15+02:00]]
## Research
- Research doc: .owlbear/research/ptoast-success-feedback.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: PToast singleton in App.tsx + useToastManager in Shell; inline edit confirmation via saved state in TaskFieldsEditor (confidence: 0.82)
- Follow-up tasks: none — this is the implementation task
- Decision requests: none (T1)

## Challenge Results
- Challenger: reconsider → proceed after revisions
- Confidence revised: 0.48 → 0.82
- Key revisions: explicit onMutationSuccess in useTaskMutation for clean success signal, p-toast-item as proof target, PToast mount in App.tsx for lifecycle safety, concrete DOM contracts for all 3 ACs

2026-05-16T16:19:33+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Success feedback only; no error-path changes |
| Interface clarity | PASS | Refined AC names exact DOM selectors, timing, and scope boundaries |
| Dependency correctness | PASS | Dep #1619 archived (deprecated); tests will be written at todo stage by test-writer |
| Module layering | PASS | PToast mount in App.tsx (top), useToastManager in Shell (consumer), indicator in TaskFieldsEditor (leaf) |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer processes at todo |
| KISS/YAGNI | PASS | Singleton mount + callback enhancement; no new context/provider layer |
| Premise challenge | PASS | No existing PDS success feedback; PToast is the sanctioned PDS mechanism |
| Pattern consistency | PASS | Follows existing PBanner error pattern (component mount + hook usage) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| useToastManager before PToast mount | querySelector returns null | Runtime warning from PDS | Yes — mount in App.tsx guarantees availability | Console warning, no toast shown |
| Save-confirmed on non-edit mutation | Hook-level callback fires broadly | N/A (logic bug) | AC2 scopes to edit-only; see guidance revision below | False positive indicator |

### Implementation Guidance Revision (from arch review)
The research doc recommends adding `onMutationSuccess` to `UseTaskMutationOptions`, but the challenger correctly identified that `runMutation` serves edit, release, AND move paths from a single hook instance. The AC2 scope constraint (\"edit-only\") means the builder must scope the indicator at the CALL SITE:

**Recommended approach:** Have `runMutation` return a success signal (`Promise<boolean>` or resolve without throwing = success). TaskFieldsEditor checks the return and triggers save-confirmed only from its own edit call site. This avoids the hook-level callback entirely for the indicator — no `onMutationSuccess` on UseTaskMutationOptions needed.

Alternatively: pass an optional `context` arg to runMutation and only fire the indicator when context matches 'edit'. Builder's choice — AC constrains behavior, not mechanism.

### Design Diverge
- Trigger: skipped — single valid approach (Option B-revised from research)

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Key findings: (1) critical — hook-level onMutationSuccess scope too broad for AC2; (2) AC1 trigger coverage; (3) AC3 omits warning path; (4) ~2s approximation; (5) conflict-retry save path
- Architect response: accepted findings 1,2,3,4. AC refined to address all. Finding 5 (conflict-retry) is implicitly covered — \"edit-only mutation in TaskFieldsEditor\" includes force-save via same UI. Added guidance revision for scoping mechanism.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC with PDS DOM contracts, scoped edit-only trigger, warning no-regression. Appended implementation guidance revision for hook-scope mitigation. Advancing to todo.

[[2026-05-16T18:19:40+02:00]]
Architecture review complete. Refined all 3 AC lines with exact PDS DOM selectors, scope boundaries, and timing constraints. Addressed challenger critical finding (hook-level callback scope) by adding guidance revision — builder scopes indicator at call site, not hook options. Proof bundle: behavioral confirmed.

[[2026-05-16T19:21:18+02:00]]
## Test-Writer Notes

**Test files:**
- `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx`
- `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`

**Classes and test breakdown:**

| Class | Category | Count |
|-------|----------|-------|
| `TestFromAC_KanbanBoardMoveMessage` | happy (2) | 2 |
| `TestFromAC_ShellToastFeedback` | happy (3) | 3 |
| `TestFromAC_PToastMount` | happy (2) | 2 |
| `TestFromAC_PBannerNoRegression` | regression (3) | 3 |
| `TestFromAC_SaveConfirmed` | happy (2), boundary (1), edge (3) | 6 |

**Total: 16 tests, 16 FAIL** (confirmed via `npm exec vitest run`)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 — KanbanBoard passes target status in onMutationSuccess | `TestFromAC_KanbanBoardMoveMessage` (2 tests: drag-drop, context-menu) |
| AC1 — Shell calls useToastManager.addMessage with state=success | `TestFromAC_ShellToastFeedback` (3 tests) |
| AC1 — App mounts PToast inside PorscheDesignSystemProvider | `TestFromAC_PToastMount` (2 tests) |
| AC2 — save-confirmed visible after edit save, resets after 2000ms, absent on error | `TestFromAC_SaveConfirmed` (6 tests) |
| AC3 — PBanner error/warning no regression alongside PToast | `TestFromAC_PBannerNoRegression` (3 tests) |

**Failure evidence:** `Tests  16 failed (16)` — commit dd58ca5d

**DOM contracts tested:**
- `p-toast-item[state='success']` via `useToastManager.addMessage({ state: 'success', text: ... })` mock
- `[data-testid='save-confirmed']` presence/absence and timing (fake timers)
- `[data-testid='ptoast-stub']` in App DOM tree
- `[data-testid='pbanner-stub']` coexistence with PToast

[[2026-05-16T20:23:18+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/App.tsx, serve/cockpit/web/src/Shell.tsx, serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/TaskFieldsEditor.tsx.
- AC1: KanbanBoard now passes target-status message on successful move (`Task moved to ${targetStatus}`); Shell consumes message via `useToastManager().addMessage({ state: 'success', text: message })`; PToast host is mounted in Shell and present in App render tree.
- AC2: TaskFieldsEditor now shows `[data-testid="save-confirmed"]` only after successful edit-path save and auto-resets at 2000ms; indicator is suppressed for error paths and non-dirty/non-edit confirmation scenarios.
- AC3: Existing PBanner error/warning behavior preserved while adding toast success flow.
- Quality-runner: initial scoped runs were unstable with environment errors (`HTMLElement is not defined`); retried once per protocol, then used direct frontend fallback commands.
- Verification (direct fallback evidence):
  - `npm exec vitest run src/__tests__/PToastSuccess_1624.test.tsx src/__tests__/SaveConfirmed_1624.test.tsx --reporter=verbose` -> exit 0, task tests passing (16/16).
  - `npm exec eslint -- src/App.tsx src/Shell.tsx src/KanbanBoard.tsx src/components/TaskFieldsEditor.tsx src/__tests__/PToastSuccess_1624.test.tsx src/__tests__/SaveConfirmed_1624.test.tsx` -> exit 0, lint clean.
  - `npm exec vitest run src/__tests__/Shell.pbanner-1498.test.tsx src/__tests__/KanbanBoard.pbanner-1498.test.tsx src/__tests__/DetailTab.pbanner-1498.test.tsx --reporter=verbose` -> exit 0, regression suite passing (30/30).
- Commit: 17b48844 (`feat: add success feedback via ptoast and save confirmation (#1624, builder)`).

[[2026-05-17T06:00:32+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1624 -> in-progress | AC2 save-confirmed can show on failed edits, and the task tests miss that real failure path.
- Builder evidence reviewed first: task tests passing 16/16, scoped lint clean, and existing PBanner regressions passing 30/30. No independent rerun was needed because the blocking issue is visible in the integrated code path and in the mismatch between production error semantics and task-local test modeling.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | `TaskFieldsEditor` decides whether to show `[data-testid='save-confirmed']` after `await onSave(...)` using the pre-submit `serverValidationMessage` prop snapshot. The real `onSave` path delegates to `useTaskMutation.runMutation()`, which catches warning/error paths and resolves without throwing. A failing edit can therefore still fall through the success gate, and a successful retry after a prior error can also miss the indicator because the stale prop was non-null before submit. | `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` (success gate after `await onSave`); `serve/cockpit/web/src/components/DetailTab.tsx` (edit path delegates to `runMutation`); `serve/cockpit/web/src/hooks/useTaskMutation.ts` (422/network/generic error paths return without rethrowing) | in-progress |
| 2 | AC2 | The task-local save-confirmed tests do not exercise the real integrated failure semantics. They model failure as a rejected `onSave` promise or a pre-seeded validation prop, so they would pass while the current AC2 defect remains in place. | `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx` (rejection-based error cases and clean-form check) compared with `serve/cockpit/web/src/components/DetailTab.tsx` and `serve/cockpit/web/src/hooks/useTaskMutation.ts` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Change edit-success signaling so `save-confirmed` is driven only by a true successful edit outcome and never by warning/error/conflict paths. | `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/hooks/useTaskMutation.ts` | Finding #1 |
| 2 | builder | Replace the current AC2 proof with an integration-level test that drives `TaskFieldsEditor` through the real `DetailTab`/`useTaskMutation` path, including at least one first-attempt failure and one successful retry after a prior error. | `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx` | Finding #2 |

## Observations
- AC1 implementation wiring looks sound on direct inspection: `KanbanBoard` passes the target-status message, `Shell` forwards it to `useToastManager().addMessage({ state: 'success', text })`, and `PToast` is mounted in the rendered Shell tree. I did not find a code-path defect there.
- AC1 toast proof remains seam-based and mock-heavy because the suite stubs `PToast` and `useToastManager`; that is weaker than the task’s literal `p-toast-item` wording, but it is secondary to the blocking AC2 defect.
- I could not independently run the scoped git contamination check from this reviewer session because terminal and `.git` access were not available through the current tool surface.

[[2026-05-17T07:35:20+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/hooks/useTaskMutation.ts, serve/cockpit/web/src/components/TaskFieldsEditor.tsx, serve/cockpit/web/src/components/DetailTab.tsx, and serve/cockpit/web/src/components/TaskActions.tsx.
- Fix applied (AC2): `runMutation` now returns explicit success/failure (`boolean`) across all mutation paths; `TaskFieldsEditor` now shows `[data-testid="save-confirmed"]` only when edit-save returns true success (and dirty form), removing stale pre-submit `serverValidationMessage` gating.
- Scope behavior: edit-only success indicator remains owned by `TaskFieldsEditor` call site (`DetailTab.handleSave`), and non-edit mutation flows (TaskActions) continue unchanged functionally while accepting the boolean return signature.
- Tests (quality-runner, scoped): 107 passed, 0 failed, 1 skipped.
  - Included task tests: `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx`, `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`
  - Included regression/integration suites: `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.valid-edits.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.body-preview-toggle.1508.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`
- Coverage (quality-runner scoped modules):
  - `src/hooks/useTaskMutation.ts`: 96.66%
  - `src/components/TaskFieldsEditor.tsx`: 91.57%
- Lint: clean (`eslint` exit 0) on touched files.
- Evidence summary: reviewer-reported false-positive success confirmation path is removed by true outcome signaling from mutation hook to editor save UI.
- Commit: `be9bbccf80f4addea2e4fe2ca0a75760f88fd3f9` (`feat: fix save-confirmed success gating for edit mutations (#1624, builder)`).

[[2026-05-17T08:39:27+02:00]]
## Review Evidence
- Verdict: FAIL (2nd review cycle)
- Routing signal: FAIL #1624 -> backlog | AC2 success confirmation is torn down by selected-task refresh, and AC1/AC2 proof remains insufficient.
- Builder evidence reviewed first: scoped quality-runner report in the task notes shows 107 passed, 0 failed, 1 skipped; lint clean; coverage 96.66% for `src/hooks/useTaskMutation.ts` and 91.57% for `src/components/TaskFieldsEditor.tsx`. No independent rerun was needed because the blocking issues are visible in the integrated state flow and in the proof packet itself.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | The real successful edit path still does not satisfy the required 2000ms confirmation window. `runMutation()` calls `onTaskUpdated(updatedTask)` before returning success; Shell handles that by calling `update(updatedTask)`, and the provider immediately schedules a selected-task refresh that clears `selectedTask` to `null`. `DetailTab` returns `null` when `task` is absent, so the editor is torn down almost immediately after success. Even before the unmount, `TaskFieldsEditor` also resets `saveConfirmed` on task/task.updated resync. The result is a built-in race against the required 2000ms visibility window for `[data-testid='save-confirmed']`. | `serve/cockpit/web/src/hooks/useTaskMutation.ts:95-98`; `serve/cockpit/web/src/Shell.tsx:384-388`; `serve/cockpit/web/src/Shell.tsx:482-486`; `serve/cockpit/web/src/hooks/CockpitProvider.tsx:97-98`; `serve/cockpit/web/src/hooks/CockpitProvider.tsx:178-182`; `serve/cockpit/web/src/components/DetailTab.tsx:118`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:133`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:187`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:191` | backlog |
| 2 | AC2 | The task-local AC2 suite still does not prove the real regression boundary. It renders `TaskFieldsEditor` in isolation, uses mocked `onSave` results, models failure as rejected promises or pre-seeded `serverValidationMessage`, and never drives the real `DetailTab` + `useTaskMutation` path or the shared-hook/non-edit action surface named in the AC. The real hook clears `serverValidationMessage` at mutation start and reports handled failures by returning `false`, so the current tests can pass without exercising the shipped failure semantics. | `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:124`; `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:160`; `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:168`; `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:295`; `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:338-345`; `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx:356-394`; `serve/cockpit/web/src/hooks/useTaskMutation.ts:93`; `serve/cockpit/web/src/hooks/useTaskMutation.ts:104`; `serve/cockpit/web/src/hooks/useTaskMutation.ts:137`; `serve/cockpit/web/src/hooks/useTaskMutation.ts:149`; `serve/cockpit/web/src/components/DetailTab.tsx:123-126`; `serve/cockpit/web/src/components/TaskActions.tsx:40`; `serve/cockpit/web/src/components/TaskActions.tsx:49`; `serve/cockpit/web/src/components/TaskActions.tsx:59` | backlog |
| 3 | AC1 | The AC1 proof is still seam-level and does not establish the literal toast contract. The task suite stubs both `PToast` and `useToastManager`, then stops at callback/addMessage assertions and host mounting. It never proves that a real `p-toast-item[state='success']` with target-status text appears within 500ms of the move response, which is the AC language the task was approved against. | `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx:27-28`; `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx:350-364`; `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx:395-448`; `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx:469-483` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-plan the AC2 success-feedback lifecycle so the save confirmation survives the selected-task refresh boundary for the full required window, then redelegate implementation. | `serve/cockpit/web/src/hooks/useTaskMutation.ts`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/hooks/CockpitProvider.tsx`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` | Finding #1 |
| 2 | architect | Redefine the AC2 proof plan around the real `DetailTab`/`useTaskMutation` path, including a successful save that remains visible for about 2000ms and at least one handled failure path that returns `false` without showing save-confirmed. | `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` | Finding #2 |
| 3 | architect | Either require literal toast DOM/timing proof for AC1 or narrow the AC to the app-owned callback/toast-manager seam before re-dispatch. | `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx` | Finding #3 |

## Observations
- AC3 looks intact on direct inspection. The Shell banner surface remains wired, and the adjacent durable `DetailTab.pbanner-1498` coverage still exercises real warning/error mutation paths.
- The builder’s boolean-success change in `useTaskMutation()` is directionally correct and does remove the previously reported swallowed-error fall-through at the hook boundary.
- I could not perform a git dirty-tree contamination check from this reviewer session because no git-status-capable tool is available in the current surface.

[[2026-05-17T09:21:25+02:00]]
## Architecture Review (cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Success feedback only; error paths untouched |
| Interface clarity | PASS | Refined AC names exact selectors, timing, and scope boundaries; narrowed AC1 to provable seam |
| Dependency correctness | PASS | No blocking deps; consolidation test #1629 exists |
| Module layering | PASS | CockpitProvider (state) → Shell (toast consumer) → TaskFieldsEditor (indicator leaf); fix touches provider + leaf only |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer processes at todo |
| KISS/YAGNI | PASS | Two surgical guards (provider null-guard + sync-effect task-ID guard); no new abstractions |
| Premise challenge | PASS | PToast is sanctioned PDS success mechanism; no existing alternative |
| Pattern consistency | PASS | Follows existing PBanner pattern (host mount + hook usage); CockpitProvider already uses isTaskSwitch flag |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| CockpitProvider same-task refetch after edit | Previously: nulls selectedTask → unmount → indicator lost | N/A (state logic) | FIX: guard `setSelectedTask(null)` to only fire on `isTaskSwitch` | Indicator now survives refetch |
| TaskFieldsEditor sync effect on task prop refresh | Previously: unconditionally resets saveConfirmed | N/A (state logic) | FIX: guard `setSaveConfirmed(false)` to only fire on task-ID change | Indicator survives data refresh |
| useToastManager called before PToast mount | querySelector returns null | PDS runtime warning | Yes — PToast mounted in Shell before consumers fire | Console warning only |
| 409/404/generic error from runMutation | Returns false; TaskFieldsEditor sees non-success | N/A | AC2: indicator suppressed for all failure paths | No false-positive indicator |

### Root Cause Analysis (from 2 failed review cycles)
The save-confirmed indicator failed because of TWO independent teardown paths:
1. **Provider-level unmount** (primary): `CockpitProvider.tsx` line 98 — `setSelectedTask(null)` fires unconditionally during refetch, including same-task refetch triggered by nonce increment after `update()`. This causes `DetailTab` to return `null` (line 125), unmounting `TaskFieldsEditor` entirely.
2. **Sync-effect reset** (secondary): `TaskFieldsEditor.tsx` line 133 — `setSaveConfirmed(false)` fires whenever the `task` dep changes, including same-task data refreshes (new `updated` timestamp from server).

### Implementation Guidance (revised)
**Fix 1 — CockpitProvider (`serve/cockpit/web/src/hooks/CockpitProvider.tsx` line 98):**
Guard `setSelectedTask(null)` with `isTaskSwitch`:
```typescript
if (isTaskSwitch) {
  setSelectedTask(null)
  setSelectedTaskError(null)
}
```
The `isTaskSwitch` flag already exists at line 93. For same-task refetches, keep existing selectedTask visible while fetch is in-flight. The fresh data replaces it atomically when `runFetch()` completes.

**Fix 2 — TaskFieldsEditor (`serve/cockpit/web/src/components/TaskFieldsEditor.tsx` line 133):**
Add a ref tracking previous task ID; guard saveConfirmed reset:
```typescript
const prevTaskIdRef = useRef(task.id)
// In the sync effect:
const isTaskSwitch = prevTaskIdRef.current !== task.id
prevTaskIdRef.current = task.id
// ... existing field syncs ...
if (isTaskSwitch) {
  setSaveConfirmed(false)
}
```

**AC1 — Toast wiring (existing implementation is correct):**
Shell mounts `PToast` and calls `useToastManager().addMessage()` on move success. KanbanBoard passes target status in message. No changes needed from current committed code.

### Proof Plan
**AC2 tests must cover:**
1. CockpitProvider unit: after `update(task)` where `task.id === selectedTaskId`, `selectedTask` never becomes null during refetch cycle
2. TaskFieldsEditor unit: onSave returns true → re-render with new `task.updated` (same id) → indicator survives → disappears at 2000ms
3. TaskFieldsEditor unit: onSave returns false → indicator never appears
4. TaskFieldsEditor unit: re-render with different `task.id` → indicator resets immediately

**AC1 tests (existing seam-level proof accepted):**
- `useToastManager().addMessage()` called with correct args after move
- `PToast` present in Shell render tree
- Shadow-DOM timing deferred to consolidation test #1629

### Design Diverge
- Trigger: skipped — single valid approach (guard same-task refetch at two levels)

### Challenge Results
- Challenger: block (confidence 0.34 on original proposal)
- Key findings: (1) CRITICAL — provider-level unmount not addressed by ref guard alone; (2) proof plan still too isolated; (3) AC1 narrowing loses coverage without rehoming
- Architect response: accepted all. Revised fix to include CockpitProvider null-guard. Proof plan now covers provider-level behavior. AC1 explicitly defers shadow-DOM proof to consolidation #1629.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined all 3 AC lines addressing reviewer and challenger findings. Added two-level implementation guidance (CockpitProvider unmount guard + TaskFieldsEditor sync-effect guard). Narrowed AC1 to unit-testable seam with explicit consolidation deferral. Removed "correctly" from AC3. Advancing to todo.

[[2026-05-17T09:21:32+02:00]]
Architecture review cycle 2 complete. Refined all 3 ACs addressing reviewer's two failed cycles:
- AC2: Root cause identified as TWO teardown paths (CockpitProvider unconditional null during same-task refetch + sync-effect unconditional reset). Fix requires guards at both levels.
- AC1: Narrowed to unit-testable app-owned seam; literal shadow-DOM proof deferred to consolidation #1629.
- AC3: Fixed wording per h-ac-quality.
Challenger invoked and critical finding (provider unmount) accepted and incorporated. Proof bundle: behavioral confirmed.
