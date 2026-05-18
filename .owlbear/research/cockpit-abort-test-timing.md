# CockpitProvider Abort-Test Timing Regression

> **Owning task:** #1657 — Fix CockpitProvider abort-test timing regression
> **Date:** 2026-05-18 **Status:** Complete

## 1. Context and Question

The test "aborts in-flight getTask fetch when selectedTaskId changes (task switch)" in `CockpitProvider.test.tsx` fails because React Testing Library's `act()` flushes the 1ms `setTimeout` used to defer the new fetch on task switch. This causes `mockGetTask` to fire a second time, overwriting `capturedSignal` with the new (non-aborted) controller's signal.

**Question:** What is the minimal, correct test fix that preserves the abort-contract verification without modifying `CockpitProvider.tsx`?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | [Testing Library — Using Fake Timers](https://testing-library.com/docs/using-fake-timers/) | 0.9 — Official docs confirming fake timers prevent uncontrolled timer flushing |
| 2 | [Vitest issue #3088 — fake timers and AbortSignal.timeout](https://github.com/vitest-dev/vitest/issues/3088) | 0.6 — Confirms `vi.useFakeTimers()` does NOT mock AbortSignal.timeout but DOES mock setTimeout |
| 3 | Codebase: 20+ existing `vi.useFakeTimers()` uses in `serve/cockpit/web/src/__tests__/` | 0.9 — Established pattern in this project |
| 4 | `CockpitProvider.tsx:133` — `setTimeout(() => { void runFetch() }, 1)` | 1.0 — Direct source of the timing issue |

## 3. Analysis

| Option | Approach | Pros | Cons | Confidence |
|--------|----------|------|------|-----------|
| A — Save first signal | `const firstSignal = capturedSignal` before second `select()`, assert on `firstSignal` | 1-line change, KISS, no timer setup | Deferred fetch still fires (benign, but less explicit) | 0.90 |
| B — Fake timers | `vi.useFakeTimers()` prevents setTimeout from firing during assertion | Explicit control, proven pattern (20+ precedents) | More setup/teardown, must not advance timers | 0.85 |
| C — Signal array | Capture all signals in `signals[]`, assert `signals[0].aborted` | Can assert on specific calls | More verbose, same underlying logic as A | 0.75 |

**Key insight:** The `abort()` call happens synchronously in the React effect cleanup (line 97: `activeTaskControllerRef.current?.abort()`), BEFORE the deferred setTimeout fires. The signal IS aborted correctly — the test just reads the wrong reference after `act()` flushes the timer.

## 4. Recommendation

**Option A — Save first signal reference.** Confidence: 0.90.

```typescript
// After first select:
const firstSignal = capturedSignal
// After second select, assert:
expect(firstSignal?.aborted).toBe(true)
```

This is the minimal fix (1 line added, 1 line changed). It directly addresses the root cause: the test was reading a stale reference after it was overwritten. The abort contract verification is preserved — we still verify that the FIRST controller's signal is aborted after a task switch.

Option B (fake timers) is acceptable but over-engineered for this case — it prevents the deferred fetch entirely rather than just fixing the reference capture. If the implementation's setTimeout delay changes (e.g., removed), Option A still passes correctly while Option B would need updating.

Challenge: FALLBACK — trivial test fix, no architecture decisions.

## 5. Follow-up Tasks

Single task needed: implement the fix in the test file. Task already exists at #1657 — advance to `todo` status for builder pickup.
