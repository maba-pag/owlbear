---
id: 1261
title: Integrate EventSource into useBoard with fallback orchestration
status: in-progress
priority: nice-to-have
created: 2026-05-01T09:34:27.630685+00:00
updated: 2026-05-02T07:32:37.145230+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
- 1259
- 1260
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Wire useEventSource into useBoard: SSE open pauses polling, tasks-changed triggers refetchTasks(), SSE failure/stall resumes polling. Update useConnectionHealth to accept transport-state override for health badge (green=SSE open, yellow=reconnecting, red=fallback). See .owlbear/research/1235-eventsource-client-implementation.md §3.4 and §3.6. Depends on the paused-option (#1259) and useEventSource (#1260) tasks.
[[2026-05-02]]
## Research

**Key findings:** All building blocks exist — `useEventSource` (#1260 done), `paused` option (#1259 done), backend `/api/events` endpoint live. Integration is ~30 LOC wiring in `useBoard.ts`:
- Derive `paused = (sseStatus === 'open')` for polling
- `useEffect` on `lastEventMtime` → `refetchTasks()`
- Compute `effectiveHealth` from SSE status (open→green, connecting→yellow, closed→fall through to polling health)

**Decision:** Option Y — health override stays in `useBoard` (local orchestration), NOT pushed into `useConnectionHealth` (kept as generic polling utility). Confidence: 0.85.

**Trade-offs:** See `.owlbear/research/1261-eventsource-board-integration.md` §3.3 table.

**No new follow-up tasks needed** — #1261 is self-contained (implementation = this task at backlog).
[[2026-05-02]]


## Acceptance Criteria

_Supersedes the original task description where they conflict (notably: useConnectionHealth is NOT modified)._

1. `useBoard` calls `useEventSource('/api/events')` and uses its return values for orchestration (td:1)
2. When `sseStatus === 'open'`, `usePollingFetch` receives `paused: true`, suppressing interval-driven polling (td:2)
3. When `lastEventMtime` changes (and SSE is open), `refetchTasks()` is called to fetch fresh task data (td:2)
4. When SSE is not open (`'connecting'` or `'closed'`), `paused` is `false` and polling resumes on its normal interval (td:2)
5. `useBoard` returns `health` (same field name, same `HealthState` type) computed as: `'green'` when sseStatus=`'open'`, `'yellow'` when sseStatus=`'connecting'`, falls through to polling-based `useConnectionHealth` value when sseStatus=`'closed'` (td:2)
6. `useConnectionHealth.ts` is NOT modified — health override is local to `useBoard` (Option Y per research) (td:0)
7. Existing `useBoard` tests pass with a global or per-suite `EventSource` stub/mock added to test infrastructure (td:1)
8. All existing Shell tests pass unchanged — `health` field name preserved in `UseBoardResult` (td:1)

### Builder Notes

- **Test infrastructure:** jsdom has no `EventSource`. Add a global stub in `vitest.setup.ts` that defaults to CLOSED (or mock per-test). Existing useBoard tests must not break.
- **Paused + pending edge case:** `usePollingFetch` suppresses pending-poll drain while paused (line ~89 in usePollingFetch.ts). If an SSE event arrives during an in-flight poll, the refetch queues but won't drain until the next event trigger or paused becomes false. Acceptable — next event catches up.
- **Stale health transient:** When SSE closes after a long open period, polling-based health from `useConnectionHealth` may briefly show stale state until the first successful poll calls `markHealthy()`. Brief transient, acceptable.
- **Reference:** `.owlbear/research/1261-eventsource-board-integration.md` §3.2–3.5
[[2026-05-02]]
## Architecture Review

**Verdict:** APPROVE — AC refined, architecture sound.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 1. useEventSource call | Clear, testable | Kept (td:1) |
| 2. paused=true when SSE open | Specific condition, verified `paused` option exists in usePollingFetch | Kept (td:2) |
| 3. lastEventMtime triggers refetch | Clear trigger + guard (SSE open) | Kept (td:2) — noted paused+pending edge case in builder notes |
| 4. Polling resumes on SSE not-open | Inverse of AC2, covers connecting + closed | Kept (td:2) |
| 5. health field with SSE-aware mapping | Rewrote from original — original said "update useConnectionHealth" which contradicted research Option Y. Now specifies local computation in useBoard, same field name | Refined (td:2) |
| 6. useConnectionHealth unchanged | Added — makes Option Y decision explicit and testable | Added (td:0) |
| 7. Existing useBoard tests pass | Added per challenger finding — jsdom has no EventSource, stub required | Added (td:1) |
| 8. Shell tests pass (field name) | Added per challenger finding — health field name must be preserved | Added (td:1) |

### Architecture Notes

- **Design:** Option Y (health override local to useBoard) is correct — useConnectionHealth is a polling-focused utility, SSE transport awareness doesn't belong there.
- **Module layering:** useBoard → useEventSource, usePollingFetch, useConnectionHealth. All peer hooks, no upward imports. ✓
- **Scope:** ~30 LOC in useBoard.ts + test infrastructure (EventSource mock). Single file change + test file.
- **Original AC contradiction fixed:** Task description said "Update useConnectionHealth" but research chose Option Y. Formalized AC supersedes.

### Dependency Analysis

- #1235 (SSE backend): archived/done — `/api/events` endpoint live
- #1259 (paused option): archived/done — `paused` option confirmed in usePollingFetch.ts
- #1260 (useEventSource): archived/done — hook exists at `serve/cockpit/web/src/hooks/useEventSource.ts`
- No missing dependencies

### Challenger Results

Challenger returned `block` at confidence 0.33. Evaluation:
1. **Test infrastructure** (critical) — Valid. Added AC7 requiring EventSource mock + builder note. Addressed.
2. **Paused+pending race** (critical) — Partially valid. Edge case when SSE event collides with in-flight poll — narrow window, next event catches up. Documented in builder notes. Not a design flaw.
3. **API contract** (moderate) — Valid. Added AC8 preserving `health` field name.
4. **Spec-coherence** (moderate) — Already identified. Fixed by AC rewrite superseding contradictory prose.
Override rationale: all concerns addressable through AC refinement, not architectural changes.
[[2026-05-02]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/useBoard_1261.test.ts
- Classes: TestFromAC_UseBoardSSEIntegration
- Tests per category: happy 6, edge 4, boundary 1, regression 1
- Total: 12 tests, all FAIL
- ESLint: clean

### AC Coverage

| AC | Tests | Category |
|----|-------|----------|
| AC1 (td:1) | creates an EventSource for /api/events on mount | happy |
| AC2 (td:2) | suppresses polling when SSE opens; no fires across multiple intervals; pauses mid-interval | happy, edge, boundary |
| AC3 (td:2) | triggers refetchTasks on tasks-changed event; triggers for each distinct event | happy, edge |
| AC4 (td:2) | polling resumes when SSE closes; polling resumes after SSE stall | happy, edge |
| AC5 (td:2) | health=green overrides degraded polling; health=yellow overrides healthy polling; health stays green during extended SSE-open | happy, happy, edge |
| AC6 (td:0) | skipped |  |
| AC7 (td:1) | returns all UseBoardResult fields with EventSource globally available | regression |
| AC8 (td:1) | folded into AC7 regression guard (health field name check) |  |

### Infrastructure Note
MockEventSource defined per-suite (same shape as useEventSource_1260.test.ts). No changes to vitest.setup.ts — builder should add a global closed-by-default stub there per AC7 builder note.
[[2026-05-02]]
## Builder Notes
- Implementation: integrated SSE orchestration in serve/cockpit/web/src/hooks/useBoard.ts and added a closed-by-default global EventSource jsdom stub in serve/cockpit/web/vitest.setup.ts.
- AC mapping:
  - AC1: useBoard now calls useEventSource('/api/events').
  - AC2/AC4: usePollingFetch now receives paused: sseStatus === 'open' (poll suppressed on open, resumes when not open).
  - AC3: useEffect now refetches tasks when lastEventMtime changes while SSE is open.
  - AC5: health remains the existing field name and type, computed locally as green(open) / yellow(connecting) / polling health(closed).
  - AC6: useConnectionHealth.ts unchanged.
  - AC7/AC8: test infra supports EventSource globally without changing useBoard result shape.
- Fixes applied during GREEN: removed unstable refetch loop by routing refetchTasks through a ref-backed effect trigger keyed only to lastEventMtime and sseStatus.
- Tests: 26 passed, 0 failed, 0 skipped (scoped run: useBoard_1261 + existing useBoard tests).
- Coverage: useBoard.ts 93.87% statements, 57.69% branches, 100% functions, 93.87% lines.
- Lint: ESLint clean (0 violations) on changed files.
- Commit: 2b26a212 (feat: integrate SSE orchestration in useBoard (#1261, builder)).

### Evidence Summary
- quality-runner scoped verification: vitest exit 0, eslint exit 0, no failures.
- Initial post-edit run had 4 failing tests; resolved by stabilizing SSE-triggered refetch effect dependencies.
[[2026-05-02]]
## Review Evidence
### Test Results
- vitest: 44 passed, 0 failed, 0 skipped
- Suites: useBoard_1261.test.ts (12), useBoard_967.test.ts (19), Shell_966.test.tsx (4), Shell_1227.test.tsx (9)

### Lint
- eslint: clean on serve/cockpit/web/src/hooks/useBoard.ts, serve/cockpit/web/vitest.setup.ts, and serve/cockpit/web/src/__tests__/useBoard_1261.test.ts

### Coverage
- serve/cockpit/web/src/hooks/useBoard.ts: 95.91% statements/lines, 69.23% branches, 100% functions

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC | Evidence | Mapped test(s) | Verdict |
|---|---|---|---|
| 1 | useBoard calls useEventSource('/api/events') at useBoard.ts:56 | useBoard_1261.test.ts:132 | COVERED |
| 2 | paused is driven by sseStatus === 'open' at useBoard.ts:61 | useBoard_1261.test.ts:143 | COVERED |
| 3 | SSE event refetch gate is at useBoard.ts:87 | useBoard_1261.test.ts:205 | COVERED |
| 4 | useBoard.ts:61 distinguishes open vs not-open; useBoard_1261.test.ts:254 proves resume after closed; useBoard_967.test.ts:87 proves polling with the global closed stub | Missing proof that polling still runs when SSE remains connecting across a full interval | MISSING |
| 5 | health mapping is local at useBoard.ts:127 and returned unchanged at useBoard.ts:136 | useBoard_1261.test.ts:313 proves open->green; useBoard_1261.test.ts:333 proves connecting->yellow; no test proves closed->polling-health fallback | MISSING |
| 6 | useConnectionHealth stays generic at useConnectionHealth.ts:11-24; override stays local to useBoard.ts:127-136 | static inspection | COVERED |
| 7 | Global EventSource stub added at vitest.setup.ts:50-78 | quality-runner green on useBoard_967.test.ts plus the new suite | COVERED |
| 8 | health field name remains health at useBoard.ts:136 | useBoard_967.test.ts:246, Shell_966.test.tsx:116, Shell_1227.test.tsx:147 and :219 | COVERED |

#### Security Review
- No issues found.

#### Test Integrity
- No weakening evidence found in the reviewed tests.
- Small confidence deduction: no commit diff was available to prove TestFromAC immutability against the original pre-builder snapshot.

#### Test Quality
- FAIL: proof quality is insufficient for td:2 on two natural branches.
- AC4 misses the connecting-not-open branch. Current pause tests open the EventSource before or during the boundary; a regression that pauses while connecting would survive.
- AC5 misses the closed fallback branch. Current health tests prove open->green and connecting->yellow, but not the required closed->polling-health behavior.

#### Data Safety
- No issues found.

#### Builder Process Quality
- CLEAN: one builder cycle, no loop pattern detected.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. useBoard calls useEventSource('/api/events') | useBoard.ts:56 | useBoard_1261.test.ts:132 | PASS |
| 2. paused=true when SSE is open | useBoard.ts:61 | useBoard_1261.test.ts:143 | PASS |
| 3. lastEventMtime change triggers refetchTasks() while open | useBoard.ts:87 | useBoard_1261.test.ts:205 | PASS |
| 4. polling resumes when SSE is not open (connecting or closed) | useBoard.ts:61 plus useBoard_1261.test.ts:254 and useBoard_967.test.ts:87 only prove closed-after-open / closed-default paths | missing connecting full-interval proof | FAIL |
| 5. health is green/open, yellow/connecting, polling fallback/closed | useBoard.ts:127-136 plus useBoard_1261.test.ts:313 and :333 prove open and connecting only | missing closed fallback proof | FAIL |
| 6. useConnectionHealth.ts is not modified for override logic | useConnectionHealth.ts:11-24 | static inspection | PASS |
| 7. existing useBoard tests pass with EventSource stub/mock | quality-runner: useBoard_967.test.ts passed | runtime evidence | PASS |
| 8. existing Shell tests pass unchanged with health field preserved | quality-runner: Shell_966.test.tsx and Shell_1227.test.tsx passed; useBoard.ts:136 still returns health | runtime evidence | PASS |

### Deductions
- -0.10: AC4 connecting branch unproved
- -0.07: AC5 closed fallback unproved
- -0.02: TestFromAC immutability confidence reduced without diff access
- Confidence: 0.81

### Verdict
- FAIL -> todo
- Rationale: scoped suites are green and the implementation reads correct, but the review gate cannot pass because the task-specific proof misses two td:2 branches.

### Required Follow-up
1. Add a test that keeps EventSource in connecting state for a full 3s interval and proves polling still fires.
2. Add a test that leaves SSE closed and proves useBoard.health falls through to the polling-based useConnectionHealth value with an exact color assertion.
3. Re-run the same scoped frontend suites after the test additions. No source-code change is required unless the strengthened tests expose a defect.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer-cited gaps. Both PASS against current implementation.
- Builder skip: test-only retry, all tests green — advancing directly to review.

### New tests added to `serve/cockpit/web/src/__tests__/useBoard_1261.test.ts`

| Gap (from Review Evidence) | New test | Result |
|---|---|---|
| AC4: connecting-branch unproved | `polling fires on schedule when SSE remains in connecting state for a full interval` | PASS |
| AC5: closed-fallback unproved | `health falls through to polling-based value (green) when SSE is closed` | PASS |

### Scoped run results (all 4 suites from review)
- useBoard_1261.test.ts: 14 tests (12 original + 2 new) — all pass
- useBoard_967.test.ts: 19 tests — all pass
- Shell_966.test.tsx: 4 tests — all pass
- Shell_1227.test.tsx: 9 tests — all pass
- Total: 46 passed, 0 failed

### ESLint: clean (no violations on test file)

### Commit: 88595659 (test: add connecting-branch and closed-fallback proof tests (#1261, test-writer))
[[2026-05-02]]
## Builder Notes
- Non-implementation pass-through on retry cycle: prior builder implementation already landed; this cycle only required verification after test-writer proof additions.
- Validation run via quality-runner (scoped): 46 passed, 0 failed, 0 skipped across `useBoard_1261`, `useBoard_967`, `Shell_966`, `Shell_1227`.
- Lint: clean on `src/hooks/useBoard.ts`, `vitest.setup.ts`, and `src/__tests__/useBoard_1261.test.ts`.
- Coverage (scoped): `src/hooks/useBoard.ts` statements/lines 95.91%, functions 100%, branches 69.23%.
- Files changed in this builder cycle: none.

### Evidence Summary
- Existing implementation behavior remains green after reviewer-requested proof expansion.
- No source changes were required in this pass.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner: 46 passed, 0 failed, 0 skipped
- Suites: useBoard_1261.test.ts (14), useBoard_967.test.ts (19), Shell_966.test.tsx (4), Shell_1227.test.tsx (9)

### Lint
- quality-runner: eslint clean on serve/cockpit/web/src/hooks/useBoard.ts, serve/cockpit/web/vitest.setup.ts, serve/cockpit/web/src/__tests__/useBoard_1261.test.ts, serve/cockpit/web/src/__tests__/useBoard_967.test.ts, serve/cockpit/web/src/__tests__/Shell_966.test.tsx, and serve/cockpit/web/src/__tests__/Shell_1227.test.tsx

### Coverage
- quality-runner: serve/cockpit/web/src/hooks/useBoard.ts -> 95.91% statements, 69.23% branches, 100% functions, 95.91% lines
- Uncovered lines reported: 101, 110 (informational only)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC | Evidence | Mapped test(s) | Verdict |
|---|---|---|---|
| 1 | useBoard.ts:56 calls useEventSource('/api/events') | useBoard_1261.test.ts:132 | COVERED |
| 2 | useBoard.ts:61 passes paused when sseStatus === 'open'; open-state pause is exercised across normal, repeated, and boundary intervals | useBoard_1261.test.ts:143-200 | COVERED |
| 3 | useBoard.ts:87-89 refetches on open + lastEventMtime change | useBoard_1261.test.ts:205-249 | COVERED |
| 4 | useBoard.ts:61 makes paused false when SSE is not open; closed-state resume is covered and the retry-added connecting-state interval proof is now discriminating | useBoard_1261.test.ts:254-308, 367-383 | COVERED |
| 5 | useBoard.ts:126-136 maps open->green, connecting->yellow, closed->health; open/connecting are proved, but the closed retry test only asserts green after a healthy poll | useBoard_1261.test.ts:313-344, 388-408 | LAX |
| 6 | useConnectionHealth.ts remains unchanged; override stays local in useBoard.ts:126-136 | static inspection | COVERED |
| 7 | vitest.setup.ts:50-78 provides a global closed-by-default EventSource stub and existing useBoard suites stay green | runtime + static inspection | COVERED |
| 8 | health field name is still returned at useBoard.ts:136 and existing durable suites stay green | useBoard_967.test.ts plus Shell_966.test.tsx and Shell_1227.test.tsx runtime evidence | COVERED |

#### Security Review
- No issues found. The reviewed change uses fixed same-origin endpoints only and adds in-memory test scaffolding only.

#### Test Integrity
- No weakening or removal evidence found in the reviewed tests.
- Small confidence deduction: git logs confirm commits 2b26a212 and 88595659 exist, but no diff-scoped proof was available to verify TestFromAC immutability against the original pre-builder snapshot.

#### Test Quality
- FAIL: AC5 still lacks discriminating proof for the named closed-state fallback semantics.
- Source behavior is `sseStatus === 'open' ? 'green' : sseStatus === 'connecting' ? 'yellow' : health` at useBoard.ts:126-127.
- The retry-added closed-state test at useBoard_1261.test.ts:388-408 first makes polling health green, then closes SSE, then asserts green.
- A mutation to `closed => 'green'` would still pass that test, so the test proves the symptom value, not the required fallback-to-polling-source behavior.

#### Data Safety
- No issues found.

#### Builder Process Quality
- CLEAN: no builder loop detected in the implementation cycle.
- Review loop-breaker applies separately: this task already contains one prior `## Review Evidence` section, and the same AC5 proof-quality concern persists on this second review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. useBoard calls useEventSource('/api/events') | useBoard.ts:56 | useBoard_1261.test.ts:132 | PASS |
| 2. paused=true when SSE is open | useBoard.ts:61 | useBoard_1261.test.ts:143-200 | PASS |
| 3. lastEventMtime change triggers refetchTasks() while open | useBoard.ts:87-89 | useBoard_1261.test.ts:205-249 | PASS |
| 4. polling resumes when SSE is not open (connecting or closed) | useBoard.ts:61 plus closed resume and connecting interval tests | useBoard_1261.test.ts:254-308, 367-383 | PASS |
| 5. health is green/open, yellow/connecting, polling fallback/closed | useBoard.ts:126-136; open and connecting proved, closed fallback source semantics not discriminating | useBoard_1261.test.ts:313-344, 388-408 | FAIL |
| 6. useConnectionHealth.ts is not modified for override logic | useConnectionHealth.ts:11-24 | static inspection | PASS |
| 7. existing useBoard tests pass with EventSource stub/mock | quality-runner green on useBoard_967.test.ts and task suite | runtime evidence | PASS |
| 8. existing Shell tests pass unchanged with health field preserved | quality-runner green on Shell_966.test.tsx and Shell_1227.test.tsx; useBoard.ts:136 still returns `health` | runtime evidence | PASS |

### Deductions
- -0.09: AC5 closed-state fallback proof is still lax
- -0.02: TestFromAC immutability confidence reduced without diff-scoped proof
- Confidence: 0.87

### Verdict
- FAIL -> backlog
- Rationale: the independent frontend run is green, but the task still fails review because AC5's closed-state branch is not proved in a way that would fail a plausible wrong implementation. This is the second review failure on the same task, so the loop-breaker route applies.

### Required Follow-up
1. Redesign the AC5 closed-state proof so it cannot pass if `useBoard` hardcodes green on close. The test should drive polling health to a non-green value while SSE is closed and assert exact equality with the underlying polling-based health.
2. Keep the new AC4 connecting-state test; that gap is now closed.
3. Re-run the same 4 frontend suites after strengthening AC5. Only send the task back to builder if the stronger proof exposes a real implementation defect.

### Reflection
- The retry fixed the prior AC4 objection cleanly.
- Green Vitest output was not enough here because the surviving AC5 test still permits a false-green mutation.
- Commit presence was verifiable from git logs, but lack of diff access kept test-immutability confidence slightly below maximum.
[[2026-05-02]]
## Architecture Review (retry)

**Verdict:** APPROVE — AC unchanged, test proof guidance added for retry cycle.

### Context

Task returned from review via loop-breaker. Two review cycles failed on the same issue: AC5 closed-state fallback test is non-discriminating. The implementation is correct (`useBoard.ts:126-127` falls through to polling `health` when `sseStatus === 'closed'`). All 46 tests green, lint clean, coverage at 95.91%.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 1–4 | Previously approved, review-confirmed | No change |
| 5 | AC text is already precise ("falls through to polling-based useConnectionHealth value") — the deficiency is test proof quality, not AC clarity | No change to AC |
| 6–8 | Previously approved, review-confirmed | No change |

### Reviewer Gap Analysis

The existing closed-fallback test (`useBoard_1261.test.ts:388`) drives polling health to `green`, closes SSE, then asserts `green`. A mutation `closed => 'green'` would pass. The test proves the symptom value, not the fallback mechanism.

### Test-Writer Guidance for Retry

Rewrite the AC5 closed-state test to be discriminating:
1. After initial render, advance fake timers by ≥15 000 ms so `computeHealth(elapsed)` in `useConnectionHealth` returns `'red'` (or ≥6 000 ms for `'yellow'`).
2. Trigger `updateHealth()` (via the polling interval callback) so the polling-based `health` state becomes non-green.
3. Close SSE via `simulateFatalClose()`.
4. Assert `result.current.health` equals the non-green polling health value (e.g., `'red'`).

This proves the fallback mechanism — if `useBoard` hardcoded any value on close, the non-green assertion would catch it.

### Architecture Notes

- No AC changes needed. AC5 already specifies "falls through to polling-based useConnectionHealth value" — unambiguous.
- No implementation changes expected. The code is correct; only the test proof needs strengthening.
- Dependencies #1235, #1259, #1260 remain archived/done.
[[2026-05-02]]
## Test-Writer Notes
- Retry: added 1 discriminating test for reviewer AC5 gap. Passes against current implementation → direct-to-review advance.
- Builder skip: test-only retry, all tests green.

### New test added to `serve/cockpit/web/src/__tests__/useBoard_1261.test.ts`

| Gap (from Review Evidence) | New test | Result |
|---|---|---|
| AC5: closed-fallback non-discriminating — prior test asserted 'green' when polling health was already green | `health falls through to degraded polling health (red) when SSE closes — discriminating AC5 proof` | PASS |

### Why this test is discriminating
- Uses `makeFailFetch()` so `markHealthy()` is never called → polling health degrades
- Advances fake timers 15 001 ms: 5 failed polls drive `computeHealth(elapsed)` to `'red'`
- Closes SSE via `simulateFatalClose()` → sseStatus = `'closed'`
- Asserts `result.current.health === 'red'` — a mutation `closed => 'green'` fails this assertion

### Scoped run results (all 4 suites from review)
- useBoard_1261.test.ts: 15 tests (14 prior + 1 new) — all pass
- useBoard_967.test.ts: 19 tests — all pass
- Shell_966.test.tsx: 4 tests — all pass
- Shell_1227.test.tsx: 9 tests — all pass
- Total: 47 passed, 0 failed

### ESLint: clean (no violations on test file)

### Commit: 9f2b7bdd (test: add discriminating AC5 closed-fallback proof (#1261, test-writer))