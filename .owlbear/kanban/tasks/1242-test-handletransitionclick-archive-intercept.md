---
id: 1242
title: 'Test: handleTransitionClick archive intercept'
status: review
priority: needed
created: 2026-05-01T03:07:57.562942+00:00
updated: 2026-05-01T15:47:54.385690+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1265
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Clicking the `→ archived` transition in the context menu opens `ArchivalModal`; no `POST /api/tasks/{id}/move` fires immediately
- All other status transitions (e.g., `→ done`, `→ in-progress`) remain unaffected — they still fire the move request immediately
- `ArchivalModal` receives `taskId`, `taskStatus`, and `expectedUpdated` as props
- `expectedUpdated` equals `task.updated` frozen at context-menu-open time — not re-read from a polling-updated task reference after the menu opens

## In Scope

- `handleTransitionClick` conditional branch for `targetStatus === "archived"`
- Prop forwarding to `ArchivalModal`

## Out of Scope

- `ArchivalModal` internal behaviour (F2 task #1241)
- Backend archival flow

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F3
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx
- Classes: TestFromAC_HandleTransitionClickArchive
- Tests per category: happy 1 (AC1 modal opens), error 2 (AC1 no POST; AC2 POST+no-POST combined), boundary 3 (AC3 props: taskId, taskStatus, expectedUpdated), edge 1 (AC4 frozen expectedUpdated under polling)
- Total: 7 tests, all FAIL
- TypeScript: clean (tsc --noEmit passes)
- ESLint: clean

AC coverage:
| AC | Tests |
|---|---|
| Clicking → archived opens ArchivalModal, no POST fires | tests 1, 2 |
| Other transitions remain unaffected (regression guard) | test 3 (combined: archived→no POST, non-archived→POST, exactly 1 move call) |
| ArchivalModal receives taskId, taskStatus, expectedUpdated | tests 4, 5, 6 |
| expectedUpdated frozen at context-menu-open time | test 7 (fake timers, advances 3100ms to trigger one poll cycle, verifies FROZEN value not POLLED) |

Mock: vi.mock('../components/ArchivalModal', factory) — factory stub renders data-testid="archival-modal-stub" with data attributes for prop assertions. File does not yet exist; factory bypasses module resolution.

Commit: 805fd6f3
[[2026-05-01]]
## Builder Notes
- Implementation: added archived-transition intercept and ArchivalModal wiring in serve/cockpit/web/src/KanbanBoard.tsx.
- Behavior change: `targetStatus === "archived"` now opens `ArchivalModal` and skips immediate `POST /api/tasks/{id}/move`; non-archived transitions continue existing immediate POST path.
- Prop forwarding: `ArchivalModal` now receives `taskId`, `taskStatus`, and `expectedUpdated` captured from context-menu-open state.
- Tests: task suite `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx` passed (7/7).
- Regression check: durable suite `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` passed (35/35).
- Lint: clean on scoped files via quality-runner.
- Coverage: N/A for scoped frontend Vitest runs (not configured in this run).
- Commit: c6ad561b (`feat: intercept archived transition click (#1242, builder)`).

- problems_faced: start_work returned task details with `claimed:false` despite successful claim flow; proceeded with normal builder lifecycle since task remained in-progress and unblocked.
- workarounds_applied: enforced claim+verification flow via kanban tools and quality-runner evidence rather than relying on claimed flag display.
- patterns_discovered: freezing context-menu values in state is the safest way to satisfy polling-race ACs for transition handlers.
[[2026-05-01]]
## Review Evidence
### Source Scope
- Reviewed the declared F3 board-side scope in `serve/cockpit/web/src/KanbanBoard.tsx` plus the task-owned suite `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx` and durable regression suites `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` / `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- `handleTransitionClick` has one live call-site; usage tracing shows the archived click passes `contextMenu.taskStatus` and `contextMenu.taskUpdated` from menu-open state into the handler.

### Test Results
- quality-runner scoped run: 83 passed, 0 failed, 0 skipped.
- Suites: `ArchivalModal_1241.test.tsx` 41 passed, `KanbanBoard_1242.test.tsx` 7 passed, `KanbanBoard.test.tsx` 35 passed.

### Lint
- ESLint clean on `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`, and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.

### Diagnostics
- `get_errors` reported no TS/diagnostic errors in `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, or `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`.

### Coverage
- quality-runner coverage: `KanbanBoard.tsx` 80.4% statements / 70.37% branches / 79.56% lines.
- quality-runner coverage: `ArchivalModal.tsx` 93.68% statements / 88.33% branches / 93.68% lines.
- The rejection below is not a raw percentage gate; it is grounded in a specific brief-bound timing path that the current green suite does not prove.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC / Bound Contract | Mapped Test | Would Fail If Violated? | Verdict |
|---|---|---|---|
| Clicking `→ archived` opens `ArchivalModal` and does not POST immediately | `KanbanBoard_1242.test.tsx:163-187` | Yes; modal render + zero move calls are asserted directly | COVERED |
| Other status transitions still POST immediately | `KanbanBoard_1242.test.tsx:196-220` plus durable move-path checks in `KanbanBoard.test.tsx:611-682` | Yes; the non-archived branch still requires exactly one move POST | COVERED |
| `ArchivalModal` receives `taskId`, `taskStatus`, `expectedUpdated` props | `KanbanBoard_1242.test.tsx:226-262` | Partially; proves prop presence, but not the brief-bound timing split for `taskStatus` vs `expectedUpdated` | LAX |
| `expectedUpdated` is frozen at context-menu-open time | `KanbanBoard_1242.test.tsx:271-362` | Yes; polling updates are forced and the frozen value is asserted | COVERED |
| Brief F3 binding: `taskStatus` is `task.status` at intercept time while only `expectedUpdated` is frozen at context-menu-open time (`.owlbear/briefs/draft-archival-ux/brief.md:165-170`) | none; current suite asserts the opposite for `taskStatus` at `KanbanBoard_1242.test.tsx:240-249` | No; the current suite codifies menu-open timing for `taskStatus`, so the required intercept-time contract could be violated without failing tests | MISSING |

#### Security Review
- No security findings in scoped code. The change only routes same-origin UI state into existing local fetch paths.

#### Test Integrity
- No evidence that the builder weakened or removed existing `TestFromAC_*` assertions.
- However, the current `TestFromAC_HandleTransitionClickArchive` suite encodes the wrong timing contract for `taskStatus`, so the green suite is a false positive against the bound brief.

#### Test Quality
- FAIL: the task body is explicitly brief-grounded (`.owlbear/briefs/draft-archival-ux/brief.md` — F3), and the suite proves `taskStatus` at context-menu-open time (`KanbanBoard_1242.test.tsx:240-249`) even though the brief freezes only `expectedUpdated` (`brief.md:165-170`).
- FAIL: there is no polling-race proof for `taskStatus` freshness at archived-click/intercept time; the only race proof targets `expectedUpdated` (`KanbanBoard_1242.test.tsx:271-362`).

#### Data Safety
- No independent data-safety finding beyond the contract drift below.

#### Implementation-Aware Gap Analysis
- FAIL: the implementation snapshots `taskStatus` and `taskUpdated` together when the context menu opens (`serve/cockpit/web/src/KanbanBoard.tsx:90-93`), then passes that stale `contextMenu.taskStatus` into the archived intercept (`serve/cockpit/web/src/KanbanBoard.tsx:159-163`, `serve/cockpit/web/src/KanbanBoard.tsx:236-240`).
- FAIL: the bound F3 brief requires a split timing contract: `taskStatus` at intercept time, but `expectedUpdated` frozen at context-menu-open time (`.owlbear/briefs/draft-archival-ux/brief.md:165-170`).
- FAIL: this matters to live behavior because `ArchivalModal` gates the `completed` reason on `taskStatus === "done"` (`serve/cockpit/web/src/components/ArchivalModal.tsx:205`). A polled status change between menu-open and archived-click can therefore surface the wrong reason set.
- FAIL: the current task-owned suite would not catch that defect; it explicitly asserts menu-open timing for `taskStatus` (`serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx:240-249`) and only stress-tests `expectedUpdated` drift (`serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx:271-362`).

#### Necessity Check
- Not applicable; no new dependency or external integration was added.

#### Builder Process Quality
- CLEAN: one builder cycle, no retry loop evidence.

### AC Compliance Table
| AC Line / Bound Contract | Evidence | Mapped Test | Status |
|---|---|---|---|
| Clicking `→ archived` opens `ArchivalModal`; no immediate POST | `KanbanBoard.tsx:159-163`; tests `KanbanBoard_1242.test.tsx:163-187` | AC1 pair | PASS |
| Other transitions remain immediate POST path | `KanbanBoard.tsx:166-175`; tests `KanbanBoard_1242.test.tsx:196-220`, `KanbanBoard.test.tsx:611-682` | AC2 | PASS |
| `ArchivalModal` receives correct props | `KanbanBoard.tsx:159-163`, `:211-216`, `:236-240`; tests `KanbanBoard_1242.test.tsx:226-262` | AC3 | FAIL |
| `expectedUpdated` frozen at menu-open time | `KanbanBoard.tsx:93`, `:163`, `:240`; tests `KanbanBoard_1242.test.tsx:271-362` | AC4 | PASS |
| Brief F3 timing split: `taskStatus` at intercept time; `expectedUpdated` frozen at menu-open time | `brief.md:165-170` vs `KanbanBoard.tsx:90-93`, `:159-163`, `:236-240`; live consumer `ArchivalModal.tsx:205` | none; current suite asserts the opposite at `KanbanBoard_1242.test.tsx:240-249` | FAIL |

### Deductions
- `-0.10` implementation drifts from the bound F3 brief by freezing `taskStatus` at menu-open instead of sourcing it at archived-click/intercept time.
- `-0.08` task-owned tests codify the wrong `taskStatus` timing contract and miss the polling/status-freshness proof needed to expose the defect.
- `-0.02` direct commit diff was not available in the primary reviewer toolchain; source scope was verified from the task record plus live file inspection.

### Verdict
- FAIL, confidence 0.80.

### Required Follow-up
- Add task-owned failing proof that `taskStatus` is read at archived-click/intercept time while `expectedUpdated` remains frozen at context-menu-open time.
- Update the archived intercept in `KanbanBoard.tsx` so only `expectedUpdated` is frozen; `taskStatus` must come from the current task snapshot at click time.
- Preserve the existing `TestFromAC_*` assertions and replace the incorrect `taskStatus` timing expectation rather than weakening coverage elsewhere.

### Action
- Reject to `todo` because the current green suite misses a brief-bound behavior and therefore allows a real implementation defect to pass.
[[2026-05-01]]
## Test-Writer Notes
- Retry: added 1 new failing test for reviewer gap (Brief F3 `taskStatus` timing split).
- Test file: `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`
- Class: `TestFromAC_HandleTransitionClickArchive`
- Tests per category: happy 1, error 2, boundary 3, edge 2 (AC4 frozen expectedUpdated + new F3 timing split)
- Total: 8 tests — 7 pass (existing), 1 FAIL (new)
- ESLint: clean
- TypeScript: clean (no new TS errors detected)

New test: `taskStatus passed to ArchivalModal reflects task.status at archived-click time, not context-menu-open time`
- Simulates a polling cycle between menu-open (task.status='done') and archived-click (task.status='in-progress' after poll)
- Asserts `data-task-status='in-progress'` (live intercept time) — FAILS with current impl which returns 'done' (frozen menu-open)
- Also asserts `data-expected-updated=FROZEN_UPDATED` (frozen at menu-open) — still correct in both old and new impl
- Failure: `AssertionError: expected 'done' to be 'in-progress'` at line 473

AC coverage:
| AC | Tests |
|---|---|
| Clicking → archived opens ArchivalModal, no POST fires | tests 1, 2 |
| Other transitions remain unaffected (regression guard) | test 3 |
| ArchivalModal receives taskId, taskStatus, expectedUpdated | tests 4, 5, 6 |
| expectedUpdated frozen at context-menu-open time | test 7 |
| Brief F3: taskStatus at intercept time (not menu-open) | test 8 (NEW, FAIL) |
[[2026-05-01]]
## Builder Notes
- Implementation: updated archived transition click path in KanbanBoard to read `taskStatus` from current task snapshot at click/intercept time while keeping `expectedUpdated` from context-menu-open state.
- Files changed: serve/cockpit/web/src/KanbanBoard.tsx
- Tests: 43 passed, 0 failed, 0 skipped (`KanbanBoard_1242.test.tsx` + durable `KanbanBoard.test.tsx`).
- Lint: clean (eslint scoped to touched source/test files).
- Coverage: KanbanBoard.tsx 80.53% overall (stmt 80.53%, branch 70.28%, func 76.47%, line 79.78) from scoped quality-runner run.
- Evidence summary: previously failing test `taskStatus passed to ArchivalModal reflects task.status at archived-click time...` now passes; archived path keeps no immediate POST behavior and non-archived path still POSTs.
- Commit: 869d5d05 (`fix: use live status at archived click (#1242, builder)`).

- problems_faced: none during code change; one pre-existing failure reproduced and resolved.
- workarounds_applied: sourced click-time status via current tasks lookup at click call-site to preserve split timing contract with minimal diff.
- patterns_discovered: for polling-sensitive UI flows, freeze only OCC token fields (`updated`) and derive behavioral fields (`status`) from live state at action time.
[[2026-05-01]]
## Review Evidence
### Source Scope
- Builder commit `869d5d05` is present in `.git/logs/HEAD:1328`; direct commit diff was not available in the reviewer toolchain, so changed-file scope was reconstructed from the builder note and live code inspection.
- Reviewed `serve/cockpit/web/src/KanbanBoard.tsx` plus the task-owned and adjacent durable suites: `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`, and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- `handleTransitionClick` has one live call-site in `KanbanBoard.tsx` (`:155`, `:236-240`), so the behavior change is localized to the context-menu transition path.

### Test Results
- quality-runner scoped run: 89 passed, 0 failed, 0 skipped.
- Suites: `KanbanBoard_1242.test.tsx` 8 passed, `KanbanBoard.test.tsx` 60 passed, `ArchivalModal_1241.test.tsx` 21 passed.

### Lint
- ESLint clean on `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`, and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.

### Diagnostics
- `get_errors` reported no TS/diagnostic errors in `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`, and `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`.

### Coverage
- quality-runner did not provide usable TSX coverage detail for this expanded frontend-only run. Gate evidence is the independent Vitest/ESLint pass plus direct AC proof below.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line / Bound Contract | Mapped Test | Would Fail If Violated? | Verdict |
|---|---|---|---|
| Clicking the archived transition opens `ArchivalModal` and does not fire an immediate move request | `KanbanBoard_1242.test.tsx:163`, `:175`, exact zero-move assertion at `:187` | Yes | COVERED |
| Other status transitions still fire the move request immediately | `KanbanBoard_1242.test.tsx:196`, exact one-call assertion at `:219-220` | Yes | COVERED |
| `ArchivalModal` receives `taskId`, `taskStatus`, and `expectedUpdated` props | `KanbanBoard_1242.test.tsx:226`, `:240`, `:253`, plus split-timing proof at `:378`, `:473`, `:475` | Yes | COVERED |
| `expectedUpdated` stays frozen from context-menu-open time | `KanbanBoard_1242.test.tsx:271`, exact frozen assertion at `:362`; reinforced again at `:475` | Yes | COVERED |
| Brief F3 binding: `taskStatus` comes from intercept time while `expectedUpdated` stays frozen from context-menu-open time | `KanbanBoard_1242.test.tsx:378`, exact live-status assertion at `:473`, exact frozen-updated assertion at `:475` | Yes | COVERED |

#### Security Review
- No security findings in scoped code. The change only forwards local UI state into the existing same-origin task move flow.

#### Test Integrity
- No evidence that the builder weakened or removed `TestFromAC_*` assertions.
- The retry adds the missing timing-split proof at `KanbanBoard_1242.test.tsx:378-475`; the suite now discriminates live `taskStatus` from frozen `expectedUpdated`.

#### Test Quality
- PASS: assertions are exact-value checks, not presence checks. The suite verifies zero versus one move calls, exact target URL, exact prop values, and the polling race with fake timers.
- PASS: adjacent consumer behavior remains covered. `ArchivalModal` still filters the `completed` reason by `taskStatus` in `ArchivalModal.tsx:205`, and the durable modal suite proves both hidden and visible branches at `ArchivalModal_1241.test.tsx:155` and `:164`.

#### Data Safety
- No data-safety finding. The implementation keeps the OCC token (`expectedUpdated`) frozen from menu-open time while sourcing behavioral state (`taskStatus`) from the live snapshot at click time.

#### Implementation-Aware Gap Analysis
- `KanbanBoard.tsx:90-93` still captures the menu-open snapshot, which is the correct source for `expectedUpdated`.
- The archived click path now passes live status from `tasks.find((task) => task.id === contextMenu.taskId)?.status ?? contextMenu.taskStatus` at `KanbanBoard.tsx:239` while preserving frozen `contextMenu.taskUpdated` at `KanbanBoard.tsx:240`; `handleTransitionClick` then forwards those values into `setArchivalModal` at `KanbanBoard.tsx:160-163`.
- That matches the bound brief contract in `.owlbear/briefs/draft-archival-ux/brief.md:169-170` and the modal consumer logic that uses `taskStatus` for the completed filter and `expectedUpdated` in the archival POST payload at `ArchivalModal.tsx:157-159` and `:205`.
- No untested significant path remains inside task scope.

#### Necessity Check
- Not applicable; no new dependency, integration, or external tool was introduced.

#### Builder Process Quality
- CLEAN: one prior review failure, then one builder retry with a changed approach that directly addressed the missing live-status proof. No loop behavior.

### AC Compliance Table
| AC Line / Bound Contract | Evidence | Mapped Test | Status |
|---|---|---|---|
| Clicking the archived transition opens `ArchivalModal`; no immediate move request fires | `KanbanBoard.tsx:159-163`; `KanbanBoard_1242.test.tsx:163-187` | AC1 pair | PASS |
| Other transitions remain immediate move requests | `KanbanBoard.tsx:166-172`; `KanbanBoard_1242.test.tsx:196-220`; durable board suite also green in the scoped run | AC2 | PASS |
| `ArchivalModal` receives correct props | `KanbanBoard.tsx:160-163`, `:239-240`; `KanbanBoard_1242.test.tsx:226-262`, `:378-475` | AC3 | PASS |
| `expectedUpdated` is frozen at context-menu-open time | `KanbanBoard.tsx:90-93`, `:240`; `KanbanBoard_1242.test.tsx:271-362` | AC4 | PASS |
| Brief F3 timing split: live `taskStatus`, frozen `expectedUpdated` | `.owlbear/briefs/draft-archival-ux/brief.md:169-170`; `KanbanBoard.tsx:239-240`; `ArchivalModal.tsx:157-159`, `:205`; `KanbanBoard_1242.test.tsx:378-475` | brief-bound retry proof | PASS |

### Deductions
- `-0.03` TSX coverage detail was unavailable in the expanded quality-runner report, so confidence rests on direct source and assertion proof instead of a coverage percentage.

### Verdict
- PASS, confidence 0.95.

### Required Follow-up
- None.

### Action
- Advance to docs.

### Reflection
- The adjacent `ArchivalModal` suite was necessary review evidence because the behavioral impact of stale versus live `taskStatus` appears in the completed-reason filter, not just in the board click handler.
- For polling-sensitive UI flows, the safe split is to freeze OCC tokens (`updated`) while deriving behavior-driving fields (`status`) from live state at action time.
- Frontend review confidence here comes from exact-value assertions plus clean diagnostics, not from TSX coverage percentages.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose doc references `handleTransitionClick`, `KanbanBoard.tsx`, or `ArchivalModal.tsx` by behavior |
| 2 | Module docstrings | No | N/A | No Python files modified |
| 3 | External attribution | No | N/A | No external patterns sourced |
| 4 | Research doc | No | N/A | No research doc produced or referenced |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index has no `describes` glob matching `serve/cockpit/web/**`; no diagram to update |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/KanbanBoard.tsx | OUT | Application source — no doc edit |
| serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx | OUT | Test file — no doc edit |
| serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx | OUT | Test file — no doc edit |
| serve/cockpit/web/src/components/ArchivalModal.tsx | OUT | Application source — no doc edit |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (.owlbear/scratch/1242-* — no files found)
[[2026-05-01]]
## Planning

Created single follow-up task:

| ID | Title | Status | Parent | Tags |
|----|-------|--------|--------|------|
| #1265 | Fix stale test fixture in KanbanBoard_1242.test.tsx after #1227 API change | backlog | #1238 | scope:frontend |

No TDD pair needed — this IS a test-fix task (the deliverable is passing tests).
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Clicking → archived opens ArchivalModal; no POST fires immediately | `KanbanBoard.tsx:157-163` — `targetStatus === 'archived'` sets archival modal state and returns before POST path | PASS (impl) |
| Other transitions remain unaffected — still fire move request immediately | `KanbanBoard.tsx:166-175` — non-archived path calls fetch POST; durable suite `KanbanBoard.test.tsx` 35/35 green | PASS (impl) |
| ArchivalModal receives taskId, taskStatus, expectedUpdated as props | `KanbanBoard.tsx:208-214` — conditional render passes all three props from `archivalModal` state | PASS (impl) |
| expectedUpdated equals task.updated frozen at context-menu-open time | `KanbanBoard.tsx:238` passes `contextMenu.taskUpdated` (frozen at menu-open via `:90-93`) | PASS (impl) |
| Brief F3 split timing: taskStatus live at intercept, expectedUpdated frozen | `KanbanBoard.tsx:237` uses `tasks.find(...)?.status ?? contextMenu.taskStatus` (live); `:238` uses `contextMenu.taskUpdated` (frozen) | PASS (impl) |

**Note:** All AC lines verified via code inspection only. Task-scoped test evidence unavailable — see test results below.

### Test Results
- vitest (task-scoped `KanbanBoard_1242.test.tsx`): **8 failed, 0 passed** — all tests stuck at "Loading…" because `renderBoard()` renders `<KanbanBoard />` with no props; #1227 (`6452345f`) changed the component to accept props, breaking the old internal-fetch pattern.
- vitest (durable `KanbanBoard.test.tsx`): 35 passed, 0 failed.
- pytest (full suite): 3420 passed, 104 failed, 4 skipped — no failures in task scope.
- ruff: 4 errors — none in task-scoped files.
- ESLint: 1 error in `usePolling.ts`, 4 warnings — none in task-scoped files.

### Uncommitted Deliverable
Test-writer retry added an 8th test (brief F3 timing-split proof, lines 367-480) but never committed it. Only the original 7-test commit (`805fd6f3`) exists.

### Architect Quality: 3/5
Original AC omitted the split-timing contract between `taskStatus` (live at intercept) and `expectedUpdated` (frozen at menu-open). Required a full reject-retry cycle to surface.

### Deduction Breakdown
- −0.05: Task-scoped test suite fails 8/8 (cross-task regression from #1227 API change)
- −0.03: AC quality ≤ 3

### Confidence: 0.92
### Action: reject-to-backlog

### Required Follow-up
- Follow-up #1265 created: fix stale test fixture and commit missing 8th test.

### Process Concern
`start_work` on a `done`-status task unexpectedly archived it (moved file to archive/, set status to archived). Manual restoration was required.
[[2026-05-01]]

## Architecture Review (re-review after audit reject)

### Context

Auditor rejected to backlog (confidence 0.92) citing:
1. Task-scoped tests fail 8/8 — cross-task regression from #1227 (internal-fetch → prop-based)
2. Architect quality 3/5 — original AC missed the brief F3 split-timing contract
3. Created follow-up #1265 to fix stale test fixtures

Implementation is committed and code-correct (builder commit 869d5d05, reviewer PASS 0.95).
The only remaining gap is test fixture staleness, addressed by #1265.

### AC Refinement

Refined AC with timing-split requirement (AC5) and test-depth annotations:

1. Clicking `→ archived` opens `ArchivalModal`; no `POST /api/tasks/{id}/move` fires immediately (td:1)
2. Other status transitions remain unaffected — still fire the move request immediately (td:1)
3. `ArchivalModal` receives `taskId`, `taskStatus`, and `expectedUpdated` as props (td:1)
4. `expectedUpdated` equals `task.updated` frozen at context-menu-open time (td:2)
5. `taskStatus` reflects live `task.status` at archived-click/intercept time, not context-menu-open time — per brief F3 split timing contract `.owlbear/briefs/draft-archival-ux/brief.md:169-170` (td:2)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: archived transition intercept in KanbanBoard |
| Interface clarity | PASS | AC specifies exact prop sources and timing contracts |
| Dependency correctness | PASS | Added `depends_on: [1265]` — test fixture fix must complete first |
| Module layering | PASS | KanbanBoard → ArchivalModal (parent→child); verified import at KanbanBoard.tsx:9 |
| TDD compliance | PASS | Test file exists with 8 tests covering all 5 AC lines; #1265 fixes stale fixtures |
| KISS/YAGNI | PASS | Minimal scope: one conditional branch + prop forwarding |
| Premise challenge | PASS | Brief F3 requires this intercept; no existing capability covers it |
| Pattern consistency | PASS | Follows existing context-menu → handler → modal pattern in KanbanBoard |
| Security surface | N/A | Same-origin UI state routing only |
| Single domain | PASS | Frontend only (scope:frontend tag) |

### Dependency Analysis

- `depends_on: [1265]` — #1265 fixes stale test fixtures in KanbanBoard_1242.test.tsx
- Parent: #1238 (closeout, depends on #1246 which depends on #1242)
- Downstream: #1246 (implement F3 intercept) depends on #1242

### Challenge Results

- Challenger: `block` (0.34) — core argument: task-owned proof is currently broken
- Architect response: rebutted. The dependency on #1265 gates pipeline re-entry until
  tests are fixed. Challenger's concern about current evidence state is valid but
  addressed by the gating mechanism, not by holding the task indefinitely in backlog.
  Menu staleness blind spot is out of F3 scope. Stale test comments are cosmetic
  cleanup for #1265.

### Test Depth

- Max depth: td:2 (AC4, AC5 — polling race proofs)
- Test-writer: PROCEED (existing tests cover all AC lines; test-writer should verify
  post-#1265 fixture updates and pass through if green)

### Verdict: APPROVE
### Action Taken: Added AC5 (timing-split), td annotations, depends_on #1265. Task will
re-enter pipeline after #1265 fixes test fixtures. Implementation is committed (869d5d05);
pipeline agents should verify green tests and pass through existing work.
[[2026-05-01]]
Re-review after audit reject. Refined AC: added AC5 (taskStatus live at intercept time per brief F3 split timing), td annotations on all 5 AC lines. Added depends_on #1265 (test fixture fix). Implementation committed (869d5d05), reviewer PASS 0.95 — pipeline re-entry gated on #1265 completion. Challenger block (0.34) rebutted: broken proof concern addressed by dependency gate.
[[2026-05-01]]
## Test-Writer Notes
- Retry: verified post-#1265 fixture updates — all 8 tests GREEN against current implementation.
- Builder skip: test-only retry; implementation committed (869d5d05, 805fd6f3), all tests pass.
- Test file: serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx
- Classes: TestFromAC_HandleTransitionClickArchive
- Tests: 8/8 PASS (prop-based fixtures confirmed working after #1265 fix)
- ESLint: clean
- AC coverage: AC1–AC5 (incl. Brief F3 timing-split proof at test 8) all covered and green

[[2026-05-01]]
## Builder Notes
- Implementation: no new code changes in this builder run; existing committed implementation already present for AC1-AC5.
- Files changed: none.
- Tests: 89 passed, 0 failed, 0 skipped across scoped frontend suites (`KanbanBoard_1242.test.tsx`, `KanbanBoard.test.tsx`, `ArchivalModal_1241.test.tsx`).
- Lint/diagnostics: quality-runner ruff is not applicable to TSX paths; VS Code diagnostics report no errors in `KanbanBoard.tsx`, `ArchivalModal.tsx`, or `KanbanBoard_1242.test.tsx`.
- Coverage: TSX percentage detail not emitted by quality-runner in this run; test gate evidence is full scoped green suite.
- Evidence summary: task-scoped retry proof is green in current snapshot, including the F3 timing split behavior (`taskStatus` live at intercept time, `expectedUpdated` frozen at context-menu-open time).

- problems_faced: quality-runner lint stage is Python/ruff-only and reports expected parse errors on TSX paths.
- workarounds_applied: relied on scoped Vitest pass + VS Code diagnostics for frontend safety evidence.
- patterns_discovered: when a builder task re-enters after test-only retries and implementation is already committed, a no-op builder verification pass is sufficient before advancing.
