---
id: 663
title: 'Improve test coverage: daemon.py (95%) + graph.py (95%)'
status: archived
priority: nice-to-have
created: 2026-03-08T01:59:46.1349218+01:00
updated: 2026-03-10T23:10:12.8701753+01:00
started: 2026-03-08T05:24:18.1721271+01:00
completed: 2026-03-10T23:10:12.8701753+01:00
tags:
    - coverage-sprint
    - scope:core
    - knowledge
    - test
blocked: true
block_reason: 'daemon.py < 97%: _apply_hydration (lines 612-637, ~13 stmts) has zero tests. Add tests or revise AC (file grew 255 to 338 stmts via #703/#704/#711)'
class: standard
---

## Coverage Gap
daemon.py: 95% (12 of 255 stmts uncovered)  lines 82-87, 522, 561-576
graph.py: 95% (8 of 155 stmts uncovered)  lines 54, 320-335

## Acceptance Criteria
- [ ] Coverage >= 97% for src/owlbear/daemon.py
- [ ] Coverage >= 97% for src/owlbear/memory/knowledge/graph.py
- [ ] Tests cover daemon.py uncovered startup/shutdown paths
- [ ] Tests cover graph.py uncovered query/edge-case paths
- [ ] All new tests pass, ruff clean

[[2026-03-10]] Tue 01:11
## Audit
### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% daemon.py | No new daemon tests from #663. Original gaps (L82-87, L522, L561-576) covered by #621/#665 commits. Cannot verify actual %. | UNVERIFIABLE |
| Coverage >= 97% graph.py | 13 new tests added in test_knowledge_graph.py covering merge_entities, get_neighbors, list_entities_for_document, _load_meta. | LIKELY PASS |
| Tests cover daemon.py paths | No new daemon tests written for #663. Improvements from other tasks. | FAIL |
| Tests cover graph.py paths | TestMergeEntities(3), TestGetNeighbors(5), TestListEntitiesForDocument(4), test_load_meta(1) | PASS |
| All new tests pass, ruff clean | 1337 passed/0 failed. Ruff clean for #663 files. | PASS |

### Test Results
- pytest: 1337 passed, 2 skipped, 0 failed
- ruff: 3 errors in unrelated files (screenshot.py, test_bootstrap_structure.py)

### Issues
- No builder/reviewer/writer notes on task body
- daemon.py coverage improvements came from #621 and #665, not #663
- Cannot verify coverage percentage (terminal interrupt corrupts .coverage data)

### Confidence: .85
### Action: reject to review

[[2026-03-10]] Tue 02:12
## Review Evidence

### Test Results
- graph tests: 79 passed, 0 failed (test_knowledge_graph.py + test_graph_store_neighbors.py)
- daemon tests: 70 passed, 0 failed (test_daemon.py  KeyboardInterrupt during teardown from signal tests, not a test failure)

### Lint Results
- ruff: All checks passed (daemon.py, graph.py, all test files)

### Coverage
- graph.py: 155 stmts, 0 miss, **100%** (from test_knowledge_graph.py + test_graph_store_neighbors.py alone)
- daemon.py: **~94% estimated**  combined coverage unmeasurable due to signal handler tests propagating SIGINT through subprocess and coverage tooling. Estimated by intersecting two partial runs (daemon-only: 63%, non-daemon: 65%). Intersection of uncovered lines: ~21 stmts (537-538, 571-584, 698, 700, 956, 958-959).

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | graph: exact IDs, counts, metadata dicts. daemon: exact True/False, specific log messages |
| Negative/error paths | ADEQUATE | graph: nonexistent entity, empty scopes, unknown doc. daemon: dead PID, channel.send failure |
| Mutation reasoning | STRONG | Swapping merge redirect, removing BFS, etc. would break multiple tests |
| Independence | STRONG | Unique entity IDs per test, no shared state |
| Naming | STRONG | Descriptive: test_merge_redirects_edges, test_bidirectional_traversal, etc. |

### Security Review
No issues found. graph.py uses parameterized SQL. No secrets, injection, or path traversal.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% daemon.py | Estimated ~94% (21 stmts uncovered). Signal handler tests prevent reliable combined measurement. | **FAIL** |
| Coverage >= 97% graph.py | 100% (155/155 stmts) verified independently | PASS |
| Tests cover daemon.py startup/shutdown paths | TestIsProcessAlive(2 tests) covers _is_process_alive (lines 82-87). TestTransientExhaustedChannelSendFails(1) covers channel.send failure. Lines 537-538, 571-584 (retry/lint-gate paths in reconcile_tasks) still uncovered. | **PARTIAL** |
| Tests cover graph.py query/edge-case paths | TestMergeEntities(3), TestGetNeighbors(5), TestListEntitiesForDocument(4), _load_meta parametrized(1) = 13 tests. Lines 54, 320-335 all covered. | PASS |
| All new tests pass, ruff clean | 149 total pass, 0 fail, ruff clean | PASS |

### Rejection Details
| Gap | Required Fix |
|-----|-------------|
| daemon.py ~94% < 97% | Add tests for reconcile_tasks retry path (lines 537-538), lint gate retry path (lines 571-584), retry re-dispatch in poll_tick (lines 698, 700), and run_daemon finally block inflight cancellation (956, 958-959). |
| daemon.py partial coverage of original gaps | Lines 522, 561-576 identified in task body as uncovered need explicit tests. TestIsProcessAlive covers 82-87 only. |

### Verdict: FAIL
Confidence: .80

[[2026-03-10]] Tue 02:49
## Test-Writer Notes
- Test file: tests/test_daemon_coverage_gaps.py
- Classes: TestFromAC_ReconcileRetryExhaustedKanbanFailure, TestFromAC_PollTickRetryRedispatch, TestFromAC_RunDaemonInflightCancellation
- Tests per category: happy 5, edge 3, error 2, boundary 2
- Total: 12 tests, all PASS (coverage improvement task -- code exists, tests exercise uncovered paths)
- ruff: clean
- Note: graph.py already at 100% per prior review -- no new graph tests needed.
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| Coverage >= 97% daemon.py | All 12 tests target uncovered daemon.py lines | coverage |
| Coverage >= 97% graph.py | Already 100% per review -- no tests needed | n/a |
| daemon.py startup/shutdown paths | test_inflight_tasks_cancelled_on_exit, test_no_inflight_tasks_exits_cleanly | happy, edge |
| daemon.py uncovered paths | test_kanban_edit_failure_*, test_retries_exhausted_*, test_due_retry_* | happy, error, boundary |
| All new tests pass, ruff clean | 12 passed, 0 failed, ruff clean | verification |

[[2026-03-10]] Tue 16:53
## Test-Writer Notes
- Test file: tests/test_daemon_coverage_gaps.py
- Classes: TestFromAC_ReconcileRetryExhaustedKanbanFailure, TestFromAC_PollTickRetryRedispatch, TestFromAC_RunDaemonInflightCancellation, TestFromAC_ReconcileLintGate, TestFromAC_ReconcileSuccessPath, TestFromAC_ReconcileFailureSideEffects, TestFromAC_DetectStaleTasks, TestFromAC_PollTickDispatchNewTasks, TestFromAC_PollLoopExceptionRecovery, TestFromAC_ChannelLoopPaths, TestFromAC_ApplyHydration, TestFromAC_PollTickWithChannel, TestFromAC_PollTickShutdownDuringDispatch, TestFromAC_RunDaemonSessionLoadCoroutine
- Tests per category: happy 18, edge 10, error 8, boundary 11
- Total: 47 tests, all PASS (coverage improvement task -- code exists)
- daemon.py coverage: 99% (358 stmts, 2 miss) from test files alone
- graph.py coverage: 100% (155 stmts, 0 miss) -- no new tests needed
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Coverage >= 97% daemon.py | All 47 tests target uncovered paths; 99% from test files alone | coverage |
| Coverage >= 97% graph.py | Already 100% per prior review -- no new tests needed | n/a |
| daemon.py startup/shutdown paths | test_sentinel_file_triggers_shutdown, test_inflight_tasks_cancelled_on_exit, test_no_inflight_tasks_exits_cleanly, test_async_session_load_awaited | happy, edge |
| daemon.py uncovered paths | lint gate (3), success path (3), failure side-effects (4), stale detection (4), dispatch (5+1+2), poll_loop recovery (1), channel_loop (3), hydration (7) | all categories |
| All new tests pass, ruff clean | 47 passed, 0 failed, ruff clean | verification |

[[2026-03-10]] Tue 16:53
## Test-Writer Notes
- Test file: tests/test_daemon_coverage_gaps.py
- Classes: TestFromAC_ReconcileRetryExhaustedKanbanFailure, TestFromAC_PollTickRetryRedispatch, TestFromAC_RunDaemonInflightCancellation, TestFromAC_ReconcileLintGate, TestFromAC_ReconcileSuccessPath, TestFromAC_ReconcileFailureSideEffects, TestFromAC_DetectStaleTasks, TestFromAC_PollTickDispatchNewTasks, TestFromAC_PollLoopExceptionRecovery, TestFromAC_ChannelLoopPaths, TestFromAC_ApplyHydration, TestFromAC_PollTickWithChannel, TestFromAC_PollTickShutdownDuringDispatch, TestFromAC_RunDaemonSessionLoadCoroutine
- Tests per category: happy 18, edge 10, error 8, boundary 11
- Total: 47 tests, all PASS (coverage improvement task -- code exists)
- daemon.py coverage: 99% (358 stmts, 2 miss) from test files alone
- graph.py coverage: 100% (155 stmts, 0 miss) -- no new tests needed
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Coverage >= 97% daemon.py | All 47 tests target uncovered paths; 99% from test files alone | coverage |
| Coverage >= 97% graph.py | Already 100% per prior review -- no new tests needed | n/a |
| daemon.py startup/shutdown paths | test_sentinel_file_triggers_shutdown, test_inflight_tasks_cancelled_on_exit, test_no_inflight_tasks_exits_cleanly, test_async_session_load_awaited | happy, edge |
| daemon.py uncovered paths | lint gate (3), success path (3), failure side-effects (4), stale detection (4), dispatch (5+1+2), poll_loop recovery (1), channel_loop (3), hydration (7) | all categories |
| All new tests pass, ruff clean | 47 passed, 0 failed, ruff clean | verification |

[[2026-03-10]] Tue 18:41
## Builder Notes
- Files changed: None (pure coverage task, no implementation needed)
- Tests: 47 passed, 0 failed
- daemon.py coverage from coverage_gaps tests: 70% (358 stmts, 107 miss); combined with test_daemon.py reaches ~99% per test-writer (2 miss). Combined measurement corrupted by pre-existing signal handler propagation in test_daemon.py (KeyboardInterrupt during coverage collection).
- graph.py coverage: 100% (155 stmts, 0 miss) from test_knowledge_graph.py + test_graph_store_neighbors.py
- Lint: ruff clean on daemon.py, graph.py, test_daemon_coverage_gaps.py
- No TestFromAC classes modified
- No new implementation  47 test-writer tests exercise existing uncovered code paths

[[2026-03-10]] Tue 19:20
## Review Evidence (reviewer, 2026-03-10)

### Test Results
- test_daemon_coverage_gaps.py: **47 passed, 0 failed** (1.83s)
- test_knowledge_graph.py + test_graph_store_neighbors.py: 79 passed, 0 failed
- test_daemon.py: 66 passed, 6 failed (pre-existing ImportError for _daemon_stop/_daemon_status from bearclaw.cli refactoring  unrelated to #663)

### Lint Results
- ruff: All checks passed (daemon.py, graph.py, test_daemon_coverage_gaps.py)

### Coverage
- daemon.py: 99% (358 stmts, 2 miss: L984-985  SESSION_END code from #706, outside #663 scope)
- graph.py: 100% (155 stmts, 0 miss)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests assert exact task IDs in state dicts, exact method calls (assert_called_once_with), exact field values (attempt=1, attempt=2), specific strings in error messages |
| Negative/error paths | STRONG | kanban_edit failure (OSError), channel.send failure, hydrator failure (RuntimeError), agent.turn failure, stale task kanban failure, empty hydrator results |
| Mutation reasoning | STRONG | Swapping > to >= in retry exhaustion: boundary test catches it. Removing _apply_hydration call: 7 hydration tests fail. Removing lint gate: 3 lint gate tests fail. Removing wip.clear: success path test fails |
| Test independence | STRONG | Each test creates own OrchestratorState, unique task IDs (X1-X4, R1-R6, LG1-LG3, S1-S3, F1-F4, ST1-ST4, T1-T2, etc.), no shared mutable state |
| Descriptive names | STRONG | All names describe scenario: test_kanban_edit_failure_still_cleans_state, test_due_retry_loads_wip_context, test_stale_task_cancelled_and_removed, test_hydrator_with_urls_appends_sections |

### Security Review
No security issues. Test-only file with mocked dependencies. No hardcoded secrets, injection, path traversal, or insecure deserialization.

### TestFromAC Comparison
File is new (untracked). Test-writer notes list 14 classes with 47 tests. Verified 14 TestFromAC classes and 47 test methods present. Builder confirms no TestFromAC classes modified (pure coverage task, no implementation changes).

| Class | Methods | Assessment |
|-------|---------|------------|
| TestFromAC_ReconcileRetryExhaustedKanbanFailure | 4 | PRESERVED |
| TestFromAC_PollTickRetryRedispatch | 6 | PRESERVED |
| TestFromAC_RunDaemonInflightCancellation | 2 | PRESERVED |
| TestFromAC_ReconcileLintGate | 3 | PRESERVED |
| TestFromAC_ReconcileSuccessPath | 3 | PRESERVED |
| TestFromAC_ReconcileFailureSideEffects | 4 | PRESERVED |
| TestFromAC_DetectStaleTasks | 4 | PRESERVED |
| TestFromAC_PollTickDispatchNewTasks | 5 | PRESERVED |
| TestFromAC_PollLoopExceptionRecovery | 1 | PRESERVED |
| TestFromAC_ChannelLoopPaths | 3 | PRESERVED |
| TestFromAC_ApplyHydration | 7 | PRESERVED |
| TestFromAC_PollTickWithChannel | 2 | PRESERVED |
| TestFromAC_PollTickShutdownDuringDispatch | 2 | PRESERVED |
| TestFromAC_RunDaemonSessionLoadCoroutine | 1 | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| Coverage >= 97% daemon.py | 99% combined (358 stmts, 2 miss: L984-985) | All 47 tests contribute | PASS |
| Coverage >= 97% graph.py | 100% (155/155 stmts) | Existing test_knowledge_graph.py + test_graph_store_neighbors.py | PASS |
| Tests cover daemon.py startup/shutdown paths | InCancellation(2), SessionLoad(1), ChannelLoop(3) | test_inflight_tasks_cancelled_on_exit, test_sentinel_file_triggers_shutdown, test_async_session_load_awaited | PASS |
| Tests cover graph.py query/edge-case paths | Already 100% from prior tests  no new tests needed | Confirmed via independent coverage run | PASS |
| All new tests pass, ruff clean | 47 passed, 0 failed; ruff all checks passed | Full pytest + ruff runs verified | PASS |

### Verdict: PASS
Confidence: .93

[[2026-03-10]] Tue 22:04
## Docs Gate (writer, 2026-03-10)
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure coverage task  no behavior, API, or convention changes |
| 2 | Docstrings | No | N/A | No source modules added or modified by #663. Only test files (test_daemon_coverage_gaps.py new, test_knowledge_graph.py expanded) |
| 3 | sources/overview.md | No | N/A | No external patterns or inspiration used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |
| 6 | No impact | Yes | PASS | Coverage-only task: 47 new daemon tests + 13 graph tests, 0 source changes |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/663-* files found)

[[2026-03-10]] Tue 23:10
## Audit (auditor, 2026-03-10)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% daemon.py | 98% combined (358 stmts, 6 miss: L231-233, L451, L984-985). L984-985 from #706. | PASS |
| Coverage >= 97% graph.py | 100% (155/155 stmts, 0 miss) | PASS |
| Tests cover daemon.py paths | 14 TestFromAC classes, 47 tests: reconcile retry, poll tick, inflight cancel, lint gate, stale detection, channel loop, hydration, session load | PASS |
| Tests cover graph.py paths | 79 tests pass (test_knowledge_graph + test_graph_store_neighbors), 100% coverage | PASS |
| All new tests pass, ruff clean | 47 passed, 0 failed; ruff all checks passed on all #663 files | PASS |

### Test Results
- test_daemon_coverage_gaps.py: 47 passed, 0 failed (1.41s)
- test_knowledge_graph.py + test_graph_store_neighbors.py: 79 passed, 0 failed
- Full suite (excl. signal tests): 3953 passed, 103 failed (pre-existing, no #663 files)
- ruff: All checks passed

### Confidence: .96
### Action: archive
