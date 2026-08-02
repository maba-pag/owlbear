---
id: 1276
title: Create EventSourceProvider context and useSSEEvent hook
status: archived
priority: medium
created: 2026-05-02T12:10:47.668244+00:00
updated: 2026-05-02T19:37:39.491534+00:00
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
[[2026-05-02]]

## Architecture Review (return from 2nd review FAIL)
### Assessment
AC is unchanged and correct. The sole remaining gap is test proof quality for one AC2 branch:

**Missing test:** stall error (readyState=CONNECTING) → advance 15s (stall timer fires, source closes) → advance 30s (retry timer fires) → assert a *second* MockEventSource instance is created. This is the `CONNECTING` reconnect path at `EventSourceProvider.tsx:111-123`.

Existing tests prove the two sub-paths independently (stall→close at test line 197, fatal→retry at test line 231) but never the composed stall→close→retry path. Removing the retry schedule inside the stall callback would leave the suite green — that's the discriminating test.

### Verdict
APPROVE — route to `todo`. Test-writer: add one AC2 test covering the full stall-reconnect path. Implementation is stable; no source changes expected.

[[2026-05-02]]
Re-approved after 2nd review FAIL. AC unchanged — sole gap is one missing AC2 test for the stall→close→reconnect composed path. Test-writer has clear guidance.
[[2026-05-02]]
## Test-Writer Notes
- Retry (3rd pass): added 1 test for sole remaining AC2 gap flagged by 2nd reviewer.
- Test file: `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx`
- New test: `stall-triggered reconnect: stall after 15s then new EventSource after 30s more`
- Covers the composed stall-error → 15s close → 30s retry → second EventSource path (EventSourceProvider.tsx:111–123). Removing the `retryTimerRef` schedule inside the stall callback would break this test while leaving all prior tests green — this is the discriminating proof.
- All tests PASS against current implementation → direct-to-review advance (Step 1b.1).
- Total: 33 tests, all PASS (32 EventSourceProvider + 1 App)
- ESLint: clean
- Commit: 3f053041
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1 (td:1) | 2 — export shape |
  | AC2 (td:2) | 14 — lifecycle + timer/stale guards + stall-reconnect composed path |
  | AC3 (td:2) | 9 — listeners, per-type mtime, malformed + recovery |
  | AC4 (td:2) | 6 — return shape, shared status, independent mtimes |
  | AC5 (td:1) | 1 — exact error message asserted |
  | AC6 (td:1) | 1 — url + Shell nesting + BrowserRouter context |
  | AC7 (td:0) | skipped |
[[2026-05-02]]
## Builder Notes
- Scope handled as verification-only builder pass for task #1276; no source edits were required.
- Verified implementation and wiring already present in:
  - serve/cockpit/web/src/hooks/EventSourceProvider.tsx
  - serve/cockpit/web/src/App.tsx
- Verified task tests:
  - serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx
  - serve/cockpit/web/src/__tests__/App_1276.test.tsx

### Test Results
- Vitest (scoped): 33 passed, 0 failed, 0 skipped.
- Files: 2 passed.

### Lint Status
- ESLint (scoped to touched source + test files): clean.
- Errors: 0, Warnings: 0.

### Coverage
- src/hooks/EventSourceProvider.tsx: 95.09% statements, 86.95% branches, 100% functions, 100% lines.
- src/App.tsx: 80% statements, 50% branches, 100% functions, 100% lines.
- Overall scoped run: 94.39% statements, 85.41% branches, 100% functions, 100% lines.

### Evidence Summary
- AC test suite is GREEN with strengthened proof for the stall->close->reconnect composed path.
- Lint is clean on all task-scoped files.
- Coverage satisfies the pipeline threshold for this task scope.
- No contract mismatch or implementation blocker identified.

### Fixes Applied
- None in this pass (verification and gate confirmation only).
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner (run from `serve/cockpit/web`): 33 passed, 0 failed, 0 skipped across `src/__tests__/EventSourceProvider_1276.test.tsx` and `src/__tests__/App_1276.test.tsx`

### Lint
- ESLint: clean on `src/hooks/EventSourceProvider.tsx`, `src/App.tsx`, `src/__tests__/EventSourceProvider_1276.test.tsx`, and `src/__tests__/App_1276.test.tsx`
- VS Code diagnostics: no errors in the same four files

### Coverage
- `src/hooks/EventSourceProvider.tsx`: 95.09% statements, 86.95% branches, 100% functions, 100% lines
- `src/App.tsx`: 80% statements, 50% branches, 100% functions, 100% lines

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `EventSourceProvider` exported from `hooks/EventSourceProvider.tsx`, accepts `url: string` + `children` | Source: `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:19-40`; provider export exercised in `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:95-101` | `TestFromAC_EventSourceProvider` export tests | PASS |
| AC2: single `EventSource(url)` on mount; stall 15s + retry 30s matching `useEventSource`; closes on unmount | Source: `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:86-126` clears a pending stall timer on `onopen`, schedules 15s stall timeout, and schedules 30s retry. Current provider tests prove timeout boundary and composed stall->close->reconnect in `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:198-227`, `:250-285`, and `:355-381`, but there is still no provider-local equivalent of the original hook’s recovery proof in `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:248-267` (`stall error` -> `open before 15s` -> advance past timeout -> remain open). If `clearStallTimer()` at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:90` were removed, the current task-local suite would stay green. | `TestFromAC_EventSourceProvider` lifecycle tests | FAIL |
| AC3: listeners for `tasks-changed`, `decisions-changed`, `activity-changed`; per-type `mtime`; malformed events ignored silently to keep stream alive | Source: `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:12-12,131-145`; tests cover listener registration, per-type mtimes, malformed JSON ignore, and valid follow-up recovery at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:390-517` | `TestFromAC_EventSourceProvider` AC3 tests | PASS |
| AC4: `useSSEEvent(eventType)` returns `{ mtime, status }` from context | Source: `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:171-183`; tests cover initial shape, shared status, independent mtimes, and unknown event type at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:525-605` | `TestFromAC_EventSourceProvider` AC4 tests | PASS |
| AC5: `useSSEEvent` throws descriptive error outside provider | Source: exact message in `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177`; exact message asserted in `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:611-619` | `TestFromAC_EventSourceProvider` AC5 test | PASS |
| AC6: `<EventSourceProvider url="/api/events">` wraps `<Shell />` in `App.tsx` inside `<BrowserRouter>` | Source: `serve/cockpit/web/src/App.tsx:1-13`; test proves provider render, exact URL, and direct Shell child in `serve/cockpit/web/src/__tests__/App_1276.test.tsx:81-98`. Router ancestry is behaviorally discriminating because `serve/cockpit/web/src/Shell.tsx:2,143-144` renders `Routes`/`Route`, so render would fail without router context. | `TestFromAC_AppWiring` | PASS |
| AC7: existing `useEventSource.ts` and `useEventSource_1260.test.ts` remain unchanged — additive only | Current snapshot of `serve/cockpit/web/src/hooks/useEventSource.ts` and `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` is consistent with additive-only work. Commit presence is confirmed in `.git/logs/HEAD:1530`, `.git/logs/HEAD:1539`, and `.git/logs/HEAD:1558`, but no commit diff was available for full immutability proof. | Snapshot + git log evidence | PASS with deduction |

### Pass 1 — Critical Findings
- Significant AC2 proof gap remains. The provider implementation includes a recovery guard at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:86-91`, but the provider-local suite never proves the branch where a transient stall is followed by `onopen` before the 15s timeout. That branch already existed in the original hook contract and is explicitly tested in `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:248-267`.
- This is a real false-green risk, not a hypothetical hardening request: removing `clearStallTimer()` at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:90` would still leave the current task-local provider suite green.

### Security Review
- No security issues found. SSE payload handling stays inside a local `try/catch` and only numeric `mtime` values are committed to state at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:131-145`.

### Test Integrity
- No weakening was visible in the current snapshot.
- Integrity confidence remains slightly reduced because no commit diff was available to prove `TestFromAC_*` immutability directly.

### Builder Process Quality
- CLEAN. This task already contains two prior `## Review Evidence` sections and the current retry is test-only; there is no sign of repeated implementation churn, but the loop-breaker still applies on a third review failure.

### Subagent Divergence
- code-reader also flagged AC6 as lax because the test does not structurally assert the `BrowserRouter` component identity.
- Direct review overruled that point: current source lines in `serve/cockpit/web/src/App.tsx:1-13` prove `BrowserRouter`, and the test remains discriminating for router ancestry because `Shell` renders `Routes`/`Route` at `serve/cockpit/web/src/Shell.tsx:2,143-144`.
- code-reader’s separate concern about literal timer values versus shared constants was treated as non-blocking. AC2 requires matching 15s/30s behavior; the current suite does exercise those timings.

### Deductions
- -0.10 missing AC2 recovery proof for `stall error` -> `onopen before timeout`
- -0.02 no commit diff available for high-confidence AC7 immutability verification

### Verdict
- FAIL -> backlog
- Confidence: 0.88

### Required Follow-up
1. Add a provider-local AC2 test mirroring `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:248-267`: trigger `simulateStallError()`, advance 5s, fire `simulateOpen()`, advance past 15s, then assert status remains `open` and no close/retry occurs.
2. Re-run scoped frontend review evidence after that test is added. Current evidence does not indicate any source-code change is needed.

### Action
- Routing to `backlog` under the reviewer loop-breaker rule because this is a third review failure on the same task and the remaining issue is still proof quality.

### Post-task Reflection
- Reused lifecycle code needs the original regression proofs, not just the copied implementation.
- Source reading was necessary to separate a real AC2 false-green from a non-blocking AC6 structural nit.
- Commit-log evidence helps, but without a diff the immutability check still carries a small confidence penalty.
[[2026-05-02]]
## Architecture Review (return from 3rd review FAIL)

### Assessment
AC is unchanged and correct. The sole remaining gap is a single missing AC2 test for the stall-recovery branch:

**Missing test:** stall error (readyState=CONNECTING) → advance 5s → fire `onopen` → advance past 15s → assert status remains `open` and no close/retry occurs. This proves `clearStallTimer()` at `EventSourceProvider.tsx:90` is exercised. The original hook has this exact test at `useEventSource_1260.test.ts:248-267`.

Existing provider tests prove stall→close→reconnect (the composed path added in 3rd test-writer pass) but never the recovery path where `onopen` cancels the stall timer before it fires.

| AC | Status | Notes |
|----|--------|-------|
| AC1 (td:1) | Proven | Export shape verified across 3 review cycles |
| AC2 (td:2) | 1 sub-branch unproven | `clearStallTimer()` in `onopen` handler — add one recovery test |
| AC3 (td:2) | Proven | Including malformed-event recovery proof |
| AC4 (td:2) | Proven | Return shape, shared status, independent mtimes |
| AC5 (td:1) | Proven | Exact error message asserted |
| AC6 (td:1) | Proven | Shell nesting + BrowserRouter behavioral proof |
| AC7 (td:0) | Proven with deduction | Additive-only, no commit diff available |

### Verdict
APPROVE — route to `todo`. Test-writer: add one AC2 test mirroring `useEventSource_1260.test.ts:248-267` for the provider: `simulateStallError()` → advance 5s → `simulateOpen()` → advance past 15s → assert status is `open` and no new EventSource created. Implementation is stable; no source changes expected.

### Challenger
Skipped — AC unchanged from prior challenger-validated approval. Gap is test-proof only.
[[2026-05-02]]
## Test-Writer Notes
- Retry (4th pass): added 1 test for sole remaining AC2 gap flagged by 3rd reviewer.
- Test file: `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx`
- New test: `stall timer is cleared when onopen fires within 15s — status remains "open"`
- Covers the stall-error → 5s → `simulateOpen()` → advance past 15s → assert status `open` + no close called + no new EventSource path (EventSourceProvider.tsx:86-91, `clearStallTimer()` in `onopen`). Removing `clearStallTimer()` from `onopen` would break this test while leaving all prior tests green — this is the sole discriminating proof.
- All tests PASS against current implementation → direct-to-review advance (Step 1b.1).
- Total: 34 tests, all PASS (33 EventSourceProvider + 1 App)
- ESLint: clean (exit 0)
- Commit: b72cf029
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1 (td:1) | 2 — export shape |
  | AC2 (td:2) | 15 — lifecycle + timer/stale guards + stall-reconnect composed + stall-recovery clearStallTimer |
  | AC3 (td:2) | 9 — listeners, per-type mtime, malformed + recovery |
  | AC4 (td:2) | 6 — return shape, shared status, independent mtimes |
  | AC5 (td:1) | 1 — exact error message asserted |
  | AC6 (td:1) | 1 — url + Shell nesting + BrowserRouter context |
  | AC7 (td:0) | skipped |
[[2026-05-02]]
## Builder Notes
- Implementation: verification-only builder pass; no source edits required in this cycle.
- Files verified: serve/cockpit/web/src/hooks/EventSourceProvider.tsx, serve/cockpit/web/src/App.tsx, serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx, serve/cockpit/web/src/__tests__/App_1276.test.tsx.
- Tests: 34 passed, 0 failed, 0 skipped (task-scoped).
- Coverage: src/hooks/EventSourceProvider.tsx 95.09%; src/App.tsx 80%.
- Lint: clean (ESLint violations: 0).
- Evidence summary: latest test-writer additions for AC2 stall-recovery and prior AC2 stall-reconnect paths are both present and green; scoped quality gate passes.
- Fixes applied: none.

### Post-task Reflection
- Retry-loop builder passes can be verification-only when reviewer feedback was test-proof and implementation is already stable.
- Scoped quality-runner evidence keeps this gate fast and reproducible.
- No-op implementation passes reduce churn and regression risk while preserving pipeline momentum.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run from `serve/cockpit/web`: 34 passed, 0 failed, 0 skipped across `src/__tests__/EventSourceProvider_1276.test.tsx` and `src/__tests__/App_1276.test.tsx`

### Lint
- ESLint: clean on `src/hooks/EventSourceProvider.tsx`, `src/App.tsx`, `src/__tests__/EventSourceProvider_1276.test.tsx`, and `src/__tests__/App_1276.test.tsx`
- VS Code diagnostics: no errors in the same four files

### Coverage
- `src/hooks/EventSourceProvider.tsx`: 95.09% statements, 86.95% branches, 100% functions, 100% lines
- `src/App.tsx`: 80% statements, 50% branches, 100% functions, 100% lines
- Diff-scoped note: AC6 only changes `src/App.tsx:9-11`, and those lines execute in `src/__tests__/App_1276.test.tsx:81-98`; the lower file-level percentages are residual untouched-branch debt, not a gate miss for this task

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `EventSourceProvider` exported from `hooks/EventSourceProvider.tsx`, accepts `url: string` + `children` | Source export at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:37`; provider usage with `url` and `children` exercised at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:96`, `:100`, and `:110` | `TestFromAC_EventSourceProvider` export + mount tests | PASS |
| AC2: single `EventSource(url)` on mount; stall 15s + retry 30s matching `useEventSource`; closes on unmount | Source lifecycle at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:81`, `:86`, and `:95`; task-local proofs cover mount/open/close/unmount at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:110`, `:145`, `:157`, `:177`; stall boundary at `:197`; fatal retry at `:233`; stall recovery / `clearStallTimer()` at `:356`; composed stall->close->reconnect at `:386` | `TestFromAC_EventSourceProvider` lifecycle tests | PASS |
| AC3: listeners for 3 event types; stores per-type `mtime`; malformed events ignored silently to keep stream alive | Source listener/parse/update path at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:131`, `:138-139`; tests cover listener registration, per-type updates, malformed JSON ignore, and valid follow-up recovery at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:421`, `:432`, `:444`, `:456`, `:506`, `:521`, and `:534` | `TestFromAC_EventSourceProvider` AC3 tests | PASS |
| AC4: `useSSEEvent(eventType)` returns `{ mtime: number | null, status: 'connecting' | 'open' | 'closed' }` from context | Source return shape at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:181-182`; tests cover initial shape, shared status, independent mtimes, and unknown event type at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:560`, `:590`, `:608`, and `:630` | `TestFromAC_EventSourceProvider` AC4 tests | PASS |
| AC5: `useSSEEvent` throws descriptive error when called outside `EventSourceProvider` | Source exact message at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:177`; exact message asserted at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:643` | `TestFromAC_EventSourceProvider` AC5 test | PASS |
| AC6: `<EventSourceProvider url="/api/events">` wraps `<Shell />` in `App.tsx` inside `<BrowserRouter>` | Source structure at `serve/cockpit/web/src/App.tsx:9-11`; wiring test at `serve/cockpit/web/src/__tests__/App_1276.test.tsx:81` proves provider render, exact URL, and direct `Shell` child. Router ancestry is behaviorally discriminating because `serve/cockpit/web/src/Shell.tsx:2`, `:143-144` render `Routes`/`Route`, so `<App />` would fail without router context | `TestFromAC_AppWiring` | PASS |
| AC7: existing `useEventSource.ts` and `useEventSource_1260.test.ts` remain unchanged — additive only | Current snapshots of `serve/cockpit/web/src/hooks/useEventSource.ts` and `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` remain consistent with additive-only work. Task commits are present in `.git/logs/HEAD:1530`, `:1539`, `:1558`, and `:1570` | Snapshot + git-log evidence | PASS with deduction |

### Pass 1 — Critical Findings
- No blocking findings in the current contract scope.
- quality-runner is green, lint/diagnostics are clean, and every AC line now has discriminating task-local proof.

### Security Review
- No security issues found. The change only opens the configured same-origin EventSource URL in `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:81`, and SSE payload handling stays inside a local `try/catch` with numeric `mtime` gating at `serve/cockpit/web/src/hooks/EventSourceProvider.tsx:138-139`.

### Test Integrity
- No weakening is visible in the current `TestFromAC_*` bodies.
- Immutability confidence remains slightly reduced because no commit diff was available for a direct before/after assertion-level comparison.

### Subagent Divergence
- code-reader surfaced two parity gaps versus the older `useEventSource` suite: stale named-event protection (`serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:379`) and post-unmount callback suppression (`serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:531` and `:549`).
- I am treating those as INFORMATIONAL, not blocking. This task is in a looped proof-only retry state, and the latest architecture refinement in `.owlbear/kanban/tasks/1276-create-eventsourceprovider-context-and-usesseevent-hook.md:422` explicitly narrowed the sole remaining blocker to the AC2 stall-recovery branch. That exact gap is now covered at `serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx:356`.

### Builder Process Quality
- CLEAN. The current cycle is a test-proof retry after prior review failures; no unnecessary implementation churn was introduced.

### Deductions
- -0.03 no commit diff available for high-confidence AC7 / TestFromAC immutability proof
- -0.01 non-blocking parity gaps remain between the provider suite and the older `useEventSource` suite, but they are outside the latest refined blocker set

### Verdict
- PASS -> docs
- Confidence: 0.94

### Action
- Advanced to `docs`

### Post-task Reflection
- On looped review tasks, the verdict has to anchor to the latest Architecture Review refinement in the task body, not older rejected proof sets.
- Adversarial code-reader findings are still useful on a PASS path, but they become informational when they do not contradict the refined AC.
- Lack of commit-diff access continues to cap confidence slightly on TestFromAC immutability checks.
[[2026-05-02]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are TS frontend hooks/App wiring; no IN-scope prose doc (README.md, serve/cockpit/README.md) references frontend hooks or SSE context provider layer |
| 2 | Module docstrings | No | N/A | No Python files changed |
| 3 | External attribution | Yes | Updated | `samouss/react-hooks-sse` cited as prior art in research doc §2; row added to `.owlbear/sources/overview.md` under new "Task #1276" section |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1276-eventsource-provider-hook.md` exists, linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**`; changed files match; footer updated from `60073954` → `8ce1a727` (current HEAD) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/hooks/EventSourceProvider.tsx | OUT | Triggers diagram describes-match (Item 5) only |
| serve/cockpit/web/src/App.tsx | OUT | Triggers diagram describes-match (Item 5) only |
| serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx | OUT | N/A |
| serve/cockpit/web/src/__tests__/App_1276.test.tsx | OUT | N/A |
| share/diagrams/cockpit.excalidraw | IN | Footer updated |
| .owlbear/sources/overview.md | IN | Attribution row added |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer: `Last verified: 2026-05-02 (8ce1a727)`
- `.owlbear/sources/overview.md` — new section for Task #1276 with `samouss/react-hooks-sse` attribution

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: EventSourceProvider exported, accepts url + children | Source: EventSourceProvider.tsx:37; reviewer line refs at test:96,100,110 | PASS |
| AC2: single EventSource on mount; stall 15s + retry 30s; closes on unmount | Source: EventSourceProvider.tsx:81-126; stall-recovery clearStallTimer test at test:356; composed stall→close→reconnect at test:386; 15 lifecycle tests total | PASS |
| AC3: listeners for 3 event types; per-type mtime; malformed events ignored + recovery | Source: EventSourceProvider.tsx:131-145; tests at test:421-534 including malformed recovery proof | PASS |
| AC4: useSSEEvent returns { mtime, status } | Source: EventSourceProvider.tsx:181-182; tests at test:560-630 | PASS |
| AC5: useSSEEvent throws descriptive error outside provider | Source: EventSourceProvider.tsx:177; exact message asserted at test:643 | PASS |
| AC6: EventSourceProvider wraps Shell in App.tsx inside BrowserRouter | Source: App.tsx:9-11; test at App_1276.test.tsx:81-98; BrowserRouter behaviorally discriminating via Shell's Routes/Route | PASS |
| AC7: useEventSource.ts and useEventSource_1260.test.ts unchanged | **Auditor-verified via `git diff ecb7a50c~1..HEAD`**: useEventSource.ts has zero diff; useEventSource_1260.test.ts change attributed to #1263 (commit 4350ba76), not #1276 | PASS |

### Test Results
- vitest (task-scoped): 34 passed, 0 failed
- vitest (full suite): 4 failures in unrelated tests (usePollingFetch_1227: 3, ActivityTab_1156: 1) — pre-existing, not caused by #1276
- pytest (full suite): 135 failures across unrelated modules (kanban engine, decisions, knowledge) — pre-existing background debt
- No cross-task regressions from #1276 changes

### Lint
- eslint: clean on all 4 task-scoped files
- ruff: 3 violations in unrelated files; 0 in task scope

### Commits Verified
- ecb7a50c feat: add SSE EventSource provider hook (#1276, builder)
- 092ecd1d test: add failing tests (#1276, test-writer)
- b49e04fe test: strengthen AC5/AC6 assertions (#1276, test-writer)
- 3f053041 test: add stall-triggered reconnect proof (#1276, test-writer)
- b72cf029 test: add stall-recovery clearStallTimer proof (#1276, test-writer)

### Architect Quality: 4/5
AC lines were specific with file paths, props, return types, and timer constants. AC2's sub-branches (stall-recovery clearStallTimer) were implicit in "matching useEventSource" rather than explicitly enumerated, leading to 4 review cycles before full proof. AC5's "descriptive error" was slightly vague. Overall adequate — gaps were filled by builder/reviewer without significant improvisation.

### Deduction Breakdown
- AC lines without evidence: 0 (all 7 verified) → 0
- Lint violations in scope: 0 → 0
- AC quality ≤ 3: no (score 4) → 0
- Missing reviewer evidence: no (detailed, 4th cycle, confidence 0.94) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: .98
(.02 conservative holdback for the 4-cycle review loop indicating AC2 could have been more explicit upstream)

### Action: archive