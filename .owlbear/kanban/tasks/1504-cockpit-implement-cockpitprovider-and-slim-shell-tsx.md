---
id: 1504
title: 'Cockpit: Implement CockpitProvider and slim Shell.tsx'
status: todo
priority: important
created: 2026-05-12T02:59:59.210772+00:00
updated: 2026-05-12T15:01:09.610057+00:00
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