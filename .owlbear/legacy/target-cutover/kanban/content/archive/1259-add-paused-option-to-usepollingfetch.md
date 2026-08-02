---
id: 1259
title: Add paused option to usePollingFetch
status: archived
priority: medium
created: 2026-05-01T09:34:21.381409+00:00
updated: 2026-05-01T21:29:54.921057+00:00
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

Add a `paused?: boolean` option to usePollingFetch. When true, skip interval ticks but keep refetch() callable. Default false for backward compatibility. See .owlbear/research/1235-eventsource-client-implementation.md §3.5
[[2026-05-01]]
## Research
- Research doc: .owlbear/research/1259-paused-option-usepollingfetch.md
- Sources: 5 studied, 3 high-relevance (Dan Abramov useInterval, TanStack Query enabled, existing codebase)
- Recommendation: Approach A — ref-based tick check (~5 LOC). Timer stays stable on pause/unpause, no unwanted immediate poll on resume, refetch() always callable. (confidence: 0.90)
- Follow-up tasks created: none needed — this task IS the implementation unit; downstream #1261 already depends on it
- Decision requests: none (T1 — backward-compatible option addition)

## Challenge Results
- Challenger: SKIP — trivial single-option-dominates change with clear prior art
- Key insight: Conditional interval (Dan Abramov pattern) actively harms the SSE use case because timer resets on resume cause unwanted immediate polls
[[2026-05-01]]

## Acceptance Criteria

- [ ] AC1: `UsePollingFetchOptions` adds `paused?: boolean` (default `false`) — `UsePollingFetchResult` unchanged (td:1)
- [ ] AC2: When `paused` is `true`, interval callback skips `poll()` (td:2)
- [ ] AC3: When `paused` is `true`, queued-repoll drain (`pendingPollRef` finalizer in `poll()`) also skips `poll()` (td:2)
- [ ] AC4: When `paused` is `true`, `refetch()` still triggers `poll()` (td:2)
- [ ] AC5: Initial mount `poll()` fires regardless of `paused` value (td:1)
- [ ] AC6: Toggling `paused` `true→false` resumes on next natural interval tick — no timer teardown/setup, no immediate burst (td:2)
- [ ] AC7: All existing `usePollingFetch_1227.test.ts` tests pass without modification (td:0)

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1 | Clear interface addition, backward-compatible default | None |
| AC2 | Core pause behavior — ref-based guard in setInterval callback | None |
| AC3 | Challenger-identified gap: pendingPollRef finalizer must also honor pause | Added (was missing from research sketch) |
| AC4 | Explicit refetch-while-paused contract for SSE consumer (#1261) | None |
| AC5 | Mount fetch is initialization, not polling — fires unconditionally | None |
| AC6 | Timer stability: no effect dep change, no teardown/setup on toggle | None |
| AC7 | Regression gate — default false means no behavior change for existing consumers | None |

### Architecture Notes

- **Approach:** Ref-based tick check (Approach A from research). Add `pausedRef` synced to `options?.paused ?? false` on every render. Guard in `setInterval` callback AND in `pendingPollRef` finalizer. No effect dep change. ~6 LOC delta.
- **Consumers:** `useBoard.ts`, `usePendingDRs.ts`, `useScanPolling.ts` — none pass `paused` today; default `false` preserves behavior.
- **Pattern consistency:** Follows existing ref-heavy pattern (isMountedRef, inFlightRef, pendingPollRef, controllerRef). No new abstractions.
- **Local precedent:** `usePolling.ts` has a skip gate but uses different timer semantics (conditional interval). Approach A is preferred here because SSE fallback needs stable timer on resume.

### Dependency Analysis

- **#1235** (dependency): archived/done — satisfied.
- **#1261** (downstream consumer): in research, depends on this + #1260. Contract: `paused` option lets useBoard suppress interval polls during active SSE.

### Challenger Results

- Confidence: 0.58 → reconsider.
- Valid finding: queued-repoll path not covered by initial sketch. **Resolved:** added AC3 to explicitly require pause guard in pendingPollRef finalizer.
- Other findings (local precedent, proof plan): informational — addressed in architecture notes. Test-writer derives tests from AC lines.
- Post-resolution confidence: sufficient for approval.

[[2026-05-01]]
APPROVED #1259 → todo. Refined AC from prose into 7 verifiable lines with test-depth annotations. Challenger surfaced queued-repoll gap (pendingPollRef finalizer must also honor pause) — added as AC3. Approach A (ref-based tick check, ~6 LOC) approved.
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts
- Classes: TestFromAC_PausedOption
- Tests per category: happy 5, edge 5, boundary 3
- Total: 13 tests, all FAIL (AssertionError — paused option not yet implemented)
- ruff: N/A (TypeScript); eslint: clean

### AC Coverage

| AC | Tests | Category |
|----|-------|----------|
| AC1 (td:1) | 1 | smoke (behavioral effect proof) |
| AC2 (td:2) | 3 | happy, edge, boundary |
| AC3 (td:2) | 2 | happy (via refetch), edge (via interval) |
| AC4 (td:2) | 3 | happy (combined w/ AC2), edge, boundary |
| AC5 (td:1) | 1 | smoke (combined w/ interval-skip to force fail) |
| AC6 (td:2) | 3 | happy, edge, boundary |
| AC7 (td:0) | 0 | skipped per skill |

### Notes for Builder
- AC3 tests: pause guard must be added to the `pendingPollRef` finalizer inside `poll()`, not just to the interval callback.
- AC4 boundary: `refetch()` while in-flight + paused → pendingPollRef queued → drain suppressed by pause (intersection with AC3).
- Approach A (ref-based): add `pausedRef = useRef(options?.paused ?? false)`, update on every render, guard in setInterval callback AND in pendingPollRef finalizer. No effect dep change — timer stays stable.
[[2026-05-01]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/hooks/usePollingFetch.ts`.
- Changes applied:
  - Added `paused?: boolean` to `UsePollingFetchOptions` (default behavior remains false via `pausedRef` assignment).
  - Added `pausedRef` synced each render from `options?.paused ?? false`.
  - Interval callback now skips `poll()` while paused.
  - `pendingPollRef` drain in `poll()` finalizer now skips recursive `poll()` while paused.
  - `refetch()` remains unchanged and still calls `poll()` directly.
- RED verification before implementation:
  - `src/__tests__/usePollingFetch_1259.test.ts`: 13/13 failed (expected).
- GREEN verification after implementation:
  - `npx vitest run src/__tests__/usePollingFetch_1259.test.ts src/__tests__/usePollingFetch_1227.test.ts` -> 26/26 passed.
- Coverage evidence:
  - `npx vitest run ... --coverage.include=src/hooks/usePollingFetch.ts` -> statements 98.43%, lines 98.41%, functions 100% on touched module.
- Lint/diagnostics:
  - ESLint on changed file clean (`npx eslint src/hooks/usePollingFetch.ts`).
  - VS Code diagnostics for changed file: no errors.
  - quality-runner full run reported unrelated Python-suite failures and confirmed Ruff is not valid for TypeScript linting; frontend gate evidence therefore uses Vitest + ESLint + diagnostics per `h-quality-runner` guidance.
- Commit:
  - `feat: add paused option to usePollingFetch (#1259, builder)`

- Reflection:
  - Full quality-runner invocation is noisy for frontend-only tasks; scoped Vitest + ESLint gives accurate task signal.
  - Keeping timer lifecycle unchanged (no effect dependency changes) satisfied resume semantics without burst behavior.
  - Guarding both interval tick and pending-drain paths was necessary; interval-only guard leaves AC3 failing.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped Vitest: 26 passed, 0 failed, 0 skipped
- `serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts`: 13/13 passed
- `serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts`: 13/13 passed
- VS Code diagnostics: no errors in `usePollingFetch.ts`, the task test, the regression test, or live callers `useBoard.ts`, `usePendingDRs.ts`, `useScanPolling.ts`

### Lint
- quality-runner Ruff output is not applicable for this TypeScript-only scope
- TypeScript/editor diagnostics are clean on the reviewed source, tests, and callers

### Coverage
- `serve/cockpit/web/src/hooks/usePollingFetch.ts`: statements 98.43%, lines 98.41%, functions 100%, branch 80%
- Uncovered line reported by quality-runner is outside the paused-path change; changed paused logic is exercised by the scoped suites

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `paused?: boolean` exists in `usePollingFetch.ts` and is exercised by the task suite, but the `UsePollingFetchResult unchanged` clause is not proved by a discriminating `TestFromAC` assertion. The task suite comment names that contract at `usePollingFetch_1259.test.ts:5`, yet the suite only exercises `result.current.refetch()` at lines 134, 192, 206, 207, and 231. No task test would fail if `isFetching` or `hasFetched` were dropped from the returned result even though the unchanged contract remains declared in `usePollingFetch.ts` lines 15-18 and is consumed by `usePendingDRs.ts:40` and `useScanPolling.ts:29`. | FAIL (missing proof) |
| AC2 | Interval callback is guarded by `!pausedRef.current` in `usePollingFetch.ts:100-101`; covered by paused interval tests in `usePollingFetch_1259.test.ts` lines 83, 95, and 107. | PASS |
| AC3 | Pending-drain guard is enforced at `usePollingFetch.ts:89`; covered by in-flight queued-repoll tests at `usePollingFetch_1259.test.ts` lines 118 and 145. | PASS |
| AC4 | `refetch()` still calls `poll()` directly at `usePollingFetch.ts:117`; covered by paused refetch tests at `usePollingFetch_1259.test.ts` lines 175, 189, and 206. | PASS |
| AC5 | Initial mount still calls `poll()` before the interval is established in `usePollingFetch.ts:96`; covered at `usePollingFetch_1259.test.ts:243`. | PASS |
| AC6 | Idle pause/unpause behavior is covered by `usePollingFetch_1259.test.ts` lines 263, 293, and 318, and the stable-timer implementation is visible in `usePollingFetch.ts` where `pausedRef.current` is updated at line 44 without adding `paused` to the effect dependencies. | PASS |
| AC7 | Existing `usePollingFetch_1227.test.ts` suite passed 13/13 in the independent quality-runner run, and no test modifications were identified in the reviewed change scope. | PASS |

#### Security Review
- No security issues found in scope. The change is limited to a frontend hook option/ref guard and introduces no new dependency, input surface, persistence, or dynamic execution path.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in scope.
- Scoped change reconstruction from builder notes and live source indicates the implementation change is limited to `serve/cockpit/web/src/hooks/usePollingFetch.ts`.
- Existing regression suite `usePollingFetch_1227.test.ts` remains intact and passes.

#### Test Quality
- Blocking issue: AC1 proof is incomplete. The task suite proves the new option is accepted and behavior changes, but it does not add a discriminating assertion for the unchanged returned result contract.
- Non-blocking note: AC6 proof would be stronger if the suite directly observed timer lifecycle stability rather than only fetch counts, but live source evidence is sufficient to keep AC6 itself green for this review.

#### Data Safety
- No issues found. Existing in-flight coalescing and unmount cleanup remain in place.

#### Builder Process Quality
- CLEAN. One builder attempt documented; commit presence was verified in `.git/logs/refs/heads/dev` for `feat: add paused option to usePollingFetch (#1259, builder)`.
- No prior `## Review Evidence` section exists in the task file, so this is the first review failure and does not trigger the loop-breaker route.

### Deductions
- -0.10: AC1 lacks a discriminating `TestFromAC` assertion for the unchanged `UsePollingFetchResult` contract.
- -0.02: AC6 timer-stability clause is proved mostly by source inspection rather than by mutation-resistant test assertions.

### Verdict
- Confidence: 0.88
- FAIL -> `todo`

### Required Follow-up
- Test-writer: strengthen AC1 so the suite would fail if `UsePollingFetchResult` changed. The proof needs to cover the returned contract, not just `paused` acceptance and `refetch()` availability.
- Optional hardening while you are in the file: add a more discriminating AC6 assertion around timer stability so an implementation that tears down/recreates the interval on pause toggles would fail.

### Action
- Rejected to `todo` because the implementation appears correct, but the `TestFromAC` proof is not yet strong enough to certify AC1.
[[2026-05-01]]
## Test-Writer Notes
- Retry cycle: added 2 new tests addressing reviewer's Required Follow-up gaps.
- Test file: serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts
- Classes: TestFromAC_PausedOption (existing)

### New tests added

**AC1 discriminating (added to "AC1: paused option type contract" describe):**
- `contract: isFetching and hasFetched have correct lifecycle values — would fail if either were dropped from UsePollingFetchResult`
  - Uses makeSlowFetch to assert isFetching=true/hasFetched=false in-flight, then isFetching=false/hasFetched=true after resolve. Would fail (undefined ≠ boolean) if either field were dropped.

**AC6 timer-stability discriminating (added to "AC6: resume on next tick" describe):**
- `timer-stability: interval fires at original timer offset after pause/unpause — would fail if implementation recreated the interval on toggle`
  - Pause at t=500ms, unpause at t=600ms, advance to t=1000ms. Stable timer fires at t=1000ms (fetch #2). Recreated timer would fire at t=1600ms — still 1 fetch at t=1000ms. Discriminating against conditional-interval implementations.

### Verification
- Total: 15 tests (13 existing preserved + 2 new), all PASS against current implementation
- usePollingFetch_1227.test.ts: 13/13 still green
- Vitest: 28/28 passed
- Commit: 3b80c85a

### AC Coverage delta
| AC | New tests | Notes |
|----|-----------|-------|
| AC1 | +1 (lifecycle contract) | Now directly proves isFetching/hasFetched lifecycle — would fail if fields dropped |
| AC6 | +1 (timer-stability) | Now proves no teardown/setup on pause toggle — mutation-resistant |

### Builder skip
All new tests PASS against current implementation. Reviewer's Required Follow-up contained only test-proof gaps — no implementation fixes needed. Advancing directly to review per w-tdd-red §Step 1b.1.
[[2026-05-01]]
Test-only retry — all new tests pass against current impl. Builder skip: advancing directly to review per w-tdd-red §Step 1b.1.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 28 passed, 0 failed, 0 skipped
- `serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts`: 15/15 passed
- `serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts`: 13/13 passed
- VS Code diagnostics: no errors in `usePollingFetch.ts`, the task suite, the regression suite, or live callers `useBoard.ts`, `usePendingDRs.ts`, and `useScanPolling.ts`

### Lint
- ESLint clean on `serve/cockpit/web/src/hooks/usePollingFetch.ts`, `serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts`, and `serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts`

### Coverage
- `serve/cockpit/web/src/hooks/usePollingFetch.ts`: 98.43% statements, 80% branch, 100% functions, 98.41% lines
- quality-runner reported one uncovered line outside the paused-path change (`line 76`); no implementation-aware gap was identified in the changed logic

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `UsePollingFetchOptions` includes `paused?: boolean` and `UsePollingFetchResult` still exposes `isFetching`, `hasFetched`, and `refetch` in `serve/cockpit/web/src/hooks/usePollingFetch.ts:5-18`. The retry test proves the runtime lifecycle contract for `isFetching`/`hasFetched` and presence of `refetch` at `serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts:76-96`. Live callers still compile clean at `usePendingDRs.ts:40-72` and `useScanPolling.ts:29-57`. | `usePollingFetch_1259.test.ts:59-96` | PASS |
| AC2 | Interval callback remains guarded by `!pausedRef.current` at `serve/cockpit/web/src/hooks/usePollingFetch.ts:100-102`; exact-count paused tick tests would fail if the guard were removed. | `usePollingFetch_1259.test.ts:102-134` | PASS |
| AC3 | Pending-drain suppression is implemented at `serve/cockpit/web/src/hooks/usePollingFetch.ts:89-91`; queued refetch and queued interval-drain tests both stay at one fetch after resolve. | `usePollingFetch_1259.test.ts:142-192` | PASS |
| AC4 | `refetch()` still calls `poll()` directly at `serve/cockpit/web/src/hooks/usePollingFetch.ts:117-118`; paused refetch tests distinguish direct refetch from the paused interval path. | `usePollingFetch_1259.test.ts:199-260` | PASS |
| AC5 | Initial mount still performs `poll()` unconditionally at `serve/cockpit/web/src/hooks/usePollingFetch.ts:98`; the mount test proves one immediate fetch even when `paused=true`. | `usePollingFetch_1259.test.ts:267-281` | PASS |
| AC6 | Pause/unpause resume behavior is covered by next-tick, no-burst, timer-stability, and multi-cycle tests at `serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts:287-398`. The new timer-stability test is discriminating against reset-on-toggle implementations. | `usePollingFetch_1259.test.ts:287-398` | PASS |
| AC7 | The unchanged regression suite `serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts:56-207` passed 13/13 in the independent quality-runner run. No weakened or removed assertions were identified in scope. | `usePollingFetch_1227.test.ts:56-207` | PASS |

#### Security Review
- No issues found. Scope is limited to a local frontend polling hook and task-scoped tests; no new dependency, persistence, shelling, path handling, or dynamic execution surface was introduced.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found.
- Retry changes strengthen proof with an AC1 lifecycle test and an AC6 timer-stability test.
- Existing `usePollingFetch_1227.test.ts` assertions remain intact in the reviewed scope.

#### Test Quality
- PASS. Assertions are specific and mutation-resistant on the changed behavior.
- AC1 now has direct runtime proof for the unchanged result fields; the remaining theoretical gap is only exact type-level equality of the exported interface, which is informational rather than a blocking AC failure for this runtime-focused task.

#### Data Safety
- No issues found. In-flight coalescing, abort cleanup, and paused gating remain component-local and bounded.

#### Builder Process Quality
- CLEAN. One builder implementation attempt, then one test-only retry by test-writer after the prior review failure. The retry changed approach by adding discriminating assertions rather than repeating the earlier proof shape.

### Informational
- `vscode_listCodeUsages` shows live hook consumers at `useBoard.ts:57`, `usePendingDRs.ts:40`, and `useScanPolling.ts:29`; all remain compatible with the unchanged result contract.
- Code-reader noted that AC1 does not include an exact type-equality assertion for `UsePollingFetchResult`, but the current runtime contract and downstream caller surface are sufficiently proved for this gate.

### Deductions
- -0.05: AC1 proof is runtime-focused rather than an exact exported-type equality assertion.

### Verdict
- Confidence: 0.95
- PASS -> `docs`

### Action
- Advanced to `docs`. The prior proof gap is closed; no blocking implementation, security, or test-integrity defects remain.

### Reflection
- Scoped frontend evidence was the right gate here: Vitest, ESLint, diagnostics, and code-reading were sufficient without pulling unrelated backend noise into the decision.
- The retry materially improved proof quality instead of only increasing test count; the AC6 timer-stability test now protects against a realistic refactor regression.
- AC1 is now strong enough for review, but if the team later wants airtight type-contract enforcement on exported interfaces, that should become an explicit test-writer convention rather than an ad hoc review requirement.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/cockpit/README.md` does not mention `usePollingFetch` or polling hooks. No other IN-scope prose doc references this internal hook. |
| 2 | Module docstrings | No | N/A | Changed file is TypeScript (`usePollingFetch.ts`) — not a Python module. |
| 3 | External attribution | Yes | Verified | Dan Abramov and TanStack Query rows already present in `.owlbear/sources/overview.md` lines 35–36, added during research phase. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1259-paused-option-usepollingfetch.md` exists; linked from task body under `## Research`. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches `serve/cockpit/web/src/hooks/usePollingFetch.ts`. Footer updated from `(7cf28a5d)` to `(81354270)`, date 2026-05-01. Committed as `056e5b8c`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/hooks/usePollingFetch.ts | OUT (TS source) | N/A |
| serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts | OUT (test) | N/A |
| serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts | OUT (test) | N/A |
| share/diagrams/cockpit.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer timestamp only)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (.owlbear/scratch/1259-* — no matches)
[[2026-05-01]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: paused option + result unchanged | `usePollingFetch.ts:7` adds `paused?: boolean`; result interface unchanged at lines 16-19; lifecycle test at `usePollingFetch_1259.test.ts:76-96` | PASS |
| AC2: interval skips poll when paused | Guard at `usePollingFetch.ts:101`; tests at `usePollingFetch_1259.test.ts:102-134` | PASS |
| AC3: pendingPollRef drain skips when paused | Guard at `usePollingFetch.ts:89`; tests at `usePollingFetch_1259.test.ts:142-192` | PASS |
| AC4: refetch() still works when paused | Direct `poll()` call at `usePollingFetch.ts:117-118`; tests at `usePollingFetch_1259.test.ts:199-260` | PASS |
| AC5: initial mount fires regardless of paused | Unconditional `void poll()` at `usePollingFetch.ts:98`; test at `usePollingFetch_1259.test.ts:267-281` | PASS |
| AC6: toggle does not teardown timer | `pausedRef.current` update at line 44, not in effect deps (line 111); timer-stability test at `usePollingFetch_1259.test.ts:350-398` | PASS |
| AC7: existing 1227 tests pass | 13/13 passed in scoped run (28 total with 1259 suite) | PASS |

### Test Results
- Vitest (task-scoped): 28 passed, 0 failed
- Vitest (full suite): pre-existing jsdom env failures in unrelated files (useRepairFlow_1165, useScanPolling_1157); NOT caused by this task
- pytest (full backend): 3492 passed, 113 failed (all failures in unrelated tasks: 973, 1015, migration); no regression from #1259
- ESLint: clean on usePollingFetch.ts and usePollingFetch_1259.test.ts

### Architect Quality: 5/5
Specific, complete, clean implementation path. 7 AC lines with test-depth annotations. Challenger surfaced AC3 gap which was addressed before development. No builder improvisation needed.

### Deduction Breakdown
- No AC lines without evidence: 0
- No lint violations: 0
- AC quality 5/5: 0
- Reviewer evidence present and detailed: 0
- No task-scope test failures: 0
- Pre-existing full-suite failures (not task-caused): informational, no deduction

### Confidence: 0.98
### Action: archive

### Commits Verified
| Commit | Type | Attribution |
|--------|------|-------------|
| e5d06f07 | test (RED) | test-writer |
| df62a068 | feat (GREEN) | builder |
| 3b80c85a | test (retry) | test-writer |
| 056e5b8c | docs (diagram) | doc-writer |