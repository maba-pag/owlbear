---
id: 1265
title: 'Fix stale test fixture in KanbanBoard_1242.test.tsx after #1227 API change'
status: archived
priority: medium
created: 2026-05-01T10:02:21.826578+00:00
updated: 2026-05-01T14:41:54.675023+00:00
tags:
- scope:frontend
- test
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Task #1227 changed KanbanBoard from internal-fetch to prop-based rendering. The task-scoped test file `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx` still uses the old `renderBoard()` pattern that renders `<KanbanBoard />` with no props, causing all 8 tests to fail with "Loading…". The durable suite `KanbanBoard.test.tsx` was updated with a `Harness` component that passes `board`, `tasks`, `loading`, `error`, and `refetchTasks` as props.

Additionally, the test-writer retry added an 8th test (brief F3 timing-split proof, lines 367-480) that was never committed (only exists as an uncommitted working-tree change).

## Acceptance Criteria

- [ ] Update `renderBoard()` in `KanbanBoard_1242.test.tsx` to use the prop-based Harness pattern from the durable suite (td:0)
- [ ] Ensure the 8th test (brief F3 timing-split proof) works with the prop-based Harness pattern and is included in the deliverable commit (td:0)
- [ ] All 8 tests in `KanbanBoard_1242.test.tsx` pass (td:0)
- [ ] No regressions in the durable `KanbanBoard.test.tsx` suite (td:0)

### Test-writer: SKIP

All AC lines are td:0 — this is a test-fix task; no new tests needed.

[[2026-05-01]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix stale test fixture in a single file |
| Interface clarity | PASS | AC references specific file, pattern, and pass criteria |
| Dependency correctness | PASS | No blocking deps needed; #1227 API change already committed, F3 impl already committed (869d5d05) |
| Module layering | N/A | Test file only, no production imports affected |
| TDD compliance | PASS | Test-fix task — the deliverable IS the test file; `test` tag added for pass-through |
| KISS/YAGNI | PASS | Minimal scope: one test file, one fixture pattern update |
| Premise challenge | PASS | Stale fixture is a real regression; audit #1242 confirmed 8/8 tests stuck at "Loading…" |
| Pattern consistency | PASS | Follows durable suite Harness pattern established in #1227 |
| Security surface | N/A | Test file only |
| Single domain | PASS | Frontend test domain only |

### Architecture Notes

- **Polling simulation concern (test 8):** KanbanBoard no longer has internal polling (removed by #1227). The 8th test (F3 timing-split proof) relies on `vi.advanceTimersByTimeAsync(3100)` to trigger a poll that changes task status between menu-open and archived-click. With the prop-based Harness, there's no internal polling interval to advance. The builder must either: (a) add a `setInterval`-based polling loop to the Harness (simplest — Harness calls `refetchTasks` on a 3s interval, matching production `useBoard` behavior), or (b) rewrite the test to trigger task updates via an alternative mechanism (e.g., expose Harness state setter). AC2's "or re-write" covers this.
- **Durable suite health:** Most recent evidence: 60 passed, 0 failed (reviewer cycle on #1242). Suite gate in AC4 is grounded.
- **Relationship to #1242:** Once #1265 is done, #1242's audit gap is resolved. #1242 should be re-audited after #1265 completes.
- **Uncommitted 8th test:** Lines ~381-494 of `KanbanBoard_1242.test.tsx` exist only as uncommitted working-tree changes (per audit #1242). If lost, the test logic is documented in #1242's test-writer retry notes.

### Dependency Analysis

- No blocking `depends_on` needed. F3 implementation (commit 869d5d05) and #1227 API change (commit 6452345f) are already in the codebase.
- Downstream: #1242 (in backlog) should be re-audited after #1265 completes. #1246 (depends_on #1242) is unblocked once #1242 is resolved.

### Test Depth

- All AC lines: td:0 — this IS a test-fix task; the deliverable is the passing test file itself. No new test-writer work.
- Test-writer: SKIP

### Challenge Results

- Challenger: SKIPPED — all td:0 per Step 2.1 gating rule.

### Verdict: APPROVE
### Action Taken: Added `test` tag for test-writer pass-through. AC refined with td:0 annotations. Builder note added about polling simulation concern for test 8.
[[2026-05-01]]
APPROVED #1265 -> todo | Fix stale test fixture in KanbanBoard_1242.test.tsx; Harness swap + polling simulation for test 8. All td:0, test-writer SKIP, challenger SKIP.
[[2026-05-01]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task is tagged `test`; AC body includes explicit "Test-writer: SKIP" directive.
- Passing through to builder.
[[2026-05-01]]
## Builder Notes
- Implementation: no code edits required; target file already contained the prop-based Harness render pattern and included the 8th timing-split test.
- Files changed: none.
- Tests (task-scoped): `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx` -> 8 passed, 0 failed (Vitest).
- Tests (durable regression gate): `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` -> 35 passed, 0 failed (Vitest).
- Quality-runner evidence:
  - Full mode: failing due to unrelated pre-existing repo baseline failures (non-task packages).
  - Scoped mode for #1265 paths: 8 passed, 0 failed; lint/coverage marked N/A for TSX per `h-quality-runner` frontend limitation guidance.
- Diagnostics: no VS Code errors in `KanbanBoard_1242.test.tsx` or `KanbanBoard.test.tsx`.
- Evidence summary: ACs satisfied without additional edits in this builder pass; task file is green and durable suite has no regression.
[[2026-05-01]]
## Review Evidence
### Test Results
- Scoped rerun on serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx: 8 passed, 0 failed, 0 skipped.
- Scoped rerun on serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx: 35 passed, 0 failed, 0 skipped.
- Initial combined scoped run reported inconsistent per-file counts (43 total with 6 in the task file and 37 in the durable suite). Per repo review guidance, I treated the individual reruns as authority.

### Lint / Diagnostics
- VS Code diagnostics: no errors in serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx, serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx, or serve/cockpit/web/src/KanbanBoard.tsx.
- Frontend lint signal was inconsistent across quality-runner invocations for TSX files, so diagnostics plus passing Vitest reruns were used as the TypeScript safety gate.

### Coverage
- N/A. This is a td:0 frontend test-fix task. Behavioral proof came from scoped Vitest reruns plus diagnostics.

### Pass 1 - CRITICAL
#### Test Integrity
- Current task file contains 8 executable `it(...)` cases at lines 169, 181, 202, 232, 246, 259, 277, and 366. No skip or todo markers found.
- Assertions are specific: modal presence, POST absence/presence, exact move target, exact taskId/taskStatus/expectedUpdated props, frozen expectedUpdated, and live taskStatus at archived-click time.

#### Security Review
- No issues. Test-only TSX scope; no new secrets, injection, path, or deserialization surface.

#### Test Quality
- STRONG. Assertions would fail on the relevant behavioral regressions in KanbanBoard.tsx.
- Negative and regression coverage are present: archived click does not POST while non-archived click still does.

#### Data Safety
- No issues. Test-only task; no persisted data or shared-state mutation path introduced.

#### Builder Process Quality
- CLEAN. One builder section only; no retry loop evidence.

### AC Compliance
| AC Line | Evidence | Status |
| --- | --- | --- |
| Update renderBoard() in KanbanBoard_1242.test.tsx to use the prop-based Harness pattern from the durable suite | serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx:128-137 passes board, tasks, loading, error, and refetchTasks explicitly; tests/test_frontend_polling_1227.py:288-303 enforces no bare `<KanbanBoard />` render in this suite; durable reference helper remains at serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx:121-181 | PASS |
| Ensure the 8th test (brief F3 timing-split proof) works with the prop-based Harness pattern and is included in the deliverable commit | The 8th test is present at serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx:366 and rerenders updated props at 404-428; KanbanBoard consumes live task status from current tasks at serve/cockpit/web/src/KanbanBoard.tsx:234-237 while freezing expectedUpdated in the archived branch at 153-160. Current snapshot proves the test is present and green. Commit provenance is indirect because no builder commit hash was recorded in the task body. | PASS (minor confidence deduction) |
| All 8 tests in KanbanBoard_1242.test.tsx pass | quality-runner single-file rerun: 8 passed, 0 failed, 0 skipped; direct grep confirms 8 executable tests in the file | PASS |
| No regressions in the durable KanbanBoard.test.tsx suite | quality-runner single-file rerun on serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx: 35 passed, 0 failed, 0 skipped | PASS |

### Deductions
- 0.03: initial combined quality-runner run returned conflicting per-file counts; resolved by individual reruns.
- 0.02: AC2 commit provenance is indirect because the task body did not record a builder commit hash and .git/logs access is grep-only.

### Verdict
- PASS with confidence 0.93.

### Action
- Advanced task to docs.

### Reflection
- Combined frontend quality-runner runs can misreport per-file counts; single-file reruns are the safer authority when suite shape and live file content disagree.
- TSX review gates still need diagnostics plus Vitest evidence; Python-oriented lint signals are not authoritative for these files.
- Builder notes should include commit hashes whenever an AC mentions deliverable-commit provenance.
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Builder changed no files; all referenced files are TSX test/source — no API, CLI, config, or package-structure changes |
| 2 | Module docstrings | No | N/A | No Python modules touched |
| 3 | External attribution | No | N/A | No external patterns referenced |
| 4 | Research doc | No | N/A | No research doc mentioned in task |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index scan: no diagram describes glob matches KanbanBoard test/source paths |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx | OUT | N/A |
| serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx | OUT | N/A |
| serve/cockpit/web/src/KanbanBoard.tsx | OUT | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1265-* scratch files existed)
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Update renderBoard() to prop-based Harness pattern | KanbanBoard_1242.test.tsx:128-137 passes board, tasks, loading, error, refetchTasks as props | PASS |
| 8th test (F3 timing-split proof) works with Harness and is committed | Lines 366-452: uses rerender() with updated props, asserts live taskStatus=in-progress and frozen expectedUpdated. Committed in b3b631bc | PASS |
| All 8 tests pass | Vitest: 8 passed, 0 failed, 0 skipped | PASS |
| No regressions in durable KanbanBoard.test.tsx | Vitest: 35 passed, 0 failed, 0 skipped | PASS |

### Test Results
- Vitest (task file): 8 passed, 0 failed
- Vitest (durable suite): 35 passed, 0 failed
- pytest full suite: 3485 passed, 110 failed (all pre-existing, unrelated: react_compiler infra, cockpit_models constants)
- ruff: no task-scope violations (background debt only)

### Architect Quality: 4/5
AC was specific, verifiable, referenced exact file, pattern, and pass criteria. Minor note: task created after #1227 builder had already applied the fix, making this a zero-edit builder pass, but the AC itself is well-structured.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 4 verified) = 0.00
- Lint violations: none = 0.00
- AC quality LE 3: no (score 4) = 0.00
- Missing reviewer evidence: no (present and detailed) = 0.00
- Full-suite failures in task scope: none = 0.00

### Confidence: 1.00
### Action: archive

### Notes
- Builder correctly identified zero edits needed; commit b3b631bc from #1227 already included the Harness pattern update and 8th test.
- Reviewer deductions (0.05 total for conflicting QR counts and indirect commit provenance) resolved by independent verification: direct git log confirms provenance, independent vitest runs confirm counts.