# EventSource Integration into useBoard — Fallback Orchestration

> **Owning task:** #1261 — Integrate EventSource into useBoard with fallback orchestration
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

Dependencies #1259 (`paused` option on `usePollingFetch`) and #1260 (`useEventSource` hook) are complete. This task wires them together inside `useBoard` and extends `useConnectionHealth` to reflect transport state. The question: what's the minimal integration pattern that preserves existing test contracts while adding SSE-first behaviour with polling fallback?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.owlbear/research/1235-eventsource-client-implementation.md` §3.4–3.6 | Design spec | 0.95 |
| 2 | `serve/cockpit/web/src/hooks/useBoard.ts` | Live code | 1.0 |
| 3 | `serve/cockpit/web/src/hooks/useEventSource.ts` | Live code | 1.0 |
| 4 | `serve/cockpit/web/src/hooks/usePollingFetch.ts` | Live code | 1.0 |
| 5 | `serve/cockpit/web/src/hooks/useConnectionHealth.ts` | Live code | 1.0 |
| 6 | `serve/cockpit/web/src/__tests__/useBoard.test.ts` | Existing tests | 0.9 |
| 7 | `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` | Existing tests | 0.8 |
| 8 | `serve/cockpit/src/owlbear_cockpit/routes/events.py` | Backend endpoint | 0.9 |

## 3. Analysis

### 3.1 Current State

- `useBoard` calls `usePollingFetch('/api/tasks', { intervalMs: 3000 })` — no SSE.
- `useConnectionHealth` computes green/yellow/red from elapsed time since last success. Returns `{ health, markHealthy, updateHealth }`. No override mechanism.
- `useEventSource('/api/events')` returns `{ status, lastEventMtime }`. It's standalone.
- Backend `GET /api/events` emits `event: tasks-changed` with `{"mtime": N}` on task-file changes.

### 3.2 Integration Design (Option A from §3.1 of parent research)

| Step | Action | Code location |
|------|--------|---------------|
| 1 | Call `useEventSource('/api/events')` inside `useBoard` | `useBoard.ts` |
| 2 | Derive `paused = (sseStatus === 'open')` → pass to `usePollingFetch` | `useBoard.ts` |
| 3 | When `lastEventMtime` changes and SSE is open → call `refetchTasks()` | `useBoard.ts` useEffect |
| 4 | Map SSE status to health override: open→green, connecting→yellow, closed→null (fall through to polling health) | `useBoard.ts` or `useConnectionHealth` |
| 5 | Extend `useConnectionHealth` to accept optional `transportOverride?: HealthState | null` | `useConnectionHealth.ts` |

### 3.3 Health Override Design

Two options for transport-state override:

| Option | Description | Complexity | Backwards compat |
|--------|-------------|-----------|-----------------|
| X: Parameter on `useConnectionHealth` | Add `transportOverride` param; when non-null, short-circuit `health` to that value | Low | Full — default null = no change |
| Y: Separate state in `useBoard` | `useBoard` computes final health from SSE status + polling health locally, never touches `useConnectionHealth` | Medium | Full — useConnectionHealth unchanged |

**Recommendation: Option Y.** `useConnectionHealth` is a polling-focused utility. SSE transport override is `useBoard`-level orchestration logic. Adding an override parameter to useConnectionHealth leaks transport awareness into a generic utility.

Implementation: `useBoard` computes `effectiveHealth`:
```
if sseStatus === 'open' → 'green'
if sseStatus === 'connecting' → 'yellow'
if sseStatus === 'closed' → fall through to existing polling-based health
```

### 3.4 Refetch Trigger

`useEventSource` exposes `lastEventMtime`. A `useEffect` watching `lastEventMtime` calls `refetchTasks()` when it changes (and SSE is open). This avoids double-fetch: the initial hydration comes from polling's immediate call on mount, SSE events only trigger subsequent refetches.

### 3.5 Edge Cases

| Case | Behaviour |
|------|-----------|
| Backend missing `/api/events` | EventSource → CLOSED immediately; fallback to polling (identical to today) |
| Server restart | Brief reconnect (yellow); onopen resumes green + pauses polling |
| Quiet board (no events) | SSE open → green; no refetch needed (no mutations) |
| SSE stall >15s | useEventSource → closed; paused=false → polling resumes |
| Browser tab hidden | EventSource stays connected (spec behaviour); no cost |
| Rapid mutations | Multiple `tasks-changed` → multiple refetches; usePollingFetch deduplicates in-flight |

### 3.6 Test Strategy

| Layer | Tests needed | Existing impact |
|-------|-------------|-----------------|
| `useBoard` integration | New test file: verify SSE open pauses polling, event triggers refetch, fallback resumes polling, health mapping | Existing useBoard tests pass (EventSource mock needed — defaults to CLOSED → fallback → same as today) |
| `useConnectionHealth` | None (unchanged with Option Y) | All pass unchanged |
| Shell | None — Shell already reads `health` from `useBoard` | Pass unchanged |

**Confidence: 0.85** — All building blocks exist; integration is straightforward wiring. The only risk is test mock complexity (must stub global EventSource in useBoard integration tests).

## 4. Recommendation

Proceed with integration as described in §3.2 + Option Y for health override. The task is well-scoped: ~30 LOC in `useBoard.ts` + a new integration test file. `useConnectionHealth.ts` remains unchanged.

## 5. Follow-up Tasks

1. **Implement #1261** — Wire `useEventSource` into `useBoard`, compute `effectiveHealth`, add `paused` derivation + refetch trigger. Write integration tests. (This is the task itself — moves to backlog for arch review.)
