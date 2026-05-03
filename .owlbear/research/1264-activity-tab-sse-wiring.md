# Wire ActivityTab to SSE activity-changed Live Updates

> **Owning task:** #1264 — Wire ActivityTab to SSE activity-changed live updates
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

ActivityTab currently fetches `/api/sessions?filter=all` once on mount via a raw `useEffect` and never refetches. The backend `/api/events` SSE endpoint already emits `activity-changed` events (implemented in #1262). The question: how to wire ActivityTab to refetch session data when an `activity-changed` event fires, without duplicating the SSE connection already owned by `useBoard`.

**Current architecture:**
- `useBoard` → calls `useEventSource('/api/events')` → creates one EventSource instance
- Each additional `useEventSource()` call creates a **separate** HTTP connection + server-side watcher thread
- Shell renders both `useBoard` (via KanbanBoard) and ActivityTab as siblings

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/hooks/useEventSource.ts` | Live code | 1.0 |
| 2 | `serve/cockpit/web/src/hooks/useBoard.ts` | Live code | 1.0 |
| 3 | `serve/cockpit/web/src/components/ActivityTab.tsx` | Live code | 1.0 |
| 4 | `serve/cockpit/web/src/hooks/usePollingFetch.ts` | Live code | 0.9 |
| 5 | `serve/cockpit/src/owlbear_cockpit/routes/events.py` | Live code | 0.9 |
| 6 | `.owlbear/research/1236-extend-sse-decisions-activity.md` | Parent research | 1.0 |
| 7 | `serve/cockpit/web/src/Shell.tsx` | Live code | 0.9 |

## 3. Analysis

### 3.1 SSE Connection Sharing — The Core Problem

`useEventSource` creates a new `EventSource` instance per hook call. Three consumers (tasks, decisions, activity) calling it independently = 3 SSE connections = 3 server-side `awatch` threads. Browsers limit concurrent connections per origin (6 for HTTP/1.1, effectively unlimited for HTTP/2). The localhost dev scenario is fine, but it's wasteful design.

| Option | Description | Connections | New LOC | Refactor delta |
|--------|-------------|-------------|---------|----------------|
| A: EventSourceProvider context | Single connection in React context; consumers subscribe by event type | 1 | ~60 | Medium — lift `useEventSource` to provider, `useBoard` consumes via context |
| B: Extend `useEventSource` + lift to Shell | Add per-event-type mtimes to hook return; call once in Shell, pass down as props | 1 | ~30 | Low — add state vars + listeners; thread props through Shell |
| C: Accept duplicate connections | ActivityTab calls `useEventSource` independently | 2–3 | ~10 | None — just call the hook |

### 3.2 Option A — EventSourceProvider (Recommended)

```typescript
// hooks/EventSourceProvider.tsx (~50 LOC)
const EventSourceContext = createContext<EventSourceState>(...)

export function EventSourceProvider({ url, children }) {
  // Single EventSource connection, multiple event listeners
  // Exposes: status, lastMtimes: Record<string, number | null>
}

export function useSSEEvent(eventType: string): { mtime: number | null; status }
```

**Advantages:**
- Single connection serves all current + future consumers
- `useBoard` refactor is small: replace `useEventSource('/api/events')` with `useSSEEvent('tasks-changed')`
- ActivityTab: `useSSEEvent('activity-changed')` — clean one-liner
- Sibling task #1263 (usePendingDRs): same pattern with `useSSEEvent('decisions-changed')`
- No props drilling — context distributes naturally

**Disadvantages:**
- Introduces a context provider (~50 LOC infra)
- `useBoard` must be refactored (breaks its current self-contained SSE ownership)
- All tests mocking `useEventSource` need provider wrapping

### 3.3 Option B — Lift + Props

Shell calls the extended `useEventSource` once, passes per-event-type results to children.

**Advantages:**
- No new abstractions (context, provider)
- Minimal new code (~30 LOC changes to `useEventSource` + Shell)

**Disadvantages:**
- Props drilling: Shell → KanbanBoard, Shell → ActivityTab, Shell → usePendingDRs
- `useBoard` API changes (accepts SSE state as parameter instead of owning it)
- Gets unwieldy with 3+ consumers

### 3.4 Option C — Accept Duplicate Connections

ActivityTab creates its own `useEventSource('/api/events')` with `activity-changed` listener.

**Advantages:**
- Zero refactoring of existing hooks
- Simplest implementation (5-line delta in ActivityTab + event listener in hook)

**Disadvantages:**
- 2 SSE connections now, 3 when #1263 lands — each with its own `awatch` thread
- Duplicates reconnection/stall logic per consumer
- Technical debt that accrues with each new event type consumer

### 3.5 ActivityTab Refetch Pattern

Regardless of SSE sharing approach, ActivityTab needs a refetchable data-fetching pattern:

| Pattern | Description | Fit |
|---------|-------------|-----|
| `usePollingFetch` with `paused: true` | Existing hook; disable timer, use `refetch()` on SSE trigger | Good — reuses existing infra |
| Custom `useFetch` wrapper | Minimal hook exposing `{ data, refetch }` | Simpler but new abstraction |
| Inline state + extracted fetch fn | Keep `useState` + extract the fetch into a stable callback | Minimal — no new hook |

**Recommendation: `usePollingFetch` with high interval + `paused: true`.** This reuses the existing hook without inventing new abstractions. Set `intervalMs` to `Infinity` or a large fallback (e.g., 120_000) and `paused: true` when SSE is connected — identical to how `useBoard` uses it. The `refetch()` callback triggers on SSE `activity-changed`.

### 3.6 Testing Strategy

- **Unit test (ActivityTab):** Mock the SSE context/hook; simulate `activity-changed` mtime change; assert refetch fires and new data renders.
- **Integration test (Shell):** Verify that a single EventSource provider exists; ActivityTab refetches when provider emits activity event.
- **Existing tests:** `ActivityTab_1156.test.tsx` tests filtering/rendering — should remain green with the refactor (mount still triggers initial fetch).

## 4. Recommendation

**Option A: EventSourceProvider context.** Confidence: **0.78**

Rationale: Three consumers (#1261 tasks, #1264 activity, #1263 decisions) need the same SSE connection. The context approach solves all three with one architectural change. The alternative (duplicate connections) works now but creates immediate tech debt since #1263 is a parallel sibling task.

**Implementation path:**
1. Create `EventSourceProvider` + `useSSEEvent` hook (~50 LOC)
2. Wrap Shell children with provider
3. Refactor `useBoard` to use `useSSEEvent('tasks-changed')` instead of `useEventSource`
4. Refactor ActivityTab: replace one-shot fetch with `usePollingFetch` (paused when SSE open) + `useSSEEvent('activity-changed')` trigger

**Key design principles:**
- SSE supplements, does not replace, the initial mount fetch (activity has no continuous poll to pause — just refetch on event)
- `usePollingFetch` with large fallback interval provides resilience if SSE drops
- Single SSE connection shared via context — no duplicate watchers

Challenge: not invoked (info-only research; no competing alternatives with close confidence scores). Option A dominates on scalability while Option C's only advantage is simplicity, offset by immediate tech debt from #1263.

## 5. Follow-up Tasks

1. **Create EventSourceProvider context and useSSEEvent hook** — new context provider managing single `/api/events` connection; typed per-event subscriptions. Depends on: none.
2. **Refactor useBoard to consume EventSourceProvider** — replace internal `useEventSource` call with `useSSEEvent('tasks-changed')`; adjust tests. Depends on: follow-up 1.
3. **Wire ActivityTab to SSE activity-changed** (implementation) — refactor to `usePollingFetch` + `useSSEEvent('activity-changed')` trigger. Depends on: follow-ups 1, 2.
