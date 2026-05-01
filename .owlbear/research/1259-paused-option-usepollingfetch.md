# Add paused option to usePollingFetch

> **Owning task:** #1259 — Add paused option to usePollingFetch
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1235 (EventSource client implementation) identified the need for a `paused` option on `usePollingFetch` so that SSE-driven boards can suppress interval ticks while the EventSource connection is active, while preserving `refetch()` for on-demand pulls triggered by SSE events.

**Question:** What is the correct implementation pattern for a `paused` boolean that skips interval-driven polls without disrupting timer stability or breaking `refetch()`?

## 2. Sources Studied

| # | Source | Relevance | Score |
|---|--------|-----------|-------|
| 1 | Dan Abramov — "Making setInterval Declarative with React Hooks" (overreacted.io) | Canonical `delay: null` pattern for pausing intervals in React | 0.9 |
| 2 | TanStack Query — `enabled` option on `useQuery` | Industry-standard pause pattern for data-fetching hooks | 0.8 |
| 3 | ReactUse — `useInterval` with `Pausable` return | Alternative: returns pause/resume methods via Pausable interface | 0.6 |
| 4 | Existing `usePollingFetch.ts` (codebase) | Current implementation — ref-heavy, inFlight guard, AbortController cleanup | 1.0 |
| 5 | `.owlbear/research/1235-eventsource-client-implementation.md` §3.5–3.6 | Consumer contract: how `useBoard` will orchestrate pause/resume | 0.9 |

## 3. Analysis

### Implementation Options

| Approach | Mechanism | Timer stability | Initial mount | Resume behavior | Code delta |
|----------|-----------|-----------------|---------------|-----------------|------------|
| **A: Ref-based tick check** | Keep interval running; check `pausedRef.current` before calling `poll()` | Stable — no teardown/setup | Always fires | Next natural tick | +5 LOC |
| **B: Conditional interval** (Dan Abramov) | Add `paused` to effect deps; don't create interval when paused | Perfect — no ticks | Conditional on paused | Immediate poll + new timer | +10 LOC |
| **C: Delay-null passthrough** | Map `paused → intervalMs: null`; wrap existing effect with `if (delay !== null)` | Reset on pause/unpause | Conditional | Immediate poll + new timer | +8 LOC |

### Trade-off Assessment

| Criterion | A (ref check) | B (conditional) | C (delay-null) |
|-----------|:---:|:---:|:---:|
| Backward compatible | ✓ | ✓ | ✓ |
| No timer drift on pause/unpause | ✓ | ✗ | ✗ |
| No unwanted immediate poll on resume | ✓ | ✗ | ✗ |
| Interval truly idle when paused | ✗ | ✓ | ✓ |
| No effect dep change | ✓ | ✗ | ✗ |
| KISS alignment | ✓ | — | — |

### Why Approach A wins for this use case

The SSE orchestration pattern (research doc §3.6) requires:
1. Mount → immediate fetch (initial hydration) — ALWAYS, regardless of paused
2. SSE opens → `paused=true` — no interval polls
3. SSE event → `refetch()` fires — must work while paused
4. SSE dies → `paused=false` — polling resumes on next natural tick (not immediately)

Point 4 is decisive: when SSE reconnection fails after 15s, the fallback to polling should resume on the next tick, not fire an immediate burst. Approach A's timer stability delivers this naturally. Approach B/C would fire an immediate poll on resume, potentially causing a redundant request if the SSE error handler already triggered a refetch.

### Implementation Sketch (Approach A)

```typescript
// In UsePollingFetchOptions:
paused?: boolean  // default false

// In hook body:
const pausedRef = useRef(options?.paused ?? false)
pausedRef.current = options?.paused ?? false

// In interval callback (inside useEffect):
const intervalId = setInterval(() => {
  if (!pausedRef.current) {
    void poll()
  }
}, intervalMs)
```

No changes to: initial `void poll()`, cleanup logic, `refetch()` return, deps array.

## 4. Recommendation

**Approach A (ref-based tick check).** Confidence: 0.90.

Challenge: SKIP — trivial, single-option-dominates addition with clear prior art and no architectural trade-offs. The only viable alternative (conditional interval) actively harms the consumer's use case (timer drift on resume).

## 5. Follow-up Tasks

This task IS the follow-up (created by #1235 research). No further decomposition needed — the implementation is ~5 LOC in a single file with a matching test addition to the existing `usePollingFetch_1227.test.ts` suite.

Downstream consumer: #1261 (integrate EventSource into useBoard) already depends on #1259.
