# Wire usePendingDRs to SSE decisions-changed Early-Refetch

> **Owning task:** #1263 — Wire usePendingDRs to SSE decisions-changed early-refetch
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

Task #1263 (child of #1236) requires `usePendingDRs` to react to `decisions-changed` SSE events by triggering an immediate refetch, supplementing (not replacing) the existing 60s poll. The parent research (#1236) defined the event model and architectural constraints. This research identifies the minimal implementation pattern for the frontend wiring.

**Current state:**
- Backend: `/api/events` already emits typed `decisions-changed` events (events.py:69)
- `useEventSource` hook exists, but only listens for `tasks-changed`
- `usePendingDRs` exposes `refetch()` and runs a 60s `usePollingFetch` poll
- Both hooks are called in `Shell.tsx` at the same component level

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | serve/cockpit/web/src/hooks/useEventSource.ts | Live code | 1.0 |
| 2 | serve/cockpit/web/src/hooks/usePendingDRs.ts | Live code | 1.0 |
| 3 | serve/cockpit/web/src/hooks/useBoard.ts | Live code | 1.0 |
| 4 | serve/cockpit/web/src/Shell.tsx | Live code | 1.0 |
| 5 | serve/cockpit/src/owlbear_cockpit/routes/events.py | Live code | 0.9 |
| 6 | .owlbear/research/1236-extend-sse-decisions-activity.md | Parent research | 1.0 |

## 3. Analysis — Implementation Options

| Option | Approach | LOC delta | New files | KISS | Future-proof |
|--------|----------|-----------|-----------|------|--------------|
| A: Generic eventTypes param | `useEventSource` accepts `eventTypes: string[]`, returns `Record<string, number>` | ~30 | 0 | Medium | High — handles activity-changed too |
| B: Add `lastDecisionsMtime` field | Hard-code 2nd listener in `useEventSource`, expose through `useBoard`, wire in Shell | ~12 | 0 | High | Low — add more fields per type |
| C: EventSource context provider | New React context wraps app, both hooks consume shared connection | ~60 | 1 | Low | High — unlimited consumers |
| D: Second EventSource in `usePendingDRs` | `usePendingDRs` opens its own `/api/events` connection | ~15 | 0 | Medium | Low — duplicate connections |

**Option D rejected:** Two SSE connections to the same endpoint wastes browser resources.
**Option C rejected:** YAGNI — only 2 consumers exist; context adds provider boilerplate.
**Option B rejected:** Next task (#1264, activity-changed) would need a 3rd field immediately, violating DRY.

### Recommendation: Option A (generic event subscription)

Extend `useEventSource` to accept subscribed event type names and return per-type mtimes. This handles both #1263 (decisions) and #1264 (activity) without further hook changes.

**API shape:**

```typescript
export type UseEventSourceResult = {
  status: 'connecting' | 'open' | 'closed'
  lastEventMtime: number | null             // backward compat (latest across all types)
  lastEventByType: Record<string, number>   // per-type latest mtime
}

export function useEventSource(
  url: string,
  options?: UseEventSourceOptions & { eventTypes?: string[] },
): UseEventSourceResult
```

Default `eventTypes` = `['tasks-changed']` (backward compat). `useBoard` adds `'decisions-changed'` and exposes `lastDecisionsMtime` in its return type.

**Wiring in Shell.tsx** (~5 LOC):

```typescript
const { lastDecisionsMtime, ...boardRest } = useBoard()
// Trigger early refetch when decisions-changed SSE fires
useEffect(() => {
  if (lastDecisionsMtime !== null) refetchPendingDRs()
}, [lastDecisionsMtime, refetchPendingDRs])
```

**60s poll stays active** — `usePendingDRs` unchanged except Shell gains early-refetch trigger. No `paused` option needed.

### Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `useBoard` test breakage from new return field | Low | Additive — existing destructuring unaffected |
| Race between SSE refetch and poll refetch | Negligible | `usePollingFetch` debounces via `inFlightRef` |
| SSE stall leaves decisions on 60s-only | By design | SSE is supplementary; poll is the safety net |

## 4. Recommendation

**Option A — generic event subscription in `useEventSource`.** Confidence: 0.82.

Changes needed:
1. `useEventSource.ts` — accept `eventTypes` option, register `addEventListener` per type, maintain `lastEventByType` map, keep `lastEventMtime` as max across all types
2. `useBoard.ts` — pass `eventTypes: ['tasks-changed', 'decisions-changed']`, expose `lastDecisionsMtime` from hook result
3. `Shell.tsx` — add `useEffect` watching `lastDecisionsMtime` → `refetchPendingDRs()`
4. Tests — extend `useEventSource_1260.test.ts` or new test file for multi-type subscription

Challenge: FALLBACK — trivial wiring task, parent research (#1236) already challenged the full architecture.

## 5. Follow-up Tasks

No new tasks needed — #1263 itself is the implementation task. Advance to backlog with AC derived from this analysis.
