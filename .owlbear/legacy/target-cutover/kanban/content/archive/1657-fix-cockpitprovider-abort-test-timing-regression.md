---
id: 1657
title: Fix CockpitProvider abort-test timing regression
status: archived
priority: medium
created: 2026-05-18T13:52:14.874519+02:00
updated: 2026-05-18T15:23:15.284708+02:00
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
archival_reason: completed
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

[[2026-05-18T14:50:25+02:00]]
## Builder Notes
- Files changed: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx`
- Fix applied: stabilized abort-on-task-switch assertion by snapshotting the first `AbortSignal` before the second `select()` call, then asserting `firstSignal.aborted === true`.
- Why: avoids timing flake where async `act()` can flush the deferred fetch and overwrite the shared `capturedSignal` reference.

### Quality Evidence
- Proof bundle: `existing`
- Required existing proof file: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx`
- quality-runner scoped (proof file): 53 passed, 0 failed, 0 skipped; lint clean; vitest exit 0, eslint exit 0.
- quality-runner full frontend domain (`mode=full`): 2134 passed, 0 failed, 11 skipped; lint clean; vitest exit 0, eslint exit 0.
- Coverage: not requested/provided by quality-runner for this `existing` proof task.

### AC Mapping
1. Abort-on-switch test passes: verified in scoped proof run.
2. Test now captures first call signal and asserts abort on that signal: implemented.
3. `npm test` equivalent frontend verification exits 0 with zero failures: verified via quality-runner full run (0 failed).

### Commit
- `7f482bc7` — `test: stabilize CockpitProvider abort switch assertion (#1657, builder)`

[[2026-05-18T14:55:58+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1657 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | No implementation change was required for this existing-proof task; builder provided scoped proof evidence for `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx` and full frontend verification with zero failures. | Builder Notes report `quality-runner scoped`: 53 passed, 0 failed, 0 skipped; `quality-runner full frontend`: 2134 passed, 0 failed, 11 skipped; vitest exit 0. | PASS |
| 2 | `serve/cockpit/web/src/hooks/CockpitProvider.tsx:92-95` aborts the active controller before the replacement fetch path, and `serve/cockpit/web/src/hooks/CockpitProvider.tsx:133-136` defers the switched-task fetch. `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx:392-411` now snapshots `firstSignal` after `select(42)` and asserts `firstSignal.aborted === true` after `select(99)`. | The existing proof test `aborts in-flight getTask fetch when selectedTaskId changes (task switch)` would now fail if the first request signal were not created or not aborted on task switch. | PASS |
| 3 | No implementation change was required for this AC. | Builder Notes report full frontend verification equivalent to `npm test` in `serve/cockpit/web/`: 2134 passed, 0 failed, 11 skipped; vitest exit 0. | PASS |
- Safety/security: not a security-sensitive surface; no new dependency, credential, storage, or input-handling risk introduced.
- Blocking findings: none.

## Observations
- Builder evidence met the `existing` proof-bundle bar, so an independent quality-runner rerun was not cost-justified.
- The updated test removes the mutable shared-reference false-negative without weakening the abort contract: it now proves the first request's signal is the one that becomes aborted on task switch.

[[2026-05-18T15:03:18+02:00]]
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A — no docs impact | Only changed file: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx`. `serve/cockpit/README.md` covers CLI commands, stack table, and feature surface — none document test-internal assertion behavior. Zero docs drift. |
| 2. External Attribution | N/A | Research applied standard RTL timer-flush knowledge; no external source citations added. |
| 3. Research Doc | PASS | `.owlbear/research/cockpit-abort-test-timing.md` linked from task body. |
| 4. Deletion Detection | N/A | No files deleted. |

### Files Updated
None — no documentation required by a single test-assertion stabilization.

### Scratch Cleanup
No `1657-*` scratch files found — clean.

[[2026-05-18T15:23:15+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 6955 passed; failures all in unrelated domains (test_cockpit_view.py structural assertions from #1067/#1068/#1071/#1132, test_server.py StatusNamesDictFormBug, test_engine_accessor_migration.py SubmodelAccessPaths, Shell.scan-health/DetailTab.conflict-resolution waitFor timeouts). None in CockpitProvider tests or the changed file's domain. Builder evidence confirmed: scoped 53/0/0, full frontend 2134/0/11. No task-caused regressions.

### Intent Verification
Changed file: `serve/cockpit/web/src/__tests__/CockpitProvider.test.tsx` — cockpit frontend test domain. Task purpose: fix timing regression in abort-on-task-switch test. Commit scope: 1 file, net +1 line. No extraneous scope. PASS.

### Architect Quality
AC-1 names exact test title, AC-2 specifies signal capture mechanism and assertion, AC-3 specifies full suite exit 0. Research doc provided trade-off matrix. Minimal scope, clear path.
Score: 5/5.

### Commit Integrity
Builder commit `7f482bc7` — `test: stabilize CockpitProvider abort switch assertion (#1657, builder)`. Format correct, scope matches task (1 file). Present in HEAD. PASS.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
