# EventSourceProvider Context and useSSEEvent Hook

> **Owning task:** #1276 — Create EventSourceProvider context and useSSEEvent hook
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

Three Cockpit consumers need SSE events from `/api/events`: `useBoard` (tasks-changed), `usePendingDRs` (decisions-changed), and `ActivityTab` (activity-changed). The current `useEventSource` hook creates a new `EventSource` per call — 3 consumers means 3 connections and 3 server-side `awatch` threads.

Task: design a React context provider managing a single EventSource connection with per-event-type subscriptions via a `useSSEEvent(eventType)` hook.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/hooks/useEventSource.ts` | Live code (156 LOC) | 1.0 |
| 2 | `serve/cockpit/web/src/hooks/useBoard.ts` | Consumer pattern | 1.0 |
| 3 | `serve/cockpit/src/owlbear_cockpit/routes/events.py` | Backend SSE endpoint | 0.9 |
| 4 | `samouss/react-hooks-sse` (GitHub, 110⭐) | Prior art — SSEProvider + useSSE pattern | 0.8 |
| 5 | `.owlbear/research/1264-activity-tab-sse-wiring.md` | Parent recommendation (Option A) | 1.0 |
| 6 | `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` | Test pattern | 0.9 |

## 3. Analysis

### 3.1 Provider Architecture

| Aspect | Design Choice | Rationale |
|--------|--------------|-----------|
| Event type registration | Static list (`EVENT_TYPES` const array) | KISS — 3 known types, backend-defined |
| Mtime storage | `Record<string, number \| null>` in state | One state update per event batch, context propagates |
| Connection logic | Lifted from `useEventSource` | Proven reconnect/stall/retry already tested (24 tests) |
| Consumer API | `useSSEEvent(eventType)` → `{ mtime, status }` | Matches existing `UseEventSourceResult` shape |
| Provider placement | Wraps Shell children in `App.tsx` | Above all consumers, below router |

### 3.2 Implementation Approach

```
EventSourceProvider (manages connection + stores per-type mtimes)
├── useSSEEvent('tasks-changed')    → consumed by useBoard
├── useSSEEvent('decisions-changed') → consumed by usePendingDRs
└── useSSEEvent('activity-changed')  → consumed by ActivityTab
```

**Key file:** `serve/cockpit/web/src/hooks/EventSourceProvider.tsx` (~55 LOC)

- `createContext<EventSourceState>` with `{ status, mtimes }`
- Provider effect: opens EventSource, registers listeners for each type in `EVENT_TYPES`
- Reconnection: 15s stall timer, 30s retry (same constants as current hook)
- Cleanup: closes source, clears timers on unmount
- `useSSEEvent`: reads context, returns `{ mtime: ctx.mtimes[eventType] ?? null, status: ctx.status }`

### 3.3 Migration Impact

| Component | Change needed | Sibling task |
|-----------|--------------|--------------|
| `App.tsx` | Wrap children with `<EventSourceProvider url="/api/events">` | This task |
| `useBoard` | Replace `useEventSource('/api/events')` → `useSSEEvent('tasks-changed')` | #1277 |
| `usePendingDRs` | Add `useSSEEvent('decisions-changed')` trigger for `refetch()` | #1263 |
| `ActivityTab` | Add `useSSEEvent('activity-changed')` + `usePollingFetch` | #1264 |

### 3.4 Testing Strategy

- Mock `EventSource` globally (same `MockEventSource` class from existing tests)
- Wrap test components with `<EventSourceProvider>` for integration
- Unit tests: provider creates single connection, multiple `useSSEEvent` hooks return correct per-type mtimes
- Verify status propagation (connecting → open → closed)
- Verify stall/retry timers work through provider layer
- ~12 test cases targeting AC for this task

### 3.5 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Context re-renders all consumers on any event type change | Medium | Use `useMemo` on returned value in `useSSEEvent`; React Compiler may auto-memoize |
| Existing `useEventSource` tests break | None | Provider is additive; old hook stays until #1277 migrates `useBoard` |
| `useEventSource.ts` becomes dead code after #1277 | Expected | Remove in cleanup task post-migration |

## 4. Recommendation

**Implement static-listener EventSourceProvider with `useSSEEvent` consumer hook.** Confidence: **0.85**

- Reuse 100% of the connection/reconnect/stall logic from `useEventSource` (proven, 24 tests)
- ~55 LOC for provider + hook combined
- Zero new dependencies
- Unblocks 3 sibling tasks (#1277, #1263, #1264)
- Aligns with `react-hooks-sse` community pattern, simplified for our fixed-event-type use case

Challenge: deferred to parent research (#1264) which already validated the provider pattern at 0.78 confidence. No competing alternatives — Option A dominates.

## 5. Follow-up Tasks

No new follow-up tasks needed. Existing sibling tasks cover the full implementation chain:
- **#1276** (this task) → create provider + hook
- **#1277** → refactor useBoard to consume provider
- **#1263** → wire decisions SSE
- **#1264** → wire activity SSE
