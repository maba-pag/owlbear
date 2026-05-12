---
id: 1504
title: 'Cockpit: Implement CockpitProvider and slim Shell.tsx'
status: in-progress
priority: important
created: 2026-05-12T02:59:59.210772+00:00
updated: 2026-05-12T16:32:40.885715+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1491
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract all state management from Shell.tsx into a CockpitProvider context component.

## Acceptance Criteria
- AC-1: `src/hooks/CockpitProvider.tsx` created; exports `CockpitProvider` component and three hooks: `useBoardState()`, `useTaskSelection()`, `useDRState()`
- AC-2: `CockpitProvider` calls `useBoard()`, `usePendingDRs()`, `useScanPolling()` internally; these hooks remain as separate modules with unchanged exports
- AC-3: `useBoardState()` exposes board, tasks, loading, error (string|null), health (HealthState), refetchTasks, plus scan state: items (ScanItem[]), isLoading (boolean), error (Error|null), refetch
- AC-4: `useTaskSelection()` exposes selectedTaskId, selectedTask (TaskDetail|null), selectedTaskError (string|null), and action functions for select/clear/update; task fetch with AbortController (abort on task switch and unmount) is encapsulated
- AC-5: `useDRState()` exposes count, items, isLoading, error (Error|null), refetch, selectedDRId, setSelectedDRId, and selectedDR (derived PendingDR|null)
- AC-6: Cross-domain effect (F10): `lastDecisionsMtime` change (non-null) triggers `refetchPendingDRs()` inside CockpitProvider; initial null value does not trigger refetch
- AC-7: `useConnectionHealth` remains inside `useBoard` (F11 — no change)
- AC-8: App.tsx provider order: PorscheDesignSystemProvider > BrowserRouter > EventSourceProvider > CockpitProvider > ErrorBoundary > Shell
- AC-9: Shell.tsx has zero direct calls to useBoard, usePendingDRs, or useScanPolling; retains only layout (CSS grid), view-local refs, tab-change a11y effect, and hook-based composition
- AC-10: `npm test` passes — including updated Shell test mocks and App tree assertions reflecting new provider hierarchy
- AC-11: Consumer hooks (useBoardState, useTaskSelection, useDRState) throw Error when called outside CockpitProvider (following useSSEEvent pattern in EventSourceProvider.tsx)

## Implementation Guidance
- LOC targets: ~150 CockpitProvider, ~75 Shell (soft constraints, not pass/fail gates)
- Unassigned state (bannerError, hasLoadedScan, selectedTaskSubtab, detailValidationMessage, taskFetchNonce): builder places in provider or Shell-local at discretion, provided AC-9 holds
- Callback identity: React Compiler handles memoization; add useCallback only if review reveals churn
- Error types: pass through unchanged from underlying hooks (no normalization required)

Proof bundle: behavioral

## Dependency Note
AC-10 requires Shell test mock-path updates that overlap with sibling #1505 scope. #1505 will be re-scoped during its own architecture review.

## Source
Research: .owlbear/research/1491-cockpit-provider-extraction.md
2026-05-12T15:01:09+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: extract Shell state management into CockpitProvider |
| Interface clarity | PASS | AC-3/4/5 name exact return fields with types; AC-11 requires context guard |
| Dependency correctness | PASS | parent=1491, #1505 depends_on=[1504]. No missing deps |
| Module layering | PASS | Follows EventSourceProvider pattern — same hooks/ dir, same createContext + consumer hook shape |
| TDD compliance | PASS | Proof bundle behavioral — test-writer writes RED, builder GREEN |
| KISS/YAGNI | PASS | Single provider (Option A) is simplest viable option. No new deps |
| Premise challenge | PASS | Shell at 305 LOC mixing 7 useState + 5 useEffect with 200 LOC layout — extraction justified |
| Pattern consistency | PASS | Mirrors EventSourceProvider: context + exported consumer hook + throw-if-outside guard |
| Security surface | PASS | No new system boundaries; internal state reshuffling only |
| Single domain | PASS | Frontend/cockpit only |
| Failure mode map | N/A | Refactoring existing functionality; re-render fan-out acknowledged (bounded to ~5 consumers, mitigated by React Compiler) |
| Decision-request verification | N/A | T1 autonomous refactor |
| User-action detection | NOT DETECTED | AC defines testable TypeScript interface (C1); expected test outcomes (C2) |

### Refinements Applied
1. Numbered all AC lines (AC-1 through AC-11) for stability
2. Removed LOC soft targets from AC → implementation guidance
3. Specified consumer hook return shapes with types (AC-3/4/5)
4. Added initial-null behavior for F10 cross-domain effect (AC-6)
5. Fixed App.tsx tree to include full provider hierarchy including BrowserRouter (AC-8)
6. Replaced callback-identity heuristic AC with context-guard requirement (AC-11)
7. AC-10 includes Shell test mocks + App.wiring.test.tsx (broader than originally stated)
8. Separated "Implementation Guidance" section for builder freedom on unassigned state

### Proof-Bundle Validation
- Planner assignment: none (parent recommended behavioral)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single viable approach (Option A) validated by research challenger at 0.72 confidence

### Challenge Results
- Challenger: reconsider (confidence: 0.42)
- Key challenges: (1) task body not yet updated — ACCEPTED, fixed; (2) test scope broader than stated (App.wiring.test.tsx) — ACCEPTED, added to AC-10; (3) AC quality semantic issues — ACCEPTED in part, refined AC-3/4/5/6/8/11; (4) error normalization gap — REBUTTED (YAGNI: provider surfaces same types as underlying hooks); (5) sibling scope overlap — ACCEPTED, documented in Dependency Note
- Architect response: revised — accepted 5 of 6 challenges, rebutted error normalization. Confidence post-revision: 0.78

### Verdict: APPROVE
### Action Taken: Refined AC (B1/B2 quality pass), assigned proof bundle behavioral, advanced backlog → todo
2026-05-12T15:50:57+00:00
## Test-Writer Notes
- Test files:
  - `serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx` — unit contract tests
  - `serve/cockpit/web/src/__tests__/App.wiring.1504.test.tsx` — App tree + Shell import guards
- Classes: `TestFromAC_CockpitProvider`, `TestFromAC_CockpitProviderWiring`
- Tests per category:
  - happy: 24 (exports, field presence, flow-through, initial state)
  - edge: 10 (boundary values, selectedDR derivation, scan items flow, lastDecisionsMtime sequence)
  - error: 8 (ApiError handling, throw-outside-provider, scan error flow)
  - boundary: 13 (AbortController abort-on-switch, abort-on-unmount, signal presence, update() re-fetch, AC-9 spy assertions, AC-8 tree structure)
- Total: 55 tests (49 in CockpitProvider_1504 + 6 in App.wiring.1504), all FAIL
- ruff: N/A (TypeScript); ESLint: clean (exit 0)

### AC Coverage
| AC | Tests | Notes |
|----|-------|-------|
| AC-1 | 4 | Named exports verified |
| AC-2 | 3 | vi.importActual regression guards for useBoard/usePendingDRs/useScanPolling |
| AC-3 | 12 | All return fields checked; scan error field tested flexibly (builder may use `scanError`) |
| AC-4 | 12 | select/clear/update actions; AbortController abort-on-switch + abort-on-unmount; getTask signal |
| AC-5 | 10 | count/items/isLoading/error/refetch/selectedDRId/setSelectedDRId/selectedDR |
| AC-6 | 3 | null no-trigger + non-null trigger + subsequent triggers |
| AC-7 | 1 | useConnectionHealth absent from CockpitProvider module exports |
| AC-8 | 3 | App renders CockpitProvider; ErrorBoundary child; Shell grandchild |
| AC-9 | 3 | Shell does not call useBoard/usePendingDRs/useScanPolling (spy assertions) |
| AC-10 | — | Meta-AC (test suite passes overall); covered by AC-8/AC-9 |
| AC-11 | 4 | useBoardState/useTaskSelection/useDRState throw outside CockpitProvider; error message matches /CockpitProvider/i |

### Design notes for builder
- AC-3 scan error: AC lists two fields both named `error`. Tests check for a `scanError` field (most natural disambiguation). If builder uses a nested `scan` sub-object, adjust accordingly.
- AC-9 tests rely on CockpitProvider mock (pass-through) providing stub values for useBoardState/useTaskSelection/useDRState — Shell must consume these in GREEN.
- Commit: aeb31984
2026-05-12T16:04:22+00:00
## Builder Notes
- Implementation attempted (uncommitted due reject):
  - serve/cockpit/web/src/hooks/CockpitProvider.tsx (new)
  - serve/cockpit/web/src/App.tsx (provider tree wiring)
  - serve/cockpit/web/src/Shell.tsx (consumes `useBoardState`, `useTaskSelection`, `useDRState`; removed direct `useBoard`/`usePendingDRs`/`useScanPolling` calls)
- RED baseline (quality-runner): task tests failed as expected before implementation.
- GREEN verification (quality-runner): BLOCKED by a test initialization defect in `src/__tests__/CockpitProvider_1504.test.tsx`.
  - Failing error: `ReferenceError: Cannot access 'DEFAULT_BOARD_STATE' before initialization` at line 67 in hoisted mock setup.
  - Result: 6 passed, 1 failed (suite blocked before reliable coverage capture).
- Lint evidence from same run:
  - `src/Shell.tsx:39` reported unused `selectedDRId` in current in-progress implementation draft.
- Commit status: no source commit created because proof gate could not be reached with current TestFromAC setup.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Fix hoisted mock initialization ordering so `DEFAULT_BOARD_STATE` is not referenced before declaration (e.g., initialize hoisted return without TDZ reference or hoist defaults too). | serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx | quality-runner failure: `ReferenceError: Cannot access 'DEFAULT_BOARD_STATE' before initialization` (line 67) |
| 2 | test-writer | Re-run and confirm the corrected `TestFromAC_CockpitProvider` suite executes end-to-end (no initialization crash) so builder can complete GREEN proof. | serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx, serve/cockpit/web/src/__tests__/App.wiring.1504.test.tsx | quality-runner report for #1504: tests blocked with 1 failing suite due init error; coverage not collectible |
| 3 | builder | After test fix lands, remove unused `selectedDRId` local destructure in Shell during final GREEN pass if still present. | serve/cockpit/web/src/Shell.tsx | eslint warning in quality-runner report: `@typescript-eslint/no-unused-vars` at line 39 |
2026-05-12T16:20:45+00:00
\n\n## Merge Note\n#1505 merged into this task — Shell test mock-path updates are already required by AC-10 (`npm test` passes — including updated Shell test mocks). 9 Shell.*.test.tsx files need mock-path updates (not 8 — Shell.scan-health.test.tsx also mocks useBoard/usePendingDRs). Shell.scan-health.test.tsx requires special attention: it intentionally does NOT mock useScanPolling for integration testing of the fetch→scan→render chain.
2026-05-12T16:32:40+00:00
## Test-Writer Notes
- Retry: fixed TDZ initialization in `CockpitProvider_1504.test.tsx`
- Fix: `mockUseBoard`, `mockUsePendingDRs`, `mockUseScanPolling` were calling `.mockReturnValue(DEFAULT_*)` inside `vi.hoisted()` closures; `DEFAULT_*` constants are module-scope (not hoisted), causing `ReferenceError: Cannot access 'DEFAULT_BOARD_STATE' before initialization`. Removed initial return values from hoisted closures — `beforeEach` already sets them.
- Suite now executes end-to-end: 59 tests run, 58 pass (builder's uncommitted impl handles them), 1 fails: `aborts in-flight getTask fetch when selectedTaskId changes (task switch)` — legitimate RED contract test for AC-4 abort-on-switch.
- `App.wiring.1504.test.tsx`: 6/6 pass (App wiring + Shell AC-9 guards).
- ESLint: clean (exit 0). Commit: 4f858316.

### AC Coverage (unchanged from prior pass)
| AC | Tests |
|----|-------|
| AC-1 | 4 |
| AC-2 | 3 |
| AC-3 | 12 |
| AC-4 | 12 |
| AC-5 | 10 |
| AC-6 | 3 |
| AC-7 | 1 |
| AC-8 | 3 |
| AC-9 | 3 |
| AC-11 | 4 |