---
id: 1260
title: Create useEventSource hook
status: archived
priority: medium
created: 2026-05-01T09:34:24.718353+00:00
updated: 2026-05-02T01:54:00.567330+00:00
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
[[2026-05-01]]
## Review Evidence
### Scope
- Second review cycle confirmed: one prior `## Review Evidence` section already exists in `.owlbear/kanban/tasks/1260-create-useeventsource-hook.md`.
- Builder retry commit present in git logs: `a03c3741` (`fix: harden stale-event guards in useEventSource (#1260, builder)`).
- Reviewed live scope: `serve/cockpit/web/src/hooks/useEventSource.ts` and `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`.
- Downstream usages of `useEventSource`: task test file only.

### Test Results
- quality-runner: 28 passed, 0 failed on `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`.

### Lint
- quality-runner does not execute TypeScript lint; no TS/TSX diagnostics were reported on the changed source or test file.

### Coverage
- `serve/cockpit/web/src/hooks/useEventSource.ts`: 97.89% statements, 90.47% branches, 100% functions, 100% lines.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | Source signature/export is correct at `serve/cockpit/web/src/hooks/useEventSource.ts:15-17`, and the test imports the named type at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:17`, but the AC1 proof is still lax: it only checks `typeof useEventSource === 'function'` at `:91`, property presence at `:95-98`, and result-type assignability at `:104-108`. It does not prove exact exported hook type/signature. | FAIL |
| AC2 | State-machine behavior is directly exercised by the tests at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:115-142` against `serve/cockpit/web/src/hooks/useEventSource.ts:19-20,63,68-87`. | PASS |
| AC3 | Listener registration and `lastEventMtime` update are exercised at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:153-171` against `serve/cockpit/web/src/hooks/useEventSource.ts:112-123`. | PASS |
| AC4 | Stall detection and single-stall-timer behavior are exercised at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:181-248` against `serve/cockpit/web/src/hooks/useEventSource.ts:93-105`. | PASS |
| AC5 | The hook implements retry deduping and clear-on-open at `serve/cockpit/web/src/hooks/useEventSource.ts:73,86-87,104-105`, and stale `onerror` / stale `tasks-changed` retry races are covered at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:334-399`. But the AC5 suite only proves retry timing and stale `onerror` / event filtering (`:262`, `:278`, `:298`, `:312`, `:334`, `:368`); it never proves the explicit "only one retry timer is active" clause or stale `onopen` inertness after a source is superseded. | FAIL |
| AC6 | Cleanup code exists at `serve/cockpit/web/src/hooks/useEventSource.ts:146-150`, and unmount close/timer cleanup tests exist at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:410-460`. But the post-unmount callback proof at `:464-479` only asserts that no new instance is created; it does not directly prove the AC6 clause that no React state updates occur after unmount. | FAIL |
| AC7 | Disable/reset logic exists at `serve/cockpit/web/src/hooks/useEventSource.ts:129-139`, and the test suite proves disabled initial state, close on disable, re-enable, and stale event inertness at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:486-564`. But none of those tests disables while a stall timer or retry timer is actually pending, so the explicit `clear all timers` clause is still not discriminatingly proven. | FAIL |

#### Security Review
- No security issues found in the reviewed scope. The hook uses native browser `EventSource`, parses in-memory JSON, and adds no filesystem, shell, eval, or dependency surface.

#### Test Integrity
- No `TestFromAC_*` weakening found in the current task suite. The stale-source tests added in the retry cycle strengthen the prior failure area.
- Small confidence deduction: current-file inspection and task history show strengthening, but this review did not have a direct commit diff of the original test-writer artifact.

#### Test Quality
- WEAK.
- AC1 proof is still assignability/property-shape based rather than exact exported hook-type proof.
- AC5 names a one-retry-timer guarantee, but unlike AC4's explicit single-timer test at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:213`, AC5 has no duplicate-failure test that would fail if retry timers stacked.
- AC6's callback-after-unmount test at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:464-479` proves "no reconnect" but not "no state write".
- The source guards stale `onopen` at `serve/cockpit/web/src/hooks/useEventSource.ts:68-74`, but the suite has no stale-`onopen` regression.

#### Data Safety
- No implementation-side data-safety issue remains in the current hook. The source-identity guards are present on `onopen`, `onerror`, stall-timeout callback, and `tasks-changed` listener at `serve/cockpit/web/src/hooks/useEventSource.ts:68-74,77-109,112-123`.

#### Implementation-Aware Test Gap Analysis
- A stale-`onopen` regression on a superseded-but-still-mounted source is untested even though that guard is part of the implemented fix.
- Duplicate retry scheduling is untested; repeated failure before reopen could regress the explicit AC5 single-retry-timer contract without failing the current suite.
- Disable-time timer clearing is untested while a stall or retry timer is active.
- Post-unmount state-write suppression is only indirectly checked.

#### Necessity Check
- No issue. A local hook around native `EventSource` is necessary for this frontend behavior.

#### Builder Process Quality
- CLEAN. The current code appears to address the previously reported stale-source implementation defect; the remaining gate failure is proof quality.

### Confidence
- 0.83

### Verdict
- FAIL

### Action
- Rejected to `backlog` as a loop-breaker: this is the second review failure on the task, and the remaining issues are test-proof quality rather than a current source-code defect.

### Required Follow-up
- Add an exact exported hook-type proof for AC1, not only named-type/result-shape checks.
- Add an AC5 regression that would fail if retry timers stacked or if a stale `onopen` from a superseded source mutated state.
- Add a direct AC6 proof that callback activity after unmount cannot write `status` or `lastEventMtime`.
- Add an AC7 proof that disabling while stall/retry timers are pending clears them and prevents reconnect.

### Post-task Reflection
- EventSource state-machine fixes can be correct in code while still false-green unless each async callback path is directly exercised.
- ACs that say "single timer" need duplicate-trigger tests, not just boundary-time tests.
- Post-unmount safety needs a direct state-write suppression proof, not only a "no new instances" surrogate.
[[2026-05-01]]
## Architecture Review (loop-breaker re-entry)

**Context:** Reviewer rejected to `backlog` after 2nd review cycle (confidence 0.83). Implementation is correct — all issues are test-proof quality gaps. Architecture unchanged; challenger results from first cycle still valid.

### Evaluation (delta only)

No AC or architecture changes needed. The 7 AC lines are precise and verifiable. The reviewer's gaps are about test methodology, not AC vagueness:

| Reviewer Gap | AC Line | Issue |
|-------------|---------|-------|
| AC1 type proof | AC1 | Runtime shape check ≠ named export proof |
| AC5 timer stacking | AC5 | "only one retry timer" clause untested discriminatingly |
| AC5 stale onopen | AC5 | Guard exists in code but no regression test |
| AC6 state-write | AC6 | "no state updates after unmount" proven indirectly |
| AC7 timer clear | AC7 | "clears all timers" untested with active timers |

### Test-Writer Guidance (loop-breaker)

Add these discriminating proofs to the existing test suite. The implementation already passes — these strengthen proof quality:

1. **AC1 exact type proof:** Use `expectTypeOf<UseEventSourceResult>().toEqualTypeOf<{status: 'connecting' | 'open' | 'closed', lastEventMtime: number | null}>()` — compile-time exact shape, not assignability.
2. **AC5 single-retry-timer:** Trigger two consecutive fatal errors without an intervening `onopen`; advance 30s; assert only ONE `new EventSource` call (not two). This fails if retry timers stack.
3. **AC5 stale onopen:** After retry creates a new source, fire `onopen` on the OLD source; assert `status` reflects the new source's state, not the stale callback.
4. **AC6 direct state-write suppression:** After unmount, fire `simulateOpen()` and `simulateEvent('tasks-changed', ...)` on the captured source; assert no `console.error` from React (act warnings) AND assert the hook's last returned values are unchanged.
5. **AC7 timer-clear during active timers:** Enable → trigger stall (start 15s timer) → disable before 15s elapses → advance 15s → assert no state transition to `'closed'` (stall timer was cleared). Same pattern for retry timer.

### Verdict: APPROVE (loop-breaker)

Implementation is correct, AC is precise, architecture is sound. Test-writer adds 5 discriminating proofs per guidance above. Builder confirms GREEN (code already handles all cases). Reviewer verifies proof quality.
[[2026-05-01]]
Architecture Review (loop-breaker): APPROVED. Implementation correct (reviewer confidence 0.83), AC precise (7 lines unchanged), architecture sound (10/10 criteria from first cycle). Remaining issues are 5 test-proof quality gaps — test-writer guidance provided with exact discriminating test patterns. Challenger skip justified: design unchanged since first-cycle challenge.
[[2026-05-01]]
## Test-Writer Notes
- Retry (loop-breaker, 2nd retry): added 6 discriminating proofs for reviewer gaps. All 6 PASS against current impl.
- Builder skip: test-only retry, all tests green. Advancing directly to review.
- Test file: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
- Classes: `TestFromAC_UseEventSource`
- 6 new tests added, all PASS (implementation already correct per architect confirmation):

| New test | AC | Result |
|----------|-----|--------|
| `UseEventSourceResult full object shape matches exactly (no extra or missing properties)` | AC1 | PASS ✓ |
| `stale onopen from a superseded source does not mutate status after new source is active` | AC5 | PASS ✓ |
| `only one retry timer active — two consecutive fatal errors schedule exactly one retry` | AC5 | PASS ✓ |
| `callbacks firing after unmount do not write status or lastEventMtime (direct state suppression)` | AC6 | PASS ✓ |
| `disabling while stall timer is pending clears the timer — no retry EventSource created` | AC7 | PASS ✓ |
| `disabling while retry timer is pending clears the timer — no new EventSource after disable` | AC7 | PASS ✓ |

- Total suite: 34 tests — 34 pass, 0 fail
- Lint: ESLint exit 0
- Commit: `57bd7d77`

### AC coverage (loop-breaker additions)
| AC | Gap addressed | Status |
|----|--------------|--------|
| AC1 | Full object `toEqualTypeOf` proof (not per-property assignability) | Covered (passes — correct) |
| AC5 | Stale onopen from superseded source does not mutate status | Covered (passes — isCurrentSource guard works) |
| AC5 | Duplicate retry scheduling guard (single-timer contract) | Covered (passes — clearRetryTimer prevents stacking) |
| AC6 | Direct state-write suppression after unmount | Covered (passes — isMountedRef guard works) |
| AC7 | Stall timer cleared when disabled | Covered (passes — clearStallTimer in disabled path) |
| AC7 | Retry timer cleared when disabled | Covered (passes — clearRetryTimer in disabled path) |
[[2026-05-01]]
## Builder Notes
- Implementation: no source changes required in this cycle; existing `serve/cockpit/web/src/hooks/useEventSource.ts` already satisfies AC behavior.
- Tests: 34 passed / 0 failed on `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` (quality-runner scoped run).
- Coverage: `useEventSource` 97.89% statements, 90.47% branch, 100% functions, 100% lines.
- TypeScript diagnostics: no errors in both `serve/cockpit/web/src/hooks/useEventSource.ts` and `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`.
- Lint note: quality-runner does not execute TypeScript ESLint; frontend lint must be handled by frontend tooling, but diagnostics are clean.
- Approach: validated current implementation against task-scoped proof suite and moved forward with no additional code churn.

- Post-task reflection:
  - Loop-breaker test additions now provide discriminating proof for stale-callback and timer-clear paths.
  - Branch coverage remains above gate even with defensive guard branches intentionally untouched.
  - A no-edit builder cycle is appropriate when RED/GREEN evidence is already complete and clean.

[[2026-05-02]]
## Review Evidence
### Scope
- Third review cycle. Two prior Review Evidence sections exist in .owlbear/kanban/tasks/1260-create-useeventsource-hook.md (lines 160 and 290).
- Commit presence confirmed in git logs for a03c3741 (builder fix) and 57bd7d77 (test-writer proof-strengthening).
- Reviewed live scope: serve/cockpit/web/src/hooks/useEventSource.ts and serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts.
- Downstream usages of useEventSource remain task-local.

### Test Results
- quality-runner: 34 passed, 0 failed on serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts.

### Lint
- quality-runner ruff is not applicable to TypeScript; no Python lint scope here.
- VS Code diagnostics: no errors in the reviewed hook or task test file.

### Coverage
- Current quality-runner run could not emit TypeScript coverage.
- Prior reviewer evidence on the same unchanged hook recorded 97.89% statements, 90.47% branches, 100% functions, 100% lines for serve/cockpit/web/src/hooks/useEventSource.ts.
- Small confidence deduction applied for not independently re-running TS coverage in this cycle.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | Named exports exist in serve/cockpit/web/src/hooks/useEventSource.ts lines 3 and 15. Tests prove function export, exact UseEventSourceResult shape, and optional second arg at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 92, 114, and 579. | PASS |
| AC2 | Initial connecting state, EventSource(url), open transition, and fatal closed transition are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 124, 129, 135, and 146 against serve/cockpit/web/src/hooks/useEventSource.ts lines 15 and 63-88. | PASS |
| AC3 | tasks-changed listener registration and numeric mtime update are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 167 and 174 against serve/cockpit/web/src/hooks/useEventSource.ts lines 112-123. | PASS |
| AC4 | Stall timeout, boundary, single-stall-timer reset, and onopen-clear behavior are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 190, 222, and 246 against serve/cockpit/web/src/hooks/useEventSource.ts lines 78-105. | PASS |
| AC5 | Retry creation and reopen behavior are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 271, 287, and 320; stale-onerror, stale-onopen, and one-retry-timer guarantees are exercised at lines 343, 415, and 444; implementation clears retry state in serve/cockpit/web/src/hooks/useEventSource.ts line 73 and schedules retries at lines 87 and 105. | PASS |
| AC6 | Unmount close, timer clearing, and direct post-unmount state suppression are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 475, 508, and 547 against serve/cockpit/web/src/hooks/useEventSource.ts lines 69, 96, and 137-150. | PASS |
| AC7 | Disabled initial state, true->false shutdown, stale-event inertness after disable, and pending-timer clearing are exercised at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 577, 587, 624, and 689 against serve/cockpit/web/src/hooks/useEventSource.ts lines 129-150. | PASS |

#### Security Review
- No issues. The hook uses native browser EventSource, parses in-memory JSON defensively, and adds no filesystem, shell, eval, or dependency surface.

#### Test Integrity
- No weakening found in the current TestFromAC suite.
- Small confidence deduction: this session did not have a direct commit diff of the original test-writer artifact, so immutability is inferred from the current strict assertions, task history, and unchanged failure targets.

#### Test Quality
- STRONG.
- The suite now contains discriminating proofs for the previously missing stale-callback, direct post-unmount suppression, and active-timer clearing paths.
- Code-reader flagged AC5 clearRetryTimer-on-open as lax and noted malformed-payload and url-change gaps. I did not treat those as blocking: the clearRetryTimer call is present in source at serve/cockpit/web/src/hooks/useEventSource.ts line 73 and the observable AC5 contract is already covered by retry-open, stale-onopen, and single-retry tests; malformed payload and url-change behavior are not AC-traceable in this task.

#### Data Safety
- No issues. Source-identity and mounted guards are present at serve/cockpit/web/src/hooks/useEventSource.ts lines 69, 78, 96, and 113 and are exercised by stale-source and post-unmount tests at serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts lines 343, 415, 547, and 624.

#### Implementation-Aware Test Gap Analysis
- No AC-blocking gaps remain.
- Informational only: malformed JSON or non-number payload handling and url-change reconnection are untested defensive paths outside the declared AC.

#### Necessity Check
- No issue. A local EventSource hook is necessary for this frontend behavior.

#### Builder Process Quality
- CLEAN. Current cycle is a test-only retry with builder skip; no loop concern remains after loop-breaker re-entry.

### Deductions
- -0.03: quality-runner cannot supply TypeScript lint or coverage; used diagnostics plus scoped Vitest and prior unchanged-hook coverage evidence.
- -0.02: TestFromAC immutability not proven from a direct diff in this session.

### Confidence
- 0.93

### Verdict
- PASS

### Action
- Advancing to docs.

### Post-task Reflection
- Frontend reviews need an explicit note when quality-runner falls back to Vitest plus diagnostics because ruff cannot parse TypeScript.
- For hook state machines, stale-source regression tests are the proof that matters; they closed the actual prior false-green.
- Not every subagent-flagged gap is task-blocking; AC traceability is the deciding filter for gate failures.
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are `serve/cockpit/web/src/hooks/useEventSource.ts` and task test file — frontend TypeScript only. No IN-scope prose docs (README, setup guides, share/README) reference the `hooks/` directory or `useEventSource`. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | Yes | Verified | Sources already recorded in `.owlbear/sources/overview.md` under `## useEventSource Hook (Task #1260)` (lines 24-29): ReactUse and NepeinAV/react-sse-hooks. No new entries needed. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1260-useeventsource-hook.md` exists and is linked from the task body. Follow-up tasks noted as none (this was the implementation task). |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches changed files. Footer updated from `8142e272` → `a5073046` (current HEAD, 2026-05-02). Committed as `d5369ffa`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

- `serve/cockpit/web/src/hooks/useEventSource.ts` — TypeScript source, not IN-scope for direct doc edits
- `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` — test file, OUT-scope

### Files Updated

- `share/diagrams/cockpit.excalidraw` — footer hash updated to `a5073046` (commit `d5369ffa`)

### Child Tasks Created

None.

### Scratch Files Cleaned

No `.owlbear/scratch/1260-*` files found.
[[2026-05-02]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1 | Named exports at hooks/useEventSource.ts:3,15; exact type proof at test:579 | PASS |\n| AC2 | State transitions exercised at test:124-146 against hook:63-88 | PASS |\n| AC3 | tasks-changed listener + mtime update at test:167-174 against hook:112-123 | PASS |\n| AC4 | Stall timeout + single-timer + boundary at test:190-246 against hook:78-105 | PASS |\n| AC5 | Retry + stale-onerror/onopen + one-timer at test:271-444 against hook:73,87,105 | PASS |\n| AC6 | Unmount close + timer clear + direct state suppression at test:475-547 against hook:137-150 | PASS |\n| AC7 | Disable reset + stale inertness + timer clear at test:577-689 against hook:129-150 | PASS |\n\n### Test Results\n- Task suite (Vitest): 34 passed, 0 failed\n- Full Python suite: 115 failures, all pre-existing (unrelated packages: engine, mcp-kanban, models, decisions)\n- Full TS suite: 2 failures in FilterPanel_1250 and ActivityTab_1156 (unrelated)\n- No cross-task regressions from #1260\n\n### Lint\n- 4 ruff violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator)\n- Zero lint issues in task scope (TS diagnostics clean)\n\n### Commit Integrity\n- c9e001a6: feat: implement useEventSource hook (#1260, builder)\n- a03c3741: fix: harden stale-event guards in useEventSource (#1260, builder)\n- 20e1d5e8: test: add stale-source race tests (#1260, retry test-writer)\n- 57bd7d77: test: add discriminating proofs (#1260, test-writer)\n- d5369ffa: docs: update cockpit diagram footer (#1260, doc-writer)\n\n### Architect Quality: 4/5\nAC was precise and verifiable (7 lines with td annotations). Minor gap: stale-source identity guards were below AC-level specification, requiring 2 review cycles to get proof quality right. Not AC vagueness per se, but the \"only one retry timer\" clause could have been more explicit about superseded-source inertness.\n\n### Deduction Breakdown\n- Start: 1.00\n- AC lines without evidence: 0 (all 7 PASS with file:line citations)\n- Lint violations in scope: 0\n- AC quality 4/5: no deduction\n- Reviewer evidence: present and thorough (3 cycles, final PASS at 0.93)\n- Full-suite failures in task scope: 0\n- Quality-runner TS limitation (cannot independently verify TS coverage): -0.02\n\n### Confidence: 0.98\n### Action: archive