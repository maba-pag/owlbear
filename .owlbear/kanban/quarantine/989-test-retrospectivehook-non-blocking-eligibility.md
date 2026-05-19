---
id: 989
title: 'Test: RetrospectiveHook non-blocking eligibility handoff'
status: archived
priority: needed
created: 2026-03-24T04:27:25.80457+01:00
updated: 2026-03-24T14:29:15.2186613+01:00
started: 2026-03-24T14:28:22.37921+01:00
completed: 2026-03-24T14:28:22.37921+01:00
tags:
    - agent
    - hooks
    - scope:core
    - type:test
    - test
class: standard
---

AC:

1. Add `TestFromAC_981_NonBlockingEligibilityHandoff` class to `tests/test_retrospective_hook.py`.
2. Tests must FAIL on current HEAD and prove:
   (a) `__call__` does not call `_count_rejections` or `_get_priority` directly â€” patch both, call `__call__`, assert neither was called on the awaited path.
   (b) The supervisor-scheduled background task calls `_count_rejections` and `_get_priority` â€” await the scheduled coroutine, assert both were invoked.
   (c) Ineligible tasks (zero rejections + low priority) are filtered inside the background task â€” the scheduled coroutine returns early without calling `_run_retrospective`.
   (d) `create_task` fallback path also defers eligibility to the background task â€” same assertions as (a)-(c) without supervisor.
3. Existing `TestFromAC_RetrospectiveHookSupervisorSeam` tests must still pass.
4. File: `tests/test_retrospective_hook.py`.

[[2026-03-24]] Tue 05:21

## Test-Writer Notes

- Test file: tests/test_retrospective_hook.py

- Class: TestFromAC_981_NonBlockingEligibilityHandoff

- Tests per category: happy 2 (eligible task deferred), edge 2 (background invokes checks), error 2 (ineligible filtered in background), boundary 2 (create_task fallback mirrors supervisor path)

- Total: 8 tests, all FAIL (AssertionError on assert_not_called / assert_called / assert_called_once) verified

- ruff: clean

- AC coverage:

| AC Line | Test(s) | Category |

|---------|---------|----------|

| AC2(a) supervisor: __call__ does not call _count_rejections | test_call_does_not_invoke_count_rejections_directly_supervisor_path | happy |

| AC2(a) supervisor: __call__ does not call _get_priority | test_call_does_not_invoke_get_priority_directly_supervisor_path | happy |

| AC2(b) supervisor: background coro calls _count_rejections | test_supervisor_background_coro_invokes_count_rejections | edge |

| AC2(b) supervisor: background coro calls _get_priority | test_supervisor_background_coro_invokes_get_priority_zero_rejections | edge |

| AC2(c) supervisor: ineligible task scheduled, filtered in background | test_supervisor_ineligible_task_reaches_schedule_then_filtered | error |

| AC2(d) create_task: __call__ does not call_count_rejections | test_call_does_not_invoke_count_rejections_directly_create_task_path | boundary |

| AC2(d) create_task: background coro calls_count_rejections | test_create_task_fallback_background_coro_invokes_count_rejections | boundary |

| AC2(d) create_task: ineligible task reaches create_task, filtered in background | test_create_task_fallback_ineligible_task_reaches_create_task_then_filtered | error |

| AC3: existing TestFromAC_RetrospectiveHookSupervisorSeam | 5 tests still PASS | n/a |

[[2026-03-24]] Tue 09:34

## Builder Notes

- Files changed: none
- Tests: 8 passed (TestFromAC_981_NonBlockingEligibilityHandoff), 5 passed (TestFromAC_RetrospectiveHookSupervisorSeam), 51 passed in tests/test_retrospective_hook.py
- Coverage: 97% on src/owlbear/core/retrospective_hook.py (scoped run used COVERAGE_FILE=.coverage.task989 after one .coverage file lock failure)
- Lint: ruff clean on src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py
- Evidence: uv run pytest commands exited 0 for AC classes and full file; uv run ruff check exited 0
- Fixes applied: None (behavior already implemented before this builder pass)

[[2026-03-24]] Tue 10:13

## Review Evidence

## Review: #989 - Test: RetrospectiveHook non-blocking eligibility handoff

### Test Results

- pytest: `uv run pytest tests/test_retrospective_hook.py::TestFromAC_981_NonBlockingEligibilityHandoff -q --tb=short` -> 8 passed, 0 failed
- pytest: `uv run pytest tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam -q --tb=short` -> 5 passed, 0 failed
- pytest: `uv run pytest tests/test_retrospective_hook.py -q --tb=short` -> 51 passed, 0 failed
- warnings:
  - optional-dependency warnings from `tests/conftest.py:58` about missing `qdrant_client`
  - isolated run of `test_call_does_not_invoke_count_rejections_directly_create_task_path` passes but emits `RuntimeWarning: coroutine 'RetrospectiveHook._run_retrospective_if_eligible' was never awaited` after teardown

### Lint Results

- ruff: All checks passed (`uv run ruff check src/owlbear/core/retrospective_hook.py tests/test_retrospective_hook.py`)

### Coverage

- `src/owlbear/core/retrospective_hook.py`: 97% (`uv run pytest tests/test_retrospective_hook.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`)

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| AC1: add `TestFromAC_981_NonBlockingEligibilityHandoff` class in `tests/test_retrospective_hook.py` | class at line 1195 | Yes | COVERED |
| AC2(a): supervisor path defers `_count_rejections` out of `__call__` | `test_call_does_not_invoke_count_rejections_directly_supervisor_path` (line 1227; assert line 1243) | Yes | COVERED |
| AC2(a): supervisor path defers `_get_priority` out of `__call__` | `test_call_does_not_invoke_get_priority_directly_supervisor_path` (line 1246; assert line 1262) | Yes | COVERED |
| AC2(b): supervisor background calls `_count_rejections` | `test_supervisor_background_coro_invokes_count_rejections` (line 1267; assert line 1289) | Yes | COVERED |
| AC2(b): supervisor background calls `_get_priority` | `test_supervisor_background_coro_invokes_get_priority_zero_rejections` (line 1292; assert line 1314) | Yes | COVERED |
| AC2(c): supervisor ineligible task is scheduled then filtered in background | `test_supervisor_ineligible_task_reaches_schedule_then_filtered` (line 1319; assert line 1340) | Yes | COVERED |
| AC2(d): create_task path defers `_count_rejections` out of `__call__` | `test_call_does_not_invoke_count_rejections_directly_create_task_path` (line 1345; assert line 1365) | Yes | COVERED |
| AC2(d): create_task background calls `_count_rejections` | `test_create_task_fallback_background_coro_invokes_count_rejections` (line 1368; assert line 1392) | Yes | COVERED |
| AC2(d): create_task path defers `_get_priority` out of `__call__` | none | No | MISSING |
| AC2(d): create_task background calls `_get_priority` | none | No | MISSING |
| AC2(d): create_task ineligible task is filtered in background | `test_create_task_fallback_ineligible_task_reaches_create_task_then_filtered` (line 1395; asserts lines 1416 and 1418) | Partially; it never asserts `_get_priority` timing or invocation | LAX |
| AC3: existing `TestFromAC_RetrospectiveHookSupervisorSeam` tests still pass | class at line 1070; scoped run -> 5 passed | Yes | COVERED |
| AC4: file is `tests/test_retrospective_hook.py` | new class lives in that file at line 1195 | Yes | COVERED |

#### Security Review

- No security issues found in the source diff from `078da2d..HEAD`; the committed production changes are limited to `src/owlbear/core/retrospective_hook.py` lines 162-191 and 262-268, with no new dependency or external-input surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| `TestFromAC_981_NonBlockingEligibilityHandoff` | `git diff --unified=3 078da2d..HEAD -- tests/test_retrospective_hook.py src/owlbear/core/retrospective_hook.py` shows no committed edits to `tests/test_retrospective_hook.py` after the #989 test-writer commit; working-tree diff collapses to a single blank-line deletion at line 1419 under `--ignore-all-space` | PRESERVED |
| `TestFromAC_RetrospectiveHookSupervisorSeam` | same diff shows no committed edits to the existing seam tests after the #989 test-writer commit | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | uses `assert_not_called`, `assert_called`, exact `call_count`, and `mock_run.assert_not_called` at lines 1243, 1262, 1289, 1314, 1340, 1365, 1392, 1416, and 1418 |
| Negative/error paths | ADEQUATE | supervisor and create_task ineligible cases exist at lines 1319 and 1395, but create_task priority assertions are incomplete |
| Mutation reasoning | WEAK | a regression that calls `_get_priority` synchronously in `__call__` or skips `_get_priority` inside the create_task background helper would still pass, because only the supervisor path has `_get_priority` timing/invocation tests (lines 1246 and 1292) while the implementation still depends on `_get_priority` in both `__call__` and `_run_retrospective_if_eligible` |
| Test independence | WEAK | isolated run of `test_call_does_not_invoke_count_rejections_directly_create_task_path` passes but emits `RuntimeWarning: coroutine 'RetrospectiveHook._run_retrospective_if_eligible' was never awaited` after teardown, indicating leaked coroutine cleanup on the create_task fallback seam |
| Descriptive names | STRONG | names map directly to the AC clauses and expected behavior |

#### Data Safety

- No data-safety issues found in the reviewed production change.

#### Implementation-Aware Test Gaps

- The actual create_task fallback schedules `_run_retrospective_if_eligible(task_id)` at `src/owlbear/core/retrospective_hook.py:191`, and that helper calls `_get_priority(task_id)` at line 266 when `rejection_count == 0`. The test suite never asserts create_task-path parity for `_get_priority`, even though AC2(d) requires the same assertions as the supervisor path.

### Pass 2 - INFORMATIONAL

- No informational findings beyond the blocking test-coverage and cleanup issues.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| 1. Add `TestFromAC_981_NonBlockingEligibilityHandoff` class | class exists at `tests/test_retrospective_hook.py:1195` | class presence | PASS |
| 2(a). `__call__` does not call `_count_rejections` or `_get_priority` directly | supervisor tests at lines 1227 and 1246 pass; source schedules background helper at `src/owlbear/core/retrospective_hook.py:187-191` | `test_call_does_not_invoke_count_rejections_directly_supervisor_path`; `test_call_does_not_invoke_get_priority_directly_supervisor_path` | PASS |
| 2(b). background task calls `_count_rejections` and `_get_priority` | helper at `src/owlbear/core/retrospective_hook.py:262-268`; supervisor tests at lines 1267 and 1292 pass | `test_supervisor_background_coro_invokes_count_rejections`; `test_supervisor_background_coro_invokes_get_priority_zero_rejections` | PASS |
| 2(c). ineligible tasks are filtered inside the background task | helper returns early before `_run_retrospective`; test at line 1319 asserts `mock_run.assert_not_called()` at line 1340 | `test_supervisor_ineligible_task_reaches_schedule_then_filtered` | PASS |
| 2(d). create_task fallback mirrors (a)-(c) without supervisor | only create_task tests are at lines 1345, 1368, and 1395; there are no create_task `_get_priority` direct/background assertions | `test_call_does_not_invoke_count_rejections_directly_create_task_path`; `test_create_task_fallback_background_coro_invokes_count_rejections`; `test_create_task_fallback_ineligible_task_reaches_create_task_then_filtered` | FAIL |
| 3. Existing `TestFromAC_RetrospectiveHookSupervisorSeam` tests still pass | scoped run -> 5 passed; class at line 1070 | `TestFromAC_RetrospectiveHookSupervisorSeam` | PASS |
| 4. File: `tests/test_retrospective_hook.py` | reviewed class lives in that file | file inspection | PASS |

### Verdict

- FAIL
- Confidence: .82
- Reason: AC2(d) is not fully enforced. The create_task fallback path is missing `_get_priority` parity tests, and one create_task test leaks an unawaited coroutine warning.

### Action Taken

- `kanban\kanban-md.exe edit 989 --status todo --release`

[[2026-03-24]] Tue 11:20

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL cited MISSING tests — AC2(d) create_task path never tested_get_priority timing/invocation
- Added 2 new tests to TestFromAC_981_NonBlockingEligibilityHandoff:
  - test_call_does_not_invoke_get_priority_directly_create_task_path (PASS — impl already correct)
  - test_create_task_fallback_background_coro_invokes_get_priority_zero_rejections (PASS — impl already correct)
- Preserved 2 pre-existing failing tests already in working tree (not committed at review time):
  - test_real_helper_path_supervisor_schedules_ineligible_task (FAIL —_uses_default_eligibility_helpers shortcut blocks scheduling)
  - test_real_helper_path_create_task_schedules_ineligible_task (FAIL — same for create_task path)
- Result: 12 tests total, 10 PASS, 2 FAIL (real-helper-path expose deeper implementation gap)
- AC3: TestFromAC_RetrospectiveHookSupervisorSeam 5 passed
- ruff: clean

[[2026-03-24]] Tue 13:05

## Builder Notes

- Files changed: none
- Tests: 12 passed (TestFromAC_981_NonBlockingEligibilityHandoff), 5 passed (TestFromAC_RetrospectiveHookSupervisorSeam), 55 passed (tests/test_retrospective_hook.py)
- Coverage: 96% on src/owlbear/core/retrospective_hook.py (bare --cov scoped run)
- Lint: ruff clean on src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py
- Evidence: scoped class runs and full-file run passed; bare --cov run reported retrospective_hook.py 96%; ruff reported All checks passed
- Fixes applied: None (current HEAD already satisfies AC tests; no implementation changes required)

[[2026-03-24]] Tue 13:32

## Review Evidence\n### Findings\n- No blocking findings.\n\n### Test Results\n- pytest: uv run pytest tests/test_retrospective_hook.py::TestFromAC_981_NonBlockingEligibilityHandoff -q --tb=short -> 12 passed, 2 warnings.\n- pytest: uv run pytest tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam -q --tb=short -> 5 passed, 2 warnings.\n- pytest: uv run pytest tests/test_retrospective_hook.py -q --tb=short -> 55 passed, 2 warnings.\n- pytest: uv run pytest tests/test_retrospective_hook.py::TestFromAC_981_NonBlockingEligibilityHandoff::test_call_does_not_invoke_count_rejections_directly_create_task_path -q --tb=short -> 1 passed, 2 warnings and no unawaited-coroutine warning.\n- warnings: optional qdrant_client skips from tests/conftest.py:58 only.\n\n### Lint Results\n- ruff: All checks passed via uv run ruff check src/owlbear/core/retrospective_hook.py tests/test_retrospective_hook.py.\n\n### Coverage\n- bare --cov run reported src/owlbear/core/retrospective_hook.py at 96 percent.\n- Note: bare --cov also prints unrelated project modules because coverage is configured at repo scope.\n\n### Pass 1 - CRITICAL\n#### Test-Writer AC Coverage\n| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |\n| --- | --- | --- | --- |\n| AC1 add TestFromAC_981_NonBlockingEligibilityHandoff in tests/test_retrospective_hook.py | class at line 1195 | Yes | COVERED |\n| AC2(a) supervisor path defers _count_rejections and _get_priority out of __call__ | tests at lines 1227 and 1246 | Yes | COVERED |\n| AC2(b) supervisor background invokes _count_rejections and _get_priority | tests at lines 1267 and 1292 | Yes | COVERED |\n| AC2(c) supervisor ineligible task is scheduled then filtered in background | test at line 1319 | Yes | COVERED |\n| AC2(d) create_task path mirrors deferral, background invocation, and ineligible filtering | tests at lines 1345, 1368, 1395, 1422, and 1450 | Yes | COVERED |\n| AC3 existing TestFromAC_RetrospectiveHookSupervisorSeam still passes | class at line 1070 and scoped pytest run -> 5 passed | Yes | COVERED |\n| AC4 file is tests/test_retrospective_hook.py | class lives at line 1195 in that file | Yes | COVERED |\n\n#### Security Review\n- No security issues found. Post-retry production history is one commit, 1a1b61b, touching only src/owlbear/core/retrospective_hook.py with 28 insertions and 7 deletions and no new dependency or input surface.\n\n#### Test Integrity\n| Original Test | Change Made | Assessment |\n| --- | --- | --- |\n| TestFromAC_981_NonBlockingEligibilityHandoff | git diff --name-only aeb0142 HEAD -- tests/test_retrospective_hook.py src/owlbear/core/retrospective_hook.py returned only src/owlbear/core/retrospective_hook.py | PRESERVED |\n| TestFromAC_RetrospectiveHookSupervisorSeam | same diff showed no post-retry edits to tests/test_retrospective_hook.py | PRESERVED |\n\n#### Test Quality\n| Dimension | Rating | Evidence |\n| --- | --- | --- |\n| Assertion specificity | STRONG | uses assert_not_called, assert_called, len(captured) == 1, and mock_run.assert_not_called across lines 1227 through 1450 |\n| Negative and error paths | STRONG | supervisor and create_task ineligible cases are covered at lines 1319 and 1450, plus real-helper no-local-log cases at lines 1478 and 1506 |\n| Mutation reasoning | STRONG | direct-call regressions, missing background helper calls, or lost filtering would break the paired supervisor and create_task tests |\n| Test independence | STRONG | isolated create_task test run passed with only optional-dependency warnings; no RuntimeWarning or leaked coroutine remained |\n| Descriptive names | STRONG | test names map directly to the AC clauses and path variants |\n\n#### Data Safety\n- No data-safety issues found.\n\n#### Implementation-Aware Coverage\n- The live implementation has two meaningful branches in __call__: a preserved local-activity-log fast path at lines 196 through 201 and the deferred background path at lines 206 through 211 with helper calls in_run_retrospective_if_eligible at lines 283 through 290.\n- The preserved seam class at line 1070 covers the legacy fast path, and the #989 class at line 1195 covers the deferred supervisor and create_task paths, including real-helper no-local-log scheduling at lines 1478 and 1506.\n- No significant untested branch remained in the reviewed scope.\n\n### Pass 2 - INFORMATIONAL\n- git log --oneline aeb0142..HEAD -- src/owlbear/core/retrospective_hook.py shows one source commit after the retry test-writer commit: 1a1b61b fix: defer retrospective eligibility handoff (#988, builder). The #989 tests are preserved and now validate that source change.\n\n### AC Compliance\n| AC Line | Evidence | Mapped Test | Status |\n| --- | --- | --- | --- |\n| 1. Add TestFromAC_981_NonBlockingEligibilityHandoff class | class exists at tests/test_retrospective_hook.py line 1195 | class presence | PASS |\n| 2(a). __call__ does not call_count_rejections or_get_priority directly | supervisor tests at lines 1227 and 1246 pass; create_task parity tests at lines 1345 and 1368 pass; deferred scheduling happens at source lines 206 through 211 | direct deferral tests | PASS |\n| 2(b). background task calls _count_rejections and _get_priority | supervisor tests at lines 1267 and 1292 pass; create_task parity tests at lines 1395 and 1422 pass; helper calls happen at source lines 285 and 287 | background invocation tests | PASS |\n| 2(c). ineligible tasks are filtered inside the background task | supervisor test at line 1319 and create_task test at line 1450 pass; helper returns before _run_retrospective at source lines 285 through 290 | ineligible filtering tests | PASS |\n| 2(d). create_task fallback mirrors (a) through (c) without supervisor | create_task tests at lines 1345, 1368, 1395, 1422, and 1450 all pass | create_task parity tests | PASS |\n| 3. Existing TestFromAC_RetrospectiveHookSupervisorSeam tests still pass | scoped run -> 5 passed; class at line 1070 | seam class run | PASS |\n| 4. File: tests/test_retrospective_hook.py | reviewed class is in that file | file inspection | PASS |\n\n### Verdict\n- PASS\n- Confidence: .93\n\n### Action Taken\n- kanban\\kanban-md.exe edit 989 --status docs --release

[[2026-03-24]] Tue 13:35

## Review Evidence

PASS review rerun on 2026-03-24.

Pytest results:
TestFromAC_981_NonBlockingEligibilityHandoff: 12 passed, 2 warnings.
TestFromAC_RetrospectiveHookSupervisorSeam: 5 passed, 2 warnings.
tests/test_retrospective_hook.py: 55 passed, 2 warnings.
Isolated create_task path test: 1 passed, 2 warnings, no RuntimeWarning.

Ruff: All checks passed.
Coverage: src/owlbear/core/retrospective_hook.py at 96 percent in the scoped bare --cov run.

AC evidence:
AC1 class at line 1195.
AC2a tests at lines 1227, 1246, 1345, and 1368.
AC2b tests at lines 1267, 1292, 1395, and 1422.
AC2c tests at lines 1319 and 1450.
AC2d create_task parity covered by lines 1345, 1368, 1395, 1422, and 1450.
AC3 seam class at line 1070 still passes.
AC4 file is tests/test_retrospective_hook.py.

Additional evidence:
The retry test file was preserved after commit aeb0142; only src/owlbear/core/retrospective_hook.py changed afterward.
The only post-retry source commit was 1a1b61b fix: defer retrospective eligibility handoff (#988, builder).
Confidence .93.

[[2026-03-24]] Tue 13:53

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Runtime row already documents RetrospectiveHook background scheduling; eligibility deferral is internal |
| 2 | Docstrings | Yes | Pass | All modified/new methods in retrospective_hook.py have accurate docstrings:_LazyCoroutine, __call__, _uses_default_eligibility_helpers, _run_retrospective_if_eligible. No gaps. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used; retrospective hook attributed under Tasks 621 and 964 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | type:test task; no research phase |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/989-builder-cov.txt (deleted)

[[2026-03-24]] Tue 14:28

## Audit

AC1 PASS: class at line 1195.
AC2(a) PASS: tests at lines 1227, 1246, 1345, 1368.
AC2(b) PASS: tests at lines 1267, 1292, 1395, 1422.
AC2(c) PASS: tests at lines 1319, 1450.
AC2(d) PASS: tests at 1345, 1368, 1395, 1422, 1450.
AC3 PASS: seam tests 5 passed.
AC4 PASS: correct file.
Full suite: 4231 passed, 38 failed (none in test_retrospective_hook.py, 55 passed there).
One retrospective_hook failure in test_cancellation.py is pre-existing from #870 (6fa7c85).
ruff: clean.
Architect AC quality: 4.
Confidence: .96
Action: archive

[[2026-03-24]] Tue 14:29

## Commits

7a455a6 chore: archive task #989 (#989, auditor) - kanban/tasks/989-*.md
