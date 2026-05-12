# Cockpit: Extract CockpitProvider from Shell.tsx

> **Owning task:** #1491 — Cockpit: Extract CockpitProvider from Shell.tsx
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

Shell.tsx has grown to 305 LOC mixing state management (7 useState, 3 data-fetch hooks, 5 useEffect, inline fetch with AbortController) with layout (CSS grid regions, component composition). Should state be extracted into a single CockpitProvider context, and if so, what pattern minimizes re-render risk, test blast radius, and callback identity churn?

The task AC specifies: single CockpitProvider (~150 LOC) with 3 consumer hooks, Shell becomes ~60 LOC layout-only, fold in F10 (SSE refetch extraction) and F11 (inline useConnectionHealth).

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/Shell.tsx` (305 LOC) | Local | 1.0 |
| 2 | `serve/cockpit/web/src/hooks/EventSourceProvider.tsx` (185 LOC) | Local | 0.9 |
| 3 | `serve/cockpit/web/src/hooks/useBoard.ts` — board/tasks/health state | Local | 1.0 |
| 4 | `serve/cockpit/web/src/hooks/usePendingDRs.ts` — DR polling | Local | 0.9 |
| 5 | `serve/cockpit/web/src/hooks/useScanPolling.ts` — scan polling | Local | 0.8 |
| 6 | `serve/cockpit/web/src/hooks/useConnectionHealth.ts` — health state | Local | 0.8 |
| 7 | React docs — createContext, React Compiler memoization | Web | 0.9 |
| 8 | wisp.blog "Nest or Merge Multiple Context Providers" (Mar 2025) | Web | 0.8 |
| 9 | LogRocket "Pitfalls of overusing React Context" (Jun 2024) | Web | 0.8 |
| 10 | `.owlbear/research/1277-refactor-useboard-sse-context.md` | Local | 0.7 |
| 11 | 9 Shell test files in `__tests__/Shell.*.test.tsx` | Local | 0.9 |

## 3. Analysis

### 3.1 State Domains in Shell.tsx

| Domain | Source | State items | LOC |
|--------|--------|-------------|-----|
| Board/tasks | `useBoard()` | board, tasks, loading, error, health, refetchTasks, lastDecisionsMtime | ~5 |
| DR | `usePendingDRs()` | count, items, isLoading, error, refetch + selectedDRId | ~10 |
| Scan/health | `useScanPolling()` | items, isLoading, error, refetch + hasLoadedScan | ~10 |
| Task selection | Local state | selectedTaskId, selectedTask, selectedTaskError, selectedTaskSubtab, detailValidationMessage, taskFetchNonce | ~40 |
| Cross-domain effects | useEffect chains | lastDecisionsMtime → refetchPendingDRs, tab change listener | ~20 |
| View-local refs | useRef | tabsRef, detailRef, activityRef | ~15 |

Total state+effects: ~100 LOC. Layout/JSX: ~200 LOC.

### 3.2 Option Comparison

| Criterion | A: Single CockpitProvider | B: Split providers (3) | C: Provider + use-context-selector |
|-----------|--------------------------|------------------------|--------------------------------------|
| Files added | 1 | 3 | 1 + dep |
| KISS alignment | High | Low | Medium |
| Re-render isolation | Low (all consumers) | High (domain-scoped) | High (selector-scoped) |
| React Compiler mitigation | Yes — auto-memoizes subtrees | N/A — natural isolation | Potential conflict |
| Cross-domain effect placement | Natural (one provider) | Needs shared layer | Natural |
| Test seam preservation | Hooks survive as internals | Hooks survive, separate test contexts | Same as A |
| New dependency | None | None | use-context-selector |
| Callback identity risk | Medium — needs stabilization | Low — narrower values | Medium |

### 3.3 Challenger Findings (Accepted)

1. **Render fan-out is real but bounded**: Context value change triggers re-render of all consumers (~5 components). React Compiler memoizes *within* components but cannot prevent the trigger. Accepted: risk is low given 5 consumers, but must be documented.
2. **LOC targets need adjustment**: Shell retains view-local refs (tabsRef, detailRef, activityRef) and tab-change accessibility effect (~15 LOC). Revised targets: Shell ~75 LOC, Provider ~150 LOC.
3. **Callback identity churn**: `refetchTasks`, `refetchPendingDRs`, `refetch` (scan) are already unstable — Shell uses `refetchPendingDRsRef` to compensate. Provider value must stabilize these, either via React Compiler auto-memoization or explicit `useCallback`.
4. **Test blast radius is significant**: 8 Shell test files mock current hooks via `vi.mock(...)`. All need mock-path updates. 4 hook test files (useBoard, usePendingDRs, useScanPolling, useBoard.sse-context) survive unchanged since hooks remain as implementation modules.
5. **F10/F11 targets clarified**: F10 = the `lastDecisionsMtime → refetchPendingDRs()` cross-domain effect moves into provider. F11 = `useConnectionHealth` remains inside `useBoard` (already there); no provider-level change needed since the AC's "inline" means keeping it co-located.

### 3.4 Challenger Findings (Rebutted)

1. **"Shell already has narrow boundaries"**: The `kanbanProps` object, `onTaskUpdated` (15 LOC), and `onTaskCleared` (5 state resets) are state management disguised as props — this is the prop-drilling smell the refactor targets.
2. **"Risk is HIGH"**: Downgraded to **moderate**. Hooks survive as internal modules with existing tests. Shell tests update mock paths but test the same assertions. No async ownership changes — the task fetch effect moves intact.

## 4. Recommendation

**Option A: Single CockpitProvider** — confidence: **0.72**

Rationale:
- Simplest option (KISS) — one file, one context, three consumer hooks
- Cross-domain effects naturally centralized (no shared-layer coordination)
- React Compiler mitigates re-render cost for 5 consumers
- Existing hooks (useBoard, usePendingDRs, useScanPolling) stay as internal modules — hook-level tests unchanged

Key implementation constraints:
1. Provider creates context with `createContext`, calls useBoard/usePendingDRs/useScanPolling internally
2. Three consumer hooks: `useBoardState()`, `useTaskSelection()`, `useDRState()` — thin context accessors
3. Task fetch effect (AbortController) moves into provider or a `useTaskFetch` internal hook
4. Callback identities: rely on React Compiler auto-memoization; if churn is observed at review, add explicit `useCallback` for refetch functions
5. Shell keeps: view-local refs (tabsRef, detailRef, activityRef), tab-change effect, CSS grid layout, component composition
6. Provider placed in App.tsx: `EventSourceProvider > CockpitProvider > ErrorBoundary > Shell`

Challenge: reconsider — confidence in original: 0.44. Researcher response: **revised** — accepted LOC adjustment (60→75), callback stabilization requirement, test blast radius documentation. Rebutted HIGH risk assessment and "narrow boundaries" claim. Confidence lowered from 0.85 to 0.72.

## 5. Follow-up Tasks

| # | Title | Status | Tier |
|---|-------|--------|------|
| 1 | Implement CockpitProvider extraction from Shell.tsx | research | T1 |
| 2 | Update Shell test suites for CockpitProvider hooks | research | T1 |
