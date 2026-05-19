---
id: 954
title: Implement TASK_COMPLETE audit-map advisory worker pilot
status: archived
priority: important
created: 2026-03-23T03:10:52.6646719+01:00
updated: 2026-03-24T23:48:38.2511423+01:00
started: 2026-03-24T23:48:29.9383526+01:00
completed: 2026-03-24T23:48:29.9383526+01:00
tags:
    - agent
    - daemon
    - hooks
    - scope:core
    - type:build
depends_on:
    - 953
    - 982
    - 983
class: standard
---

## Research-Decomposed Parent

Research doc delivered: docs/research/task-complete-audit-map-advisory-worker.md

Implementation scope fully decomposed into:

- #982: RED tests - AuditMapAdvisoryHook eligibility and safety (backlog, needed)
- #983: Implement AuditMapAdvisoryHook class (backlog, needed)

This task tracks completion through its follow-ups. No independent implementation work remains.

## AC (Governance)

- [ ] Research doc docs/research/task-complete-audit-map-advisory-worker.md addresses all 6 original AC lines
- [ ] RED test task #982 created with 10 verifiable test AC lines covering trigger eligibility, artifact generation, and safety boundaries
- [ ] Implementation task #983 created with 10 verifiable build AC lines covering hook class, gating, artifact, notifications, safety, and bootstrap wiring
- [ ] Both follow-ups reference the research doc and have correct inter-task dependencies
- [ ] Attribution recorded in docs/sources/overview.md

## Architecture Review

**Verdict:** APPROVED (governance parent after decomposition)

### Original AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Register opt-in TASK_COMPLETE worker pilot | Covered by #983 AC line 2 | Moved to #983 |
| Require explicit rollout gates | Covered by #983 AC lines 2, 7 | Moved to #983 |
| Produce scratch-only artifact + notification | Covered by #983 AC lines 4, 5 | Moved to #983 |
| No board mutations | Covered by #983 AC line 6 | Moved to #983 |
| Use supervised background-worker path | Covered by #983 AC line 3 | Moved to #983 |
| Add tests | Fully covered by #982 (10 test AC) | Moved to #982 |

### Architecture Notes

- Research phase complete: docs/research/task-complete-audit-map-advisory-worker.md
- Dependency #953 (HookWorkerSupervisor) archived -- prerequisite met
- No namespace conflicts: audit_map/AuditMap absent from src/
- Module placement src/owlbear/core/audit_map_hook.py follows retrospective_hook.py peer pattern
- Config flag audit_map_worker_enabled follows 9 existing *_enabled patterns in config.py
- Note for #983 architect review: AC line 8 says build_hooks() but wiring must be in_wire_post_model_hooks() (supervisor lives there)
- Note for #983 architect review: _wire_post_model_hooks lacks channel param -- needed for hook notification AC

### Changes Made

- Rewrote body to governance AC reflecting completed research decomposition
- Added depends_on: [982, 983]

### Dependencies

- Verified: #953 (HookWorkerSupervisor) -- archived
- Added: depends_on 982, 983 -- tracks decomposed implementation

[[2026-03-24]] Tue 21:10

## Test-Writer Notes

- Governance parent task — no testable implementation code.
- Body explicitly states: 'No independent implementation work remains.'
- Implementation decomposed into #982 (RED tests, archived) and #983 (implementation, archived).
- Passing through to builder.

[[2026-03-24]] Tue 22:07

## Builder Notes

- Non-implementation task - no code changes needed.
- Passing through to review.

[[2026-03-24]] Tue 22:20

## Review Evidence

### Findings

- FAIL: Parent AC2 and AC3 are no longer true. The governance card still says #982 should have 8 AC lines and #983 should have 9, but the live child tasks each contain 10 AC lines after architecture refinement.
- Current implementation state is otherwise healthy: scoped pytest passed with 43 tests, task-scoped ruff passed, and src/owlbear/core/audit_map_hook.py is 99 percent covered in the bare coverage report.

### Test Results

- Scoped pytest on tests/test_audit_map_hook.py passed: 43 passed, 2 warnings.
- The warnings were the existing optional-dependency skips for qdrant_client from tests/conftest.py.
- Task-scoped ruff on src/owlbear/core/audit_map_hook.py, src/owlbear/config.py, src/owlbear/bootstrap/**init**.py, and tests/test_audit_map_hook.py passed.
- Bare coverage run reported src/owlbear/core/audit_map_hook.py at 99 percent. src/owlbear/config.py and src/owlbear/bootstrap/**init**.py stayed low in the whole-project report, which is expected for bare coverage runs.

### AC Compliance

- AC1 PASS: docs/research/task-complete-audit-map-advisory-worker.md sections 3.1 to 3.5 and lines 92 to 97 address implementation approach, gating, artifact format, bootstrap wiring, and the six original safety gates.
- AC2 FAIL: kanban/tasks/954-implement-task-complete-audit-map-advisory-worker.md line 35 requires #982 to be created with 8 verifiable test AC lines, but kanban/tasks/982-red-tests-auditmapadvisoryhook-eligibility-and.md lines 20 to 29 define 10 AC lines.
- AC3 FAIL: kanban/tasks/954-implement-task-complete-audit-map-advisory-worker.md line 36 requires #983 to be created with 9 verifiable build AC lines, but kanban/tasks/983-implement-auditmapadvisoryhook-class.md lines 20 to 29 define 10 AC lines.
- AC4 PASS: Both child tasks reference the research doc at line 39 in #982 and line 31 in #983. Dependency links also exist in #954 lines 14, 16, 17, in #983 lines 14 to 15, and in #982 line 40.
- AC5 PASS: docs/sources/overview.md lines 55 to 56 record the attribution for this research and design work.

### Verdict

- FAIL
- Confidence: .95

### Action Taken

- Task moved to todo.
- Reviewer claim released.

[[2026-03-24]] Tue 22:46

## Builder Notes

- Files changed: kanban/tasks/954-implement-task-complete-audit-map-advisory-worker.md
- Tests: Not run (governance-only metadata fix; no source or test code changed)
- Lint: Not run (no Python files changed)
- Evidence: Updated #954 AC2 and AC3 to match archived child tasks #982 and #983, each with 10 AC lines after architecture refinement
- Fixes applied: Corrected stale governance AC counts and aligned architecture review row for test AC count

[[2026-03-24]] Tue 23:05

## Review Evidence

### Review: #954 - Implement TASK_COMPLETE audit-map advisory worker pilot

### Test Results

- Scoped audit-map regression passed: 43 passed, 2 warnings in tests/test_audit_map_hook.py with bare coverage enabled.
- Bootstrap wiring regression slice passed: 1 passed, 179 deselected, 2 warnings in the wire_post_model_hooks slice of tests/test_bootstrap.py.
- Warnings were the existing optional-dependency skips for qdrant_client from tests/conftest.py.

### Lint Results

- Task-scoped ruff passed on src/owlbear/core/audit_map_hook.py, src/owlbear/config.py, src/owlbear/bootstrap/**init**.py, and tests/test_audit_map_hook.py.

### Coverage

- src/owlbear/core/audit_map_hook.py: 99 percent in the scoped bare coverage run.
- src/owlbear/config.py: 70 percent and src/owlbear/bootstrap/**init**.py: 35 percent in that same whole-file report.
- Tooling note: #954 is a governance-only metadata fix, so the coverage run is regression evidence for the decomposed child implementation rather than changed-line coverage for this card.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- Not applicable: #954 is a governance parent with no direct TestFromAC surface or task-owned implementation file. The testable behavior was decomposed into archived child tasks #982 and #983.

#### Security Review

- No security issue found in this cycle. The live change is the parent task metadata alignment in kanban/tasks/954-implement-task-complete-audit-map-advisory-worker.md, and fresh regression slices for the decomposed implementation still pass.

#### Test Integrity

- Not applicable: no test file changed in the #954 review cycle. The live task file now shows the corrected AC counts at lines 33 and 34 plus the aligned architecture note at line 48.

#### Test Quality

- Not applicable to #954 directly; this governance parent owns no tests.

#### Data Safety

- No data safety issue found in this cycle. The live change is kanban metadata only.

#### Implementation-Aware Test Gaps

- No new untested behavioral path was introduced in this cycle because #954 changed only governance metadata.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Research doc addresses all 6 original AC lines | docs/research/task-complete-audit-map-advisory-worker.md analysis sections at lines 29, 31, 46, 60, 72, and 86 plus the follow-up task section at line 119 cover implementation approach, gating, artifact format, bootstrap wiring, safety boundaries, and the two child-task creation commands at lines 124 and 128 | Governance parent; no direct test | PASS |
| AC2: RED test task #982 created with 10 verifiable test AC lines | Parent task line 33 now requires 10 test AC lines; child task #982 is archived at line 4 and contains 10 explicit AC bullets at lines 20 through 29 | Fresh audit-map regression slice still passes | PASS |
| AC3: Implementation task #983 created with 10 verifiable build AC lines | Parent task line 34 now requires 10 build AC lines; child task #983 is archived at line 4 and contains 10 explicit AC bullets at lines 20 through 29 | Fresh audit-map regression slice and bootstrap wiring slice both pass | PASS |
| AC4: Both follow-ups reference the research doc and have correct inter-task dependencies | #982 references the research doc at line 39 and parent dependency at line 40; #983 references the research doc at line 31 and dependency on #982 at line 32; parent frontmatter keeps depends_on links to 953, 982, and 983 at lines 14 through 17 | Governance parent; no direct test | PASS |
| AC5: Attribution recorded in docs/sources/overview.md | docs/sources/overview.md has the task section header at line 51 and the recorded source entries for this task at lines 55 and 56 | Governance parent; no direct test | PASS |

### Verdict: PASS

- Confidence: .95

### Action Taken

- Review evidence appended.
- Task moved to docs.
- Reviewer claim released.

[[2026-03-24]] Tue 23:48

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Research doc addresses all 6 original AC lines | docs/research/task-complete-audit-map-advisory-worker.md sections 3.1-3.6 cover implementation approach, gating, artifact format, bootstrap wiring, safety boundaries, notification | PASS |
| AC2: RED test task #982 created with 10 verifiable test AC lines | #982 archived with 10 AC bullets (AC1-AC10) at lines 20-29; parent line 33 says 10 | PASS |
| AC3: Implementation task #983 created with 10 verifiable build AC lines | #983 archived with 10 AC bullets (AC1-AC10) at lines 20-29; parent line 34 says 10 | PASS |
| AC4: Both follow-ups reference research doc and have dependencies | #982 references doc at line 39, parent dep at line 40; #983 references doc at line 31, #982 dep at line 32; parent depends_on 953, 982, 983 | PASS |
| AC5: Attribution in docs/sources/overview.md | Lines 51, 55-56 record ruflo README and asyncio docs attribution | PASS |

### Test Results

- pytest (full suite, 4 RED-phase files ignored): 4227 passed, 91 failed (all pre-existing RED-phase or known failures), 20 skipped
- Task-scoped ruff on audit_map_hook.py, config.py, bootstrap/**init**.py, test_audit_map_hook.py: All checks passed
- No task-relevant failures detected

### Upstream Commit Gaps

- Research doc and sources attribution were uncommitted (orphaned by upstream agents)
- Committed as 6952e14: docs: add audit-map advisory worker research and attribution (#954, auditor)

### Architect Quality (AC Quality Score: 4)

- AC was adequate for a governance parent task
- AC counts were initially stale (8/9 instead of 10/10) but builder corrected them after reviewer caught the mismatch
- Minor gap: AC should have anticipated that child task AC counts would evolve during architecture refinement

### Confidence: .97

### Action: archive

[[2026-03-24]] Tue 23:48

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6952e14 | docs | research doc, sources/overview.md | #954 |
