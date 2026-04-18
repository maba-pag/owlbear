# RED: useBoard Polling + Mtime-Skip + Error State Tests

> **Owning task:** #965 — RED: useBoard polling + mtime-skip + error state tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #965 is a RED phase task: write failing tests for the polled `useBoard` hook before implementation. The hook currently lives in `KanbanBoard.tsx` as a one-shot `useEffect` + `fetch()`. The #960 research recommends plain `setInterval` + `useRef` polling with mtime-aware skip. Question: what's the test approach, infrastructure requirements, and edge cases?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | usePolling.test.ts (existing template) | `serve/cockpit/web/src/__tests__/usePolling.test.ts` | 1.0 |
| 2 | KanbanBoard.test.tsx (fetch stub patterns) | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` | 0.9 |
| 3 | KanbanBoard.tsx (current useBoard hook) | `serve/cockpit/web/src/KanbanBoard.tsx` L43-95 | 1.0 |
| 4 | #960 research doc | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 1.0 |
| 5 | Backend read.py (mtime response shape) | `serve/cockpit/src/owlbear_cockpit/routes/read.py` | 0.8 |

## 3. Analysis

### 3.1 Infrastructure — All In Place

All needed test utilities are already `devDependencies` and used in existing tests:

| Utility | Used in | Purpose |
|---------|---------|---------|
| `vi.useFakeTimers()` / `advanceTimersByTime()` | usePolling.test.ts | Control 3s interval |
| `renderHook()` / `act()` | usePolling.test.ts | Test hook in isolation |
| `vi.stubGlobal('fetch', vi.fn(...))` | KanbanBoard.test.tsx | Mock API responses |
| `vi.unstubAllGlobals()` | KanbanBoard.test.tsx | Cleanup |

No new dependencies needed.

### 3.2 AC → Test Approach Mapping

| AC | Technique | Gotcha |
|----|-----------|--------|
| 3s polling interval | `advanceTimersByTime(3000)`, count `fetchMock.mock.calls` for `/api/tasks` | Flush microtasks with `await act(async () => {})` after advancing timers |
| Skip `setTasks` when mtime unchanged | Return same `mtime` from stub, compare `result.current.tasks` reference via `toBe()` (same ref = no state update) | Must use `Object.is` equality — `toBe` does this |
| Update tasks when mtime differs | Return new `mtime`, verify `result.current.tasks` changes | Use counter in fetch stub to vary mtime per call |
| Error state for red traffic-light | Reject fetch, check `result.current.error` is truthy | Error should persist until next successful poll |
| `isFetching`/`isStale` for yellow traffic-light | Check `result.current.isFetching` during in-flight request (use deferred promise); check `isStale` after error | Need deferred promise pattern to keep request in-flight |
| AbortController cleanup on unmount | Spy on `AbortController.prototype.abort`, call `unmount()`, verify spy was called | Restore prototype after test |
| `/api/board` fetched once on mount | After multiple intervals, filter `fetchMock.mock.calls` for `/api/board` URL — expect exactly 1 | Separate from `/api/tasks` call counting |

### 3.3 Hook Interface for Tests

Current `useBoard` returns: `{ board, tasks, loading, error, refetchTasks }`.

Tests should expect the expanded interface:

```typescript
interface UseBoardResult {
  board: Board | null
  tasks: Task[]
  loading: boolean       // initial load only
  error: string | null   // last fetch error (red traffic-light)
  isFetching: boolean    // request in-flight (yellow traffic-light)
  isStale: boolean       // data not refreshed within expected interval
  refetchTasks: () => void
}
```

### 3.4 Edge Cases to Test

1. **Deferred promise for `isFetching`**: Use `new Promise(() => {})` (never resolves) to keep `isFetching: true` while request is in-flight.
2. **Reference stability**: When mtime is unchanged, `result.current.tasks` must be the exact same array reference — no `setTasks([...same])`.
3. **AbortController per tick**: Each interval should create a new AbortController, aborting the previous if still pending.

### 3.5 Existing Test Count

AC mentions "existing 26 KanbanBoard tests." Actual count is 35 in `KanbanBoard.test.tsx` + 11 in `_933` + 10 in `_963` = 56 total. Test-writer should verify all pass after adding the new file.

## 4. Recommendation

Copy the `usePolling.test.ts` pattern directly — same structure (fake timers, renderHook, fetch stubs, act wrappers). The test file is `useBoard.test.ts`, importing `useBoard` from `../KanbanBoard`. Tests will fail immediately because the current hook lacks polling, mtime-skip, isFetching/isStale, and AbortController. Confidence: 0.90.

Challenge: skipped — single viable approach (renderHook + fake timers is the only way to test React hooks with intervals). No alternative to compare.

## 5. Follow-up Tasks

None — this task IS the follow-up from #960. It proceeds to backlog for the test-writer.
