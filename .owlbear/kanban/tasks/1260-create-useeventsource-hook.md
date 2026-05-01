---
id: 1260
title: Create useEventSource hook
status: in-progress
priority: nice-to-have
created: 2026-05-01T09:34:24.718353+00:00
updated: 2026-05-01T15:55:24.348183+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create hooks/useEventSource.ts implementing the SSE connection state machine: connect, listen for tasks-changed events, track readyState transitions, implement 15s reconnect-stall detection, cleanup on unmount. Returns {status, lastEventMtime}. See .owlbear/research/1235-eventsource-client-implementation.md §3.2 and §3.5
[[2026-05-01]]
## Research
- Research doc: .owlbear/research/1260-useeventsource-hook.md
- Sources: 7 studied, 4 high-relevance (≥0.8)
- Recommendation: Native EventSource + custom state machine (~60 LOC), zero deps (confidence: 0.85)
- Follow-up tasks created: none (this IS the implementation task)
- Decision requests: none (T1 — autonomous implementation)

## Challenge Results
- Challenger: FALLBACK — trivial implementation with architecture fully defined by parent research #1235 (which already survived challenger scrutiny)
- Confidence in original: 0.85
- Key findings: jsdom lacks EventSource (mock required); native API + refs = simplest approach; existing vi.stubGlobal pattern proven in usePollingFetch tests; state machine maps directly to 3 React state values
[[2026-05-01]]

## Acceptance Criteria

- [ ] AC1: `hooks/useEventSource.ts` exports `useEventSource(url: string, options?: { enabled?: boolean }): UseEventSourceResult` where `UseEventSourceResult = { status: 'connecting' | 'open' | 'closed', lastEventMtime: number | null }` — both the function and the result type are named exports (td:1)
- [ ] AC2: When `enabled` is true (default), creates a native `EventSource` connecting to `url`; `status` is `'connecting'` initially, transitions to `'open'` on `onopen`, and to `'closed'` on fatal error (`readyState===EventSource.CLOSED` after `onerror`) (td:2)
- [ ] AC3: Listens for `tasks-changed` events via `addEventListener('tasks-changed', ...)`; on receipt, parses `event.data` as JSON and updates `lastEventMtime` to the `mtime` number value (td:2)
- [ ] AC4: Reconnect-stall detection — when `onerror` fires with `readyState===EventSource.CONNECTING`, starts a 15s stall timer; clears any previous stall timer first (single timer guarantee); if `onopen` does not fire within 15s, calls `close()` and sets `status='closed'` (td:2)
- [ ] AC5: Retry after failure — after entering `'closed'` state (fatal error or stall timeout), schedules a 30s retry timer to create a new `EventSource`; on successful `onopen`, transitions to `'open'` and clears the retry timer; only one retry timer is active at a time (td:2)
- [ ] AC6: Cleanup on unmount — closes any active `EventSource` instance and clears all pending timers (stall timer, retry timer); no React state updates occur after unmount (td:2)
- [ ] AC7: When `enabled` is false or transitions from true to false, closes any active `EventSource` and clears all timers; returns `status='closed'` and `lastEventMtime=null`; re-enabling creates a fresh connection (td:1)

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One hook, one concern: SSE connection lifecycle |
| Interface clarity | PASS | 7 AC lines specify inputs, outputs, state transitions, timers, cleanup |
| Dependency correctness | PASS | #1235 (archived/done); no runtime deps beyond native EventSource API |
| Module layering | PASS | New file in `hooks/` — same level as `usePollingFetch.ts`, `useConnectionHealth.ts`; no upward imports |
| TDD compliance | PASS | Standard pipeline — test-writer processes before builder |
| KISS/YAGNI | PASS | ~60 LOC, zero deps, native API; 3-state return (downstream #1261 derives richer state) |
| Premise challenge | PASS | No existing EventSource hook in codebase; React lifecycle wrapping is necessary |
| Pattern consistency | PASS | Ref-based mutable state (matches `usePollingFetch`); cleanup in `useEffect` return |
| Security surface | PASS | Same-origin connection to `/api/events`; no user-controlled path construction |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `new EventSource(url)` | Endpoint missing/wrong content-type | N/A (readyState→CLOSED) | Yes — AC2 fatal error path | `status='closed'`, retry after 30s |
| `onerror` + CONNECTING | Browser auto-reconnect stalls | N/A | Yes — AC4 15s stall timer | `status='closed'` after 15s |
| Fast unmount | Timer leak / state update after unmount | N/A | Yes — AC6 cleanup | No leak, no React warning |
| `event.data` parse | Malformed JSON from server | SyntaxError | Builder should guard — implementation detail | `lastEventMtime` unchanged |
| enabled toggle | Rapid true→false→true | N/A | Yes — AC7 full cleanup then fresh connection | Clean reconnect cycle |

### Backend Contract Note

The backend endpoint (#1234) is in `todo` with a known defect (`if not changes: break` → should be `continue`) — the refined AC on #1234 requires idle-timeout to continue watching. This hook's state machine correctly handles both the current (broken) and fixed backend behavior: if the stream closes prematurely, the hook enters `closed` and retries after 30s. Once #1234 is fixed, quiet boards stay connected with `status='open'`.

### Design Diverge

Skipped — single viable approach from research (native EventSource + refs, zero deps). No competing design.

### Challenge Results

- Challenger: reconsider (0.42)
- Key concerns: (1) backend contract mismatch, (2) downstream interface sufficiency, (3) complexity understated
- Architect response:
  - (1) **Rebutted.** Backend bug is already identified and being fixed in #1234 (refined AC6c: `continue` not `break`). Hook state machine handles both current and fixed backend correctly.
  - (2) **Rebutted.** 3-state interface is a low-level primitive. Downstream #1261 (in `research`) will derive reconnecting-vs-initial from status transitions. Adding a 4th state violates KISS for this layer.
  - (3) **Partially accepted.** Added single-timer guarantees to AC4 and AC5 to prevent stacking. Test depth annotations (td:2) on 5 of 7 AC lines correctly reflect complexity.
- Final: Proceed with APPROVE — concerns are either resolved (backend fix) or downstream scope (integration).

### Test Depth

- Max depth: td:2
- Test-writer: PROCEED

### Builder Guidance

- Use refs (`useRef`) for EventSource instance, stall timer, and retry timer — not closures over stale state (React Compiler compatibility per research §3.5).
- Mock pattern for tests: `vi.stubGlobal('EventSource', MockEventSource)` — same pattern as `vi.stubGlobal('fetch', ...)` in `usePollingFetch_1227.test.ts`, but MockEventSource must simulate `readyState`, `onopen`, `onerror`, `addEventListener`, and `close()`.
- Unmount safety: check `isMountedRef.current` before any `setState` call in async callbacks.
- Timer-driven hooks have stricter test precedent in this codebase — see `useScanPolling_1157.test.ts` for StrictMode and rerender coverage patterns.

### Verdict: APPROVE
### Action Taken: AC written (7 lines, max td:2), architecture sound, advancing to todo

[[2026-05-01]]
## Architecture Review

**Verdict: APPROVE** — AC written (7 lines, max td:2), architecture sound, advancing to todo.

Codebase verified: hook placement in `hooks/` matches existing pattern (`usePollingFetch.ts`, `useConnectionHealth.ts`); ref-based mutable state pattern consistent; backend endpoint exists at `routes/events.py` (emits `event: tasks-changed`). All 10 criteria PASS. Failure mode map covers 5 codepaths. Challenger rebutted (reconsider 0.42 → backend bug already being fixed in #1234, downstream interface is #1261 scope, timer stacking addressed in AC4/AC5). Test-writer: PROCEED.
[[2026-05-01]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
- Classes: `TestFromAC_UseEventSource`
- Total: 24 tests, all FAIL (ImportError — `hooks/useEventSource.ts` not yet created)
- Lint: clean (ESLint exit 0)

### Tests per category

| AC | Tests | Categories |
|----|-------|-----------|
| AC1 (td:1) | 2 | return type shape |
| AC2 (td:2) | 4 | happy (status transitions), edge (url passed) |
| AC3 (td:2) | 3 | happy (lastEventMtime update), edge (listener registration), boundary (null initial) |
| AC4 (td:2) | 4 | happy (15s fires), boundary (14999ms no-fire), edge (single-timer guarantee), edge (onopen clears timer) |
| AC5 (td:2) | 4 | happy (fatal error → retry), happy (stall → retry), boundary (29999ms no-retry), happy (retry onopen → open) |
| AC6 (td:2) | 4 | happy (close on unmount), edge (stall timer cleared), edge (retry timer cleared), edge (post-unmount callbacks inert) |
| AC7 (td:1) | 3 | happy (enabled=false), happy (true→false transition), happy (re-enable) |

### AC coverage table

| AC | Covered | Tests |
|----|---------|-------|
| AC1 | ✓ | 2 |
| AC2 | ✓ | 4 |
| AC3 | ✓ | 3 |
| AC4 | ✓ | 4 |
| AC5 | ✓ | 4 |
| AC6 | ✓ | 4 |
| AC7 | ✓ | 3 |

### Mock pattern
`vi.stubGlobal('EventSource', MockEventSource)` with full state machine simulation: `simulateOpen()`, `simulateStallError()` (readyState===CONNECTING), `simulateFatalError()` (readyState===CLOSED), `simulateEvent(type, data)`. Consistent with `vi.stubGlobal('fetch', ...)` pattern from `usePollingFetch_1227.test.ts`.