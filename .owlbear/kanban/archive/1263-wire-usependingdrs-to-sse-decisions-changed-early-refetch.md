---
id: 1263
title: Wire usePendingDRs to SSE decisions-changed early-refetch
status: archived
priority: medium
created: 2026-05-01T09:53:38.534934+00:00
updated: 2026-05-02T17:38:56.281572+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1235
- 1262
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Listen for `decisions-changed` SSE event and trigger immediate refetch of /api/decisions/pending ahead of the 60s timer. Keep 60s poll active (SSE is supplementary, not replacement — avoids stale-data bug when decisions/pending doesn't exist yet). Requires useEventSource hook from #1235 and backend multi-surface events from sibling task. See .owlbear/research/1236-extend-sse-decisions-activity.md
[[2026-05-02]]
## Research
- Research doc: .owlbear/research/1263-wire-usependingdrs-sse-decisions.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: Option A — extend useEventSource with generic eventTypes param + lastEventByType map (confidence: 0.82)
- Follow-up tasks created: none (task itself is the implementation target)
- Decision requests: none

## Implementation Summary
Backend ready (events.py already emits decisions-changed). Frontend needs:
1. useEventSource.ts — accept eventTypes option, register per-type listeners, return lastEventByType map
2. useBoard.ts — subscribe to decisions-changed, expose lastDecisionsMtime
3. Shell.tsx — useEffect watching lastDecisionsMtime → refetchPendingDRs()
4. 60s poll stays active (supplementary SSE, not replacement)

## Challenge Results
- Challenger: FALLBACK — trivial wiring, parent research (#1236) already challenged full architecture
- Confidence in original: 0.82
[[2026-05-02]]

## Acceptance Criteria
- [ ] `useEventSource` accepts optional `eventTypes?: string[]` defaulting to `['tasks-changed']`; registers `addEventListener` for each type; `eventTypes` identity changes do not cause reconnection (content-compare or caller-stabilized ref) (td:2)
- [ ] `useEventSource` returns `lastEventByType: Record<string, number>` with per-type latest mtime; existing `lastEventMtime` equals max across all types for backward compatibility; test must include a reverse-order scenario (higher mtime arrives first on type A, lower mtime arrives second on type B) to discriminate `Math.max` from last-write-wins (td:2)
- [ ] `useBoard` passes `eventTypes: ['tasks-changed', 'decisions-changed']` to `useEventSource`; task refetch triggers on type-specific `lastEventByType['tasks-changed']` (not aggregate `lastEventMtime`) to prevent cross-surface refetch regression; returns `lastDecisionsMtime: number | null` derived from `lastEventByType` (td:2)
- [ ] `Shell.tsx` calls `refetchPendingDRs()` via `useEffect` when `lastDecisionsMtime` changes; uses ref-stabilized callback pattern (matching existing `refetchTasksRef` in useBoard.ts:81-88) to prevent rerender loops; test must prove both halves: (a) identity churn with unchanged mtime does not trigger, and (b) after identity swap + subsequent mtime change, the NEW callback fires exactly once (not the stale one) (td:2)
- [ ] `usePendingDRs` 60s polling remains active and unchanged — SSE supplements but does not replace polling (td:1)
- [ ] Existing `useEventSource_1260.test.ts` behavior assertions pass; exact-shape type test (line 115 `toEqualTypeOf`) requires additive update for new `lastEventByType` field (td:0)

[[2026-05-02]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: wire decisions-changed SSE to trigger usePendingDRs refetch |
| Interface clarity | PASS | AC specifies exact param shape (`eventTypes?: string[]`), return types (`lastEventByType`, `lastDecisionsMtime`), and ref-stabilization requirement |
| Dependency correctness | PASS | #1235 (archived), #1262 (archived) — both done; backend events.py already emits `decisions-changed` |
| Module layering | PASS | useEventSource → useBoard → Shell follows existing hook composition pattern |
| TDD compliance | PASS | Frontend Vitest suite; existing test file `useEventSource_1260.test.ts` provides MockEventSource pattern |
| KISS/YAGNI | PASS | Option A (generic eventTypes) justified by immediate sibling task #1264 (activity-changed) needing same hook extension |
| Premise challenge | PASS | No existing capability — confirmed by reading all 4 source files |
| Pattern consistency | PASS | Ref-stabilized callback pattern matches existing `refetchTasksRef` in useBoard.ts:81-88 |
| Security surface | PASS | No new system boundaries — same SSE endpoint, same API |
| Single domain | PASS | Frontend cockpit only |

### Challenger Results
- Verdict: reconsider (0.37)
- 3 valid concerns addressed in AC refinement:
  1. **Race condition (critical)**: Shell useEffect with unstable refetchPendingDRs identity → AC4 now requires ref-stabilized pattern matching useBoard.ts:81-88
  2. **Cross-surface refetch regression (moderate)**: aggregate lastEventMtime triggers task refetch on decisions events → AC3 now requires useBoard to watch type-specific `lastEventByType['tasks-changed']` instead
  3. **Type-shape test contradiction (moderate)**: exact `toEqualTypeOf` at line 115 would fail with new field → AC6 clarified that additive type-shape update is expected
- Post-refinement confidence: 0.85
[[2026-05-02]]
## Test-Writer Notes

### Test files
- `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts`
- `serve/cockpit/web/src/__tests__/useBoard_1263.test.ts`
- `serve/cockpit/web/src/__tests__/Shell_1263.test.tsx`

### Classes
- `TestFromAC_UseEventSourceEventTypes` (useEventSource_1263.test.ts)
- `TestFromAC_UseBoardDecisionsWiring` (useBoard_1263.test.ts)
- `TestFromAC_ShellDecisionsRefetch` (Shell_1263.test.tsx)

### Counts by category

**useEventSource_1263.test.ts (12 tests, 12 FAIL)**
- AC1 — happy: 2 (decisions-changed listener, both listeners), edge: 2 (empty eventTypes, no tasks-changed when omitted), boundary: 1 (content-compare no reconnect)
- AC2 — happy: 4 (lastEventByType property, empty initially, per-type updates, max for lastEventMtime), edge: 1 (null backward compat with empty lastEventByType), compile: 1 (type shape includes lastEventByType)

**useBoard_1263.test.ts (5 tests, 5 FAIL)**
- AC3 — happy: 4 (decisions-changed listener registered, lastDecisionsMtime null initially, updates on event, independent tracking), boundary: 1 (cross-surface isolation combined with lastDecisionsMtime assertion)

**Shell_1263.test.tsx (4 tests, 3 FAIL + 1 PASS)**
- AC4 — happy: 2 (null→value triggers refetch with null-initial guard, subsequent change), edge: 1 (ref-stabilized identity change)
- AC5 — smoke: 1 (usePendingDRs called with no args) **PASSES — regression guard for unchanged behavior**

### Totals
**21 tests, 20 FAIL, 1 PASS** — lint: clean

### AC coverage
| AC | td | Tests |
|----|-----|-------|
| AC1 — eventTypes param | td:2 | 5 tests (all fail) |
| AC2 — lastEventByType return | td:2 | 7 tests (all fail) |
| AC3 — useBoard decisions wiring | td:2 | 5 tests (all fail) |
| AC4 — Shell refetchPendingDRs effect | td:2 | 4 tests (3 fail) |
| AC5 — usePendingDRs unchanged | td:1 | 1 test (passes — regression guard) |
| AC6 — type shape additive update | td:0 | skipped |

### Notes
- AC5 regression guard passes from start (behavior already exists). Per skill, "unchanged" AC lines require direct regression guard tests; this test documents the contract for the builder not to accidentally pass `intervalMs` or disable polling.
- MockEventSource pattern mirrors useBoard_1261.test.ts (real integration via stubGlobal) for useBoard tests; useEventSource tests use same mock to remain consistent with useEventSource_1260.test.ts.
- Shell tests mock all child components and hooks; cast `makeUseBoardReturn` to `unknown as ReturnType<typeof useBoard>` to allow `lastDecisionsMtime` field before builder adds it to the type.
[[2026-05-02]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/hooks/useEventSource.ts`, `serve/cockpit/web/src/hooks/useBoard.ts`, and `serve/cockpit/web/src/Shell.tsx`.
- Fixes applied:
  - `useEventSource` now accepts `eventTypes?: string[]` (default `['tasks-changed']`), registers listeners per event type, and keeps connection stable across same-content `eventTypes` rerenders.
  - `useEventSource` now returns `lastEventByType: Record<string, number>` and preserves backward-compatible `lastEventMtime` as max across event-type mtimes.
  - `useBoard` now subscribes to `['tasks-changed', 'decisions-changed']`, triggers task refetch only from `tasks-changed`, and exposes `lastDecisionsMtime` from type-specific event state.
  - `Shell.tsx` now uses a ref-stabilized callback pattern to call `refetchPendingDRs()` when `lastDecisionsMtime` changes, without rerender-loop side effects.
- Tests (RED verification before implementation): 20 failed, 1 passed in task suite (`useEventSource_1263`, `useBoard_1263`, `Shell_1263`).
- Tests (GREEN verification after implementation): 21 passed, 0 failed in task suite.
- Regression evidence: 68 passed, 0 failed across adjacent durable tests (`useEventSource_1260`, `useBoard_1261`, `Shell.test.tsx`).
- Lint status: clean (ESLint scoped to changed source files + task tests).
- Coverage: frontend scoped quality run does not report module coverage in current setup (`vite` coverage not configured in this path).
- Commit: `d4e50069` (`feat: wire decisions SSE pending refetch (#1263, builder)`).
[[2026-05-02]]
## Review Evidence
### Test Results
- Quality-runner frontend scoped pass: 89 passed, 0 failed, 0 skipped across the three task suites plus adjacent durable suites for useEventSource, useBoard, and Shell.
- Builder commit d4e50069 was verified in .git/logs/HEAD and .git/logs/refs/heads/dev.
- Live editor diagnostics on useEventSource.ts, useBoard.ts, Shell.tsx, and the task test files reported no errors.

### Lint
- ESLint clean on the changed source files and task test files.

### Coverage
- Frontend scoped coverage extracted from the v8 report: overall 52 percent.
- Touched modules: src/Shell 74 percent, src/hooks/useBoard 61 percent, src/hooks/useEventSource 44 percent.
- This is informational only here: the changed paths are directly exercised by the task suite, but overall module coverage remains low outside this diff.

### AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC1 | useEventSource.ts lines 17-25 and 117-142; useEventSource_1263.test.ts lines 76-148; legacy tasks-changed behavior still covered in useEventSource_1260.test.ts lines 160-178 | PASS |
| AC2 | useEventSource.ts lines 3-6, 117-142, and 173; useEventSource_1263.test.ts lines 154-236 | PASS |
| AC3 | useBoard.ts lines 57-62 and 92-95; useBoard_1263.test.ts lines 123-224; adjacent durable SSE behavior still green in useBoard_1261.test.ts | PASS |
| AC4 | Shell.tsx lines 19-21 and 68-77; Shell_1263.test.tsx lines 126-191 | PASS |
| AC5 | Shell.tsx line 21 still calls usePendingDRs() with no args and usePendingDRs.ts lines 4 and 34 still default to 60000, but the mapped TestFromAC only asserts zero arguments under a fully mocked hook in Shell_1263.test.tsx lines 196-207 | FAIL |
| AC6 | useEventSource_1260.test.ts lines 111-117 still assert the pre-1263 two-field exact shape; the additive update for lastEventByType required by the AC was not made | FAIL |

### Pass 1 Critical Checks
- Test-writer AC coverage: FAIL. AC5 is not discriminating enough to prove live 60s polling remains active, and AC6's required additive durable-test update is missing.
- Security review: PASS. No new boundary, injection, path, secret, or persistence risk found in the changed code.
- Test integrity: PASS with deduction. No visible weakening of the task's TestFromAC suites, but commit-diff proof was unavailable, so immutability confidence is slightly lower.
- Test quality: FAIL. The AC5 smoke check would still pass if internal default polling changed, and the stale AC6 type-shape assertion is weaker than its comment claims.
- Data safety: PASS. The new code keeps source-identity guards, numeric mtime validation, and ref-stabilized callback handling.
- Builder loop check: PASS. No prior Review Evidence section was present, so this is the first review failure.

### Deductions
- Minus 0.07 for missing live proof that 60s polling remains active and unchanged.
- Minus 0.05 for the missing additive update to the durable type-shape assertion in useEventSource_1260.test.ts.
- Minus 0.02 because commit diff was unavailable for high-confidence immutability verification.
- Confidence: 0.86

### Required Follow-up
- Add a proof that would fail if usePendingDRs default polling stops or its default interval changes. The current Shell smoke test is insufficient because the hook is fully mocked.
- Update the legacy exact-shape assertion in useEventSource_1260.test.ts so the durable suite explicitly acknowledges lastEventByType additively.
- Keep the current source implementation unless new evidence appears. I did not find a source-level defect in useEventSource.ts, useBoard.ts, or Shell.tsx.

### Verdict
- FAIL.
- Return to todo because this is the first review failure and only test and proof changes remain.

### Reflection
- Mocked hook-usage tests can confirm integration shape while still missing the live behavior named by the AC.
- Comments around expectTypeOf matchers can overstate proof strength; the executable assertion matters, not the comment.
- Frontend module coverage stayed low despite good diff-scoped proof, so it was useful only as context here.
- Lack of commit diff prevented a high-confidence TestFromAC immutability check, so I took a small confidence deduction.
[[2026-05-02]]
## Test-Writer Notes
- Retry: reviewer gaps addressed — test-only changes, all pass against current implementation.

### Changes made
1. **New file**: `serve/cockpit/web/src/__tests__/usePendingDRs_1263.test.ts`
   - Class: `TestFromAC_PendingDRsPollingActive`
   - 3 tests — live regression guards for AC5's 60s default polling:
     - no refetch before 59 999 ms (boundary — proves interval is ≥ 60 000 ms)
     - refetches at exactly 60 000 ms (proves interval is ≤ 60 000 ms)
     - polling continues past first interval (proves repeating, not one-shot)
   - All 3 PASS immediately (implementation correct). Unlike the Shell smoke test, these call usePendingDRs() directly without mocking — would fail if DEFAULT_INTERVAL_MS changes or setInterval is removed.

2. **Updated**: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
   - AC6 exact-shape assertion updated: `toEqualTypeOf<{status, lastEventMtime}>()` → `toEqualTypeOf<{status, lastEventMtime, lastEventByType: Record<string, number>}>()` to acknowledge the 1263 builder addition.
   - All 34 existing tests still pass.

### Totals
- 3 new tests, all PASS (regression guards for already-correct implementation)
- 1 durable test assertion updated to reflect current contract
- ESLint: clean
- Commit: `4350ba76`

### AC coverage (retry gaps only)
| AC | Gap filled | Tests |
|----|-----------|-------|
| AC5 | Live 60s interval proof (not mocked-hook smoke) | 3 new direct tests — all pass |
| AC6 | Exact-shape assertion updated for lastEventByType | 1 updated assertion — still passes |

### Step 1b.1 rationale
All new tests PASS against current code (implementation already correct). Reviewer required test-only changes — no builder work needed. Advancing directly to review.
[[2026-05-02]]
## Builder Notes
- Implementation: no source edits in this pass; existing 1263 frontend implementation and test-writer retry updates were validated as-is.
- Files changed: none.
- Tests: 58 passed, 0 failed, 0 skipped (scoped quality-runner run across 1263 suites + durable type-shape suite).
- Coverage: overall 86.38%; src/hooks/useEventSource.ts 97.93%, src/hooks/useBoard.ts 86.27%, src/Shell.tsx 79.45%.
- Lint: clean (eslint violations: 0).
- Evidence summary: AC5/AC6 retry proof is present and currently green; task is ready for reviewer verification.
- Fixes applied: none required in this builder pass.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend pass: 92 passed, 0 failed, 0 skipped across `useEventSource_1263`, `useBoard_1263`, `Shell_1263`, `usePendingDRs_1263`, `useEventSource_1260`, `useBoard_1261`, and `Shell.test.tsx`
- ESLint scoped pass: clean on changed source files and task/durable test files
- Live editor diagnostics: no errors in `serve/cockpit/web/src/hooks/useEventSource.ts`, `useBoard.ts`, `usePendingDRs.ts`, `serve/cockpit/web/src/Shell.tsx`, or the scoped test files
- Builder/test-writer commits verified in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`: `d4e50069` and `4350ba76`

### Lint
- Clean

### Coverage
- `src/hooks/useEventSource.ts`: 97.93% statements, 89.47% branches, 100% functions, 97.93% lines
- `src/hooks/useBoard.ts`: 96.07% statements, 73.33% branches, 100% functions, 96.07% lines
- `src/hooks/usePendingDRs.ts`: 83.33% statements, 74.07% branches, 80% functions, 85.71% lines
- `src/Shell.tsx`: 81.5% statements, 82.56% branches, 50% functions, 75% lines
- Overall scoped coverage: 40.38%
- Coverage is informational here. The rejection is for proof quality, not a source-level defect.

### AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC1 | `serve/cockpit/web/src/hooks/useEventSource.ts:17-25,121-140` plus `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts:72-145` prove per-type registration, default behavior, and no reconnect on same-content arrays | PASS |
| AC2 | Implementation is correct at `serve/cockpit/web/src/hooks/useEventSource.ts:129-137`, but the only aggregate-max proof in `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts:193-207` sends the larger mtime last; that would stay green if `lastEventMtime` incorrectly tracked only the latest event rather than the max across types | FAIL |
| AC3 | `serve/cockpit/web/src/hooks/useBoard.ts:57-62,86-95` plus `serve/cockpit/web/src/__tests__/useBoard_1263.test.ts:113-210` prove dual event subscription, decisions isolation, and task refetch only from `tasks-changed` while open | PASS |
| AC4 | `serve/cockpit/web/src/Shell.tsx:67-76` implements the ref-stabilized pattern, but `serve/cockpit/web/src/__tests__/Shell_1263.test.tsx:113-191` proves only trigger-on-mtime-change and no extra call on callback identity churn; it does not prove the ref refresh uses the latest callback on a later decisions event | FAIL |
| AC5 | `serve/cockpit/web/src/hooks/usePendingDRs.ts:4,30-41` plus `serve/cockpit/web/src/__tests__/usePendingDRs_1263.test.ts:44-79` directly prove the default 60s interval, exact boundary, and repeated polling | PASS |
| AC6 | `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts:107-119` now includes `lastEventByType` in the exact-shape assertion, and the durable suite is green | PASS |

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | `useEventSource_1263.test.ts` AC1 block | Yes | COVERED |
| AC2 | `useEventSource_1263.test.ts` aggregate-max test | No — a latest-event-wins mutation still passes when the larger mtime arrives second | LAX |
| AC3 | `useBoard_1263.test.ts` listener/isolation/independence tests | Yes | COVERED |
| AC4 | `Shell_1263.test.tsx` effect tests | No — a stale-ref implementation can still pass the current assertions | LAX |
| AC5 | `usePendingDRs_1263.test.ts` live timer tests | Yes | COVERED |
| AC6 | `useEventSource_1260.test.ts` exact-shape assertion | Yes | COVERED |

#### Security Review
- PASS. No new boundary, injection, path, secret, or dependency risk in the changed code.

#### Test Integrity
- PASS with deduction. The visible durable-suite change in `useEventSource_1260.test.ts:111-119` strengthens the shape assertion additively. I could not inspect the original diff directly, so immutability confidence remains slightly reduced.

#### Test Quality
- FAIL. AC2 proof is weak: `useEventSource_1263.test.ts:193-207` does not discriminate between `Math.max(...Object.values(lastEventByType))` and `lastEventMtime = payload.mtime`.
- FAIL. AC4 proof is weak: `Shell_1263.test.tsx:167-191` proves dependency isolation but not ref refresh to the latest `refetchPendingDRs` callback on a later `lastDecisionsMtime` change.

#### Data Safety
- PASS. State updates are local and guarded; no persistence, race, or unbounded-input issue introduced.

#### Builder Loop Check
- FAIL route escalation only. A prior `## Review Evidence` section is already present in the task body, so this is the second review failure on the same task. Loop-breaker routing applies.

### Deductions
- Minus 0.05: AC2 aggregate-max proof is non-discriminating for a plausible wrong implementation.
- Minus 0.04: AC4 ref-stabilization proof does not verify that the latest callback is used after identity changes.
- Minus 0.02: no direct commit diff for high-confidence TestFromAC immutability verification.
- Confidence: 0.89

### Required Follow-up
- Add an AC2 test where the higher mtime arrives first and a lower mtime arrives second; assert `lastEventMtime` stays at the cross-type max.
- Add an AC4 test that swaps the `refetchPendingDRs` function identity, then changes `lastDecisionsMtime`, and asserts the new callback fires exactly once while the old callback is not reused.
- Do not change the current source implementation unless new evidence appears. I did not find a source-level defect in `useEventSource.ts`, `useBoard.ts`, `usePendingDRs.ts`, or `Shell.tsx`.

### Verdict
- FAIL.
- Return to `backlog`. This is the second review failure on task `1263`, and the remaining issue is test quality / proof strength rather than implementation.

### Reflection
- Exact-value assertions can still be false-green when the test ordering makes the wrong implementation observationally equivalent.
- Ref-stabilization tasks need proof of both halves of the pattern: dependency isolation and ref refresh to the newest callback.
- The current frontend implementation appears correct; the gate failure is about proof quality, not behavior.
- Green scoped coverage was useful context but not sufficient to overcome weak discriminating assertions.
[[2026-05-02]]

## Architecture Review (loop-breaker pass)

### Context
Second review failure routed task back to backlog. Both reviewer passes confirmed implementation is correct — no source defect in useEventSource.ts, useBoard.ts, or Shell.tsx. The only remaining gaps are 2 test discrimination weaknesses:
- AC2: aggregate-max test sends higher mtime last → doesn't discriminate `Math.max` from last-write-wins
- AC4: ref-stabilization test proves identity isolation but not ref-refresh to newest callback

### AC Refinements
AC2 and AC4 refined with explicit test-discrimination requirements (see updated AC below). All other AC lines unchanged.

**Refined AC2:** `useEventSource` returns `lastEventByType: Record<string, number>` with per-type latest mtime; existing `lastEventMtime` equals max across all types for backward compatibility; test must include a reverse-order scenario (higher mtime arrives first on type A, lower mtime arrives second on type B) to discriminate `Math.max` from last-write-wins (td:2)

**Refined AC4:** `Shell.tsx` calls `refetchPendingDRs()` via `useEffect` when `lastDecisionsMtime` changes; uses ref-stabilized callback pattern (matching existing `refetchTasksRef` in useBoard.ts:81-88) to prevent rerender loops; test must prove both halves: (a) identity churn with unchanged mtime does not trigger, and (b) after identity swap + subsequent mtime change, the NEW callback fires exactly once (not the stale one) (td:2)

### Test-Writer Guidance (loop-breaker)
**Implementation is CORRECT — do NOT change source files.** Only 2 test additions needed:
1. In `useEventSource_1263.test.ts`: add a test that sends `decisions-changed` with mtime 9000 FIRST, then `tasks-changed` with mtime 3000 SECOND; assert `lastEventMtime` remains 9000 (the cross-type max, not the latest arrival).
2. In `Shell_1263.test.tsx`: add a test that (a) sets `lastDecisionsMtime=1000` → first refetch fires, (b) swaps `refetchPendingDRs` to a new mock function, (c) sets `lastDecisionsMtime=2000` → assert the NEW mock fires exactly once and the old mock was not called again.

### Evaluation
| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — unchanged |
| Interface clarity | PASS — AC2/AC4 now include discrimination requirements |
| Dependency correctness | PASS — #1235, #1262 both archived/done |
| Module layering | PASS — unchanged |
| TDD compliance | PASS — existing test suites green; 2 additions scoped |
| KISS/YAGNI | PASS — minimal additions, no new abstractions |
| Pattern consistency | PASS — unchanged |
| Security surface | PASS — no new boundaries |
| Single domain | PASS — frontend cockpit only |

### Challenger Results
- Verdict: reconsider (0.58)
- Concerns: AC refinements must be written to task body before approving (addressed — this section), useBoard open-state guard not exercised from negative side (minor, out of scope — reviewer passed AC3 twice)
- Post-refinement confidence: 0.88

### Verdict
APPROVED → todo. Two test additions required per loop-breaker guidance above. Implementation must not change.

[[2026-05-02]]
Loop-breaker architecture pass. AC2 and AC4 refined with explicit test-discrimination requirements. Implementation confirmed correct — no source changes needed. Two targeted test additions required per guidance in body.

[[2026-05-02]]
## Test-Writer Notes
- Retry (loop-breaker pass): added 2 discriminating tests for reviewer gaps only.

### Changes made
1. **Updated**: `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts`
   - Added: `'lastEventMtime stays at cross-type max when higher mtime arrives first (discriminates Math.max from last-write-wins)'`
   - Scenario: `decisions-changed` mtime 9000 arrives FIRST, `tasks-changed` mtime 3000 arrives SECOND; asserts `lastEventMtime === 9000` (cross-type max, not last-write-wins)
   - A last-write-wins impl yields 3000 → test would fail discriminatingly

2. **Updated**: `serve/cockpit/web/src/__tests__/Shell_1263.test.tsx`
   - Added: `'after refetchPendingDRs identity swap, new callback fires on next mtime change (not the stale one)'`
   - Proves both halves of ref-stabilization: (a) initial mtime change fires old mock exactly once; (b) identity swap with unchanged mtime does NOT trigger; (c) subsequent mtime change fires NEW callback exactly once, old mock count unchanged

### Totals
- 2 new tests added, both PASS immediately (implementation correct, reviewer confirmed no source defect)
- 26 tests total across task suites — 26 pass, 0 fail
- ESLint: clean
- Commit: `7a448077`

### AC coverage (retry gaps only)
| AC | Gap filled | Tests |
|----|-----------|-------|
| AC2 | Reverse-order scenario discriminates `Math.max` from last-write-wins | 1 new test — passes |
| AC4 | Ref-refresh proof: NEW callback fires after identity swap + mtime change | 1 new test — passes |

### Step 1b.1 rationale
All new tests PASS against current code (implementation already correct per two reviewer passes). Only test-quality gaps remained. Advancing directly to review — builder has no work to do.
[[2026-05-02]]
## Builder Notes
- Implementation: no source edits in this builder pass; existing 1263 implementation remained unchanged.
- Files changed: none.
- Tests: 95 passed, 0 failed, 0 skipped (scoped frontend run across task suites plus adjacent durable suites).
- Lint: clean (eslint scoped run, 0 violations).
- Coverage: overall 81%; src/hooks/useEventSource.ts 70%, src/hooks/useBoard.ts 96%, src/Shell.tsx 77%, src/hooks/usePendingDRs.ts not covered in this scoped run due to mocking in selected suites.
- Evidence summary: loop-breaker test gaps for AC2/AC4 are now represented by discriminating tests and the full scoped suite is green.
- Fixes applied: none required in builder; this pass verifies readiness for review.

### Reflection
- The remaining risk for this task was proof quality, not implementation behavior.
- Scoped durable-suite inclusion was useful to validate no regressions while keeping runtime manageable.
- Coverage on useEventSource remains below 90% in this scoped pass, but no code changed in builder and all AC-mapped tests are green.
- No additional blockers detected for reviewer handoff.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend pass: 95 passed, 0 failed, 0 skipped across `useEventSource_1263`, `useEventSource_1260`, `usePendingDRs_1263`, `useBoard_1263`, `useBoard_1261`, `Shell_1263`, and `Shell.test.tsx`
- ESLint scoped pass: clean on `src/hooks/useEventSource.ts`, `src/hooks/useBoard.ts`, `src/hooks/usePendingDRs.ts`, `src/Shell.tsx`, and the scoped task and durable test files
- VS Code diagnostics: no errors in the touched source and test files
- Commit presence verified in `.git/logs/HEAD` and `.git/logs/refs/heads/dev` for `d4e50069`, `4350ba76`, and `7a448077`

### Lint
- Clean

### Coverage
- `src/hooks/useEventSource.ts`: 97.93%
- `src/hooks/useBoard.ts`: 96.07%
- `src/hooks/usePendingDRs.ts`: 83.33%
- `src/Shell.tsx`: 81.5%
- Overall scoped coverage: 40.38%
- Gate assessment: PASS for diff-scoped review. The changed paths in `useEventSource.ts`, `useBoard.ts`, and `Shell.tsx` are directly exercised by the task suites and adjacent durable suites. Lower untouched-module percentages are informational only.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | `useEventSource_1263.test.ts:77`, `useEventSource_1263.test.ts:127`, `useEventSource_1260.test.ts:168` | Yes - listener registration, same-content rerender stability, and legacy default `tasks-changed` behavior are all exercised discriminatingly | COVERED |
| AC2 | `useEventSource_1263.test.ts:195`, `useEventSource_1263.test.ts:239` | Yes - the reverse-order case fails a last-write-wins mutation and proves cross-type max aggregation | COVERED |
| AC3 | `useBoard_1263.test.ts:123`, `useBoard_1263.test.ts:168`, `useBoard_1263.test.ts:195`, `useBoard_1261.test.ts:205`, `useBoard_1261.test.ts:273` | Yes - decisions subscription, task-event refetch, decisions isolation, and per-type independence are all exercised | COVERED |
| AC4 | `Shell_1263.test.tsx:126`, `Shell_1263.test.tsx:167`, `Shell_1263.test.tsx:194` | Yes - null-initial no-op, identity churn with unchanged mtime, and stale-vs-new callback refresh are all proven | COVERED |
| AC5 | `Shell_1263.test.tsx:231`, `usePendingDRs_1263.test.ts:49`, `usePendingDRs_1263.test.ts:62`, `usePendingDRs_1263.test.ts:75` | Yes - Shell proves no override is passed, and the direct hook tests prove default 60s polling remains live and repeating | COVERED |
| AC6 | `useEventSource_1260.test.ts:111` plus green durable suite execution | Yes - the exact-shape assertion now includes `lastEventByType` additively and the durable suite still passes | COVERED |

#### Security Review
- PASS. No new boundary, injection, path, secret, or dependency risk in the reviewed frontend code.

#### Test Integrity
- PASS with small deduction. The visible durable-suite change in `useEventSource_1260.test.ts:111` is additive, the current task body records source edits separately from later test-writer retries, and commit-log evidence aligns with that history. Direct commit diff inspection was unavailable, so immutability confidence is slightly reduced.

#### Test Quality
- PASS. The strongest discriminators are `useEventSource_1263.test.ts:239` for max-vs-last-write-wins and `Shell_1263.test.tsx:194` for latest-callback refresh after identity swap.
- Informational only: `usePendingDRs_1263.test.ts:75` uses lower-bounded call counts for repeated polling, so it would not catch a duplicate-timer regression. That is outside the touched scheduler logic in this task and does not block the AC proof here.

#### Data Safety
- PASS. `useEventSource.ts:120-136` guards stale sources and malformed payloads, `usePendingDRs.ts:34-74` preserves the live polling contract, and `Shell.tsx:32,70,74-75` uses a ref-stabilized callback path without introducing stale-callback races.

#### Builder Loop Check
- PASS. This task previously failed review twice, but the loop-breaker architecture pass refined AC2 and AC4 in the task body and the new discriminating tests now satisfy those refined AC lines. No repeated identical builder retry or unresolved loop remains.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `useEventSource.ts:22,120-121,173` implements stabilized `eventTypes` and per-type listeners; `useEventSource_1263.test.ts:77,127` and `useEventSource_1260.test.ts:168` prove registration and no reconnect on same-content rerenders | `useEventSource_1263`, `useEventSource_1260` | PASS |
| AC2 | `useEventSource.ts:130-136,173` stores per-type mtimes and computes aggregate max; `useEventSource_1263.test.ts:195,239` proves both normal and reverse-order max behavior | `useEventSource_1263` | PASS |
| AC3 | `useBoard.ts:58,61,92,143` subscribes to both event types, refetches only from `tasks-changed`, and exposes `lastDecisionsMtime`; `useBoard_1263.test.ts:123,168,195` plus `useBoard_1261.test.ts:205,273` prove the wiring and isolation | `useBoard_1263`, `useBoard_1261` | PASS |
| AC4 | `Shell.tsx:32,70,74-75` updates and consumes the stable ref on `lastDecisionsMtime` changes; `Shell_1263.test.tsx:126,167,194` proves null guard, no extra call on identity churn, and new-callback refresh on later mtime change | `Shell_1263` | PASS |
| AC5 | `usePendingDRs.ts:4,34,40,74` retains the default 60s polling path; `Shell_1263.test.tsx:231` proves no override is passed, and `usePendingDRs_1263.test.ts:49,62,75` proves the 60s boundary and continued polling | `Shell_1263`, `usePendingDRs_1263` | PASS |
| AC6 | `useEventSource_1260.test.ts:111` contains the additive exact-shape update and the scoped durable run kept the existing suite green | `useEventSource_1260` | PASS |

### Deductions
- Minus 0.03: direct commit diff inspection was unavailable, so TestFromAC immutability relied on commit-log evidence plus current-file inspection.
- Minus 0.01: AC5 repeated-poll proof uses lower-bounded counts rather than exact single-timer cadence, which is a minor residual risk outside the touched logic.
- Confidence: 0.94

### Verdict
- PASS
- Advance to docs

### Reflection
- Loop-breaker passes are valid when the refined AC is written back into the task and the new tests prove that refined contract.
- Reverse-order scenarios are the cleanest discriminator for max-aggregation logic.
- Ref-stabilized callback tasks need proof of both halves: no spurious trigger on identity churn and refresh to the newest callback on the next real signal.
- Commit-log verification is useful when diff access is unavailable, but it should still cost a small confidence deduction.
[[2026-05-02]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are frontend TS hooks and Shell.tsx. No IN-scope prose doc references `useEventSource`, `useBoard`, `usePendingDRs`, or `lastDecisionsMtime`. `serve/cockpit/README.md` SSE mention (line 99) is backend-only. |
| 2 | Module docstrings | No | N/A | No Python modules changed — all TypeScript/TSX. |
| 3 | External attribution | No | N/A | Task used only internal codebase sources (Research section: "6 studied (all internal codebase)"). |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1263-wire-usependingdrs-sse-decisions.md` exists and is linked in task body `## Research`. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — match. Footer updated from `(092ecd1d)` to `(68c15f33)`. Commit: `8068f7f6`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. All changed files are new/modified frontend files. |

### Scope Classification
- Changed files: `serve/cockpit/web/src/hooks/useEventSource.ts`, `serve/cockpit/web/src/hooks/useBoard.ts`, `serve/cockpit/web/src/Shell.tsx`, plus test files in `serve/cockpit/web/src/__tests__/` — all OUT-scope source/test, except Item 5 (diagram describes-match via glob `serve/cockpit/web/src/**`).

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated (commit `8068f7f6`)

### Child Tasks Created
None.

### Scratch Files Cleaned
No `1263-*` scratch files found.
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — eventTypes param | `useEventSource.ts:10-11,22-26` content-compare stabilization; `useEventSource_1263.test.ts:77,127` + `useEventSource_1260.test.ts:168` prove registration and no reconnect | PASS |
| AC2 — lastEventByType return | `useEventSource.ts:130-137` stores per-type + `Math.max` aggregate; `useEventSource_1263.test.ts:195,239` including reverse-order discriminator | PASS |
| AC3 — useBoard decisions wiring | `useBoard.ts:57-62,92-95` dual subscription + type-specific refetch; `useBoard_1263.test.ts:123,168,195` prove isolation | PASS |
| AC4 — Shell refetchPendingDRs effect | `Shell.tsx:32,68-74` ref-stabilized pattern; `Shell_1263.test.tsx:126,167,194` proves both halves (identity churn + ref refresh) | PASS |
| AC5 — usePendingDRs unchanged | `usePendingDRs.ts:4,34`; `usePendingDRs_1263.test.ts:49,62,75` live 60s boundary + repeat proof | PASS |
| AC6 — type shape additive | `useEventSource_1260.test.ts:111` includes `lastEventByType` in exact-shape assertion; durable suite green | PASS |

### Test Results
- pytest (full): 3647 passed, 135 failed, 4 skipped — all failures in unrelated modules (decisions_1195, mcp-kanban, neutral-shared, etc.). Zero failures in task scope.
- vitest (full): 942 passed, 4 failed — failures in usePollingFetch_1227 (3) and ActivityTab_1156 (1). Zero failures in task scope. Task suites: 95 passed, 0 failed.
- ruff: 3 violations in unrelated files (copilot_auth.py, server.py, hello_world.py).
- eslint: 4 issues in unrelated files (usePolling.ts, KanbanBoard_933, Shell_1228).

### Commits Verified
- `d4e50069` — `feat: wire decisions SSE pending refetch (#1263, builder)`
- `4350ba76` — `test: strengthen AC5/AC6 proofs (#1263, test-writer retry)`
- `7a448077` — `test: add discriminating AC2/AC4 tests (#1263, test-writer)`
- `8068f7f6` — `docs: update cockpit diagram footer (#1263, doc-writer)`

### Architect Quality: 4/5
Initial AC was specific with exact param shapes, return types, and td annotations. Required one loop-breaker pass to add explicit discrimination requirements for AC2/AC4 test proofs. Post-refinement AC was clean and precise. Not a 5 because two review cycles were needed before AC was tight enough for discriminating tests.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 have specific file:line + test evidence) → -0.00
- Lint in task scope: none → -0.00
- AC quality ≤ 3: no (4/5) → -0.00
- Missing reviewer evidence: no (3 detailed passes) → -0.00
- Full-suite failures in task scope: none → -0.00
- Commit diff direct inspection unavailable: -0.01
- Extended pipeline (3 review cycles / loop-breaker): -0.01

### Confidence: 0.98
### Action: archive