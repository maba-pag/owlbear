# useBoard Polling GREEN Implementation Approach

> **Owning task:** #967 — GREEN: useBoard polling with mtime-skip and error states
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #967 is a GREEN-phase build: extract `useBoard` from `KanbanBoard.tsx` to `hooks/useBoard.ts`, add 3s polling with mtime-skip, error/stale states, and AbortController cleanup. Prior research #960 chose plain `setInterval` over TanStack Query. This research validates the implementation approach and resolves edge cases.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | React docs: useEffect | https://react.dev/reference/react/useEffect | 0.9 |
| 2 | MDN: AbortController | https://developer.mozilla.org/en-US/docs/Web/API/AbortController | 0.8 |
| 3 | Prior research: #960 polling choice | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 1.0 |
| 4 | Prior research: #966 Shell wiring | `.owlbear/research/966-shell-traffic-light-wiring.md` | 0.9 |
| 5 | Codebase: `usePolling.ts` (existing pattern) | `serve/cockpit/web/src/usePolling.ts` | 1.0 |
| 6 | Codebase: `KanbanBoard.tsx` useBoard + refetchTasks | `serve/cockpit/web/src/KanbanBoard.tsx` L39-95, L243 | 1.0 |
| 7 | Codebase: `cache.py` mtime source (st_mtime_ns) | `serve/cockpit/src/owlbear_cockpit/cache.py` L23-28 | 0.9 |
| 8 | Codebase: `models.py` TaskListOut.mtime (int) | `serve/cockpit/src/owlbear_cockpit/models.py` L57-61 | 0.9 |

## 3. Analysis

### 3.1 Hook Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Polling strategy** | `setInterval` + skip-when-in-flight | Simpler than abort-per-tick; matches `usePolling.ts` pattern |
| **Mtime storage** | `useRef<number>` | Avoids re-render on mtime-only updates |
| **Board fetch** | One-shot `useEffect([], [])` | Config is quasi-static; no polling needed |
| **Unmount cleanup** | `AbortController` + `clearInterval` | Prevents state updates after unmount |
| **Overlap protection** | `isFetchingRef` flag — skip tick if true | No abort of in-flight requests; tolerates slow server |
| **`refetchTasks`** | Keep in return signature | Called at L243 after POST `/api/tasks/{id}/move` |

### 3.2 Return Signature

```typescript
interface UseBoardResult {
  board: Board | null
  tasks: Task[]
  loading: boolean      // true until first successful tasks+board load
  error: string | null  // last fetch error message, cleared on success
  isStale: boolean      // true when last poll errored (data may be outdated)
  isFetching: boolean   // true during any in-flight /api/tasks request
  refetchTasks: () => void  // immediate re-poll (post-mutation)
}
```

### 3.3 Edge Cases Resolved

| Edge Case | Resolution |
|-----------|-----------|
| **refetchTasks after mutation** | Kept in API. Triggers immediate poll outside interval. Resets stale flag on success. |
| **isStale semantics** | `isStale = true` when last poll errored. Cleared on next success. Traffic-light consumes `usePolling`, not this. |
| **Slow server (>3s response)** | Skip-when-in-flight: if a request is pending, the interval tick is a no-op. No abort. Request completes naturally. |
| **Mtime JS precision** | `st_mtime_ns` (~1.78×10¹⁸) exceeds `MAX_SAFE_INTEGER` (9×10¹⁵). JS float64 resolution at this magnitude is ~256ns. File operations differ by ms+, so false equality is not a practical risk. |
| **React StrictMode double-mount** | Cleanup aborts in-flight fetch and clears interval. Remount starts fresh. Two initial board fetches are harmless. |
| **Two polling loops** | Intentional per #966 research: `usePolling` is health-only (no body parse), `useBoard` is data-only. Backend `MtimeScanCache` makes repeated reads cheap. |

### 3.4 Implementation Sketch (~60 LoC)

```
useBoard():
  state: board, tasks, loading, error, isStale, isFetching
  refs: lastMtimeRef, isFetchingRef, abortCtrlRef

  useEffect([], []):  // one-shot board fetch
    fetch('/api/board', { signal }) → setBoard()
    cleanup: abort

  useEffect([], []):  // polled tasks fetch
    async pollTasks():
      if isFetchingRef.current → return (skip)
      isFetchingRef.current = true; setIsFetching(true)
      fetch('/api/tasks', { signal }) → parse → compare mtime
        → if different: setTasks(), update lastMtimeRef
        → setError(null), setIsStale(false), setLoading(false)
      catch: setError(), setIsStale(true)
      finally: isFetchingRef.current = false, setIsFetching(false)

    pollTasks()  // initial fetch
    interval = setInterval(pollTasks, 3000)
    cleanup: clearInterval, abort

  refetchTasks = () => pollTasks()  // immediate trigger

  return { board, tasks, loading, error, isStale, isFetching, refetchTasks }
```

### 3.5 Test Compatibility

| Concern | Status |
|---------|--------|
| 26 existing KanbanBoard tests | Compatible — they stub `fetch` globally; `useBoard` still calls `fetch` |
| `refetchTasks` call in tests | Preserved — same name, same behavior |
| Timer-based tests | New tests use `vi.useFakeTimers()` per `usePolling.test.ts` pattern |

## 4. Recommendation

**(rec)** Skip-when-in-flight polling with `refetchTasks` preserved — confidence: **0.85**

Challenge: `reconsider` — confidence in original: 0.50. Challenger identified five issues: (1) `refetchTasks` removal breaks L243 move flow — **accepted, kept in API**; (2) `isStale` semantics unresolved — **accepted, defined as "last poll errored"**; (3) abort-per-tick masks slow server — **accepted, switched to skip-when-in-flight**; (4) mtime JS precision — **analyzed, safe in practice (~256ns resolution vs ms-scale operations)**; (5) dual polling loops — **intentional per #966, documented**.

## 5. Follow-up Tasks

None needed — implementation AC is fully scoped on #967 itself. RED tests come from the upstream task in the pipeline.
