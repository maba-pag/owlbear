---
id: 967
title: 'GREEN: useBoard polling with mtime-skip and error states'
status: archived
priority: medium
created: 2026-04-18T15:59:11.242411+00:00
updated: 2026-04-18T21:33:51.666413+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent:
depends_on:
- 960
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Implement polled `useBoard` hook using plain `setInterval` + `useRef` pattern. No new dependencies.

## Context

Research #960 recommends plain polling over TanStack Query (KISS/YAGNI). The hook needs: 3s polling of `/api/tasks`, mtime-aware skip, one-shot `/api/board` fetch, error/stale states for traffic-light, and AbortController for cleanup.

## Acceptance Criteria

- [ ] `useBoard` polls `/api/tasks` every 3s using `setInterval`
- [ ] `useRef` stores `lastMtime`; skips `setTasks` when mtime unchanged
- [ ] `/api/board` fetched once on mount (quasi-static config)
- [ ] Hook exposes: `{ board, tasks, loading, error, isStale, isFetching }`
- [ ] `AbortController` cancels in-flight request on unmount and before new poll tick
- [ ] Zero new runtime dependencies
- [ ] All RED-phase tests pass
- [ ] Existing 26 KanbanBoard tests still pass

## Files

- `serve/cockpit/web/src/hooks/useBoard.ts` (extract from KanbanBoard.tsx)
- `serve/cockpit/web/src/KanbanBoard.tsx` (import from hooks/)

See `.owlbear/research/960-tanstack-query-vs-plain-polling.md`
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/967-useboard-polling-green.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: skip-when-in-flight polling with refetchTasks preserved (confidence: 0.85)
- Follow-up tasks created: none (implementation fully scoped on #967)
- Decision requests: none

Key findings:

1. Keep `refetchTasks` in return signature — called at L243 after POST move
2. Use skip-when-in-flight (not abort-per-tick) — simpler, matches usePolling.ts pattern
3. Define `isStale` = last poll errored (data may be outdated)
4. Mtime JS precision safe in practice (~256ns resolution vs ms-scale file ops)
5. Two polling loops (usePolling for health, useBoard for data) intentional per #966 research

Challenge: reconsider → confidence in original 0.50. Accepted 3 of 5 challenger concerns (refetchTasks removal, isStale ambiguity, abort-per-tick). Revised to skip-when-in-flight with refetchTasks preserved.
[[2026-04-18]]

## Architecture Review

### AC Refinements Applied

**AC #4 (critical fix):** Added `refetchTasks` to return signature — omission would break existing move flow at KanbanBoard.tsx L243 and fail AC #8.

Before: `Hook exposes: { board, tasks, loading, error, isStale, isFetching }`
After: `Hook exposes: { board, tasks, loading, error, isStale, isFetching, refetchTasks }`

**AC #5 (critical fix):** Rewritten to match research conclusion (skip-when-in-flight, not abort-per-tick).

Before: `AbortController cancels in-flight request on unmount and before new poll tick`
After: `AbortController cancels in-flight request on unmount; poll ticks skip (no-op) when a fetch is already in-flight`

**AC #8 (clarification):** Added note that existing tests may require `vi.useFakeTimers()` to prevent interval leakage.

After: `Existing 26 KanbanBoard tests still pass (may require vi.useFakeTimers to control polling interval)`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extract hook to hooks/useBoard.ts, update import in KanbanBoard.tsx |
| Interface clarity | PASS (after refinement) | Return signature now includes all 7 fields; skip-vs-abort clarified |
| Dependency correctness | PASS | Depends on #960 (research, completed/archived). No missing deps |
| Module layering | PASS | Hook in hooks/ consumed by component — correct direction |
| TDD compliance | PASS | GREEN phase, RED tests written upstream |
| KISS/YAGNI | PASS | Plain setInterval, no TanStack Query, zero new deps |
| Premise challenge | PASS | Polling needed for live board updates; no existing solution |
| Pattern consistency | PASS | Follows usePolling.ts skip pattern (skipRef + setInterval) |
| Security surface | PASS | No new user input or external APIs; same /api/tasks and /api/board endpoints |
| Single domain | PASS | Frontend/cockpit domain only |

### Challenge Results

- Challenger: block (confidence 0.35)
- Identified: AC #5 contradicts research (abort-per-tick vs skip-when-in-flight), AC #4 missing refetchTasks, timer interference with existing tests
- Architect response: accepted C1 (rewrote AC #5), accepted C2 (added refetchTasks to AC #4), partially accepted C3 (added timer note to AC #8), noted C4 (minor, no action)
- Post-refinement: all critical defects resolved

### Verdict: REFINE then APPROVE

### Action Taken: Fixed 3 AC lines (critical contradictions and omissions), advancing to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: serve/cockpit/web/src/**tests**/useBoard_967.test.ts
- Classes: TestFromAC_useBoardHook967
- Tests per category: happy 9, edge 3, error 3, boundary 5
- Total: 20 tests, all FAIL (ImportError: `../hooks/useBoard` module does not exist)
- ruff: N/A (TypeScript — no syntax errors, vitest parses file correctly before import resolution fails)
- Commit: eb833bf5

### AC Coverage

| AC | Tests |
|----|-------|
| polls /api/tasks every 3s via setInterval | polls-at-3s, no-tick-before-3s, polls-3-times-in-9s |
| useRef stores lastMtime; skips setTasks when mtime unchanged | same-ref-on-same-mtime, new-ref-on-mtime-change, content-updated-after-change |
| /api/board fetched once on mount | board-fetched-once, board-data-exposed |
| Hook exposes { board, tasks, loading, error, isStale, isFetching, refetchTasks } | all-fields-present, loading-false-after-mount, refetchTasks-triggers-fetch |
| skip-when-in-flight (not abort-per-tick) | tick-skipped-when-in-flight, isFetching-true-while-in-flight, isFetching-false-after-resolve |
| AbortController.abort on unmount | abort-called-on-unmount, no-state-update-after-unmount |
| error/isStale states | error-set-on-poll-reject, isStale-true-on-failure, error-and-isStale-cleared-on-recovery |

Key decision: import from `'../hooks/useBoard'` (not `'../KanbanBoard'`) — forces tests RED until builder creates hooks/useBoard.ts per AC files spec.
[[2026-04-18]]

## Builder Notes

**Files changed:** `serve/cockpit/web/src/hooks/useBoard.ts` (1 file — hook already existed from prior work, committed here)

**Test results:** 19/19 `TestFromAC_useBoardHook967` passed, 66/66 KanbanBoard tests passed (4 files)

**Lint/build:** Vite build ✓. `tsc --noEmit` shows pre-existing type errors in test files (`resolvePoll!: () => void` typing in TestFromAC_classes) — not caused by this task, not fixable without touching TestFromAC_ classes.

**Coverage:** N/A — TypeScript/Vitest suite (no Python coverage tooling).

**Fix applied:** The only failing test was `'polls at least 3 times after 9 seconds'` (expected ≥3, got 2). Root cause: `vi.advanceTimersByTime(9000)` fires all 3 interval ticks synchronously before any promise resolves, so `inFlightRef=true` from tick 1 blocked ticks 2 and 3.

Added `pendingPoll` flag to the effect closure: when a tick arrives while in-flight, sets `pendingPoll=true` instead of skipping silently. After the current fetch completes (in `finally`), if `pendingPoll=true && !cancelled`, fires one additional poll. This satisfies both AC1 (3+ polls in 9s with instant mocks) and AC5 (no new fetch call when deferred poll is in-flight — the tick sets pendingPoll but doesn't call fetch).

**Commit:** baf4681a
[[2026-04-18]]

## Review Evidence

### Test Results

- vitest: 74 passed, 0 failed (all test files; 19 TestFromAC_useBoardHook967 + 55 KanbanBoard suite)
- No test failures across any file

### Lint

- TypeScript (tsc): 3 TS2322 errors in `useBoard_967.test.ts` lines 276, 312, 369 — `resolvePoll!: () => void` assignment type mismatch in TestFromAC_deferred-promise pattern. Pre-existing from test-writer commit `eb833bf5`, confirmed by builder. Not caused by this task; cannot be fixed without modifying TestFromAC_ classes (prohibited). Tests still pass under Vitest (esbuild transpilation, not tsc).
- No lint issues in `hooks/useBoard.ts`

### Coverage

- N/A — TypeScript/Vitest suite; no Python coverage tooling applicable

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| polls /api/tasks every 3s via setInterval | polls-at-3s, no-tick-before-3s, polls-3-times-in-9s | Yes — advance 2999ms asserts no new call; advance 3000ms asserts more calls | COVERED |
| useRef stores lastMtime; skips setTasks when mtime unchanged | same-ref-on-same-mtime (`.toBe(tasksRef)`), new-ref-on-mtime-change, content-updated-after-change | Yes — reference equality check fails if setTasks called on same mtime | COVERED |
| /api/board fetched once on mount | board-fetched-once (`.toBe(1)`), board-data-exposed (`.toEqual(BOARD)`) | Yes — exact count 1 fails if called again; deep equality fails if board missing | COVERED |
| Hook exposes 7 fields incl. refetchTasks | all-fields-present, loading-false-after-mount, refetchTasks-triggers-fetch | Yes — `toHaveProperty` + typeof function check; loading `.toBe(false)` | COVERED |
| skip-when-in-flight | tick-skipped-when-in-flight (`callCount toBe frozen`), isFetching-true-while-in-flight, isFetching-false-after-resolve | Yes — exact call count freeze fails if new fetch started; isFetching `.toBe(true/false)` | COVERED |
| AbortController.abort on unmount | abort-called-on-unmount (`toHaveBeenCalled`), no-state-update-after-unmount (reference equality after unmount) | Yes — spy check fails if abort not called; reference equality fails if state mutated | COVERED |
| error/isStale states | error-set-on-poll-reject, isStale-true-on-failure, error-and-isStale-cleared-on-recovery | Yes — error `toBeTruthy()` fails if null; isStale `.toBe(true)` fails if false; both cleared checks exact | COVERED |
| Zero new dependencies | (not unit-testable — verified by inspection of import statement) | N/A | COVERED (inspection) |

Note: Test-writer brief stated 20 tests but AC coverage table maps to 19 unique tests. Count was a brief error; all AC lines are fully covered by the 19 tests in the file. No gap.

#### 5.1 Security Review

- No hardcoded secrets or API keys. URLs are static `/api/board` and `/api/tasks`.
- No injection risk: response data flows only to React state.
- AbortController used with `cancelled` flag guarding all `setState` calls — prevents state updates after unmount.
- AbortError filtered via `err instanceof DOMException && err.name === 'AbortError'` — clean, no false suppression.
- No new external dependencies or third-party APIs.
- **No security issues.**

#### 5.2 Test Integrity — TestFromAC Comparison

All 19 TestFromAC_useBoardHook967 tests verified against original test-writer intent:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| fetches /api/tasks on mount and polls again after 3 seconds | None | PRESERVED |
| does not fire an extra poll tick before 3 seconds | None | PRESERVED |
| polls at least 3 times after 9 seconds | None | PRESERVED |
| keeps same tasks array reference when mtime unchanged | None | PRESERVED |
| updates tasks array reference when mtime changes | None | PRESERVED |
| tasks content reflects updated data after mtime change | None | PRESERVED |
| fetches /api/board exactly once | None | PRESERVED |
| exposes board data from single mount fetch | None | PRESERVED |
| exposes all required fields | None | PRESERVED |
| loading is false after mount fetch completes | None | PRESERVED |
| refetchTasks triggers an additional /api/tasks fetch | None | PRESERVED |
| skips interval tick when poll is in-flight | None | PRESERVED |
| isFetching is true while poll is in-flight | None | PRESERVED |
| isFetching is false once in-flight poll resolves | None | PRESERVED |
| calls AbortController.abort on unmount | None | PRESERVED |
| does not update tasks state after unmount | None | PRESERVED |
| sets error to truthy when poll rejects | None | PRESERVED |
| sets isStale to true after poll failure | None | PRESERVED |
| clears error and isStale on next successful poll | None | PRESERVED |

No tests weakened or removed.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are exact (`.toBe`, `.toEqual`, reference equality). One lazy: `error.toBeTruthy()` — acceptable given AC wording "sets error to truthy"; null vs non-empty string is the meaningful distinction |
| Negative/error-path coverage | STRONG | Error/isStale tests, unmount cleanup test, pre-3s tick guard all covered |
| Manual mutation resistance | STRONG | Reference equality checks (`toBe(tasksRef)`) catch unintended setTasks calls; count freeze on skip-when-in-flight catches spurious fetches |
| Test independence | STRONG | `beforeEach/afterEach` with `vi.useFakeTimers/useRealTimers/unstubAllGlobals/restoreAllMocks`; no shared mutable state |
| Descriptive test names | STRONG | All names describe behavior (e.g., "does not fire an extra poll tick before 3 seconds have elapsed") |

**Overall: ADEQUATE–STRONG. No definitively WEAK test.**

#### 5.4 Data Safety

- `cancelled` closure flag guards all `setState` calls — no state updates after unmount from polling path.
- `pendingPoll` flag is a closure variable scoped to the effect instance; no cross-render sharing.
- `inFlightRef` is a stable `useRef` — no race condition risk.
- No multi-step operations requiring atomicity.
- **No data safety issues.**

#### 5.5 Implementation-Aware Test Gap Analysis

- `pendingPoll` deferred-fetch logic in `finally` block: tested indirectly by `polls-3-times-in-9s` — the test passes only when the deferred poll fires after tick 1 completes.
- `refetchTasks()` has no AbortController signal or `cancelled` guard (`useBoard.ts:L121–L134`). If called just before unmount, a setState could fire on an unmounted component (React warning). This path is **not tested**. However: (a) the AC never required cleanup for refetchTasks, (b) the test-writer did not write a cleanup test for it, (c) impact is a React developer warning, not a crash or data corruption. **Flagged as informational — not a fail criterion for this AC scope.**
- All other branches covered: AbortError filter, `!boardRes.ok`, `!tasksRes.ok`, poll error, mtime skip/update.

#### 5.6 Necessity Check

- Not applicable — zero new dependencies added.

#### 5.7 Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Fix applied | `pendingPoll` deferred-fetch to handle synchronous fake-timer tick accumulation |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

1. **refetchTasks cleanup gap** (`useBoard.ts:L121–L134`): no `cancelled` flag or AbortController signal. Calling `refetchTasks()` just before unmount can trigger setState on unmounted component. Low priority; consider adding in a follow-up.
2. **TS2322 type errors in test file** (lines 276, 312, 369): pre-existing from test-writer, not caused by this task. The `resolvePoll!: () => void` assignment pattern could be typed as `(value?: unknown) => void` to satisfy the Promise resolve signature.
3. **`error` assertion uses `.toBeTruthy()`** (line 419): minor; acceptable given AC wording. Could be tightened to `.toMatch(/network failure/)` in a future polish pass.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| polls /api/tasks every 3s via setInterval | `useBoard.ts:L108` — `setInterval(() => void pollTasks(), 3000)` | polls-at-3s, no-tick-before-3s | PASS |
| useRef stores lastMtime; skips setTasks when mtime unchanged | `useBoard.ts:L33` (`mtimeRef = useRef`), `L76-77` (mtime compare + conditional setTasks) | same-ref-on-same-mtime, new-ref-on-mtime-change | PASS |
| /api/board fetched once on mount | `useBoard.ts:L49-50` — `Promise.all([fetch('/api/board'), fetch('/api/tasks')])` in `load()`; no board fetch in `pollTasks()` | board-fetched-once | PASS |
| Hook exposes 7 fields incl. refetchTasks | `useBoard.ts:L114` — `return { board, tasks, loading, error, isFetching, isStale, refetchTasks }` | all-fields-present | PASS |
| skip-when-in-flight; AbortController on unmount | `useBoard.ts:L69-70` (inFlightRef guard + pendingPoll), `L111-112` (controller.abort + clearInterval) | tick-skipped-when-in-flight, abort-called-on-unmount | PASS |
| Zero new runtime dependencies | `useBoard.ts:L1` — only `{ useState, useEffect, useRef } from 'react'` | inspection | PASS |
| All RED-phase tests pass | vitest: 19/19 TestFromAC_useBoardHook967 passed | all TestFromAC tests | PASS |
| Existing KanbanBoard tests still pass | vitest: 74 total passed (KanbanBoard suite included) | KanbanBoard test files | PASS |

---

### Verdict

0 Pass 1 failures. All AC lines implemented with code evidence. All 19 TestFromAC tests preserved unmodified. Builder process CLEAN (one fix, sound reasoning). Confidence: **.94 → PASS**
[[2026-04-18]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `useBoard.ts` is an internal hook; copilot-instructions.md documents stack/tooling, not individual hooks. No new endpoint, no new dependency, no stack change. |
| 2 | Module docstrings (Python) | No | N/A | Only TypeScript files changed (`hooks/useBoard.ts`, `KanbanBoard.tsx`). No Python modules modified. |
| 3 | External attribution → sources/overview.md | Yes | PASS | Section "useBoard Polling GREEN Implementation (Task #967)" already present at lines 87–92 of sources/overview.md with React docs:useEffect and MDN:AbortController entries. |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified. |
| 5 | Research doc linked | Yes | PASS | `.owlbear/research/967-useboard-polling-green.md` exists; linked in task body under "Research" section. |
| 6 | Scratch files | — | PASS | No `.owlbear/scratch/967-*` files found. |

**Files updated:** none — all checks passed without modification.
**Verdict:** no docs impact beyond what was already committed by prior agents. Gate passed.
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| polls /api/tasks every 3s via setInterval | `useBoard.ts:L108` — `setInterval(() => void pollTasks(), 3000)` + tests polls-at-3s, no-tick-before-3s, polls-3-times-in-9s | PASS |
| useRef stores lastMtime; skips setTasks when mtime unchanged | `useBoard.ts:L33,L76-77` — mtimeRef + conditional setTasks + tests same-ref-on-same-mtime, new-ref-on-mtime-change | PASS |
| /api/board fetched once on mount | `useBoard.ts:L49-50` — Promise.all in load(), no board fetch in pollTasks + test board-fetched-once | PASS |
| Hook exposes 7 fields incl. refetchTasks | `useBoard.ts:L114` — return statement matches + test all-fields-present | PASS |
| skip-when-in-flight + AbortController on unmount | `useBoard.ts:L69-70,L110-112` — inFlightRef guard + controller.abort() + tests tick-skipped, abort-on-unmount | PASS |
| Zero new runtime dependencies | `useBoard.ts:L1` — only react imports | PASS |
| All RED-phase tests pass | 19/19 TestFromAC_useBoardHook967 passed | PASS |
| Existing KanbanBoard tests still pass | 192 vitest total, 0 failures | PASS |

### Test Results

- vitest: 192 passed, 0 failed (13 test files)
- pytest: 126 passed, 0 failed
- ruff: clean
- tsc: 5 TS2322 errors in test files — all pre-existing from test-writer commit eb833bf5 (resolve function type mismatch). Not caused by this task.

### Architect Quality: 4/5

Original AC had 3 critical defects (refetchTasks omission, abort-per-tick contradiction, timer interference). Architect + challenger caught and fixed all before builder phase. Post-refinement AC was specific and verifiable. System working as designed; minor deduction for upstream AC quality requiring intervention.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 8 verified) → 0
- Lint violations: pre-existing only, not from this task → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed PASS) → 0
- Full-suite failures in scope: 0 → 0

### Confidence: 1.00

### Action: archive
