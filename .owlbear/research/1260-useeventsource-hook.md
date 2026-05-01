# useEventSource Hook Implementation Research

> **Owning task:** #1260 — Create useEventSource hook
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1260 (child of #1235) implements the SSE client hook: `hooks/useEventSource.ts`. The parent research (§3.2, §3.5) defines the state machine and interface. This research validates feasibility, confirms the implementation approach against prior art, and identifies testing constraints.

**Core question:** What's the simplest implementation that satisfies the state machine from §3.2, is testable in jsdom/vitest, and integrates with the existing hook architecture?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | WHATWG HTML Spec §9.2 (EventSource) | Normative spec | 0.95 |
| 2 | ReactUse `useEventSource` (reactuse.com) | React hook library | 0.8 |
| 3 | NepeinAV/react-sse-hooks (GitHub) | React hook library | 0.6 |
| 4 | serve/cockpit/web/src/hooks/usePollingFetch.ts | Live codebase | 1.0 |
| 5 | serve/cockpit/web/src/hooks/useConnectionHealth.ts | Live codebase | 1.0 |
| 6 | .owlbear/research/1235-eventsource-client-implementation.md | Parent research | 1.0 |
| 7 | jsdom + vitest EventSource mocking patterns | Testing constraint | 0.85 |

## 3. Analysis

### 3.1 Implementation Approach Comparison

| Approach | Description | Deps | Complexity | KISS |
|----------|-------------|------|-----------|------|
| A: Native EventSource + custom state machine | Zero-dep, ~60 LOC hook | 0 | Low | 0.9 |
| B: Use ReactUse `useEventSource` | Wraps library hook, add stall detection | 1 | Low | 0.7 |
| C: Use react-sse-hooks (provider pattern) | Context provider + listener hooks | 1 | Medium | 0.5 |

**Verdict: Approach A.** Our needs are narrow (one event type, stall detection, `enabled` toggle). Library hooks (B, C) add generic features we don't need (multiple events, data parsing, reconnect config). Native EventSource is ~60 LOC with zero additional dependencies.

### 3.2 jsdom Testing Constraint

jsdom does **not** implement `EventSource`. Tests must mock the global:

```typescript
class MockEventSource {
  static instances: MockEventSource[] = []
  static CONNECTING = 0; static OPEN = 1; static CLOSED = 2
  readyState = 0
  url: string
  onopen: ((e: Event) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  close = vi.fn()
  listeners: Record<string, ((e: MessageEvent) => void)[]> = {}
  addEventListener(type: string, fn: (e: MessageEvent) => void) { ... }
  constructor(url: string) { this.url = url; MockEventSource.instances.push(this) }
}
vi.stubGlobal('EventSource', MockEventSource)
```

This is the same pattern used by the existing test suite (e.g., `vi.stubGlobal('fetch', ...)` in `usePollingFetch_1227.test.ts`). Confirmed viable.

### 3.3 State Machine Mapping to Implementation

| State | React state value | Trigger in → Trigger out |
|-------|-------------------|--------------------------|
| CONNECTING | `'connecting'` | Mount/enabled → onopen or onerror |
| OPEN | `'open'` | onopen fires → onerror fires |
| CLOSED | `'closed'` | 15s stall timer or readyState===CLOSED → 30s retry |

Key refs needed: `timerRef` (stall detection), `retryTimerRef` (30s reconnect), `esRef` (EventSource instance).

### 3.4 Interface (confirmed from parent research §3.5)

```typescript
interface UseEventSourceResult {
  status: 'connecting' | 'open' | 'closed'
  lastEventMtime: number | null
}
function useEventSource(url: string, options?: { enabled?: boolean }): UseEventSourceResult
```

### 3.5 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Timer leak on fast unmount | Low | Medium | Clear both timers in cleanup |
| React Compiler ref stability | Low | Low | All mutable state in refs, not closures |
| Event listener named `tasks-changed` | N/A | N/A | Use `addEventListener('tasks-changed', ...)` per spec |
| Backend endpoint not yet live | Expected | None | Graceful fallback: EventSource fails → status='closed' immediately |

## 4. Recommendation

Proceed with Approach A: native `EventSource`, zero dependencies, ~60 LOC hook. The state machine from the parent research (§3.2) maps directly to implementation. Testing via mock global is proven in the existing suite.

**Confidence: 0.85**

Challenge: FALLBACK — trivial implementation task with architecture already defined by parent research. Challenger would add no value beyond what §3.2 already validated (which survived challenger scrutiny in #1235).

## 5. Follow-up Tasks

No additional follow-up tasks needed — this task IS the follow-up from #1235. The implementation task (#1260) is well-scoped with clear AC from the parent research.
