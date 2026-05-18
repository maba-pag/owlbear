---
id: 1657
title: Fix CockpitProvider abort-test timing regression
status: in-progress
priority: important
created: 2026-05-18T13:52:14.874519+02:00
updated: 2026-05-18T14:23:55.082975+02:00
tags:
  - frontend
  - cockpit
  - test
parent:
depends_on: []
ac:
  - The test "aborts in-flight getTask fetch when selectedTaskId changes (task 
    switch)" in CockpitProvider.test.tsx passes when run via `npm test` in 
    `serve/cockpit/web/`
  - The test captures the AbortSignal from the first `getTask` mock call and 
    asserts `signal.aborted === true` after a second `select()` triggers (abort 
    contract preserved)
  - '`npm test` in `serve/cockpit/web/` exits 0 with zero failures'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Fix the failing test "aborts in-flight getTask fetch when selectedTaskId changes (task switch)" in `CockpitProvider.test.tsx` (~line 392).

## Problem

The implementation at `CockpitProvider.tsx:133` defers the new fetch with `setTimeout(..., 1)` on task switch. React Testing Library's `await act()` flushes the timer, causing the second fetch to fire and overwrite `capturedSignal` with the new (non-aborted) controller's signal. The assertion then checks the wrong signal.

## Fix approach

Update the test to capture the FIRST signal independently before the second `select()` call fires, so the assertion checks the correct signal regardless of whether the deferred fetch fires during `act()`. Alternative: use `vi.useFakeTimers()` to prevent the setTimeout from firing during the assertion window.

## Scope

- File: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx`
- Only the abort-on-task-switch test (~line 392-410)
- No implementation changes to `CockpitProvider.tsx`

[[2026-05-18T14:04:38+02:00]]


## Research Findings

See `.owlbear/research/cockpit-abort-test-timing.md`

**Root cause:** `act()` flushes the 1ms `setTimeout` at CockpitProvider.tsx:133, causing `mockGetTask` to fire again and overwrite `capturedSignal` with the new (non-aborted) controller's signal.

**Recommended fix (Option A):** Save the first signal reference before the second `select()` call:
```typescript
// After first select:
const firstSignal = capturedSignal
// Change assertion to:
expect(firstSignal?.aborted).toBe(true)
```

Minimal 1-line add + 1-line change. Confidence: 0.90. T1 — autonomous test fix.

[[2026-05-18T14:04:45+02:00]]
## Research

**Key findings:** `act()` flushes the 1ms deferred setTimeout, overwriting `capturedSignal` with the new controller's signal. The abort IS happening correctly — the test just reads the wrong reference.

**Recommendation:** Option A — save first signal ref before second `select()`. 1-line add + 1-line change. Confidence 0.90.

**Trade-off matrix:** See `.owlbear/research/cockpit-abort-test-timing.md` §3 — 3 options compared.

**Tier:** T1 — autonomous test fix. No architecture/security/capability changes.

**Follow-ups:** Task #1657 itself IS the follow-up — advances to backlog for builder pickup.

[[2026-05-18T14:23:21+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single test fix, one file |
| Interface clarity | PASS | Clear: capture signal ref before second select, assert aborted |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | PASS | Test file only, no implementation changes |
| TDD compliance | PASS | This IS a test fix; bundle `existing` |
| KISS/YAGNI | PASS | 1-line add + 1-line change |
| Premise challenge | PASS | Test is genuinely failing due to timer-flush timing |
| Pattern consistency | PASS | Signal snapshot before re-trigger is standard test pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend/cockpit/test only |

### Challenge Results
- Challenger: reconsider (0.67)
- Findings: AC-2 wording ambiguity ("FIRST controller" not a source-level identifier); evidence-chain concern about timer-flush mechanism; contract-coverage concern about second-fetch path
- Architect response: ACCEPTED AC-2 wording concern — tightened to "captures AbortSignal from the first getTask mock call and asserts signal.aborted === true". REBUTTED evidence-chain: act() flushing 1ms setTimeout is standard RTL behavior (no fake timers = real timers fire within async act boundary). REBUTTED contract-coverage: second-fetch verification is out-of-scope — separate tests at ~line 460 already cover call-count assertions.

### Proof-Bundle Validation
- Planner assignment: existing
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx` (the abort-on-switch test itself)
- Test-writer: SKIP (bundle `existing`)

### Design Diverge
- Trigger: skipped — single clear approach (Option A from research), no competing criteria

### Verdict: APPROVE
### Action Taken: Tightened AC-2 wording for mechanical verifiability; advanced to todo.

[[2026-05-18T14:23:55+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx` (the abort-on-switch test itself; currently failing — builder fixes it).
- Passing through to builder.
