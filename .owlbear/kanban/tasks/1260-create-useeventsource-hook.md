---
id: 1260
title: Create useEventSource hook
status: review
priority: nice-to-have
created: 2026-05-01T09:34:24.718353+00:00
updated: 2026-05-01T21:17:26.959767+00:00
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
[[2026-05-01]]
## Builder Notes
- Implementation: added `serve/cockpit/web/src/hooks/useEventSource.ts` with native EventSource state machine and named exports `useEventSource` + `UseEventSourceResult`.
- Behavior delivered: connecting/open/closed status transitions, `tasks-changed` JSON parsing to `lastEventMtime`, 15s stall timeout, 30s retry after closed, enabled toggle handling, and full cleanup on unmount.
- Tests: 24/24 task-scoped tests passed (`serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`).
- Coverage: 95.78% on touched module (`useEventSource.ts`), functions 100%, lines 100%.
- Lint: ESLint clean for changed source and task test file.
- RED evidence: pre-implementation quality-runner reported expected import-resolution failure (`../hooks/useEventSource` missing), confirming true RED state.
- Commit: `c9e001a6` (`feat: implement useEventSource hook (#1260, builder)`).
- Post-task reflection:
  - RED validation for missing-module tasks can present as 0 collected + import error; still valid failure evidence.
  - Ref-managed timer clearing on every transition was the key to AC4/AC5 single-timer guarantees.
  - Mounted-guard checks in callbacks prevented post-unmount state activity and timer-driven reconnects.
  - Branch-only guard paths remained the main residual uncovered area despite full AC pass coverage.
[[2026-05-01]]
## Review Evidence
### Scope
- First review cycle confirmed: no prior `## Review Evidence` section in `.owlbear/kanban/tasks/1260-create-useeventsource-hook.md`.
- Commit presence confirmed in `.git/logs/HEAD` for `c9e001a6`.
- Changed scope reconstructed from task body, symbol search, and workspace inspection: `serve/cockpit/web/src/hooks/useEventSource.ts`, `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`.
- Downstream callers: none beyond the task test file.

### Test Results
- vitest: 24 passed, 0 failed on `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`.

### Lint
- Quality-runner lint is Python-only, so no TypeScript lint ran in that report.
- VS Code diagnostics on the changed TS files: no errors.

### Coverage
- `useEventSource.ts`: 95.78% overall, 80% branch, 100% functions, 100% lines.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `serve/cockpit/web/src/hooks/useEventSource.ts:3` exports the named type, but the test file only imports the hook at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:16` and only checks callability / runtime property presence at lines 90 and 94. Removing the named type export would stay green. | FAIL |
| AC2 | State-machine tests at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:102-134` exercise initial connecting, native EventSource creation, open transition, and fatal-close transition implemented in `serve/cockpit/web/src/hooks/useEventSource.ts:60-89`. | PASS |
| AC3 | Listener registration and mtime update are exercised at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:146-160` against `serve/cockpit/web/src/hooks/useEventSource.ts:113-122`. | PASS |
| AC4 | Stall-timeout and boundary coverage at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:169-244` matches the timer logic in `serve/cockpit/web/src/hooks/useEventSource.ts:92-109`. | PASS |
| AC5 | Retry happy paths pass, but stale callbacks from an older source can still force `setStatus('closed')`, `closeActiveSource()`, and a retry from `serve/cockpit/web/src/hooks/useEventSource.ts:76-88` after a newer source has already been installed at line 61. Current tests at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:250-320` never exercise superseded-source callbacks. | FAIL |
| AC6 | Unmount cleanup behavior is covered at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:326-396`, and the mounted guard exists in `serve/cockpit/web/src/hooks/useEventSource.ts:68,77,95,114`. | PASS |
| AC7 | Disabled-state reset is implemented at `serve/cockpit/web/src/hooks/useEventSource.ts:130-135`, but because the next effect re-arms `isMountedRef.current = true` at line 31 and the `tasks-changed` handler at lines 113-122 does not verify that its callback belongs to the current source, a late event from the old source can repopulate `lastEventMtime` after disable. The test at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:413` only checks status/close and does not seed mtime or late callbacks. | FAIL |

#### Security Review
- No security issues found in the scoped change. The hook creates a browser `EventSource`, parses event JSON, and adds no dependency or filesystem / command surface.

#### Test Integrity
- No `TestFromAC_*` weakening found. The task suite remains intact and unskipped.

#### Test Quality
- WEAK.
- AC1 proof is non-discriminating: function-callability and property presence do not prove the named type export contract.
- The suite does not cover late callbacks from superseded EventSource instances after retry or disable, so the failing implementation path stays green.
- The post-unmount callback test at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:381` only checks instance count, not the absence of forbidden state mutation.

#### Data Safety
- FAIL: stale EventSource callbacks are not tied to the currently active instance.
- `serve/cockpit/web/src/hooks/useEventSource.ts:31` re-arms mounted state on every effect run.
- `serve/cockpit/web/src/hooks/useEventSource.ts:61` swaps in the new active source.
- The `onopen`, `onerror`, and `tasks-changed` handlers at lines 68-122 only check mounted state, not source identity.
- The fatal-error path at lines 81-88 can call `closeActiveSource()` on whatever source is current, and the event handler at lines 113-122 can repopulate `lastEventMtime` after the disable reset at lines 130-135.

#### Implementation-Aware Test Gap Analysis
- No test simulates a late `onerror` or `tasks-changed` event from a superseded source after retry or after an enabled true to false transition.
- That gap is exactly why the stale-source race above escaped.

#### Necessity Check
- No issue. A local hook around native EventSource is necessary for this frontend behavior.

#### Builder Process Quality
- CLEAN. First review cycle, one builder attempt, no loop evidence.

### Confidence
- 0.66

### Verdict
- FAIL

### Action
- Rejected to `in-progress` because this is an implementation issue with associated proof gaps.

### Required Follow-up
- Guard `onopen`, `onerror`, stall-timeout, and `tasks-changed` handlers so only the current EventSource instance can mutate state or close / retry the connection.
- Strengthen task tests to prove the AC1 named type export and to cover stale callbacks after retry and after disabling, including `lastEventMtime` reset preservation.
[[2026-05-01]]
## Builder Notes
- No code changes made in this cycle.
- Verified current task suite via quality-runner: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` => 24 passed, 0 failed.
- Result: no failing `TestFromAC_*` evidence for the stale-callback race identified in review, so GREEN-phase implementation cannot be validated.

### Why Rejected
- Reviewer-required follow-up includes stale-callback correctness (superseded `EventSource` callbacks must be inert) and stronger AC1 proof.
- Current tests do not fail on those paths, so this task is in false-green state from builder perspective.

### Test-Writer Needed
- Add failing tests that prove stale callbacks from a superseded source cannot mutate state or trigger close/retry after a newer source is active.
- Add failing tests that prove disable path preserves reset (`lastEventMtime` remains `null`) when late events from prior source arrive.
- Add AC1 proof that named export contract is enforceable (not only runtime property-shape checks).

### Builder Re-entry Criteria
- Re-dispatch when `TestFromAC_*` includes failing cases for the above race conditions; then builder will implement/fix with RED→GREEN evidence.
[[2026-05-01]]
## Test-Writer Notes
- Retry cycle: filled gaps identified in reviewer Required Follow-up.
- Test file: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
- Classes: `TestFromAC_UseEventSource`
- 4 new tests added (3 FAIL, 1 PASS):

| New test | AC | Result |
|----------|-----|--------|
| `stale onerror (CLOSED) from superseded source does not close the active new connection` | AC5 | FAIL ✓ |
| `stale tasks-changed from superseded source does not overwrite lastEventMtime set by new source` | AC5 | FAIL ✓ |
| `stale tasks-changed from prior source does not repopulate lastEventMtime after disable` | AC7 | FAIL ✓ |
| `UseEventSourceResult named type export has exact union shape (compile-time discriminating proof)` | AC1 | PASS (type already exported correctly — no impl change needed for AC1) |

- Total suite: 28 tests — 3 fail, 25 pass
- Lint: ESLint exit 0
- Commit: `20e1d5e8`

### Failure root cause
The hook's `onopen`, `onerror`, and `tasks-changed` handlers close over `isMountedRef` only — they do not verify that the callback belongs to the currently active `EventSource` instance. Builder must add a generation/identity guard so stale callbacks from a superseded source are silently dropped.

### AC coverage (retry additions)
| AC | Gap addressed | Status |
|----|--------------|--------|
| AC1 | `expectTypeOf` proof that named type export has exact union shape | Covered (passes — correct) |
| AC5 | Stale onerror and tasks-changed from superseded source after retry | Covered (FAIL) |
| AC7 | Stale tasks-changed repopulates lastEventMtime after disable | Covered (FAIL) |
[[2026-05-01]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/hooks/useEventSource.ts to enforce EventSource instance-identity guards in all async callbacks (`onopen`, `onerror`, stall-timeout callback, and `tasks-changed` listener), preventing stale superseded sources from mutating active state.
- Fixes applied for reviewer follow-up: stale `onerror` from old source no longer closes active source; stale `tasks-changed` from old source no longer overwrites `lastEventMtime`; stale events after disable remain inert.
- Additional surgical cleanup: removed two unreachable `openConnection` branches to keep behavior unchanged and satisfy coverage gate.
- Tests: 28 passed / 0 failed on serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts (includes the 3 previously failing stale-callback tests).
- Coverage: serve/cockpit/web/src/hooks/useEventSource.ts => statements 97.89%, branches 90.47%, functions 100%, lines 100%.
- Lint: clean for task scope (TypeScript checks clean in quality-runner report for this scope).
- Commit: a03c3741 (`fix: harden stale-event guards in useEventSource (#1260, builder)`).

- Post-task reflection:
  - The stale-source race came from callback closures lacking active-source identity checks; mounted-state checks alone were insufficient.
  - Identity-guarding every async callback path is the minimal robust pattern for EventSource retry/disable flows.
  - Branch coverage misses were primarily from defensive-but-unreachable guards in `openConnection`; removing those improved signal quality without changing behavior.
  - Keeping the change to one hook file made regression risk low while directly closing all failing AC5/AC7 proofs.