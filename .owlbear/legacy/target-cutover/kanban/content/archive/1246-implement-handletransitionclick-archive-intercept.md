---
id: 1246
title: 'Implement: handleTransitionClick archive intercept'
status: archived
priority: medium
created: 2026-05-01T03:08:09.832815+00:00
updated: 2026-05-02T04:20:46.797546+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1242
- 1245
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `handleTransitionClick` opens `ArchivalModal` instead of immediately posting when `targetStatus === "archived"`
- Props passed to `ArchivalModal`: `taskId`, `taskStatus` (from `task.status`), `expectedUpdated` (from `task.updated` frozen at context-menu-open time)
- `expectedUpdated` is not re-read from a polling-updated task reference while the modal is open
- Non-archival transitions are unchanged
- All tests from #1242 pass

## In Scope

- `KanbanBoard.tsx`: `handleTransitionClick` function and modal open/close state

## Out of Scope

- `ArchivalModal` internals (already done by #1245)
- Backend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F3
[[2026-05-02]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/KanbanBoard_1246.test.tsx`
- Classes: `TestFromAC_ArchiveIntercept`, `TestFromAC_ModalLifecycle`
- Tests per category: happy 5, edge 2, regression 2, lifecycle 1
- Total: 10 tests

**⚠️ Anomaly: implementation pre-done — all 10 tests PASS (not fail)**

`KanbanBoard.tsx` already contains the complete F3 implementation:
- `handleTransitionClick` has the `if (targetStatus === 'archived')` branch
- `setArchivalModal({ taskId, taskStatus, expectedUpdated: updated })` wired correctly
- `ArchivalModal` rendered with `onClose={() => setArchivalModal(null)}` and `onRefresh={refetchTasks}`
- `taskStatus` reads live from `tasks.find(...)?.status` at click time (not frozen context-menu snapshot)

All 8 tests from #1242 also pass (verified separately).

**Tests written cover 5 AC items:**
| AC line | tests |
|---------|-------|
| archived click opens modal, no POST | 2 (TestFromAC_ArchiveIntercept tests 1-2) |
| context menu dismissed | 1 (test 3) |
| non-archived transition POST unchanged | 1 (test 4) |
| props: taskId, taskStatus, expectedUpdated | 3 (tests 5-7) |
| expectedUpdated frozen at menu-open | 1 (test 8) |
| onClose dismisses modal | 1 (TestFromAC_ModalLifecycle test 1) |
| onRefresh calls refetchTasks | 1 (TestFromAC_ModalLifecycle test 2) |

The onClose/onRefresh callback-wiring tests (TestFromAC_ModalLifecycle) are NOT in #1242 — they add genuine regression coverage for the modal lifecycle.

**Builder action: no code changes needed.** Verify tests pass and advance to review.
[[2026-05-02]]
## Builder Notes
- Implementation: no code changes were required; AC behavior already present in `serve/cockpit/web/src/KanbanBoard.tsx`.
- Tests: 18 passed (10 from `KanbanBoard_1246.test.tsx`, 8 from `KanbanBoard_1242.test.tsx`), 0 failed.
- Coverage: task-scoped vitest coverage run completed; `src/KanbanBoard.tsx` reported 72.72% statements (informational; no touched module in this builder pass).
- Lint: clean (0 errors, 0 warnings) on scoped files.
- Approach: validated pre-implemented archival intercept behavior and modal lifecycle wiring against TestFromAC expectations, then advanced without modifications.

## Post-task Reflection
- Initial quality-runner invocation hit the known Vitest hang pattern in this environment; adjusted invocation strategy resolved it.
- For frontend scoped runs, explicit single-run execution plus coverage flag produced stable execution in this workspace state.
- Pre-implemented builder tasks should still run scoped quality evidence before pass-through to avoid false-green routing.
- No blocking edge cases surfaced beyond existing TestFromAC coverage for this AC.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped run: 18 passed, 0 failed, 0 skipped
- `serve/cockpit/web/src/__tests__/KanbanBoard_1246.test.tsx`: 10 passed
- `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`: 8 passed

### Lint
- ESLint: clean on `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard_1246.test.tsx`, and `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx`
- VS Code diagnostics: 0 errors in the same three files

### Coverage
- `serve/cockpit/web/src/KanbanBoard.tsx`: 72.72% statements, 66.92% branches, 68.75% functions, 75.82% lines
- Module-level coverage is informational only on this pass-through review: builder notes report no code changes, so the diff-scoped 90% gate is not applicable to changed lines in this builder pass

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| `handleTransitionClick` opens `ArchivalModal` instead of immediately posting when `targetStatus === "archived"` | `KanbanBoard_1246.test.tsx` lines 164, 176; `KanbanBoard_1242.test.tsx` lines 169, 181 | Yes - modal render and zero-POST assertions fail if archived path posts immediately or skips modal | COVERED |
| Props passed to `ArchivalModal`: `taskId`, `taskStatus` (from `task.status`), `expectedUpdated` (from `task.updated` frozen at context-menu-open time) | `KanbanBoard_1246.test.tsx` lines 222, 235, 248, 263; `KanbanBoard_1242.test.tsx` lines 277, 366 | Yes - exact data-attribute assertions fail if any prop source or timing changes | COVERED |
| `expectedUpdated` is not re-read from a polling-updated task reference while the modal is open | `KanbanBoard_1246.test.tsx` line 263; `KanbanBoard_1242.test.tsx` line 277 | Yes - rerender with a POLLED timestamp then assert exact FROZEN value | COVERED |
| Non-archival transitions are unchanged | `KanbanBoard_1246.test.tsx` line 204; `KanbanBoard_1242.test.tsx` line 202 | Yes - tests require exactly one `/move` POST for the non-archived transition and zero archival POSTs in the same session | COVERED |
| All tests from #1242 pass | quality-runner report for `KanbanBoard_1242.test.tsx` | Yes - any regression in the inherited suite would flip the run red | COVERED |

#### Security Review
- No issues in current scope. The reviewed code in `serve/cockpit/web/src/KanbanBoard.tsx` only routes task data into internal `fetch` calls to `/api/tasks/{id}/move`; no eval, shell execution, path handling, new dependency, or secret surface was introduced.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in the live files. Current assertions are discriminating: exact prop equality, explicit zero-POST checks, and exact modal lifecycle effects.
- Limitation: no builder commit hash or diff was present in the task body, so TestFromAC immutability could not be proven directly against a builder diff. Applied a small confidence deduction only.

#### Test Quality
- Assertion specificity: STRONG
- Negative/error-path coverage for AC-relevant behavior: STRONG
- Manual mutation resistance: STRONG
- Test independence: STRONG
- Test naming clarity: STRONG
- No WEAK dimensions found

#### Data Safety
- No AC-relevant data safety issues found in reviewed scope

#### Implementation-Aware Test Gaps
- No significant AC-relevant gaps found. The critical timing split is exercised: `taskStatus` is read from the live task snapshot at click time, while `expectedUpdated` remains frozen from the context-menu snapshot.

#### Necessity Check
- N/A - no new dependency, integration, or external capability added in this task

#### Builder Process Quality
- CLEAN - one builder section, no retry loop pattern, no evidence of repeated identical attempts

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `handleTransitionClick` opens `ArchivalModal` instead of immediately posting when `targetStatus === "archived"` | `serve/cockpit/web/src/KanbanBoard.tsx` lines 153-163 branch to `setArchivalModal(...)` and `return` before any POST | `KanbanBoard_1246.test.tsx` lines 164, 176; `KanbanBoard_1242.test.tsx` lines 169, 181 | PASS |
| Props passed to `ArchivalModal`: `taskId`, `taskStatus`, `expectedUpdated` | `serve/cockpit/web/src/KanbanBoard.tsx` lines 158-161 store modal state, lines 210-216 pass props to `ArchivalModal`, line 237 reads live `task.status` at click time | `KanbanBoard_1246.test.tsx` lines 222, 235, 248; `KanbanBoard_1242.test.tsx` line 366 | PASS |
| `expectedUpdated` is not re-read from a polling-updated task reference while the modal is open | `serve/cockpit/web/src/KanbanBoard.tsx` line 237 passes `contextMenu.taskUpdated`, not a refreshed `task.updated` lookup | `KanbanBoard_1246.test.tsx` line 263; `KanbanBoard_1242.test.tsx` line 277 | PASS |
| Non-archival transitions are unchanged | `serve/cockpit/web/src/KanbanBoard.tsx` lines 165-177 retain the existing POST `/move` path for non-archived targets | `KanbanBoard_1246.test.tsx` line 204; `KanbanBoard_1242.test.tsx` line 202 | PASS |
| All tests from #1242 pass | quality-runner scoped result: `KanbanBoard_1242.test.tsx` 8 passed, 0 failed | quality-runner | PASS |

### Deductions
- -0.03 confidence: no builder commit hash or diff available, so test immutability was inferred from live files and task notes rather than proven from a builder diff

### Verdict
- PASS
- Confidence: 0.95

### Action
- Advance to `docs`
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|---------|
| 0a | Review Evidence section present | Yes | PASS | `## Review Evidence` found in task body with full AC coverage table and verdict |
| 1 | Descriptive prose docs | Yes (check) | N/A | `serve/cockpit/README.md` documents backend API only; the archival reference on line 31 (valid_transitions bypass) is unchanged by this task. Root README.md `## Cockpit` section covers only launch commands. No IN-scope prose doc describes `handleTransitionClick` or frontend modal intercept behavior. No update needed. |
| 2 | Module docstrings | No | N/A | No Python files changed |
| 3 | External attribution | No | N/A | No external patterns cited |
| 4 | Research doc | No | N/A | No research doc produced or referenced |
| 5 | Diagram maintenance | Yes | DONE | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches `KanbanBoard.tsx`. Footer updated: `Last verified: 2026-05-02 (cb41d512)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files; no orphaned IN-scope docs |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer hash updated from `a5073046` → `cb41d512`

### Commit
- `ea16f84c` — `docs: update cockpit diagram footer for archival intercept (#1246, doc-writer)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/1246-*` — no matches)
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| handleTransitionClick opens ArchivalModal when targetStatus === "archived" | KanbanBoard.tsx:155-161 sets archivalModal state and returns before POST | PASS |
| Props passed: taskId, taskStatus, expectedUpdated | KanbanBoard.tsx:210-216 passes all three from archivalModal state | PASS |
| expectedUpdated not re-read from polling | KanbanBoard.tsx:237 uses contextMenu.taskUpdated (frozen at menu-open) | PASS |
| Non-archival transitions unchanged | KanbanBoard.tsx:165-177 retains POST /move path | PASS |
| All tests from #1242 pass | quality-runner: KanbanBoard_1242.test.tsx 8/8 passed | PASS |

### Test Results
- vitest (full suite): 838 passed, 4 failed (all outside scope: ActivityTab_1156, usePollingFetch_1227 x3)
- eslint: 4 issues (all outside scope: KanbanBoard_933, Shell_1228, usePolling)
- Task-scoped tests: 18/18 passed (10 from _1246, 8 from _1242)

### Commit Verification
- 7a82b9fa test: add regression tests (#1246, test-writer)
- ea16f84c docs: update cockpit diagram footer (#1246, doc-writer)
- No builder commit needed (pre-implemented by #1242, well-documented)

### Architect Quality: 4/5
Specific, verifiable AC. Minor ambiguity on task.status source timing resolved by test-writer notes. Clean scope boundary.

### Deduction Breakdown
- All 5 AC lines verified with code and test evidence: 0
- Reviewer evidence present and detailed (PASS verdict): 0
- Full-suite failures outside task scope (pre-existing): 0
- Lint issues outside task scope: 0
- AC quality 4/5 (above threshold): 0

### Confidence: 0.98
### Action: archive