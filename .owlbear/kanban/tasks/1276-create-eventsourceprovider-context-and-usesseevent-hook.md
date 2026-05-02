---
id: 1276
title: Create EventSourceProvider context and useSSEEvent hook
status: backlog
priority: someday
created: 2026-05-02T12:10:47.668244+00:00
updated: 2026-05-02T15:47:32.501214+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Create a React context provider that manages a single EventSource connection to /api/events. Expose a useSSEEvent(eventType) hook that returns { mtime: number | null, status } for the specified event type. The provider should handle reconnection, stall detection, and lifecycle (reuse existing useEventSource logic). ~50 LOC. See .owlbear/research/1264-activity-tab-sse-wiring.md
[[2026-05-02]]
## Research

**Key findings:** EventSourceProvider context with static event-type listeners is the correct approach. Lift existing `useEventSource` connection/reconnect/stall logic (~156 LOC) into a context provider (~55 LOC). Expose `useSSEEvent(eventType)` → `{ mtime: number | null, status }`. Zero new deps.

**Implementation approach:** Single `EventSourceProvider.tsx` file creates one EventSource, registers listeners for 3 known event types (`tasks-changed`, `decisions-changed`, `activity-changed`), stores per-type mtimes in context state. Consumer hook reads context and selects by type.

**Prior art:** `react-hooks-sse` (110⭐) validates the pattern. Our version is simpler — fixed event types, no reducer/parser abstraction.

**Testing:** ~12 unit tests using existing MockEventSource pattern. Provider is additive — existing `useEventSource` tests unaffected until #1277 migrates useBoard.

**Challenge:** deferred to parent research (#1264) which validated Option A at 0.78 confidence. Revised confidence: 0.85.

**Classification:** T1 — autonomous. Refactoring existing proven patterns into context shape.

**Doc:** .owlbear/research/1276-eventsource-provider-hook.md
[[2026-05-02]]


## Acceptance Criteria
- [ ] AC1: `EventSourceProvider` exported from `hooks/EventSourceProvider.tsx`, accepts `url: string` + `children` (td:1)
- [ ] AC2: Provider opens single `EventSource(url)` on mount; stall (15s) + retry (30s) matching `useEventSource` constants `STALL_TIMEOUT_MS` / `RETRY_TIMEOUT_MS`; closes on unmount (td:2)
- [ ] AC3: Provider registers listeners for `tasks-changed`, `decisions-changed`, `activity-changed`; stores per-type `mtime` from `JSON.parse(event.data).mtime`; malformed events ignored silently to keep stream alive (td:2)
- [ ] AC4: `useSSEEvent(eventType)` returns `{ mtime: number | null, status: 'connecting' | 'open' | 'closed' }` from context (td:2)
- [ ] AC5: `useSSEEvent` throws descriptive error when called outside `EventSourceProvider` (td:1)
- [ ] AC6: `<EventSourceProvider url="/api/events">` wraps `<Shell />` in `App.tsx` inside `<BrowserRouter>` (td:1)
- [ ] AC7: Existing `useEventSource.ts` and `useEventSource_1260.test.ts` remain unchanged — additive only (td:0)

[[2026-05-02]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: shared SSE connection via context provider + consumer hook |
| Interface clarity | PASS | AC specifies exact props (`url`, `children`), return shape (`{ mtime, status }`), event types, timer constants, error behavior |
| Dependency correctness | PASS | No upstream deps. Parent #1236 at `todo`. Siblings #1277, #1278 depend on this task |
| Module layering | PASS | New file `hooks/EventSourceProvider.tsx` — no upward imports; provider wraps Shell in App.tsx |
| TDD compliance | PASS | Existing MockEventSource pattern in `useEventSource_1260.test.ts` (24 tests) provides foundation; Vitest + RTL available |
| KISS/YAGNI | PASS | Static 3-type list, ~55 LOC, zero new deps. Deletion test: removing provider forces 3 separate connections — justified |
| Premise challenge | PASS | No existing SSE context in hooks/; `useEventSource` is per-instance, not shared |
| Pattern consistency | PASS | Follows existing hooks pattern; connection logic adapted from proven `useEventSource.ts` (148 LOC) |
| Security surface | PASS | Same-origin `/api/events` endpoint; no new boundaries |
| Single domain | PASS | Frontend cockpit only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Provider mount | EventSource constructor throws | DOMException | Cleanup effect | Status shows `closed`, retry fires |
| Event listener | Malformed JSON in event.data | SyntaxError | AC3: silent catch | Stream stays alive |
| Missing provider | useSSEEvent outside EventSourceProvider | AC5: thrown Error | Consumer sees descriptive error | Dev-time crash with clear message |
| Interim dual connection | Provider + useBoard's existing useEventSource | N/A | Acceptable | 2 SSE connections until #1277 migrates |

### Challenger Results
- Verdict: block (0.36)
- **Critical concern: cross-task contract conflict with #1263** — #1263 (at `todo`) has approved AC extending `useEventSource` with generic `eventTypes` param. This directly conflicts with the provider approach.
- **Override reasoning:** Provider approach is architecturally superior — single shared connection via context vs. funneling all SSE through `useBoard`. **#1263's AC must be revised** to consume the provider (use `useSSEEvent('decisions-changed')`) instead of extending `useEventSource`. This revision is the orchestrator's responsibility.
- **Other concerns addressed:** interim duplicate connection (temporary, 1 task gap), static EVENT_TYPES (YAGNI-justified), malformed events (added to AC3), StrictMode replay (cleanup handles it).
- Post-refinement confidence: 0.82

### Cross-Task Conflict Notice
**⚠️ #1263 AC is stale.** Its approved AC extends `useEventSource` with `eventTypes` param — incompatible with this provider. #1263 must be revised to consume `useSSEEvent('decisions-changed')` from this provider instead. The orchestrator should send #1263 back to `backlog` for AC revision before its test-writer picks it up.

### Builder Guidance
- Copy connection/reconnect/stall logic from `useEventSource.ts` into provider effect — adapt for multi-type listener registration
- Use same `STALL_TIMEOUT_MS` (15s) and `RETRY_TIMEOUT_MS` (30s) constants
- `EVENT_TYPES = ['tasks-changed', 'decisions-changed', 'activity-changed'] as const`
- Context shape: `{ status, mtimes: Record<string, number | null> }`
- Reference files: `useEventSource.ts` (source logic), `useEventSource_1260.test.ts` (MockEventSource pattern), `App.tsx` (provider placement)
[[2026-05-02]]
## Test-Writer Notes
- Test files:
  - `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx` (AC1–AC5)
  - `serve/cockpit/web/src/__tests__/App_1276.test.tsx` (AC6)
- Classes: `TestFromAC_EventSourceProvider`, `TestFromAC_AppWiring`
- Tests per category:
  - AC1 (exports): happy 2
  - AC2 (lifecycle): happy 4, edge 3, boundary 3
  - AC3 (listeners + mtime): happy 4, edge 2, error 2
  - AC4 (useSSEEvent return): happy 3, edge 2, boundary 1
  - AC5 (error outside provider): error 1
  - AC6 (App wiring): happy 1
- Total: 28 tests, all FAIL
- RED evidence:
  - `EventSourceProvider_1276.test.tsx`: 27 tests — import fails (hooks/EventSourceProvider.tsx does not exist)
  - `App_1276.test.tsx`: 1 test — AssertionError: `capturedCalls.length` is 0 (EventSourceProvider not yet in App.tsx)
- ESLint: clean
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1 (td:1) | 2 smoke tests — export shape |
  | AC2 (td:2) | 10 tests — happy/edge/boundary for lifecycle, stall/retry timers |
  | AC3 (td:2) | 8 tests — all 3 listeners, per-type mtime, malformed events |
  | AC4 (td:2) | 6 tests — return shape, shared status, independent mtimes |
  | AC5 (td:1) | 1 test — throws outside provider |
  | AC6 (td:1) | 1 test — App wiring via vi.mock spy |
  | AC7 (td:0) | skipped |
[[2026-05-02]]
## Builder Notes
- Implementation: added `serve/cockpit/web/src/hooks/EventSourceProvider.tsx` and updated `serve/cockpit/web/src/App.tsx`.
- Approach: lifted the existing SSE connection lifecycle pattern (connect/open/error, 15s stall detection, 30s retry, cleanup) into a single shared context provider and exposed `useSSEEvent(eventType)` selector output `{ mtime, status }`.
- AC alignment:
  - AC1/AC4/AC5: exported `EventSourceProvider` + `useSSEEvent`, hook returns `{ mtime: number | null, status }`, throws descriptive error outside provider.
  - AC2: single `EventSource(url)` on mount, stall/retry timers (15_000/30_000), closes + clears timers on unmount.
  - AC3: listeners for `tasks-changed`, `decisions-changed`, `activity-changed`; numeric `mtime` capture per type; malformed JSON ignored.
  - AC6: wired `<EventSourceProvider url="/api/events">` around `<Shell />` in `App.tsx` inside `BrowserRouter`.
  - AC7: left `useEventSource.ts` and `useEventSource_1260.test.ts` unchanged.
- Verification (quality-runner, scoped): 28 passed, 0 failed, 0 skipped.
- Coverage: `EventSourceProvider.tsx` 92.15% statements (82.6% branches, 94.11% funcs, 98.78% lines).
- Lint: clean (no violations).
- Commit: `ecb7a50c` with only task files staged.

### Post-task Reflection
- Reusing the proven hook state machine reduced risk and kept behavior parity.
- Scoped quality-runner checks were sufficient for fast, reliable GREEN evidence.
- Keeping the diff to two files avoided unintended cross-task regressions.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner first attempt failed at the frontend environment layer (`ReferenceError: document is not defined`); retry with explicit frontend cwd succeeded.
- vitest: 28 passed, 0 failed, 0 skipped

### Lint
- eslint: clean

### Coverage
- `EventSourceProvider.tsx`: 92.15% statements, 82.6% branches, 94.11% functions, 98.78% lines
- `App.tsx`: 80% statements, 50% branches, 100% functions, 100% lines
- Diff-scoped note: the changed `App.tsx` lines execute under the task-local test, but AC6 proof is still insufficient.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `EventSourceProvider` exported from `hooks/EventSourceProvider.tsx`, accepts `url: string` + `children` | Source: `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:23-24,37`; tests exercise export/use at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:96-111` | PASS |
| AC2: single `EventSource(url)` on mount; stall 15s + retry 30s; close on unmount | Source: lifecycle at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:86-126`; task-local tests cover open/closed/unmount/retry at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:121,132,145,198,233` | FAIL — copied state-machine guard paths remain unproven |
| AC3: listeners for 3 event types; per-type `mtime`; malformed events ignored silently to keep stream alive | Source: listeners/parse/catch at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:131-145`; tests cover listeners and mtime updates at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:254,265,277,289,353` | FAIL — malformed-event test at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:338-350` proves only "no throw" + unchanged mtime, not continued stream usability |
| AC4: `useSSEEvent(eventType)` returns `{ mtime, status }` from context | Source: return shape at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:181-182`; tests at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:371,388,401,419,441` | PASS |
| AC5: `useSSEEvent` throws descriptive error outside provider | Source: exact message at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177`; test uses bare `toThrow()` at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:458` | FAIL — descriptive message not asserted |
| AC6: `<EventSourceProvider url="/api/events">` wraps `<Shell />` in `App.tsx` inside `<BrowserRouter>` | Source: actual structure is correct at `serve/cockpit/web/src/App.tsx:9-13`; test only checks provider call + url at `serve/cockpit/web/src/__tests__/App_1276.test.tsx:80-86` | FAIL — test does not prove BrowserRouter placement or Shell nesting |
| AC7: existing `useEventSource.ts` and `useEventSource_1260.test.ts` remain unchanged — additive only | Current snapshot is consistent with additive-only work in `serve/cockpit/web/src/hooks/useEventSource.ts` and `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`; builder commit `ecb7a50c` exists in `.git/logs/HEAD` | PASS with deduction — no commit diff available to prove immutability at high confidence |

### Pass 1 — Critical Findings
- Test quality is WEAK. AC5 and AC6 use lax assertions that would stay green under contract-breaking changes:
  - `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:458` only asserts `toThrow()`, not the required descriptive message from `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177`.
  - `serve/cockpit/web/src/__tests__/App_1276.test.tsx:80-86` only asserts provider invocation with `/api/events`; it does not prove `<Shell />` is wrapped by `EventSourceProvider` inside `BrowserRouter`, even though the code currently does so at `serve/cockpit/web/src/App.tsx:9-13`.
- Implementation-aware test gaps remain in copied state-machine behavior. The provider contains stale-source and timer-guard branches at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:87,96,114,132` that are not covered by task-local tests. The older hook suite already had equivalent regressions at `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:222,377,415,444`, but no provider equivalents were added.
- AC3's "keep stream alive" clause is under-proven. The malformed-event test at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:338-350` never sends a valid follow-up event after malformed JSON, so it cannot catch a listener that silently dies after the parse failure.

### Security Review
- No security issues found in scope. Fixed relative SSE URL in `serve/cockpit/web/src/App.tsx:10`; incoming payload narrowed to numeric `mtime` before state mutation in `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:138-145`.

### Builder Process Quality
- CLEAN: one `## Builder Notes` section, no prior `## Review Evidence` section.

### Deductions
- -0.06 lax AC5/AC6 assertions
- -0.08 missing provider equivalents for copied timer/race regressions
- -0.03 malformed-event recovery under-proven
- -0.02 no commit diff available for AC7 immutability

### Verdict
- FAIL -> todo
- Confidence: 0.81

### Required Follow-up
1. Strengthen AC5 to assert the exact descriptive error message from `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177`.
2. Strengthen AC6 to prove `<Shell />` is nested inside `EventSourceProvider` inside `BrowserRouter`, not just that the provider was invoked with the right URL.
3. Add provider-local equivalents for the copied `useEventSource` race/timer protections: second stall error resets the timer, stale source events/onopen/onerror are ignored, and only one retry timer is active.
4. Add an AC3 recovery proof: after malformed JSON, a subsequent valid event for the same type must still update `mtime`.

### Action
- Routing to `todo` because the implementation appears correct, but the task-local tests do not yet prove the contract strongly enough for review sign-off.
[[2026-05-02]]
## Test-Writer Notes
- Retry: strengthened 4 test gaps flagged by reviewer. All new tests PASS against current implementation → direct-to-review advance (Step 1b.1).
- Test files:
  - `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx` (AC1–AC5)
  - `serve/cockpit/web/src/__tests__/App_1276.test.tsx` (AC6)
- Changes made:
  1. **AC5 strengthened**: `toThrow()` → `toThrow('useSSEEvent must be used within an EventSourceProvider')` — exact message now asserted
  2. **AC6 strengthened**: captures `children` prop in mock; asserts `isValidElement(children)` + `children.type.name === 'Shell'`; comment explains BrowserRouter proof via successful render
  3. **AC3 recovery added**: after malformed JSON, a valid event still updates `mtime` (proves listener stays alive after parse failure)
  4. **AC2 race/timer guards added** (3 tests): second stall resets timer, stale source `onopen` ignored, stale source `onerror` ignored
- Total: 32 tests, all PASS (implementation already correct — test-only retry)
- ESLint: clean
- Commit: b49e04fe
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1 (td:1) | 2 — export shape |
  | AC2 (td:2) | 13 — lifecycle + timer/stale guards |
  | AC3 (td:2) | 9 — listeners, per-type mtime, malformed + recovery |
  | AC4 (td:2) | 6 — return shape, shared status, independent mtimes |
  | AC5 (td:1) | 1 — exact error message asserted |
  | AC6 (td:1) | 1 — url + Shell nesting + BrowserRouter context |
  | AC7 (td:0) | skipped |
[[2026-05-02]]
## Builder Notes
- Implementation: no new source changes in this builder pass; existing implementation in `serve/cockpit/web/src/hooks/EventSourceProvider.tsx` and wiring in `serve/cockpit/web/src/App.tsx` already satisfied AC.
- RED/Interface check: task-scoped `TestFromAC_*` tests are currently GREEN because this task is a post-review test-strengthening retry; no contract mismatch found.
- Tests: 32 passed, 0 failed, 0 skipped (scoped vitest run on `EventSourceProvider_1276.test.tsx` and `App_1276.test.tsx`).
- Coverage: `EventSourceProvider.tsx` 94.11% statements / 86.95% branches / 94.11% functions / 98.78% lines; `App.tsx` 80% statements / 50% branches / 100% functions / 100% lines.
- Lint: clean (ESLint exit 0) for touched source and task tests.
- Approach: verified strengthened test suite and quality evidence; no additional implementation intervention required.

### Post-task Reflection
- Re-opened builder passes can be no-op when reviewer feedback was test-only and implementation is already stable.
- Scoped quality-runner evidence is sufficient to re-advance quickly without unnecessary code churn.
- Keeping this pass verification-only preserved surgical discipline and avoided accidental regressions.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner: 32 passed, 0 failed, 0 skipped

### Lint
- eslint: clean

### Coverage
- src/hooks/EventSourceProvider.tsx: 94.11% statements, 86.95% branches, 94.11% functions, 98.78% lines
- src/App.tsx: 80% statements, 50% branches, 100% functions, 100% lines

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: EventSourceProvider exported from hooks/EventSourceProvider.tsx, accepts url + children | Source: serve/cockpit/web/src/hooks/EventSourceProvider.tsx; task tests prove named exports and provider usage at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:95-113 | PASS |
| AC2: Provider opens single EventSource(url) on mount; stall 15s + retry 30s; closes on unmount | Source stall branch schedules retry in serve/cockpit/web/src/hooks/EventSourceProvider.tsx:111-123. Tests prove mount/open/close/unmount at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:107-245 and prove stall-timer reset/stale-source guards at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:250-346, but no mounted-path test proves a new EventSource is created after the stall path closes at 15s and waits 30s. The unmount case at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:156-176 intentionally proves the opposite path. | FAIL |
| AC3: registers listeners for 3 event types; stores per-type mtime; malformed events ignored silently to keep stream alive | Source listener/parse path: serve/cockpit/web/src/hooks/EventSourceProvider.tsx:131-145. Tests cover all 3 listeners, per-type mtimes, malformed JSON no-throw, and recovery after malformed JSON at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:352-488, including the recovery proof at :468-488. | PASS |
| AC4: useSSEEvent(eventType) returns { mtime, status } from context | Source return path: serve/cockpit/web/src/hooks/EventSourceProvider.tsx:171-183. Tests cover initial shape, shared status, independent mtimes, and update behavior at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:491-570. | PASS |
| AC5: useSSEEvent throws descriptive error outside EventSourceProvider | Source exact message: serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177. Test asserts the exact message at serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:576-583. | PASS |
| AC6: <EventSourceProvider url="/api/events"> wraps <Shell /> in App.tsx inside <BrowserRouter> | Source structure is correct at serve/cockpit/web/src/App.tsx:9-11. Test proves provider render, exact url, and direct Shell child at serve/cockpit/web/src/__tests__/App_1276.test.tsx:82-93. BrowserRouter ancestry is also behaviorally proven because the real Shell renders Routes/Route at serve/cockpit/web/src/Shell.tsx:2 and :143-144, so render(<App />) would throw without router context. | PASS |
| AC7: existing useEventSource.ts and useEventSource_1260.test.ts remain unchanged — additive only | Current snapshot is consistent with additive-only work. Builder and retry commits exist in .git/logs/HEAD at lines 1530 and 1539, but no commit diff was available to prove immutability at full confidence. | PASS with deduction |

### Pass 1 — Critical Findings
- AC2 remains under-proven. The suite does not execute the full mounted stall -> close after 15s -> reconnect after 30s branch implemented at serve/cockpit/web/src/hooks/EventSourceProvider.tsx:111-123.
- This is a real AC miss, not a hypothetical hardening request: removing the stall-branch retry schedule would leave the current task-local suite green.

### Security Review
- No security issues found in scope. SSE payloads are parsed under try/catch and only numeric mtimes are committed to state in serve/cockpit/web/src/hooks/EventSourceProvider.tsx:131-145.

### Test Integrity
- No weakening was found in the current snapshot.
- Integrity confidence remains slightly reduced because no commit diff was available for direct TestFromAC immutability proof.

### Builder Process Quality
- CLEAN: one prior review rejection, then a test-strengthening retry. No evidence of repeated identical implementation loops.

### Deductions
- -0.10 missing AC2 proof for the stall-triggered reconnect branch
- -0.02 no commit diff available for high-confidence AC7 immutability verification

### Subagent Divergence
- code-reader flagged AC6 as lax because BrowserRouter ancestry is not asserted structurally.
- Direct review overruled that point: render success is discriminating here because Shell unconditionally renders Routes/Route, so removing BrowserRouter would fail the test.

### Verdict
- FAIL -> backlog
- Confidence: 0.88

### Required Follow-up
1. Add a mounted-path AC2 test that simulates a stall error, advances 15s to the close transition, then advances 30s more and asserts a second EventSource is created from the stall branch.
2. Re-run scoped frontend review evidence after that proof is added; source changes do not appear necessary from current evidence.

### Action
- Routing to backlog as the second review FAIL on this task. The remaining issue is AC proof quality, so this is now a loop-breaker/architecture-test-quality return rather than another narrow todo retry.

### Post-task Reflection
- Green scoped Vitest plus clean lint were not enough here; the missing branch was only visible by reading the exact retry schedule in the provider.
- Frontend wiring reviews need behavioral context from real children; comment-only reasoning is weak, but real router-dependent rendering can still be valid proof.
- Without commit diff access, immutability checks remain slightly lower-confidence and should be called out explicitly.