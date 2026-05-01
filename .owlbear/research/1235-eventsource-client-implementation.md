# EventSource Client Implementation: useBoard SSE Integration

> **Owning task:** #1235 — Replace useBoard polling with EventSource client
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1233 research chose SSE with invalidation-only events. Task #1234 defines the backend contract: `GET /api/events` emitting `event: tasks-changed\ndata: {"mtime": N}`. This task researches the frontend implementation: how to integrate `EventSource` into the existing hook architecture, define the fallback state machine, map connection state to health badge, and preserve test contracts.

**Critical correction:** The task body says "after 15s without events…resume polling." For invalidation-only SSE, silence means no mutations — a healthy state. The fallback trigger must be **15s in CONNECTING state** (reconnect stall) or **CLOSED** (permanent failure), not "no data events."

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | WHATWG HTML Spec §9.2 (Server-sent events) | Normative spec | 0.95 |
| 2 | reactuse.com/browser/useeventsource | React hook pattern | 0.7 |
| 3 | github.com/suqingdong/useEventSource | React hook library | 0.6 |
| 4 | serve/cockpit/web/src/hooks/useBoard.ts | Live implementation | 1.0 |
| 5 | serve/cockpit/web/src/hooks/usePollingFetch.ts | Live polling hook | 1.0 |
| 6 | serve/cockpit/web/src/hooks/useConnectionHealth.ts | Live health hook | 1.0 |
| 7 | .owlbear/research/1234-sse-endpoint-implementation.md | Backend contract | 0.9 |

## 3. Analysis

### 3.1 Architecture Options

| Option | Description | Complexity | Test impact | KISS score |
|--------|-------------|-----------|-------------|------------|
| A: New `useEventSource` hook + `paused` option on `usePollingFetch` | Separate concerns; SSE hook manages connection; polling hook gains pause | Medium | Low — existing polling tests unchanged | 0.8 |
| B: Replace `usePollingFetch` entirely with SSE-first hook | Single hook does SSE+fallback+fetch | High | High — all polling tests rewritten | 0.4 |
| C: Modify `useBoard` inline (no new hook) | SSE logic directly in useBoard | Low | Medium — useBoard tests all change | 0.5 |

**Recommendation: Option A.** Separation of concerns: `useEventSource` is reusable for future decisions/activity SSE (#1233 follow-up 3). Adding `paused` to `usePollingFetch` is a minimal, backward-compatible change (default: false).

### 3.2 EventSource State Machine

```
IDLE → new EventSource('/api/events')
  → onopen: state=CONNECTED, pause polling, mark health=green
  → onerror:
      if readyState===CONNECTING: state=RECONNECTING, start 15s timer, health=yellow
      if readyState===CLOSED: state=FAILED, resume polling, health=red
  → tasks-changed event: call refetchTasks()

RECONNECTING (browser auto-reconnects):
  → onopen: cancel 15s timer, state=CONNECTED, pause polling, health=green
  → 15s timer fires while still CONNECTING: close(), state=FAILED, resume polling, health=red

FAILED:
  → Periodic retry (30s): attempt new EventSource
  → onopen succeeds: state=CONNECTED, pause polling, health=green
```

Key spec behavior: EventSource fires `onerror` then auto-reconnects when connection drops (readyState stays CONNECTING). It fires `onerror` with readyState=CLOSED only on fatal failure (non-200, wrong content-type, HTTP 204).

### 3.3 Fallback Trigger (Revised)

| Trigger | Condition | Action |
|---------|-----------|--------|
| Fatal failure | readyState===CLOSED after onerror | Resume polling immediately |
| Reconnect stall | readyState===CONNECTING for >15s continuously | Close EventSource, resume polling |
| Missing endpoint | 404/wrong content-type → browser fails connection (CLOSED) | Resume polling (graceful degradation) |
| Successful reconnect | onopen fires during RECONNECTING | Pause polling, cancel timer |

This correctly handles: (a) quiet boards (SSE open, no events = green), (b) server restarts (brief reconnect = yellow), (c) endpoint missing (immediate fallback = red).

### 3.4 Health Badge Mapping

| State | HealthState | Source |
|-------|-------------|--------|
| EventSource OPEN | `green` | readyState check in onopen |
| EventSource CONNECTING (<15s) | `yellow` | onerror with readyState===CONNECTING |
| EventSource CLOSED / polling fallback | `red` → degrades to `yellow` per existing useConnectionHealth | Existing elapsed-time logic handles polling recovery |

**Note:** When in polling fallback, the existing `useConnectionHealth` semantics apply (green <6s since last success, yellow <15s, red ≥15s). The SSE state only overrides health when SSE is the active transport.

### 3.5 Hook Interfaces

```typescript
// New hook
interface UseEventSourceResult {
  status: 'connecting' | 'open' | 'closed'
  lastEventMtime: number | null
}
function useEventSource(url: string, options?: { enabled?: boolean }): UseEventSourceResult

// Extended option on existing hook
interface UsePollingFetchOptions<T> {
  // ... existing fields ...
  paused?: boolean  // NEW — when true, skip interval ticks (keeps refetch() working)
}
```

### 3.6 useBoard Orchestration

1. **Mount:** `usePollingFetch` fires immediate fetch (existing behavior — initial hydration)
2. **Connect:** `useEventSource('/api/events')` opens connection
3. **SSE open:** set `paused=true` on polling interval
4. **`tasks-changed` event received:** call `refetchTasks()` (triggers existing fetch+mtime logic)
5. **SSE reconnecting >15s or closed:** set `paused=false` (polling resumes at 3s)
6. **Unmount:** EventSource.close() + polling cleanup (existing AbortController)

### 3.7 Testing Strategy

| Layer | Approach | Existing tests |
|-------|----------|----------------|
| `useEventSource` | Mock global EventSource class; fire synthetic events | New suite |
| `usePollingFetch` + `paused` | Test that paused=true skips interval ticks | Existing tests pass (paused defaults false) |
| `useBoard` integration | Mock EventSource; verify refetch on event; verify fallback | Tests need EventSource mock added; behavioral assertions preserved |
| Health badge | Existing Shell tests mock usePolling/useBoard health output | Unchanged |

Mock pattern for Vitest:
```typescript
class MockEventSource {
  static instances: MockEventSource[] = []
  readyState = 0 // CONNECTING
  onopen: ((e: Event) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  close = vi.fn()
  addEventListener = vi.fn()
  // ... simulate open/error/event
}
vi.stubGlobal('EventSource', MockEventSource)
```

### 3.8 Dependency on #1234

The backend endpoint doesn't exist yet (#1234 is in backlog). Per WHATWG spec §9.2.3: if the server returns non-200 or wrong content-type, EventSource "fails the connection" (readyState→CLOSED, no reconnect). This means: deploying #1235 before #1234 is safe — EventSource will immediately fail, fallback activates, and the app behaves identically to today's polling.

## 4. Recommendation

Proceed with Option A: create `useEventSource` hook + add `paused` option to `usePollingFetch`. The state machine uses readyState (not event silence) as the fallback trigger.

**Confidence: 0.75**

Challenge: reconsider — confidence in original: 0.39. Challenger correctly identified: (1) false-fallback from "15s without events" on quiet boards, (2) timer lives in usePollingFetch not useBoard, (3) initial hydration still needs polling, (4) backend not yet live. All addressed: fallback triggers revised to readyState-based, architecture accounts for usePollingFetch ownership, initial fetch preserved, graceful degradation when endpoint missing.

## 5. Follow-up Tasks

1. Add `paused` option to `usePollingFetch` — backward-compatible (default false)
2. Create `useEventSource` hook — connection lifecycle, state machine, cleanup
3. Integrate EventSource into `useBoard` — orchestrate SSE+polling+health
4. Update `useConnectionHealth` to accept transport-state override
